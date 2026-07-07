const { test } = require('node:test');
const assert = require('node:assert');
const { buildFeedModel, readCache, writeCache, escapeHtml } = require('../assets/js/qlass-feed.js');

const NOW = new Date('2026-07-07T12:00:00Z');
const NOW_MS = NOW.getTime();

function fakeStorage() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v))
  };
}

test('buildFeedModel returns null for garbage input', () => {
  assert.strictEqual(buildFeedModel(null, NOW), null);
  assert.strictEqual(buildFeedModel('nope', NOW), null);
  assert.strictEqual(buildFeedModel({}, NOW), null);
});

test('buildFeedModel returns null when feed is empty', () => {
  assert.strictEqual(buildFeedModel({ announcements: [], upcoming: [] }, NOW), null);
});

test('buildFeedModel keeps 3 newest announcements, newest first', () => {
  const data = {
    announcements: [
      { title: 'a', postedAt: '2026-07-01T00:00:00Z' },
      { title: 'b', postedAt: '2026-07-04T00:00:00Z' },
      { title: 'c', postedAt: '2026-07-02T00:00:00Z' },
      { title: 'd', postedAt: '2026-07-03T00:00:00Z' },
      { notitle: true }
    ]
  };
  const model = buildFeedModel(data, NOW);
  assert.deepStrictEqual(model.announcements.map(a => a.title), ['b', 'd', 'c']);
});

test('buildFeedModel drops past-due items, sorts soonest first, caps at 5', () => {
  const mk = (t, d) => ({ title: t, dueAt: d });
  const data = {
    upcoming: [
      mk('past', '2026-07-01T00:00:00Z'),
      mk('f', '2026-07-14T00:00:00Z'),
      mk('a', '2026-07-08T00:00:00Z'),
      mk('e', '2026-07-13T00:00:00Z'),
      mk('c', '2026-07-10T00:00:00Z'),
      mk('b', '2026-07-09T00:00:00Z'),
      mk('d', '2026-07-12T00:00:00Z')
    ]
  };
  const model = buildFeedModel(data, NOW);
  assert.deepStrictEqual(model.upcoming.map(u => u.title), ['a', 'b', 'c', 'd', 'e']);
});

test('buildFeedModel carries the class name', () => {
  const model = buildFeedModel(
    { class: { name: 'AP Statistics' }, announcements: [{ title: 'hi', postedAt: '2026-07-06T00:00:00Z' }] },
    NOW
  );
  assert.strictEqual(model.className, 'AP Statistics');
});

test('cache roundtrips within TTL and expires after 5 minutes', () => {
  const s = fakeStorage();
  writeCache(s, 'ap-statistics', { announcements: [] }, NOW_MS);
  assert.deepStrictEqual(readCache(s, 'ap-statistics', NOW_MS + 4 * 60 * 1000), { announcements: [] });
  assert.strictEqual(readCache(s, 'ap-statistics', NOW_MS + 6 * 60 * 1000), null);
  assert.strictEqual(readCache(s, 'other-slug', NOW_MS), null);
});

test('readCache tolerates corrupt entries', () => {
  const s = fakeStorage();
  s.setItem('qlass-feed:ap-statistics', '{not json');
  assert.strictEqual(readCache(s, 'ap-statistics', NOW_MS), null);
});

test('escapeHtml neutralizes markup', () => {
  assert.strictEqual(escapeHtml('<script>"x" & \'y\'</script>'),
    '&lt;script&gt;&quot;x&quot; &amp; &#39;y&#39;&lt;/script&gt;');
});
