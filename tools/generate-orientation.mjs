#!/usr/bin/env node
// Generates orientation decks from calendar/orientation.json:
//
//   <slug>/slides/orientation-student.html
//   <slug>/slides/orientation-parent.html
//
// Two variants per course because the Back to School Checklist asks for a
// Course Orientation deck AND a Parent Night deck. They share the same data,
// so the shared blocks (grading, expectations, late work) can only ever say
// the same thing in both. Run from the repo root:
//   node tools/generate-orientation.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'calendar', 'orientation.json'), 'utf8'));
const S = data.shared;

const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const HEAD = title => `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<title>${esc(title)}</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,500;0,600;0,700;1,500&family=Atkinson+Hyperlegible+Next:wght@400;500;600;700&family=Fragment+Mono&display=swap" rel="stylesheet">

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
<link rel="stylesheet" href="/assets/slides/deck.css">
<style>
  /* One-off components for orientation decks only — deck.css stays frozen. */
  .weight-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6em; margin-top: 0.6em; }
  .weight-row .w { background: var(--white); border: 1px solid var(--line); border-top: 4px solid var(--blue); border-radius: 6px; padding: 0.7em 0.6em; text-align: center; }
  .weight-row .w .pct { font-family: 'Fragment Mono', monospace; font-size: 1.9em; color: var(--blue); line-height: 1; }
  .weight-row .w .nm { display: block; font-weight: 700; margin-top: 0.15em; }
  .weight-row .w .gl { display: block; font-size: 0.62em; color: var(--ink-soft); margin-top: 0.25em; line-height: 1.3; }

  .meme { max-width: 22em; margin: 0.4em auto 0; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: var(--white); }
  .meme .panel { padding: 0.75em 0.9em; font-family: 'Familjen Grotesk', sans-serif; font-weight: 600; font-size: 0.82em; line-height: 1.3; }
  .meme .panel.top { border-bottom: 1px solid var(--line); }
  .meme .panel.bottom { background: var(--paper-deep); }
  .meme .tag { display: block; font-family: 'Fragment Mono', monospace; font-size: 0.5em; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-soft); margin-bottom: 0.25em; }
  .meme-img { max-height: 46vh; width: auto; max-width: 90%; border: 1px solid var(--line); border-radius: 8px; margin: 0.2em auto 0; display: block; }
  .meme-caption { margin-top: 0.7em; font-size: 0.78em; color: var(--ink-soft); max-width: 30em; margin-left: auto; margin-right: auto; }

  .unit-list { list-style: none; padding: 0; margin: 0.4em 0 0; display: grid; gap: 0.35em; }
  .unit-list li { display: flex; gap: 0.7em; align-items: baseline; background: var(--white); border: 1px solid var(--line); border-radius: 5px; padding: 0.4em 0.7em; }
  .unit-list .n { font-family: 'Fragment Mono', monospace; font-size: 0.65em; color: var(--white); background: var(--blue); border-radius: 3px; padding: 0.1em 0.5em; flex: none; }

  .date-list { list-style: none; padding: 0; margin: 0.4em 0 0; display: grid; gap: 0.4em; }
  .date-list li { display: flex; justify-content: space-between; gap: 1em; border-bottom: 1px solid var(--line); padding-bottom: 0.35em; }
  .date-list .when { font-family: 'Fragment Mono', monospace; color: var(--blue); white-space: nowrap; }
</style>
</head>
<body>
<div class="reveal"><div class="slides">`;

const FOOT = `</div></div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/notes/notes.js"></script>
<script>
  Reveal.initialize({ hash: true, slideNumber: 'c/t', plugins: [ RevealNotes ] });
</script>
</body>
</html>
`;

const notes = t => `<aside class="notes">${t}</aside>`;

