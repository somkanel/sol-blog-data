(() => {
  'use strict';
  const DATA_URL = 'https://raw.githubusercontent.com/somkanel/sol-blog-data/main/writing-data/writing-stats.json';
  const DAY = 86400000;
  const number = new Intl.NumberFormat('zh-CN');
  const format = value => number.format(value);
  const byId = id => document.getElementById(id);
  const isCount = value => Number.isSafeInteger(value) && value >= 0;
  const isDay = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(value + 'T00:00:00Z'))
    && new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value;

  function validate(data) {
    if (data.schema_version !== 1 || data.complete !== true || data.scope?.period !== 'all-time'
      || !isCount(data.totals?.words) || !isCount(data.totals?.posts) || !data.by_date
      || !isDay(data.totals.first_date) || !isDay(data.totals.last_date)
      || !Number.isFinite(Date.parse(data.generated_at))) throw new Error('Invalid statistics');
    let posts = 0, words = 0;
    for (const [day, entry] of Object.entries(data.by_date)) {
      if (!isDay(day) || !isCount(entry.posts) || !isCount(entry.words)) throw new Error('Invalid daily statistics');
      posts += entry.posts;
      words += entry.words;
    }
    if (words !== data.totals.words || posts !== data.totals.posts) throw new Error('Statistics totals mismatch');
    for (const tag of ['daily', 'article']) {
      if (!isCount(data.by_tag?.[tag]?.words) || !isCount(data.by_tag?.[tag]?.posts)) throw new Error('Invalid tag statistics');
    }
  }

  function render(data) {
    validate(data);
    byId('writing-total-words').textContent = format(data.totals.words);
    byId('writing-total-posts').textContent = format(data.totals.posts);
    byId('writing-range').textContent = '全部历史 · ' + data.totals.first_date + ' 至 ' + data.totals.last_date;
    byId('writing-breakdown').textContent = '日更 ' + format(data.by_tag.daily.posts) + ' 篇 / '
      + format(data.by_tag.daily.words) + ' 字；长文 ' + format(data.by_tag.article.posts) + ' 篇 / '
      + format(data.by_tag.article.words) + ' 字。跨分类文章在累计总数中只计算一次。';
    const updated = new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).format(new Date(data.generated_at));
    const stale = Date.now() - Date.parse(data.generated_at) > 48 * 60 * 60 * 1000;
    byId('writing-status').textContent = '统计更新于 ' + updated + '（北京时间）'
      + (stale ? ' · 数据已超过两天未更新' : '');

    const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai',
      year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const part = type => parts.find(item => item.type === type).value;
    const today = Date.parse(part('year') + '-' + part('month') + '-' + part('day') + 'T00:00:00Z');
    const first = today - 364 * DAY;
    const start = first - new Date(first).getUTCDay() * DAY;
    let activeDays = 0, yearPosts = 0, yearWords = 0;
    const fragment = document.createDocumentFragment();
    const describe = (key, entry) => key + '：' + (entry.posts
      ? '发布 ' + format(entry.posts) + ' 篇，共 ' + format(entry.words) + ' 字'
      : '未发布文章');
    const select = (key, entry) => { byId('heatmap-detail').textContent = describe(key, entry); };
    let latest = null;
    for (let timestamp = start; timestamp <= today; timestamp += DAY) {
      if (timestamp < first) {
        const padding = document.createElement('span');
        padding.className = 'cube cube-padding';
        padding.setAttribute('aria-hidden', 'true');
        fragment.appendChild(padding);
        continue;
      }
      const key = new Date(timestamp).toISOString().slice(0, 10);
      const entry = data.by_date[key] || { posts: 0, words: 0 };
      if (entry.posts > 0) { activeDays += 1; latest = [key, entry]; }
      yearPosts += entry.posts;
      yearWords += entry.words;
      const cube = document.createElement('button');
      cube.type = 'button';
      const level = entry.posts === 0 ? 0 : Math.min(entry.posts, 4);
      cube.className = 'cube level-' + level;
      cube.title = describe(key, entry);
      cube.setAttribute('aria-label', cube.title);
      cube.addEventListener('click', () => select(key, entry));
      cube.addEventListener('focus', () => select(key, entry));
      cube.addEventListener('mouseenter', () => select(key, entry));
      fragment.appendChild(cube);
    }
    byId('post-stats').textContent = '过去 365 天更新 ' + format(activeDays) + ' 天，发布 '
      + format(yearPosts) + ' 篇，共 ' + format(yearWords) + ' 字';
    byId('heatmap').replaceChildren(fragment);
    byId('heatmap').setAttribute('aria-label', '过去 365 天博客更新记录，可点按日期查看篇数和字数');
    if (latest) select(...latest);
    else byId('heatmap-detail').textContent = '过去 365 天暂无文章发布。';
    requestAnimationFrame(() => {
      const scroller = byId('heatmap-scroll-container');
      scroller.scrollLeft = scroller.scrollWidth;
    });
  }

  async function load() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 25000);
    try {
      const response = await fetch(DATA_URL, { signal: controller.signal, cache: 'no-cache' });
      if (!response.ok) throw new Error('Writing statistics HTTP ' + response.status);
      render(await response.json());
    } catch (error) {
      console.error('Writing statistics loading failed:', error);
      byId('writing-status').textContent = '写作统计暂时未加载，请稍后刷新。';
      byId('post-stats').textContent = '更新记录暂时未加载。';
      byId('heatmap-detail').textContent = '';
    } finally {
      clearTimeout(timer);
    }
  }
  load();
})();
