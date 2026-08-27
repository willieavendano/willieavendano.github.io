#!/usr/bin/env node
// Renders any repo-relative HTML page to PDF using headless Chrome, the same
// way tools/build-syllabus-pdfs.mjs does for syllabi. Serves the repo over
// http first so absolute asset paths (/assets/…) and Google Fonts resolve.
//   node tools/build-handout-pdf.mjs <repo-relative.html> <output.pdf> [more pairs…]
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const args = process.argv.slice(2);
if (args.length < 2 || args.length % 2 !== 0) {
  console.error('usage: node tools/build-handout-pdf.mjs <repo-relative.html> <output.pdf> [more pairs…]');
  process.exit(1);
}

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

const PORT = 8933;
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

let failed = false;
const profile = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'handout-chrome-'));
try {
  for (let i = 0; i < args.length; i += 2) {
    const rel = args[i].replace(/^\/+/, '');
    const out = path.resolve(args[i + 1]);
    if (!fs.existsSync(path.join(root, rel))) {
      console.error(`ERROR: missing ${rel}`); failed = true; continue;
    }
    try {
      await run(CHROME, [
        '--headless', '--disable-gpu', '--no-sandbox',
        `--user-data-dir=${profile}`,
        '--no-pdf-header-footer',
        '--virtual-time-budget=12000',
        `--print-to-pdf=${out}`,
        `http://127.0.0.1:${PORT}/${rel}`
      ], { timeout: 90000 });
      const kb = (fs.statSync(out).size / 1024).toFixed(0);
      console.log(`wrote ${out} (${kb} KB)`);
    } catch (e) {
      console.error(`ERROR: ${rel}: ${e.message.split('\n')[0]}`);
      failed = true;
    }
  }
} finally {
  server.close();
  fs.rmSync(profile, { recursive: true, force: true });
}
if (failed) process.exit(1);