function deck(c, audience) {
  const parent = audience === 'parent';
  const s = [];
  const push = (...x) => s.push(...x);

  // ── cover ──
  push(`<section class="cover">
      <p class="eyebrow">${esc(c.eyebrow)} &middot; ${esc(data.year)}</p>
      <h1>${esc(c.title)}</h1>
      <p class="kicker-line">${parent ? 'Parent Night' : 'Course Orientation'}</p>
      <div class="rule"></div>
      <p class="meta-line">${esc(c.period)} &middot; ${esc(c.meets)}</p>
      ${notes(parent
        ? 'Parent Night. Keep this to about 12 minutes and leave time for questions — most parents want to know how to see the work and how to help at home. Point them at Veracross and the course page.'
        : 'Day-one orientation. Students rotate through, so this deck stands alone. Do not read the slides; use them as prompts and get to the first activity.')}
    </section>`);

  // ── who ──
  push(`<section>
      <p class="eyebrow">Who is teaching this</p>
      <h2>${esc(S.teacher)}</h2>
      <ul>${S.bio.map(b => `<li>${esc(b)}</li>`).join('')}</ul>
      <p class="meta-line">${esc(S.email)} &middot; Room ${esc(S.room)}</p>
      ${notes('Thirty seconds. The point is credibility and approachability, not a CV reading.')}
    </section>`);

  // ── the pitch ──
  push(`<section class="divider">
      <p class="eyebrow">The course</p>
      <h2>${esc(c.pitch)}</h2>
    </section>`);

  push(`<section>
      <p class="eyebrow">What this course is</p>
      <h2>${esc(c.title)}</h2>
      <p>${esc(c.blurb)}</p>
      ${notes('Say the one-line pitch out loud, then stop. The units slide does the detail work.')}
    </section>`);

  // ── units ──
  push(`<section>
      <p class="eyebrow">Units &middot; the year at a glance</p>
      <h2>What we cover</h2>
      <ul class="unit-list">
        ${c.units.map(([n, name]) => `<li><span class="n">${esc(n)}</span> ${esc(name)}</li>`).join('\n        ')}
      </ul>
      ${notes('Do not narrate all of these. Name the first one, name the last one, and say how they connect.')}
    </section>`);

  // ── meme beat ──
  // An image when we have one the teacher already used in class; otherwise a
  // typographic expectation/reality panel built from the design system.
  if (c.memeImage) {
    push(`<section>
      <p class="eyebrow">The honest version</p>
      <h2>${esc(c.memeImage.alt)}</h2>
      <img class="meme-img" src="/assets/img/orientation/${esc(c.memeImage.file)}" alt="${esc(c.memeImage.alt)}">
      <p class="meme-caption">${esc(c.memeImage.caption)}</p>
      ${notes('Let it play, let them laugh, then say the caption and move. Do not explain the joke.')}
    </section>`);
  } else {
    push(`<section>
      <p class="eyebrow">The honest version</p>
      <div class="meme">
        <div class="panel top"><span class="tag">Expectation</span>${esc(c.meme.top)}</div>
        <div class="panel bottom"><span class="tag">Reality</span>${esc(c.meme.bottom)}</div>
      </div>
      <p class="meme-caption">${esc(c.meme.caption)}</p>
      ${notes('This is the laugh that buys you the next ten minutes. Deliver it and move — do not explain the joke.')}
    </section>`);
  }

  // ── assessments ──
  push(`<section>
      <p class="eyebrow">How you are assessed</p>
      <h2>What counts</h2>
      <ul>
        ${c.assessments.map(([t, d]) => `<li><strong>${esc(t)}.</strong> ${esc(d)}</li>`).join('\n        ')}
      </ul>
      ${notes('The most common parent question lives here. Be concrete about what a grade is made of.')}
    </section>`);

  // ── grade breakdown (shared) ──
  push(`<section>
      <p class="eyebrow">Grade breakdown</p>
      <h2>How the number is built</h2>
      <div class="weight-row">
        ${S.weights.map(w => `<div class="w"><span class="pct">${w.pct}%</span><span class="nm">${esc(w.name)}</span><span class="gl">${esc(w.gloss)}</span></div>`).join('\n        ')}
      </div>
      <p class="meta-line">${esc(S.gradeNote)}</p>
      ${notes('Identical across all seven of my courses — say so. It removes a whole category of confusion.')}
    </section>`);

  // ── late work + resubmission ──
  push(`<section>
      <p class="eyebrow">Late work &amp; second chances</p>
      <h2>The policy, plainly</h2>
      <ul>${S.lateWork.map(l => `<li>${esc(l)}</li>`).join('')}</ul>
      <p class="meta-line">${esc(S.resubmit)}</p>
      ${notes('Emphasise the BEFORE. Students who come early get help; students who come after get the policy.')}
    </section>`);

  if (parent) {
    push(`<section class="divider">
        <p class="eyebrow">For families</p>
        <h2>How to see the work &mdash; and help</h2>
      </section>`);
    push(`<section>
        <p class="eyebrow">Staying in the loop</p>
        <h2>Where everything lives</h2>
        <ul>
          ${S.parentSupport.map(p => `<li><strong>${esc(p.t)}.</strong> ${esc(p.d)}</li>`).join('\n          ')}
        </ul>
        ${notes('End on the better-question line. Parents remember it and it genuinely changes dinner-table conversations.')}
      </section>`);
  } else {
    push(`<section>
        <p class="eyebrow">What I expect</p>
        <h2>Four things</h2>
        <ul>
          ${S.expectations.map(e => `<li><strong>${esc(e.t)}.</strong> ${esc(e.d)}</li>`).join('\n          ')}
        </ul>
        ${notes('Read these as commitments, not threats. Tone here sets the year.')}
      </section>`);
    push(`<section>
        <p class="eyebrow">Executive function &middot; how to actually keep up</p>
        <h2>Running your own week</h2>
        <ul>
          ${S.executiveFunction.map(e => `<li><strong>${esc(e.t)}.</strong> ${esc(e.d)}</li>`).join('\n          ')}
        </ul>
        ${notes('This is the slide that saves the most students. Spend a full minute on the planner point — the school checklist explicitly asks for notetaking and executive function.')}
      </section>`);
  }

  // ── dates ──
  push(`<section>
      <p class="eyebrow">Dates worth writing down</p>
      <h2>Mark these now</h2>
      <ul class="date-list">
        ${c.dates.map(([w, d]) => `<li><span>${esc(w)}</span><span class="when">${esc(d)}</span></li>`).join('\n        ')}
      </ul>
      ${notes('Have them write these in the planner in the room. Do not move on until pens have moved.')}
    </section>`);

  if (c.isAP) {
    push(`<section>
        <p class="eyebrow">AP commitment</p>
        <h2>What signing up means</h2>
        <ul>
          <li><strong>You sit the exam.</strong> Every enrolled student takes it in May. The school covers the cost.</li>
          <li><strong>It is a college course.</strong> The workload assumes reading and problem sets outside class.</li>
          <li><strong>Extra sessions happen.</strong> Review outside regular hours, especially in April.</li>
          <li><strong>Tell me early.</strong> If you fall behind on readings or assignments, say so before it compounds.</li>
        </ul>
        ${notes('The signed AP Student Expectations Agreement is in the syllabus. Point at it and say the deadline out loud.')}
      </section>`);
  }

  // ── support ──
  push(`<section>
      <p class="eyebrow">Getting help</p>
      <h2>How to reach me</h2>
      <ul>
        <li><strong>Extra help.</strong> ${esc(S.extraHelp)}</li>
        <li><strong>Email.</strong> ${esc(S.email)} — within 24 hours on school days; Friday emails answered by Monday.</li>
        <li><strong>Room ${esc(S.room)}.</strong> Come find me. Before the deadline, not after.</li>
      </ul>
      <p class="meta-line">${esc(S.extraHelpNote)}</p>
      ${notes('Last content slide. Say plainly that asking for help early is the single highest-return habit in the course.')}
    </section>`);

  // ── closer ──
  push(`<section class="cover">
      <p class="eyebrow">Everything, always</p>
      <h1>class.avendano.xyz</h1>
      <p class="kicker-line">/${esc(c.slug)}</p>
      <div class="rule"></div>
      <p class="meta-line">Year calendar &middot; every slide deck &middot; syllabus &middot; project briefs</p>
      ${notes('Send them there before they leave. It is the answer to most questions asked later in the year.')}
    </section>`);

  return HEAD(`${c.title} — ${parent ? 'Parent Night' : 'Orientation'} ${data.year}`) + '\n' + s.join('\n\n') + '\n' + FOOT;
}

let n = 0;
for (const c of data.courses) {
  const dir = path.join(root, c.slug, 'slides');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  for (const aud of ['student', 'parent']) {
    const out = path.join(dir, `orientation-${aud}.html`);
    const body = deck(c, aud);
    if (fs.existsSync(out) && fs.readFileSync(out, 'utf8') === body) { console.log(`unchanged ${c.slug}/slides/orientation-${aud}.html`); continue; }
    fs.writeFileSync(out, body);
    const slides = (body.match(/<section/g) || []).length;
    console.log(`wrote ${c.slug}/slides/orientation-${aud}.html (${slides} slides)`);
    n++;
  }
}
console.log(`\n${n} decks written, ${data.courses.length} courses × 2 audiences`);
