# 博客全历史写作统计

统计 https://blog.solazy.me/Daily/ 与 https://blog.solazy.me/Article/ 列表中的全部公开文章。
累计字数没有 365 天或起始年份限制。文章链接去重；分类统计允许重叠，累计只算一次。

## 文件

- scripts/writing_stats.py：读取完整列表及每篇正文，输出 writing-data/writing-stats.json。
- .github/workflows/writing-stats.yml：每日两次增量更新（全历史汇总），也支持 Actions 手动运行。
- site/about-me.html：可直接替换 Bearblog Me 页面正文的完整代码，含原介绍和观影统计。
- site/preview.html：独立预览页面。
- site/writing-activity.*：统计组件源文件。
- scripts/build_about.py：由原页面和组件生成完整替换代码及预览。

本仓库 sol-blog-data 仅保存博客自身的数据与页面接入代码。豆瓣数据与同步任务保留在 sol-douban-data，二者独立运行；Me 页面的观影数量仍从豆瓣仓库读取。
GitHub Actions 计划运行时间为 UTC 05:20、17:20，即北京时间 13:20、次日 01:20；实际启动可能延迟。

## 在 Bearblog 接入

打开 Me 页面的编辑器，以 site/about-me.html 的完整内容替换原正文并保存。
保留页面标题、slug、发布日期等元数据；此文件只包含正文 HTML/CSS/JS。
页面读取的公开 JSON 地址已经配置：

https://raw.githubusercontent.com/somkanel/sol-blog-data/main/writing-data/writing-stats.json

全历史累计与过去 365 天分别显示。热力图以北京时间确定今天，并使用博客显示的发布日期。
色深代表当天篇数（0、1、2、3、4+），点按、悬停或键盘聚焦显示当日篇数和字数。

## 手动运行

    python3 -m venv .venv
    .venv/bin/pip install -r requirements-writing.txt
    .venv/bin/python -m unittest discover -s tests -v
    .venv/bin/python scripts/writing_stats.py
    node tests/test_writing_activity.cjs
    .venv/bin/python scripts/build_about.py

正文包含段落、小标题、列表、表格、引用及行内代码。汉字每字计 1，其他语言单词、连续数字各计 1；
小数及用逗号分组的数字视为一个数字；英文词内部撇号不拆词，连字符拆词。
排除文章标题、发布日期、标签、站点导航、图片 alt 属性、脚本、交互控件、代码块及不可见属性元素。
可见的图片说明段落会统计。标点和空白不计；图片本身和图片内文字不做 OCR。
引用算入正文，所以这不是“原创字数”或“每天实际输入字数”的测量。

每次读取两个分类的完整目录，新文章、元数据变化的文章以及最近 7 天发表的文章重新读取正文；
另外按 checked_at 从旧到新轮流复查 60 篇旧文，其余沿用上次字数。汇总始终包含全部历史，删除和分类变化每次检查。
目前约 692 篇，每天两次成功运行，旧文约一周轮查一遍；旧文正文修改可能延迟到轮查时体现，失败和任务延迟会延长周期。
Actions 手动运行可勾选 full 立即全量复核；本地使用 --full。计数规则版本不匹配时自动全量重算。
只有本轮所需正文全部读取、校验成功才发布，否则保留上次完整 JSON。checked_at 表示该篇正文上次成功复查时间。
使用博客展示的发布日期（支持 ISO 或英文日期），不按文章 slug 猜日期。
输出含全历史总数、分类总数、按日期汇总及每篇文章的链接、日期、字数、正文摘要哈希（不存正文）。

任何一篇抓取失败、正文结构异常或列表为空时，脚本失败退出，不覆盖上次成功的 JSON。
图片为主且文字为空的有效文章允许记 0 字。异常减少超过 5%（至少超过 3 篇）会暂停发布，需检查列表。
前端验证统计文件的全历史标识和汇总一致性，加载失败显示提示，不显示假 0；超过 48 小时未更新也会注明。

首次抓取中断后，可用 --resume 复用 .cache/writing-stats 下的已下载 HTML。
正常定时任务不使用 --resume；轮查和 --full 必须读取实时正文。公开统计文件不包含缓存的原始 HTML。
