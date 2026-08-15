#!/usr/bin/env node
// Generates the Computer Science Math cornerstone kits from
// calendar/csmath-kits.json:
//
//   computer-science-math/kits/<id>.html   project brief + full rubric
//   computer-science-math/kits/index.html  kit hub, wired to the course page
//
// Styling reuses assets/css/syllabus.css so a kit reads as part of the same
// family as the syllabi and course pages. Run from the repo root:
//   node tools/generate-csmath-kits.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'calendar', 'csmath-kits.json'), 'utf8'));
const outDir = path.join(root, 'computer-science-math', 'kits');
fs.mkdirSync(outDir, { recursive: true });

const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const md = t => esc(t)
  .replace(/`([^`]+)`/g, '<code>$1</code>')
  .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  .replace(/\*([^*]+)\*/g, '<em>$1</em>');

const head = (title, depth = 1) => [
  '<!DOCTYPE html>', '<html lang="en">', '<head>', '<meta charset="UTF-8">',
  '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
  '<link rel="icon" href="/favicon.ico" sizes="any">',
  '<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">',
  '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
  `<title>${esc(title)}</title>`,
  '<link rel="preconnect" href="https://fonts.googleapis.com">',
  '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
  '<link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,500;0,600;0,700;1,500&family=Atkinson+Hyperlegible+Next:wght@400;500;600;700&family=Fragment+Mono&display=swap" rel="stylesheet">',
  '<link rel="stylesheet" href="/assets/css/syllabus.css">',
  '<link rel="stylesheet" href="/assets/css/kit.css">',
  '</head>', '<body class="syllabus kit">'
].join('\n');

function rubricTable(kit) {
  const S = data.rubricSpine;
  const L = ['<div class="rubric-wrap"><table class="rubric">'];
  L.push('<thead><tr><th class="crit">Criterion</th>' +
    S.levels.map(l => `<th><span class="lvl">${l.n}</span> ${esc(l.name)}</th>`).join('') +
    '</tr></thead><tbody>');
  for (const c of S.criteria) {
    L.push('<tr>');
    L.push(`<td class="crit"><strong>${esc(c.name)}</strong>${c.optional ? ' <em>(optional)</em>' : ''}<span class="q">${esc(c.question)}</span></td>`);
    for (const l of S.levels) L.push(`<td>${md(c.d[String(l.n)])}</td>`);
    L.push('</tr>');
  }
  L.push('</tbody></table></div>');
  L.push('<p class="lvl-key">' + S.levels.map(l =>
    `<span><b>${l.n} ${esc(l.name)}</b> — ${esc(l.gloss)}</span>`).join('') + '</p>');
  return L.join('\n');
}

function renderKit(kit) {
  const L = [head(`${kit.title} — Kit`)];
  const p = (...x) => L.push(...x);

  p('<div class="syl-actions">',
    '<a href="./">← All kits</a>',
    '<a href="/computer-science-math/">Course page</a>',
    '</div>');

  p('<main class="sheet">');
  p('<header class="syl-head">',
    `<p class="syl-eyebrow">${esc(kit.kicker)} &middot; ${esc(kit.weeks)}</p>`,
    `<h1>${esc(kit.title)}</h1>`,
    `<p class="syl-year">${esc(data.course)} &middot; ${esc(data.year)}</p>`,
    '</header>');

  p(`<p class="premise">${md(kit.premise)}</p>`);

  if (kit.blocked) p(`<div class="callout blocked"><strong>Not ready yet.</strong> ${md(kit.blocked)}</div>`);

  // ── the four beats ──
  p('<h2>How this kit runs</h2>');
  p('<ol class="beats">');
  p(`<li><span class="beat">Concept</span>${kit.decks.length} deck${kit.decks.length === 1 ? '' : 's'} — see the idea and why it matters.</li>`);
  if (kit.practicum) p(`<li><span class="beat">Practice</span><strong>${esc(kit.practicum.title)}</strong> — rehearse the mechanic before it counts.</li>`);
  if (kit.tool) p(`<li><span class="beat">Explore</span><strong>${esc(kit.tool.title)}</strong> — play with a working version, then rebuild its engine.</li>`);
  p(`<li><span class="beat">Build</span><strong>${esc(kit.deliverable)}</strong> — the cornerstone itself.</li>`);
  p('</ol>');

  p('<h2>Concept</h2>');
  for (const d of kit.decks) {
    const done = d.status === 'built';
    p('<div class="unit">');
    p(`<h3><span class="u-n">Deck</span> ${done ? `<a href="/computer-science-math/slides/${d.file}">${esc(d.title)}</a>` : esc(d.title)}${done ? '' : ' <span class="todo">not built yet</span>'}</h3>`);
    if (d.concept) p(`<p>${md(d.concept)}</p>`);
    p('</div>');
  }

  if (kit.practicum) {
    p('<h2>Practice</h2>');
    p(`<p><strong>${esc(kit.practicum.title)}</strong> — <code>${esc(kit.practicum.file)}</code></p>`);
    p('<ol class="drills">');
    for (const d of kit.practicum.drills) p(`<li>${md(d)}</li>`);
    p('</ol>');
  }

  if (kit.tool) {
    p('<h2>Explore</h2>');
    p('<div class="callout">');
    const built = kit.tool.status === 'built';
    p(`<p><strong>${esc(kit.tool.title)}</strong>${built ? '' : ' <span class="todo">not built yet</span>'}</p>`);
    p(`<p>${md(kit.tool.job)}</p>`);
    if (kit.tool.priority) p(`<p><em>${md(kit.tool.priority)}</em></p>`);
    p('</div>');
  }

  if (kit.challenge) {
    const ch = kit.challenge;
    p('<h2>The Challenge</h2>');
    p('<div class="challenge">');
    p(`<p class="ch-title">${esc(ch.title)}</p>`);
    p('<dl class="ch-meta">');
    p(`<dt>Platform</dt><dd>${md(ch.platform)}</dd>`);
    p(`<dt>Capital</dt><dd>${md(ch.capital)}</dd>`);
    p('</dl>');
    p('<p class="ch-sub">Rules</p><ol>');
    for (const r of ch.rules) p(`<li>${md(r)}</li>`);
    p('</ol>');
    p('<p class="ch-sub">Verticals — one holding minimum in each</p>');
    p('<ul class="verticals">');
    for (const v of ch.verticals) p(`<li><strong>${esc(v.name)}</strong><span>${esc(v.note)}</span></li>`);
    p('</ul>');
    p('</div>');
  }

  p('<h2>Build — what you hand in</h2>');
  p(`<p><strong>${esc(kit.deliverable)}</strong></p>`);
  p(`<p>${md(kit.evidence)}</p>`);
  if (kit.stretch) p(`<div class="callout"><strong>Stretch (optional).</strong> ${md(kit.stretch)}</div>`);

  p('<h2 class="page-break-before">Rubric</h2>');
  p('<p>Every cornerstone is scored on the same five criteria, so you always know what "good" means before you start.</p>');
  p(rubricTable(kit));

  if (kit.exemplars) {
    p('<h2>What each level looks like</h2>');
    p(`<p>The exemplar workbook <code>csm-${kit.id}-exemplars.xlsx</code> contains the same model built four times — one tab per level — plus a <em>What Changed</em> tab naming the specific difference between each pair. Read it before you start, not after you are graded.</p>`);
  }

  p('</main>');
  p('</body>', '</html>');
  return L.join('\n') + '\n';
}

function renderIndex() {
  const L = [head('Computer Science Math — Cornerstone Kits')];
  const p = (...x) => L.push(...x);
  p('<div class="syl-actions"><a href="/computer-science-math/">← Course page</a></div>');
  p('<main class="sheet">');
  p('<header class="syl-head">',
    '<p class="syl-eyebrow">Computer Science Math</p>',
    '<h1>Cornerstone Kits</h1>',
    `<p class="syl-year">${esc(data.year)} &middot; concept &rarr; practice &rarr; explore &rarr; build</p>`,
    '</header>');
  p('<div class="kit-grid">');
  for (const k of data.kits) {
    const bits = [];
    bits.push(`${k.decks.length} deck${k.decks.length === 1 ? '' : 's'}`);
    if (k.practicum) bits.push('practice');
    if (k.tool) bits.push('tool');
    if (k.exemplars) bits.push('exemplars');
    p(`<a class="kit-card" href="${k.id}.html">`,
      `<span class="kc-kicker">${esc(k.kicker)}</span>`,
      `<span class="kc-title">${esc(k.title)}</span>`,
      `<span class="kc-when">${esc(k.weeks)}</span>`,
      `<span class="kc-bits">${bits.join(' · ')}</span>`,
      k.blocked ? '<span class="kc-flag">needs data</span>' : '',
      '</a>');
  }
  p('</div>');
  p('</main>', '</body>', '</html>');
  return L.join('\n') + '\n';
}

let n = 0;
for (const kit of data.kits) {
  const out = path.join(outDir, `${kit.id}.html`);
  const body = renderKit(kit);
  if (fs.existsSync(out) && fs.readFileSync(out, 'utf8') === body) { console.log(`unchanged kits/${kit.id}.html`); continue; }
  fs.writeFileSync(out, body); console.log(`wrote kits/${kit.id}.html`); n++;
}
const idx = path.join(outDir, 'index.html');
const idxBody = renderIndex();
if (!fs.existsSync(idx) || fs.readFileSync(idx, 'utf8') !== idxBody) {
  fs.writeFileSync(idx, idxBody); console.log('wrote kits/index.html'); n++;
} else console.log('unchanged kits/index.html');

console.log(`\n${n} files written, ${data.kits.length} kits`);
