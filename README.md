# Sol 的博客数据

专门服务于 [blog.solazy.me](https://blog.solazy.me/) 的数据与自动化。
当前包含 Daily、Article 全部历史文章的正文统计，以及 Me 页面的接入代码。

## 更新机制

GitHub Actions 每天北京时间 01:20、13:20 各运行一次，也可手动触发。
修改抓取脚本、依赖或工作流时同样触发验证与完整重算。计划任务实际启动可能延迟。

每次读取两个分类的完整文章列表，按链接去重，重新读取全部正文并计算字数。
历史文章的修改、删除和分类调整也会反映在下一次成功统计中。
全部文章读取、校验成功后，才提交新的 writing-data/writing-stats.json；失败保留上次完整结果。
Me 页面只读取这份 JSON，不在访客浏览器里逐篇抓取文章。

## 与豆瓣数据的边界

- 本仓库：博客自身的字数、篇数、发布日期统计及相关页面代码。
- [sol-douban-data](https://github.com/somkanel/sol-douban-data)：豆瓣观影记录与同步任务，供博客等不同用途消费。

两个仓库的定时任务、数据文件和发布相互独立。博客展示观影数量时仍读取豆瓣仓库的 movie.json。

完整说明见 [WRITING-STATS.md](WRITING-STATS.md)。

- [统计 JSON](writing-data/writing-stats.json)
- [Me 页面完整替换代码](site/about-me.html)
- [更新任务](https://github.com/somkanel/sol-blog-data/actions/workflows/writing-stats.yml)
