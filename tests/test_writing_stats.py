import unittest
from datetime import datetime, timezone
from scripts.writing_stats import count_words, extract_post, parse_list, summarize, plan_scan


class WritingStatisticsTests(unittest.TestCase):
    def test_chinese_english_numbers_and_punctuation(self):
        self.assertEqual(count_words('今天使用 Bearblog 写了 100 字。'), 9)
        self.assertEqual(count_words('你好，世界！'), 4)
        self.assertEqual(count_words("Céline don't 3.14"), 3)

    def test_extract_only_body_preserves_inline_words(self):
        listed = {'url': 'https://blog.solazy.me/test/', 'title': '标题',
                  'date': '2019-05-14', 'tags': ['article']}
        html = '''<link rel="canonical" href="/test/">
        <header>导航</header><main><h1>标题</h1>
        <p><time>14 May, 2019</time></p><p>中<strong>文</strong> hello <a href="/x">world</a></p>
        <h2>小标题</h2><blockquote>引用</blockquote><pre>exclude code</pre>
        <img alt="图片描述" src="/x"><script>exclude script</script>
        <p class="tags"><a>#article</a></p><p>相关文章</p><form>点赞</form></main>
        <footer>页脚</footer>'''
        self.assertEqual(extract_post(html, listed)['words'], 9)

    def test_missing_end_marker_fails_instead_of_publishing_bad_count(self):
        with self.assertRaises(ValueError):
            extract_post('<main>invalid</main>', {'url': 'https://blog.solazy.me/test/'})

    def test_list_reads_one_date_per_post_not_url(self):
        html = '''<main><ul class="blog-posts"><li data-tags="daily article">
        <time datetime="2025-01-01T14:00Z">2025-01-01</time>
        <a href="/2025-01-01/">包含日期2025-01-01</a></li></ul></main>'''
        rows, _ = parse_list(html, 'https://blog.solazy.me/Daily/', 'daily')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['date'], '2025-01-01')

    def test_all_history_and_overlapping_tags(self):
        posts = [{'url': 'https://blog.solazy.me/old/', 'date': '2019-05-14',
                  'tags': ['daily', 'article'], 'words': 123},
                 {'url': 'https://blog.solazy.me/new/', 'date': '2026-10-25',
                  'tags': ['daily'], 'words': 456}]
        stats = summarize(posts)
        self.assertEqual(stats['totals']['words'], 579)
        self.assertEqual(stats['totals']['posts'], 2)
        self.assertEqual(stats['by_tag']['daily']['words'], 579)
        self.assertEqual(stats['by_tag']['article']['words'], 123)
        self.assertEqual(stats['totals']['first_date'], '2019-05-14')


class IncrementalTests(unittest.TestCase):
    def fixture(self):
        posts = [{'url': f'https://blog.solazy.me/p{i}/', 'title': str(i),
                  'date': '2019-05-14', 'tags': ['daily'], 'words': i,
                  'body_sha256': 'a' * 64} for i in range(150)]
        return {p['url']: {k: p[k] for k in ('url', 'title', 'date', 'tags')} for p in posts}, summarize(posts)

    def test_rotation_preserves_full_history_and_reaches_every_post(self):
        rows, previous = self.fixture()
        seen = set()
        for day in range(1, 4):
            now = datetime(2026, 10, day, tzinfo=timezone.utc)
            scan, reused = plan_scan(rows, previous, now)
            self.assertEqual(len(scan), 60)
            seen.update(p['url'] for p in scan)
            old = {p['url']: p for p in previous['posts']}
            previous = summarize(reused + [{**old[p['url']], 'checked_at': now.isoformat()} for p in scan])
            self.assertEqual(previous['totals']['words'], sum(range(150)))
        self.assertEqual(seen, set(rows))

    def test_new_recent_changed_removed_and_force_full(self):
        rows, previous = self.fixture()
        deleted = next(iter(rows)); del rows[deleted]
        keys = list(rows)
        rows[keys[-1]]['date'] = '2026-10-25'
        rows[keys[-2]]['tags'] = ['daily', 'article']
        rows[keys[-3]]['title'] = 'edited'
        rows['https://blog.solazy.me/new/'] = {'url': 'https://blog.solazy.me/new/', 'title': 'new', 'date': '2019-05-14', 'tags': ['article']}
        now = datetime(2026, 10, 26, tzinfo=timezone.utc)
        scan, reused = plan_scan(rows, previous, now)
        selected = {p['url'] for p in scan}
        self.assertTrue(set(keys[-3:]).issubset(selected))
        self.assertIn('https://blog.solazy.me/new/', selected)
        self.assertNotIn(deleted, selected | {p['url'] for p in reused})
        self.assertEqual(len(scan) + len(reused), len(rows))
        self.assertEqual(plan_scan(rows, previous, now, full=True), (list(rows.values()), []))
        previous['counting']['version'] = 0
        self.assertEqual(plan_scan(rows, previous, now)[1], [])


if __name__ == '__main__':
    unittest.main()
