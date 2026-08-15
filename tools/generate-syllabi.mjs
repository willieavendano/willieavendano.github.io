#!/usr/bin/env node
// Regenerates <slug>/syllabus.md for every course from calendar/syllabi.json.
// Shared policy text lives in the `shared` block — edit it once, rerun, and
// every syllabus updates. Run from the repo root:
//   node tools/generate-syllabi.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'calendar', 'syllabi.json'), 'utf8'));
const S = data.shared;

const RULE = '\\_'.repeat(0) + '_'.repeat(0); // (kept simple: signature rules built below)
const SIG = '\\_'.repeat(46);


function routinesFor(c) {
  let routines = S.routines.filter(r => !(c.omitRoutines || []).some(k => r.startsWith(`**${k}`)));
  if (c.makerspace) routines.splice(routines.length - 1, 0, S.makerspaceRoutine);
  if (c.virtualRoutines) routines = c.virtualRoutines.concat(routines);
  return routines;
}

/* ── HTML rendering ─────────────────────────────────────── */
const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// minimal inline markdown: **bold**, *italic*, [text](url)
function md(t) {
  return esc(t)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}

function unitsHtml(c) {
  const out = [];
  if (c.pltw) out.push(`<p>This course follows the official <strong>PLTW ${esc(c.title)}</strong> units. Each is taught through the PLTW lessons listed beneath it.</p>`);
  for (const u of c.units) {
    out.push('<div class="unit">');
    out.push(`<h3><span class="u-n">Unit ${esc(u.n)}</span> ${esc(u.name)}</h3>`);
    out.push('<ul>' + u.lessons.map(l => `<li>${md(l)}</li>`).join('') + '</ul>');
    out.push('</div>');
  }
  out.push('<p>Week-by-week pacing — including which weeks carry no new content — is on the course page.</p>');
  return out.join('\n');
}

function signBlock(labels) {
  return '<div class="sign">' + labels.map(l =>
    `<div class="sign-row"><span class="lab">${esc(l)}</span><span class="rule"></span></div>`).join('') + '</div>';
}

function contractHtml(c, S) {
  const k = S.apContract;
  const sub = t => t.replace(/\{COURSE\}/g, c.title);
  const L = ['<section class="page-break">'];
  L.push(`<h2>${esc(k.heading)}</h2>`);
  L.push(`<p>${md(sub(k.intro))}</p>`);
  L.push('<p class="contract-role">Student Responsibilities</p><ol>');
  for (const r of k.student) L.push(`<li>${md(sub(r))}</li>`);
  L.push('</ol>');
  L.push('<p class="contract-role">Parent/Guardian Responsibilities</p>');
  L.push(`<p>${md(k.parent)}</p>`);
  L.push('<p class="contract-role">School Responsibilities</p>');
  L.push(`<p>${md(k.school)}</p>`);
  L.push('</section>');
  return L.join('\n');
}

