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

  /* The four-bullet policy slides (expectations, executive function, parent
     support) run ~14px past the canvas at default leading. */
  ul.dense li { margin-bottom: 0.18em; line-height: 1.35; }
  ul.dense { margin-top: 0.3em; }

  .unit-list { list-style: none; padding: 0; margin: 0.4em 0 0; display: grid; gap: 0.35em; }
  /* Courses with more than six units go two-up, otherwise the list runs past
     the 700px canvas — Physics has ten and overflowed by 301px single-column. */
  .unit-list.two-up { grid-template-columns: 1fr 1fr; gap: 0.3em 0.6em; }
  .unit-list li { display: flex; gap: 0.7em; align-items: baseline; background: var(--white); border: 1px solid var(--line); border-radius: 5px; padding: 0.4em 0.7em; }
  .unit-list.two-up li { padding: 0.32em 0.6em; font-size: 0.86em; }
  .unit-list .n { font-family: 'Fragment Mono', monospace; font-size: 0.65em; color: var(--white); background: var(--blue); border-radius: 3px; padding: 0.1em 0.5em; flex: none; }

  .date-list { list-style: none; padding: 0; margin: 0.4em 0 0; display: grid; gap: 0.4em; }
  .date-list li { display: flex; justify-content: space-between; gap: 1em; border-bottom: 1px solid var(--line); padding-bottom: 0.35em; }
  .date-list .when { font-family: 'Fragment Mono', monospace; color: var(--blue); white-space: nowrap; }

  /* Who-is-teaching-this: photo + bio two-up. Default 32px body text
     wraps to 4-5 lines per bullet in the narrowed right column and blows
     past the 700px canvas (measured 773px) — the bio-col wrapper scales
     the whole right column down to fit. */
  .who-cols { display: grid; grid-template-columns: 340px 1fr; gap: 1.2em; align-items: center; width: 100%; }
  .who-photo { width: 340px; height: 420px; object-fit: cover; object-position: top; border-radius: 12px; border: 1px solid var(--line); display: block; box-shadow: 0 10px 30px rgba(20,40,80,.10); }
  .who-cols .bio-col { font-size: 0.78em; }
  .who-cols .bio-col h2 { margin-bottom: 0.25em; }
  .who-cols .bio-col ul { margin: 0.2em 0 0.45em; }
  .who-cols .bio-col li { margin-bottom: 0.18em; line-height: 1.35; }
  .contact-row { display: flex; flex-wrap: wrap; gap: 0.4em; margin-top: 0.5em; }
  .contact-row .chip { font-family: 'Fragment Mono', monospace; font-size: 0.6em; letter-spacing: 0.04em; color: var(--blue); background: var(--white); border: 1px solid var(--line); border-radius: 999px; padding: 0.3em 0.8em; }
  .reveal li.bio-note { color: var(--ink-soft); font-size: 0.9em; }

  /* What to bring: software logo row + materials list. */
  .logo-grid { display: grid; grid-template-columns: repeat(var(--lcols, 4), minmax(0, 1fr)); gap: 0.6em; margin-top: 0.5em; }
  .logo-grid.fit { display: flex; flex-wrap: wrap; }
  .logo-chip { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.35em; min-width: 150px; padding: 0.6em 0.8em 0.5em; background: var(--white); border: 1px solid var(--line); border-top: 4px solid var(--blue); border-radius: 6px; }
  .logo-chip .art { height: 72px; display: flex; align-items: center; justify-content: center; }
  .logo-chip img { max-height: 72px; max-width: 150px; object-fit: contain; display: block; }
  .logo-chip img.mono { height: 64px; filter: brightness(0) saturate(100%); }
  .logo-chip .word { font-family: 'Familjen Grotesk', sans-serif; font-weight: 700; font-size: 1.05em; color: var(--blue); line-height: 1; }
  .logo-chip .lbl { font-family: 'Fragment Mono', monospace; font-size: 0.48em; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-soft); }
  .materials-list { margin-top: 0.5em; font-size: 0.85em; }
  .materials-list li { margin-bottom: 0.15em; }
  /* Essentials: the two things a student must physically carry. Sits above
     the software row so hierarchy is calculator/binder first, apps second. */
  .essentials { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6em; margin: 0.4em 0 0.7em; }
  .essentials .ess { display: grid; grid-template-columns: 84px 1fr; gap: 0.7em; align-items: center; background: var(--white); border: 1px solid var(--line); border-left: 5px solid var(--blue); border-radius: 6px; padding: 0.55em 0.8em; }
  .essentials .ess .art { height: 72px; display: flex; align-items: center; justify-content: center; }
  .essentials .ess img, .essentials .ess svg { max-height: 72px; max-width: 84px; display: block; }
  .essentials .ess .t { font-family: 'Familjen Grotesk', sans-serif; font-weight: 700; font-size: 0.95em; line-height: 1.15; color: var(--ink); }
  .essentials .ess .d { font-family: 'Fragment Mono', monospace; font-size: 0.48em; letter-spacing: 0.1em; text-transform: uppercase; color: var(--blue); margin-top: 0.3em; }
  .essentials + .logo-grid .logo-chip { min-width: 120px; padding: 0.45em 0.6em 0.4em; }
  .essentials + .logo-grid .logo-chip .art, .essentials + .logo-grid .logo-chip img { height: 52px; max-height: 52px; }
  .materials-list { margin-top: 0.5em; }

  /* Room norms grid — balanced 3-up, no orphan row. */
  .norm-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5em; margin-top: 0.4em; }
  .norm-grid .tile .name { margin-top: 0; }
  .norm-grid .tile .use { margin-top: 0.3em; }

  /* AP Classroom slide. */
  .ap-ticket { display: inline-block; border: 2px dashed var(--blue); border-radius: 10px; padding: 0.5em 1.2em 0.6em; margin: 0.4em 0 0.5em; background: var(--white); }
  .ap-ticket .lbl { font-family: 'Fragment Mono', monospace; font-size: 0.48em; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-soft); display: block; }
  .ap-code { font-family: 'Fragment Mono', monospace; font-size: 2.4em; color: var(--blue); letter-spacing: 0.08em; line-height: 1.1; margin: 0; }
  .ap-url { font-size: 0.85em; margin-top: 0.2em; }

  ul.ai-list li { margin-bottom: 0.22em; }
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

