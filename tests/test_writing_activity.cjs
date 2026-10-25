const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('site/writing-activity.js', 'utf8');
const RealDate = Date;
class FixedDate extends Date {
  constructor(...args) { super(...(args.length ? args : ['2026-10-25T12:00:00Z'])); }
  static now() { return new RealDate('2026-10-25T12:00:00Z').getTime(); }
}
function node() {
  return { textContent: '', children: [], attrs: {}, listeners: {}, scrollWidth: 800,
    appendChild(child) { this.children.push(child); },
    replaceChildren(fragment) { this.children = fragment.children; },
    setAttribute(key, value) { this.attrs[key] = value; },
    addEventListener(key, callback) { this.listeners[key] = callback; },
  };
}
const data = {
  schema_version: 1, complete: true, scope: { period: 'all-time' },
  generated_at: '2026-10-25T10:00:00Z',
  totals: { words: 1079, posts: 3, first_date: '2019-05-14', last_date: '2026-10-25' },
  by_tag: { daily: { words: 956, posts: 2 }, article: { words: 123, posts: 1 } },
  by_date: { '2019-05-14': { words: 123, posts: 1 },
    '2025-10-25': { words: 500, posts: 1 }, '2026-10-25': { words: 456, posts: 1 } },
};
async function run(payload, status = 200) {
  const elements = {};
  vm.runInNewContext(source, {
    document: { getElementById: id => elements[id] ||= node(),
      createElement: node, createDocumentFragment: node },
    Date: FixedDate, Intl, AbortController, setTimeout, clearTimeout,
    console: { error() {} }, requestAnimationFrame: callback => callback(),
    fetch: async () => ({ ok: status === 200, status, json: async () => payload }),
  });
  await new Promise(resolve => setImmediate(resolve));
  return elements;
}
(async () => {
  const elements = await run(data);
  assert.equal(elements['writing-total-words'].textContent, '1,079');
  assert.match(elements['post-stats'].textContent, /更新 1 天，发布 1 篇，共 456 字/);
  const cells = elements.heatmap.children.filter(cell => cell.type === 'button');
  assert.equal(cells.length, 365);
  assert.match(cells[0].title, /^2025-10-26/);
  assert.match(cells.at(-1).title, /^2026-10-25/);
  cells.at(-1).listeners.click();
  assert.match(elements['heatmap-detail'].textContent, /456 字/);
  const failed = await run(data, 404);
  assert.match(failed['writing-status'].textContent, /暂时未加载/);
  assert.equal(failed['writing-total-words'], undefined);
  const incomplete = await run({ ...data, complete: false });
  assert.match(incomplete['writing-status'].textContent, /暂时未加载/);
  const mismatch = await run({ ...data, totals: { ...data.totals, words: 1 } });
  assert.match(mismatch['writing-status'].textContent, /暂时未加载/);
  console.log('PASS: all-time totals, exact 365-day range, mobile tap, network errors and invalid data');
})();
