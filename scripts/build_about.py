"""Build the complete Bearblog paste-in page while preserving the introduction."""
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
site = ROOT / 'site'
soup = BeautifulSoup((site / 'about-me-original.html').read_text(), 'html.parser')
old_script = soup.select_one('script')
movie_script = old_script.get_text().split('  async function renderGithubGraph()')[0].strip()
old_script.decompose()
activity = soup.select_one('.activity')
activity.replace_with(BeautifulSoup((site / 'writing-activity.html').read_text(), 'html.parser'))
style = soup.select_one('style')
style.string = style.get_text() + '\n' + (site / 'writing-activity.css').read_text()
script = soup.new_tag('script')
script.string = '\n' + movie_script + '\n\n' + (site / 'writing-activity.js').read_text() + '\n'
soup.append(script)
snippet = str(soup) + '\n'
(site / 'about-me.html').write_text(snippet)
preview_style = '''
:root { color-scheme: light dark; --background-color: #fff; --text-color: #222; }
@media (prefers-color-scheme: dark) { :root { --background-color: #1d1f21; --text-color: #eee; } }
body { max-width: 680px; margin: 40px auto; padding: 0 20px; font: 16px/1.75 system-ui, sans-serif;
  background: var(--background-color); color: var(--text-color); overflow-wrap: break-word; }
a { color: inherit; } * { box-sizing: border-box; }
'''
(site / 'preview.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Me · 全部历史写作统计预览</title><style>' + preview_style + '</style></head><body>'
    + snippet + '</body></html>\n')
print('Built site/about-me.html and site/preview.html')
