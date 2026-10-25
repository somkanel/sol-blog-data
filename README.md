# Sol 的博客数据

专门服务于 [blog.solazy.me](https://blog.solazy.me/) 的数据与自动化。
当前包含 Daily、Article 全部历史文章的正文统计，以及 Me 页面的接入代码。

## 更新机制

GitHub Actions 每天北京时间 01:20、13:20 各运行一次，也可手动触发。
修改抓取脚本、依赖或工作流时同样触发验证与更新。计划任务实际启动可能延迟。

每次读取两个分类的完整目录，新文章、元数据变化的文章以及最近 7 天发表的文章重新读取正文；
另外按 checked_at 从旧到新轮流复查 60 篇旧文，其余沿用上次字数。汇总始终包含全部历史，删除和分类变化每次检查。
目前约 692 篇，每天两次成功运行，旧文约一周轮查一遍；旧文正文修改可能延迟到轮查时体现，失败和任务延迟会延长周期。
Actions 手动运行可勾选 full 立即全量复核；本地使用 --full。计数规则版本不匹配时自动全量重算。
只有本轮所需正文全部读取、校验成功才发布，否则保留上次完整 JSON。checked_at 表示该篇正文上次成功复查时间。
Me 页面只读取这份 JSON，不在访客浏览器里逐篇抓取文章。

## 与豆瓣数据的边界

- 本仓库：博客自身的字数、篇数、发布日期统计及相关页面代码。
- [sol-douban-data](https://github.com/somkanel/sol-douban-data)：豆瓣观影记录与同步任务，供博客等不同用途消费。

两个仓库的定时任务、数据文件和发布相互独立。博客展示观影数量时仍读取豆瓣仓库的 movie.json。

完整说明见 [WRITING-STATS.md](WRITING-STATS.md)。

- [统计 JSON](writing-data/writing-stats.json)
- [Me 页面完整替换代码](site/about-me.html)
- [更新任务](https://github.com/somkanel/sol-blog-data/actions/workflows/writing-stats.yml)