function renderHtml(c) {
  const L = [];
  const p = (...x) => L.push(...x);
  const routines = routinesFor(c);

  p('<!DOCTYPE html>', '<html lang="en">', '<head>', '<meta charset="UTF-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    '<link rel="icon" href="/favicon.ico" sizes="any">',
    '<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">',
    '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
    `<title>${esc(c.title)} — Syllabus ${data.year}</title>`,
    '<link rel="preconnect" href="https://fonts.googleapis.com">',
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    '<link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,500;0,600;0,700;1,500&family=Atkinson+Hyperlegible+Next:wght@400;500;600;700&family=Fragment+Mono&display=swap" rel="stylesheet">',
    '<link rel="stylesheet" href="/assets/css/syllabus.css">',
    '</head>', '<body class="syllabus">');

  p('<div class="syl-actions">',
    `<a class="primary" href="syllabus.pdf" download>Download PDF</a>`,
    `<a href="./">← ${esc(c.title)}</a>`,
    '</div>');

  p('<main class="sheet">');
  p('<header class="syl-head">',
    '<p class="syl-eyebrow">Course Syllabus</p>',
    `<h1>${esc(c.title)}</h1>`,
    `<p class="syl-year">${esc(data.year)} &middot; The Cushman School</p>`,
    '</header>');

  p('<div class="syl-contact">');
  p(`<p><span class="lbl">Teacher</span>${esc(S.teacher)}</p>`);
  p(`<p><span class="lbl">Email</span><a href="mailto:${S.email}">${esc(S.email)}</a></p>`);
  if (!c.virtual) p(`<p><span class="lbl">Room</span>${esc(S.room)}</p>`);
  p(`<p><span class="lbl">Class meets</span>${esc(c.meets)}</p>`);
  p(`<p style="grid-column:1/-1"><span class="lbl">Extra help</span>${esc(S.officeHours)} <span class="note">${esc(S.officeHoursNote)}</span></p>`);
  p('</div>');

  p('<h2>Course Description</h2>');
  for (const para of c.description) p(`<p>${md(para)}</p>`);

  if (c.learningObjectives) {
    p('<h2>Learning Objectives</h2>', '<p>By the end of this course, students will be able to:</p>', '<ol>');
    for (const o of c.learningObjectives) p(`<li>${md(o)}</li>`);
    p('</ol>');
  }

  p('<h2>Units</h2>', unitsHtml(c));

  p('<h2>Required Texts and Links</h2>', '<p><em>Subject to change and grow.</em></p>', '<ul>');
  for (const t of c.texts) p(`<li>${md(t)}</li>`);
  p('</ul>');

  p('<h2>Course Materials</h2>', '<ul>');
  for (const m of c.materials) p(`<li>${md(m)}</li>`);
  p('</ul>');

  p('<h2>Grades and Evaluations</h2>');
  p(`<p>${md(S.gradeScaleLine)}</p>`);
  p('<div class="weights">');
  p(`<div class="weight"><span class="pct">${S.weights.summative}%</span><span class="nm">Summative</span><span class="ds">${md(c.summative)}</span></div>`);
  p(`<div class="weight"><span class="pct">${S.weights.formative}%</span><span class="nm">Formative</span><span class="ds">${md(c.formative)}</span></div>`);
  p(`<div class="weight"><span class="pct">${S.weights.diagnostic}%</span><span class="nm">Diagnostics</span><span class="ds">Entrance and exit tickets, and other checks that are neither summative nor formative.</span></div>`);
  p('</div>');

  p('<h3>Description of Common Assessments</h3>');
  for (const a of c.assessments) p(`<p><strong>${esc(a.t)}</strong> ${md(a.b)}</p>`);
  p(`<p>${md(S.classworkText)}</p>`);
  p(`<p>${md(S.homeworkText)}</p>`);
  p('<p>Scoring on homework will be as follows:</p><ul>');
  for (const h of S.homeworkScale) p(`<li>${md(h)}</li>`);
  p('</ul>');

  p('<h2>Rules and Routines</h2>');
  p(`<p>${md(S.rulesIntro)}</p>`);
  p('<h3>Rules</h3>');
  p(`<p>${md(S.respect)}</p>`);
  p('<p><strong>Consequences.</strong> Most violations will undergo the following consequences:</p><ol>');
  for (const x of S.consequences) p(`<li>${md(x)}</li>`);
  p('</ol>');
  p('<h3>Routines</h3><ol>');
  for (const r of routines) p(`<li>${md(r)}</li>`);
  p('</ol>');

  p('<h2>Academic Integrity</h2>', `<p>${md(S.academicIntegrity)}</p>`);
  p('<h2>Disclaimer</h2>', `<p>${md(S.disclaimer)}</p>`);

  if (c.ap) p(contractHtml(c, S));

  p('<section class="page-break">');
  p('<h2>Acknowledgement of Receipt and Understanding</h2>');
  p(`<p>Please sign and submit as soon as possible, but <strong>no later than ${esc(S.acknowledgementDue)}</strong>.</p>`);
  p(`<div class="callout">${md(S.acknowledgementNote)}</div>`);
  p(`<p><em>I have read and fully understand the academic and behavioral expectations outlined in Mr. Avendano's ${esc(c.title)} syllabus. I agree to abide by these guidelines or will undergo the academic and/or disciplinary consequences.</em></p>`);
  p(signBlock(c.ap ? S.apSignatures : S.signatures));
  p('</section>');

  p('</main>');
  p(`<p class="syl-foot">Generated from calendar/syllabi.json — do not edit this file by hand.</p>`);
  p('</body>', '</html>');
  return L.join('\n') + '\n';
}

function unitsSection(c) {
  const out = [];
  if (c.pltw) {
    out.push(`This course follows the official **PLTW ${c.title}** units. Each is taught through the PLTW lessons listed beneath it.`, '');
  }
  for (const u of c.units) {
    out.push(`### Unit ${u.n} — ${u.name}`, '');
    for (const l of u.lessons) out.push(`- ${l}`);
    out.push('');
  }
  out.push('Week-by-week pacing — including which weeks carry no new content — is on the course page.');
  return out.join('\n');
}

