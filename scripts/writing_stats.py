#!/usr/bin/env python3
"""Count all public Daily/Article bodies. Publish only after a complete scan."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
import regex
import requests

BASE = 'https://blog.solazy.me/'
SOURCES = {'daily': urljoin(BASE, 'Daily/'), 'article': urljoin(BASE, 'Article/')}
RULE = ('汉字每字计1，其他语言单词及连续数字各计1；包含正文小标题、列表、表格、'
        '引用和行内代码；不含文章标题、日期、标签、导航、图片说明属性、代码块、标点和空白。')
HAN = regex.compile(r'\p{Script=Han}')
WORDS = regex.compile(r"\p{L}[\p{L}\p{M}]*(?:['’]\p{L}[\p{L}\p{M}]*)*|\p{N}+(?:[.,]\p{N}+)*")


def count_words(text):
    return len(HAN.findall(text)) + len(WORDS.findall(HAN.sub(' ', text)))


def displayed_day(element):
    value = element.get_text(strip=True)
    for pattern in ('%Y-%m-%d', '%d %b, %Y', '%d %B, %Y'):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError('Unrecognized displayed publication date: ' + value)


def normalize_url(value, base=BASE):
    parts = urlsplit(urljoin(base, value))
    if parts.scheme != 'https' or parts.netloc.lower() != urlsplit(BASE).netloc:
        raise ValueError('Unexpected off-site article URL: ' + value)
    return urlunsplit(('https', parts.netloc.lower(), parts.path.rstrip('/') + '/', '', ''))


class Fetcher:
    def __init__(self, cache_dir, resume=False, interval=0.35):
        self.cache_dir = cache_dir
        self.resume = resume
        self.interval = interval
        self.lock = threading.Lock()
        self.next_request = 0.0
        self.sessions = threading.local()

    def get(self, url, allow_cache=True):
        cache = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + '.html')
        if self.resume and allow_cache and cache.exists():
            return cache.read_text(encoding='utf-8')
        if not hasattr(self.sessions, 'session'):
            self.sessions.session = requests.Session()
        for attempt in range(4):
            with self.lock:
                wait = max(0, self.next_request - time.monotonic())
                if wait:
                    time.sleep(wait)
                self.next_request = time.monotonic() + self.interval
            try:
                response = self.sessions.session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; SolazyWritingStats/1.0)',
                    'Accept': 'text/html',
                    'Cache-Control': 'no-cache',
                }, timeout=45)
                response.raise_for_status()
                normalize_url(response.url)
                response.encoding = 'utf-8'
                html = response.text
                if not BeautifulSoup(html, 'html.parser').select_one('main'):
                    raise ValueError('No main element: ' + url)
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(html, encoding='utf-8')
                return html
            except (requests.RequestException, ValueError):
                if attempt == 3:
                    raise
                delay = min(30, 2 ** (attempt + 1))
                if 'response' in locals() and response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', '')
                    if retry_after.isdigit():
                        delay = min(120, max(delay, int(retry_after)))
                time.sleep(delay)


def parse_list(html, page_url, tag):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select('main ul.blog-posts li')
    if not rows:
        raise ValueError('No article list found: ' + page_url)
    posts = []
    for row in rows:
        link, published = row.select_one('a[href]'), row.select_one('time')
        if not link or not published:
            raise ValueError('Article row has no link/date: ' + page_url)
        tags = set(regex.split(r'[,\s]+', row.get('data-tags', '').lower()))
        if tag not in tags:
            raise ValueError('Unexpected tag in article list: ' + page_url)
        day = displayed_day(published)  # Editorial date, not viewer timezone.
        posts.append({'url': normalize_url(link['href'], page_url),
                      'title': link.get_text(' ', strip=True), 'date': day, 'tags': [tag]})
    next_links = soup.select('a[rel~=next], .pagination a, a.next')
    next_urls = set()
    for link in next_links:
        if not link.get('href'):
            continue
        href = urljoin(page_url, link['href'])
        normalize_url(href)
        next_urls.add(href)  # Preserve query strings used by pagination.
    return posts, sorted(next_urls)


def extract_post(html, listed):
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.select_one('main')
    canonical = soup.select_one('link[rel=canonical]')
    heading = main.select_one('h1') if main else None
    published = main.select_one('time') if main else None
    if not main or not heading or not published or not canonical:
        raise ValueError('Missing article structure: ' + listed['url'])
    url = normalize_url(canonical.get('href', ''))
    if url != listed['url']:
        raise ValueError('Canonical URL mismatch: ' + listed['url'] + ' -> ' + url)
    day = displayed_day(published)
    if day != listed['date']:
        raise ValueError('List/body date mismatch: ' + url)
    actual_tags = {a.get_text(strip=True).lstrip('#').lower() for a in main.select('.tags a')}
    if not set(listed['tags']).issubset(actual_tags):
        raise ValueError('List/body tags mismatch: ' + url)
    # Bear puts post controls and optional related content after the tag block.
    tags = main.select_one('.tags')
    if not tags:
        raise ValueError('No article end marker: ' + url)
    for following in list(tags.next_siblings):
        following.extract()
    tags.decompose()
    heading.decompose()
    date_paragraph = published.find_parent('p')
    (date_paragraph or published).decompose()
    has_media = bool(main.select_one('img, picture, video, audio'))
    for node in main.select('script, style, noscript, template, form, nav, footer, header, '
                            'button, input, textarea, select, svg, pre, iframe, '
                            'audio, video, [hidden], [aria-hidden="true"]'):
        node.decompose()
    # Text joins without adding spaces between inline elements (中<strong>文</strong>).
    for node in main.select('p, div, section, article, li, blockquote, h1, h2, h3, h4, h5, h6, '
                            'tr, td, th, dt, dd, br, hr'):
        node.insert_before('\n')
        node.insert_after('\n')
    text = main.get_text()
    text = regex.sub(r'\s+', ' ', text).strip()
    words = count_words(text)
    if words == 0 and not has_media:
        raise ValueError('Empty article body: ' + url)
    return {**listed, 'url': url, 'words': words,
            'body_sha256': hashlib.sha256(text.encode()).hexdigest()}


def summarize(posts):
    posts = sorted(posts, key=lambda p: (p['date'], p['url']))
    by_date = {}
    for post in posts:
        day = by_date.setdefault(post['date'], {'posts': 0, 'words': 0})
        day['posts'] += 1
        day['words'] += post['words']
    return {'schema_version': 1, 'complete': True,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'scope': {'period': 'all-time', 'tags': list(SOURCES), 'sources': SOURCES,
                      'date_basis': 'publication date displayed by blog'},
            'counting': {'version': 1, 'description': RULE},
            'totals': {'posts': len(posts), 'words': sum(p['words'] for p in posts),
                       'active_days': len(by_date), 'first_date': posts[0]['date'],
                       'last_date': posts[-1]['date']},
            'by_tag': {tag: {'posts': sum(tag in p['tags'] for p in posts),
                            'words': sum(p['words'] for p in posts if tag in p['tags'])}
                       for tag in SOURCES},
            'by_date': by_date, 'posts': posts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('writing-data/writing-stats.json'))
    parser.add_argument('--cache-dir', type=Path, default=Path('.cache/writing-stats'))
    parser.add_argument('--resume', action='store_true', help='Reuse downloaded HTML only for an interrupted first scan')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('--workers must be between 1 and 8')
    fetch = Fetcher(args.cache_dir, resume=args.resume)
    articles = {}
    for tag, source in SOURCES.items():
        queue, seen = [source], set()
        while queue:
            page_url = queue.pop(0)
            if page_url in seen:
                continue
            if len(seen) >= 100:
                raise ValueError('Pagination limit reached; refusing incomplete publication')
            seen.add(page_url)
            rows, next_pages = parse_list(fetch.get(page_url, allow_cache=False), page_url, tag)
            for row in rows:
                old = articles.get(row['url'])
                if old:
                    if old['date'] != row['date']:
                        raise ValueError('Conflicting dates: ' + row['url'])
                    old['tags'] = sorted(set(old['tags'] + row['tags']))
                else:
                    articles[row['url']] = row
            queue.extend(p for p in next_pages if p not in seen)
        print(f'{tag}: {sum(tag in p["tags"] for p in articles.values())} articles', flush=True)
    previous = json.loads(args.output.read_text()) if args.output.exists() else None
    if previous:
        # An unexpected drop could be a truncated list. Preserve published data for review.
        removed = {p['url'] for p in previous['posts']} - set(articles)
        if len(removed) > max(3, len(previous['posts']) * 0.05):
            raise ValueError(f'Unexpected removal of {len(removed)} posts; output unchanged')
    posts, errors = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(lambda p: extract_post(fetch.get(p['url']), p), row): row
                   for row in articles.values()}
        for future in as_completed(futures):
            row = futures[future]
            try:
                posts.append(future.result())
            except Exception as error:
                errors.append({'url': row['url'], 'error': str(error)})
                print(f'ERROR {row["url"]}: {error}', flush=True)
            if (len(posts) + len(errors)) % 25 == 0:
                print(f'Scanned {len(posts) + len(errors)}/{len(articles)}; errors={len(errors)}', flush=True)
    if errors:
        error_path = args.output.with_suffix('.errors.json')
        error_path.parent.mkdir(parents=True, exist_ok=True)
        error_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2) + '\n')
        raise SystemExit(f'{len(errors)} articles failed; published output unchanged. See {error_path}')
    result = summarize(posts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(args.output)
    args.output.with_suffix('.errors.json').unlink(missing_ok=True)
    print(json.dumps(result['totals'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
