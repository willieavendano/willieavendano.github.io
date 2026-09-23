// Regression guard: the school's student Chrome policy blocks third-party
// script execution, so every <script> and stylesheet must be same-origin
// (Google Fonts excepted — it degrades to a system font). Also checks that
// every local /assets/vendor/... reference actually exists.
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const ALLOWED_HOSTS = new Set(['fonts.googleapis.com', 'fonts.gstatic.com']);

// Only tracked files are deployed (Vercel builds from git); gitignored
// reference projects under computer-science-math/ are excluded this way.
const files = require('node:child_process')
  .execSync('git ls-files -z -- "*.html"', { cwd: ROOT })
  .toString().split('\0').filter(Boolean).map(f => path.join(ROOT, f));

const tagRe = /<(script|link)\b[^>]*?\b(?:src|href)\s*=\s*"([^"]+)"[^>]*>/gi;

test('no HTML page loads scripts or stylesheets from a third-party host', () => {
  const bad = [];
  for (const f of files) {
    const html = fs.readFileSync(f, 'utf8');
    let m;
    while ((m = tagRe.exec(html))) {
      const [tag, kind, url] = m;
      if (kind.toLowerCase() === 'link' && !/rel\s*=\s*"(stylesheet|preload|modulepreload)"/i.test(tag)) continue;
      const host = (url.match(/^(?:https?:)?\/\/([^/"]+)/) || [])[1];
      if (host && !ALLOWED_HOSTS.has(host)) bad.push(path.relative(ROOT, f) + ' -> ' + url);
    }
  }
  assert.deepStrictEqual(bad, [], 'third-party script/css references:\n' + bad.join('\n'));
});

test('every /assets/vendor reference points at a file that exists', () => {
  const missing = new Set();
  for (const f of files) {
    const html = fs.readFileSync(f, 'utf8');
    for (const m of html.matchAll(/["'](\/assets\/vendor\/[^"'?#]+)["']/g)) {
      if (!fs.existsSync(path.join(ROOT, m[1]))) missing.add(m[1]);
    }
  }
  assert.deepStrictEqual([...missing], []);
});

test('reveal math decks point KaTeX at the local vendor copy', () => {
  const bad = files.filter(f => {
    const html = fs.readFileSync(f, 'utf8');
    return html.includes('RevealMath.KaTeX') && !html.includes("katex: { local: '/assets/vendor/katex' }");
  }).map(f => path.relative(ROOT, f));
  assert.deepStrictEqual(bad, []);
});