function render(c) {
  const L = [];
  const p = (...xs) => L.push(...xs);

  p(`# ${c.title} — Syllabus ${data.year}`, '');
  p(`**${S.teacher}**  `, `[${S.email}](mailto:${S.email})  `);
  if (!c.virtual) p(`${S.room}  `);
  p('');
  p(`**Class meets:** ${c.meets}`, '');
  p(`**Extra help:** ${S.officeHours}  `, `_${S.officeHoursNote}_`, '');
  p('---', '');

  p('## Course Description', '');
  for (const para of c.description) p(para, '');

  if (c.learningObjectives) {
    p('## Learning Objectives', '');
    p('By the end of this course, students will be able to:', '');
    c.learningObjectives.forEach((o, i) => p(`${i + 1}. ${o}`));
    p('');
  }

  p('## Units', '');
  p(unitsSection(c), '');

  p('## Required Texts and Links (subject to change and grow)', '');
  for (const t of c.texts) p(`* ${t}`);
  p('');

  p('## Course Materials', '');
  for (const m of c.materials) p(`* ${m}`);
  p('');

  p('## Grades and Evaluations', '');
  p(S.gradeScaleLine, '');
  p(`**Summative Assessments (${S.weights.summative}%)** — The goal of these assessments is to evaluate mastery of content and skills. In this course, these include (but are not limited to) ${c.summative}.`, '');
  p(`**Formative Assessments (${S.weights.formative}%)** — The goal of formative assessments is to gather feedback on student learning. Here students are working toward their mastery of content and skills. In this course, these include (but are not limited to) ${c.formative}.`, '');
  p(`**Diagnostics (${S.weights.diagnostic}%)** — ${S.diagnosticText}`, '');

  p('### Description of Common Assessments', '');
  for (const a of c.assessments) p(`**${a.t}** ${a.b}`, '');
  p(S.classworkText, '');
  p(S.homeworkText, '');
  p('Scoring on homework will be as follows:', '');
  for (const h of S.homeworkScale) p(`* ${h}`);
  p('');

  p('## Rules and Routines', '');
  p(S.rulesIntro, '');
  p('### Rules', '');
  p(S.respect, '');
  p('**Consequences.** Most violations will undergo the following consequences:', '');
  S.consequences.forEach((x, i) => p(`${i + 1}. ${x}`));
  p('');
  p('### Routines', '');
  // Some shared routines are physical-classroom only and are dropped for the
  // virtual section (see `omitRoutines`).
  const routines = routinesFor(c);
  routines.forEach((x, i) => p(`${i + 1}. ${x}`, ''));

  p('## Academic Integrity', '');
  p(S.academicIntegrity, '');

  p('## Disclaimer', '');
  p(S.disclaimer, '');
  p('---', '');

  if (c.ap) {
    const k = S.apContract;
    const sub = t => t.replace(/\{COURSE\}/g, c.title);
    p('---', '');
    p(`## ${k.heading}`, '');
    p(sub(k.intro), '');
    p('**Student Responsibilities**', '');
    k.student.forEach((r, i) => p(`${i + 1}. ${sub(r)}`, ''));
    p('**Parent/Guardian Responsibilities**', '');
    p(k.parent, '');
    p('**School Responsibilities**', '');
    p(k.school, '');
    p('---', '');
  }

  p('## Acknowledgement of Receipt and Understanding', '');
  p(`Please sign and submit as soon as possible, but **no later than ${S.acknowledgementDue}**.`, '');
  p(`> ${S.acknowledgementNote}`, '');
  p(`*I have read and fully understand the academic and behavioral expectations outlined in Mr. Avendano's ${c.title} syllabus. I agree to abide by these guidelines or will undergo the academic and/or disciplinary consequences.*`, '');
  for (const label of (c.ap ? S.apSignatures : S.signatures)) {
    p(`${label} &nbsp; ${SIG}`, '');
  }
  return L.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd() + '\n';
}

let wrote = 0, failed = false;
for (const c of data.courses) {
  const dir = path.join(root, c.slug);
  if (!fs.existsSync(dir)) {
    console.error(`ERROR: ${c.slug}: no course directory`);
    failed = true;
    continue;
  }
  for (const [file, body] of [['syllabus.md', render(c)], ['syllabus.html', renderHtml(c)]]) {
    const out = path.join(dir, file);
    const prev = fs.existsSync(out) ? fs.readFileSync(out, 'utf8') : null;
    if (prev === body) { console.log(`unchanged ${c.slug}/${file}`); continue; }
    fs.writeFileSync(out, body);
    console.log(`wrote ${c.slug}/${file}`);
    wrote++;
  }
}
console.log(`\n${wrote} syllabi written, ${data.courses.length} total`);
if (failed) process.exit(1);
