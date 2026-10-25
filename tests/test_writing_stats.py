import unittest
from scripts.writing_stats import count_words, extract_post, parse_list, summarize


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


if __name__ == '__main__':
    unittest.main()
