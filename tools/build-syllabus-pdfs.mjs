#!/usr/bin/env node
// Renders each <slug>/syllabus.html to <slug>/syllabus.pdf using headless
// Chrome. Serves the repo over http first so absolute asset paths (/assets/…)
// and the Google Fonts stylesheet resolve exactly as they do in production.
//   node tools/build-syllabus-pdfs.mjs
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const run = promisify(execFile);
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'calendar', 'syllabi.json'), 'utf8'));

// Optional slug filter: node tools/build-syllabus-pdfs.mjs ap-statistics ap-statistics-virtual
const only = process.argv.slice(2);

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
if (!fs.existsSync(CHROME)) {
  console.error('ERROR: Google Chrome not found at ' + CHROME);
  process.exit(1);
}

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.woff2': 'font/woff2', '.pdf': 'application/pdf'
};

const PORT = 8931;
const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = path.join(root, rel);
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404); res.end('not found'); return;
  }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  res.end(fs.readFileSync(file));
});

await new Promise(r => server.listen(PORT, '127.0.0.1', r));

let ok = 0, failed = false;
const profile = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'syl-chrome-'));
try {
  for (const c of data.courses) {
    if (only.length && !only.includes(c.slug)) continue;
    const src = path.join(root, c.slug, 'syllabus.html');
    const out = path.join(root, c.slug, 'syllabus.pdf');
    if (!fs.existsSync(src)) { console.error(`ERROR: missing ${c.slug}/syllabus.html`); failed = true; continue; }
    try {
      await run(CHROME, [
        '--headless', '--disable-gpu', '--no-sandbox',
        `--user-data-dir=${profile}`,
        '--no-pdf-header-footer',
        '--virtual-time-budget=12000',
        `--print-to-pdf=${out}`,
        `http://127.0.0.1:${PORT}/${c.slug}/syllabus.html`
      ], { timeout: 90000 });
      const kb = (fs.statSync(out).size / 1024).toFixed(0);
      console.log(`wrote ${c.slug}/syllabus.pdf (${kb} KB)`);
      ok++;
    } catch (e) {
      console.error(`ERROR: ${c.slug}: ${e.message.split('\n')[0]}`);
      failed = true;
    }
  }
} finally {
  server.close();
  fs.rmSync(profile, { recursive: true, force: true });
}

console.log(`\n${ok}/${only.length || data.courses.length} PDFs built`);
if (failed) process.exit(1);