// Three-ring binder, drawn in the deck's blue so it sits beside the TI mark.
const BINDER_SVG = `<svg viewBox="0 0 64 72" width="64" height="72" aria-hidden="true"><rect x="10" y="4" width="48" height="64" rx="5" fill="#fff" stroke="#0E406A" stroke-width="3"/><rect x="10" y="4" width="12" height="64" rx="3" fill="#0E406A"/><g fill="none" stroke="#0E406A" stroke-width="3" stroke-linecap="round"><circle cx="16" cy="18" r="5" fill="#fff"/><circle cx="16" cy="36" r="5" fill="#fff"/><circle cx="16" cy="54" r="5" fill="#fff"/></g><g stroke="#d6dde6" stroke-width="3" stroke-linecap="round"><line x1="30" y1="22" x2="50" y2="22"/><line x1="30" y1="34" x2="50" y2="34"/><line x1="30" y1="46" x2="44" y2="46"/></g></svg>`;

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
      <div class="cols who-cols">
        <div><img class="who-photo" src="/assets/img/orientation/willie.jpg" alt="${esc(S.teacher)}"></div>
        <div class="bio-col">
          <h2>${esc(S.teacher)}</h2>
          <ul>
            ${S.bio.map(b => `<li>${esc(b)}</li>`).join('\n            ')}
            <li class="bio-note">${esc(S.bioNote)}</li>
          </ul>
          <div class="contact-row"><span class="chip">${esc(S.email)}</span><span class="chip">Room ${esc(S.room)}</span></div>
        </div>
      </div>
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
      <ul class="unit-list${c.units.length > 6 ? ' two-up' : ''}">
        ${c.units.map(([n, name]) => `<li><span class="n">${esc(n)}</span> ${esc(name)}</li>`).join('\n        ')}
      </ul>
      ${notes('Do not narrate all of these. Name the first one, name the last one, and say how they connect.')}
    </section>`);

  // ── what to bring ──
  push(`<section>
      <p class="eyebrow">What to bring</p>
      <h2>Software &amp; materials</h2>
      ${c.dailyBring ? `<div class="essentials">
        <div class="ess"><div class="art"><img src="/assets/img/orientation/logos/ti.png" alt="Texas Instruments"></div><div><div class="t">${esc(c.dailyBring[0].t)}</div><div class="d">${esc(c.dailyBring[0].d)}</div></div></div>
        <div class="ess"><div class="art">${BINDER_SVG}</div><div><div class="t">${esc(c.dailyBring[1].t)}</div><div class="d">${esc(c.dailyBring[1].d)}</div></div></div>
      </div>` : ''}
      <div class="logo-grid${(c.software.filter(sw => !(c.dailyBring && sw.name === 'TI-84')).length <= 4) ? ' fit' : ''}" style="--lcols:${(n => n % 3 === 0 ? 3 : 4)(c.software.filter(sw => !(c.dailyBring && sw.name === 'TI-84')).length)}">
        ${c.software.filter(sw => !(c.dailyBring && sw.name === 'TI-84')).map(sw => sw.file
          ? `<div class="logo-chip"><div class="art"><img src="/${esc(sw.file)}" alt="${esc(sw.name)}"${sw.file.endsWith('.svg') ? ' class="mono"' : ''}></div><span class="lbl">${esc(sw.name)}</span></div>`
          : `<div class="logo-chip"><div class="art"><span class="word">${esc(sw.name)}</span></div><span class="lbl">${esc(sw.kind || 'software')}</span></div>`).join('\n        ')}
      </div>
      <ul class="materials-list">${c.materials.map(m => `<li>${esc(m)}</li>`).join('')}</ul>
      ${notes(c.dailyBring ? 'Hold up the calculator. Physically show them the binder. This is the slide that prevents three weeks of "I forgot it at home."' : 'Point at the logos on the projector, not just the words — half the room will recognise the icon before the name.')}
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

  // ── AI policy (shared) ──
  push(`<section>
      <p class="eyebrow">Using AI in this class</p>
      <h2>Five rules</h2>
      <ul class="dense ai-list">
        ${S.aiPolicy.map(a => `<li><strong>${esc(a.t)}.</strong> ${esc(a.d)}</li>`).join('\n        ')}
      </ul>
      ${notes('Say the tutor-not-ghostwriter line out loud. It is the whole policy in one sentence, and it is the one they will actually remember.')}
    </section>`);

  if (parent) {
    push(`<section class="divider">
        <p class="eyebrow">For families</p>
        <h2>How to see the work &mdash; and help</h2>
      </section>`);
    push(`<section>
        <p class="eyebrow">Staying in the loop</p>
        <h2>Where everything lives</h2>
        <ul class="dense">
          ${S.parentSupport.map(p => `<li><strong>${esc(p.t)}.</strong> ${esc(p.d)}</li>`).join('\n          ')}
        </ul>
        ${notes('End on the better-question line. Parents remember it and it genuinely changes dinner-table conversations.')}
      </section>`);
  } else {
    push(`<section>
        <p class="eyebrow">What I expect</p>
        <h2>Four things</h2>
        <ul class="dense">
          ${S.expectations.map(e => `<li><strong>${esc(e.t)}.</strong> ${esc(e.d)}</li>`).join('\n          ')}
        </ul>
        ${notes('Read these as commitments, not threats. Tone here sets the year.')}
      </section>`);
    push(`<section>
        <p class="eyebrow">Executive function &middot; how to actually keep up</p>
        <h2>Running your own week</h2>
        <ul class="dense">
          ${S.executiveFunction.map(e => `<li><strong>${esc(e.t)}.</strong> ${esc(e.d)}</li>`).join('\n          ')}
        </ul>
        ${notes('This is the slide that saves the most students. Spend a full minute on the planner point — the school checklist explicitly asks for notetaking and executive function.')}
      </section>`);
    push(`<section>
        <p class="eyebrow">Room norms</p>
        <h2>How the room runs</h2>
        <div class="tile-grid norm-grid" style="--cols:3">
          ${[...S.roomNorms, c.hasMakerspace ? S.makerspaceNorm : S.absenceNorm].map(n => `<div class="tile"><span class="name">${esc(n.t)}</span><p class="use">${esc(n.d)}</p></div>`).join('\n          ')}
        </div>
        ${notes('Fast slide. Point at each tile as you say it; do not read the sub-text aloud.')}
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
    push(`<section>
        <p class="eyebrow">AP Classroom</p>
        <h2>Join the course</h2>
        <div class="ap-ticket"><span class="lbl">Join code</span><p class="ap-code">${esc(S.apClassroom.code)}</p></div>
        <p class="ap-url"><a href="${esc(S.apClassroom.url)}">${esc(S.apClassroom.url)}</a></p>
        <p class="meta-line">${esc(S.apClassroom.note)}</p>
        ${notes('Have phones or laptops out and get everyone joined right now, in the room, rather than trusting it happens at home.')}
      </section>`);
  }

  // ── meme2 (palate cleanser before the close) ──
  if (!parent && c.meme2Image) {
    push(`<section>
      <p class="eyebrow">One more thing</p>
      <h2>${esc(c.meme2Image.alt)}</h2>
      <img class="meme-img" src="/assets/img/orientation/${esc(c.meme2Image.file)}" alt="${esc(c.meme2Image.alt)}">
      <p class="meme-caption">${esc(c.meme2Image.caption)}</p>
      ${notes('Second laugh of the deck. Quick beat before the logistics close — let it land, then move.')}
    </section>`);
  } else {
    push(`<section>
      <p class="eyebrow">One more thing</p>
      <div class="meme">
        <div class="panel top"><span class="tag">Expectation</span>${esc(c.meme2.top)}</div>
        <div class="panel bottom"><span class="tag">Reality</span>${esc(c.meme2.bottom)}</div>
      </div>
      <p class="meme-caption">${esc(c.meme2.caption)}</p>
      ${notes('Second laugh of the deck. Quick beat before the logistics close — let it land, then move.')}
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
