#!/usr/bin/env node
// Generates the standalone Advisory orientation decks from calendar/advisory.json:
//
//   advisory/slides/orientation-student.html
//   advisory/slides/orientation-parent.html
//
// Advisory has no course page. Teacher bio/contact and the executive-function
// moves come from calendar/orientation.json `shared` so one edit updates every
// deck. Run from the repo root:
//   node tools/generate-advisory.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { esc, head, FOOT, notes } from './orientation-shared.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const A = JSON.parse(fs.readFileSync(path.join(root, 'calendar', 'advisory.json'), 'utf8'));
const S = JSON.parse(fs.readFileSync(path.join(root, 'calendar', 'orientation.json'), 'utf8')).shared;

const CSS = `  /* One-off components for the Advisory decks — deck.css stays frozen. */
  .who-cols { display: grid; grid-template-columns: 340px 1fr; gap: 1.2em; align-items: center; width: 100%; }
  .who-photo { width: 340px; height: 420px; object-fit: cover; object-position: top; border-radius: 12px; border: 1px solid var(--line); display: block; box-shadow: 0 10px 30px rgba(20,40,80,.10); }
  .who-cols .bio-col { font-size: 0.78em; }
  .who-cols .bio-col h2 { margin-bottom: 0.25em; }
  .who-cols .bio-col ul { margin: 0.2em 0 0.45em; }
  .who-cols .bio-col li { margin-bottom: 0.18em; line-height: 1.35; }
  .reveal li.bio-note { color: var(--ink-soft); font-size: 0.9em; }
  .contact-row { display: flex; flex-wrap: wrap; gap: 0.4em; margin-top: 0.5em; }
  .contact-row .chip { font-family: 'Fragment Mono', monospace; font-size: 0.6em; letter-spacing: 0.04em; color: var(--blue); background: var(--white); border: 1px solid var(--line); border-radius: 999px; padding: 0.3em 0.8em; }

  /* Two rhythms: morning + afternoon side by side. */
  .rhythm { display: grid; grid-template-columns: 1fr 1fr; gap: 0.7em; margin-top: 0.5em; }
  .rhythm .r { background: var(--white); border: 1px solid var(--line); border-top: 5px solid var(--blue); border-radius: 6px; padding: 0.6em 0.9em 0.7em; }
  .rhythm .r .when { font-family: 'Fragment Mono', monospace; font-size: 0.55em; letter-spacing: 0.1em; text-transform: uppercase; color: var(--blue); display: block; margin-bottom: 0.2em; }
  .rhythm .r h3 { margin: 0 0 0.25em; font-size: 1.05em; }
  .rhythm .r ul { margin: 0; font-size: 0.8em; }
  .rhythm .r li { margin-bottom: 0.12em; line-height: 1.3; }

  /* Ask-me-anything: speech-bubble grid of real freshman questions. */
  .ask-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5em; margin-top: 0.5em; }
  .ask-grid .q { position: relative; background: var(--white); border: 1px solid var(--line); border-radius: 12px; padding: 0.6em 0.7em; font-family: 'Familjen Grotesk', sans-serif; font-weight: 600; font-size: 0.72em; line-height: 1.25; min-height: 3.6em; display: flex; align-items: center; }
  .ask-grid .q::after { content: ''; position: absolute; left: 1.1em; bottom: -0.55em; width: 0.9em; height: 0.9em; background: var(--white); border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); transform: rotate(45deg); }
  .ask-answer { margin-top: 1em; font-family: 'Fragment Mono', monospace; font-size: 0.6em; letter-spacing: 0.1em; text-transform: uppercase; color: var(--blue); }

  /* Who-does-what table. */
  .role-list { list-style: none; padding: 0; margin: 0.4em 0 0; display: grid; gap: 0.3em; }
  .role-list li { display: grid; grid-template-columns: 11em 1fr; gap: 0.8em; align-items: baseline; background: var(--white); border: 1px solid var(--line); border-radius: 5px; padding: 0.4em 0.7em; font-size: 0.8em; line-height: 1.3; }
  .role-list li:first-child { border-left: 5px solid var(--blue); }
  .role-list .who { font-weight: 700; color: var(--blue); }

  /* The weather check — the daily ritual, drawn as four Miami forecast cards. */
  .weather { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6em; margin-top: 0.5em; }
  .weather .w { background: var(--white); border: 1px solid var(--line); border-radius: 10px; padding: 0.7em 0.6em 0.7em; text-align: center; }
  .weather .w svg { width: 84px; height: 84px; display: block; margin: 0 auto 0.3em; }
  .weather .w .t { font-family: 'Familjen Grotesk', sans-serif; font-weight: 700; font-size: 0.9em; line-height: 1.1; }
  .weather .w .d { font-size: 0.68em; color: var(--ink-soft); margin-top: 0.3em; line-height: 1.3; }
  .weather .w.alert { border-color: var(--blue); border-width: 2px; }

  /* Year arc: four quarters as a strip. */
  .arc { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5em; margin-top: 0.5em; }
  .arc .a { background: var(--white); border: 1px solid var(--line); border-radius: 6px; padding: 0.6em 0.7em 0.7em; }
  .arc .a .q { font-family: 'Fragment Mono', monospace; font-size: 0.6em; color: var(--white); background: var(--blue); border-radius: 3px; padding: 0.1em 0.5em; }
  .arc .a .t { display: block; font-family: 'Familjen Grotesk', sans-serif; font-weight: 700; font-size: 1em; margin-top: 0.35em; }
  .arc .a .d { display: block; font-size: 0.7em; color: var(--ink-soft); line-height: 1.3; margin-top: 0.25em; }

  /* Tile grids: norms, ice breakers, rituals, parent lists. */
  .six-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5em; margin-top: 0.4em; }
  .six-grid .tile .name { margin-top: 0; }
  .six-grid .tile .use { margin-top: 0.3em; }
  .three-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6em; margin-top: 0.5em; }

  .check-list { list-style: none; padding: 0; margin: 0.4em 0 0; display: grid; grid-template-columns: 1fr 1fr; gap: 0.35em 0.8em; }
  .check-list li { display: flex; gap: 0.6em; align-items: baseline; background: var(--white); border: 1px solid var(--line); border-radius: 5px; padding: 0.4em 0.7em; font-size: 0.82em; line-height: 1.3; }
  .check-list .box { flex: none; width: 0.9em; height: 0.9em; border: 2px solid var(--blue); border-radius: 3px; transform: translateY(0.1em); }

  .meme { max-width: 24em; margin: 0.4em auto 0; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: var(--white); }
  .meme .panel { padding: 0.75em 0.9em; font-family: 'Familjen Grotesk', sans-serif; font-weight: 600; font-size: 0.82em; line-height: 1.3; }
  .meme .panel.top { border-bottom: 1px solid var(--line); }
  .meme .panel.bottom { background: var(--paper-deep); }
  .meme .tag { display: block; font-family: 'Fragment Mono', monospace; font-size: 0.5em; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-soft); margin-bottom: 0.25em; }
  .meme-caption { margin-top: 0.7em; font-size: 0.78em; color: var(--ink-soft); max-width: 30em; margin-left: auto; margin-right: auto; }

  ul.dense li { margin-bottom: 0.18em; line-height: 1.35; }
  ul.dense { margin-top: 0.3em; }
`;

// Weather glyphs in the deck palette. Hurricane is the only one in solid blue —
// it is the one that triggers a conversation.
const B = '#0E406A', SKY = '#4D8BC9', SOFT = '#d6dde6';
const ICON = {
  sun: `<svg viewBox="0 0 84 84" aria-hidden="true"><circle cx="42" cy="42" r="16" fill="#F2B134"/><g stroke="#F2B134" stroke-width="4" stroke-linecap="round">${[0,45,90,135,180,225,270,315].map(a => `<line x1="42" y1="10" x2="42" y2="18" transform="rotate(${a} 42 42)"/>`).join('')}</g></svg>`,
  cloud: `<svg viewBox="0 0 84 84" aria-hidden="true"><circle cx="30" cy="32" r="12" fill="#F2B134"/><path d="M24 62h34a11 11 0 0 0 1-22 15 15 0 0 0-28-4 10 10 0 0 0-7 26z" fill="#fff" stroke="${B}" stroke-width="3" stroke-linejoin="round"/></svg>`,
  storm: `<svg viewBox="0 0 84 84" aria-hidden="true"><path d="M22 50h38a11 11 0 0 0 1-22 15 15 0 0 0-28-4 10 10 0 0 0-11 26z" fill="${SOFT}" stroke="${B}" stroke-width="3" stroke-linejoin="round"/><path d="M44 46l-10 16h9l-4 14 14-20h-9l5-10z" fill="#F2B134" stroke="${B}" stroke-width="2" stroke-linejoin="round"/></svg>`,
  hurricane: `<svg viewBox="0 0 84 84" aria-hidden="true"><g fill="none" stroke="${B}" stroke-width="7" stroke-linecap="round"><circle cx="42" cy="42" r="10"/><path d="M52 40A20 20 0 0 0 22 20"/><path d="M32 44A20 20 0 0 0 62 64"/></g></svg>`,
};

function who() {
  return `<section>
      <p class="eyebrow">Who is your advisor</p>
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
      ${notes('Longer than the course version — a minute. This group sees you every day for a year; the coaching and the cold brew are the hooks. Then ask them one thing about themselves before moving on.')}
    </section>`;
}

function jobs() {
  return `<section>
      <p class="eyebrow">What advisory is</p>
      <h2>Three jobs</h2>
      <div class="tile-grid three-grid" style="--cols:3">
        ${A.jobs.map(j => `<div class="tile"><span class="name">${esc(j.t)}</span><p class="use">${esc(j.d)}</p></div>`).join('\n        ')}
      </div>
      ${notes('Say the first one slowly. Ninth graders do not know there is a person whose job is to be asked. Make it concrete: name a question you answered for an advisee last year.')}
    </section>`;
}

function rhythm() {
  const m = A.meets.morning, a = A.meets.afternoon;
  return `<section>
      <p class="eyebrow">When we meet</p>
      <h2>Two rhythms</h2>
      <div class="rhythm">
        <div class="r"><span class="when">${esc(m.when)}</span><h3>The check-in</h3><ul>${m.what.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
        <div class="r"><span class="when">${esc(a.when)}</span><h3>The real work</h3><ul>${a.what.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
      </div>
      ${notes('Ten minutes in the morning is short on purpose — it is a pulse check, not a class. The afternoons carry the program. Say out loud that the afternoons are not a study hall.')}
    </section>`;
}

function ask() {
  return `<section>
      <p class="eyebrow">Ask me anything</p>
      <h2>Real questions from real ninth graders</h2>
      <div class="ask-grid">
        ${A.askMe.map(q => `<div class="q">${esc(q)}</div>`).join('\n        ')}
      </div>
      <p class="ask-answer">The answer to every one of these starts with: come find me.</p>
      ${notes('Read two or three in a student voice. The point is permission — they should leave knowing there is no question too small or too awkward for 8:00 in the morning.')}
    </section>`;
}

function roles(parent) {
  return `<section>
      <p class="eyebrow">Who does what at Cushman</p>
      <h2>Start with me. I route.</h2>
      <ul class="role-list">
        ${A.roles.map(r => `<li><span class="who">${esc(r.who)}</span><span>${esc(r.for)}</span></li>`).join('\n        ')}
      </ul>
      ${notes(parent
        ? 'This is the slide parents photograph. Names of the counselor, dean, and director go here once confirmed — until then the roles are accurate and the routing rule holds: start with the advisor.'
        : 'Freshmen genuinely do not know these are different people. Keep it simple: when in doubt, me first.')}
    </section>`;
}

function weather(parent) {
  return `<section>
      <p class="eyebrow">${parent ? 'What the mornings look like' : 'Every morning'} &middot; the weather check</p>
      <h2>One word. No explanation required.</h2>
      <div class="weather">
        ${A.weather.map(w => `<div class="w${w.icon === 'hurricane' ? ' alert' : ''}">${ICON[w.icon]}<div class="t">${esc(w.t)}</div><div class="d">${esc(w.d)}</div></div>`).join('\n        ')}
      </div>
      ${notes(parent
        ? 'Tell parents to use the same four words at home. It works because it is low-stakes: a one-word answer is easy to give and hard to hide behind.'
        : 'Model it yourself first, honestly — a "partly cloudy" from you on day one gives them permission. Hurricane means you follow up privately, before lunch, every time. Never skip that; it is the whole credibility of the ritual.')}
    </section>`;
}

function arc() {
  return `<section>
      <p class="eyebrow">The year &middot; afternoons</p>
      <h2>Where the afternoons go</h2>
      <div class="arc">
        ${A.arc.map(a => `<div class="a"><span class="q">${esc(a.q)}</span><span class="t">${esc(a.t)}</span><span class="d">${esc(a.d)}</span></div>`).join('\n        ')}
      </div>
      ${notes('The specific SEL themes are internal — this is the shape, not the syllabus. Say that the arc follows the year a ninth grader actually has: arrive, get stressed, find your people, look ahead.')}
    </section>`;
}

function ef() {
  return `<section>
      <p class="eyebrow">Executive function &middot; practised here daily</p>
      <h2>The four moves</h2>
      <ul class="dense">
        ${S.executiveFunction.map(e => `<li><strong>${esc(e.t)}.</strong> ${esc(e.d)}</li>`).join('\n        ')}
      </ul>
      ${notes('Same four moves as every course deck — on purpose. Advisory is where they get rehearsed: planner checks in the morning, start-tonight reminders on Wednesdays.')}
    </section>`;
}

function norms() {
  return `<section>
      <p class="eyebrow">Circle agreements</p>
      <h2>How the room runs</h2>
      <div class="tile-grid six-grid" style="--cols:3">
        ${A.norms.map(n => `<div class="tile"><span class="name">${esc(n.t)}</span><p class="use">${esc(n.d)}</p></div>`).join('\n        ')}
      </div>
      ${notes('Have them agree out loud, not just nod. On Wednesday, add one of their own to the list and write it on the wall.')}
    </section>`;
}

function meme(i) {
  const m = A.memes[i];
  return `<section>
      <p class="eyebrow">The honest version</p>
      <div class="meme">
        <div class="panel top"><span class="tag">Expectation</span>${esc(m.top)}</div>
        <div class="panel bottom"><span class="tag">Reality</span>${esc(m.bottom)}</div>
      </div>
      <p class="meme-caption">${esc(m.caption)}</p>
      ${notes('Let it land, say the caption, move.')}
    </section>`;
}

function firstWeek() {
  return `<section>
      <p class="eyebrow">Week one</p>
      <h2>Survival checklist</h2>
      <ul class="check-list">
        ${A.firstWeek.map(f => `<li><span class="box"></span><span>${esc(f)}</span></li>`).join('\n        ')}
      </ul>
      ${notes('We check these off together Tuesday morning. The schedule one matters most — A/B days trip up every ninth grader in week one.')}
    </section>`;
}

function iceBreakers() {
  return `<section>
      <p class="eyebrow">Week one &middot; we play first</p>
      <h2>Pick two. I will pick a third.</h2>
      <div class="tile-grid six-grid" style="--cols:3">
        ${A.iceBreakers.map(n => `<div class="tile"><span class="name">${esc(n.t)}</span><p class="use">${esc(n.d)}</p></div>`).join('\n        ')}
      </div>
      ${notes('Twelve students: every one of these works as a full circle in ten minutes. Let them vote on two; you choose the third (Miami map is the sleeper hit — it tells you who commutes an hour). Run one per afternoon in week one and two, not all at once.')}
    </section>`;
}

function rituals() {
  return `<section>
      <p class="eyebrow">All year</p>
      <h2>Our rituals</h2>
      <div class="tile-grid three-grid" style="--cols:3">
        ${A.rituals.map(n => `<div class="tile"><span class="name">${esc(n.t)}</span><p class="use">${esc(n.d)}</p></div>`).join('\n        ')}
      </div>
      ${notes('Rituals are what make twelve strangers a group. Start the playlist on day two; start shout-outs the first Friday even if you are the only one talking.')}
    </section>`;
}

function parentList(eyebrow, h2, items, note) {
  return `<section>
      <p class="eyebrow">${eyebrow}</p>
      <h2>${h2}</h2>
      <ul class="dense">
        ${items.map(e => `<li><strong>${esc(e.t)}.</strong> ${esc(e.d)}</li>`).join('\n        ')}
      </ul>
      ${notes(note)}
    </section>`;
}

function reach() {
  return `<section>
      <p class="eyebrow">Getting help</p>
      <h2>How to reach me</h2>
      <ul>
        <li><strong>Every morning.</strong> 8:00–8:10 in Room ${esc(S.room)}. I am there from 7:45 with a cold brew.</li>
        <li><strong>Extra help.</strong> ${esc(S.extraHelp)} &mdash; ${esc(S.extraHelpNote)}</li>
        <li><strong>Email.</strong> ${esc(S.email)} &mdash; within 24 hours on school days; Friday emails answered by Monday.</li>
      </ul>
      ${notes('Last content slide. The 7:45 line is real and it is the most-used door all year.')}
    </section>`;
}

function deck(audience) {
  const parent = audience === 'parent';
  const s = [];

  s.push(`<section class="cover">
      <p class="eyebrow">Advisory &middot; ${esc(A.cohort)} &middot; ${esc(A.year)}</p>
      <h1>Advisory</h1>
      <p class="kicker-line">${parent ? 'Parent Night' : 'Your home base at Cushman'}</p>
      <div class="rule"></div>
      <p class="meta-line">${esc(A.meets.morning.when)} &middot; ${esc(A.meets.afternoon.when)}</p>
      ${notes(parent
        ? 'Parent Night for advisory. Most of these parents have a first-time high schooler. The job of this deck is to make them use you: what to email you about, what to email the teacher about, and what the mornings and afternoons are actually for.'
        : 'Day one. Twelve students, most of whom do not know what advisory is. Do not read the slides — this is the room where you get to be a person first. Aim for ten minutes of deck and ten minutes of an ice breaker.')}
    </section>`);

  s.push(who());

  s.push(`<section class="divider">
      <p class="eyebrow">Advisory</p>
      <h2>${parent ? 'One adult who knows your kid, every day.' : `${A.size} of you. One room. Every morning, all year.`}</h2>
    </section>`);

  s.push(jobs());
  s.push(rhythm());

  if (parent) {
    s.push(parentList('How to use your advisor', 'Me first, for almost everything', A.parent.useMe,
      'The routing rule is the most useful thing parents take home. Non-academic → advisor. Grade → teacher, copy the advisor.'));
    s.push(roles(true));
    s.push(weather(true));
    s.push(ef());
    s.push(arc());
    s.push(parentList('How to help at home', 'Four things that work', A.parent.atHome,
      'End on the charger line — parents laugh, and it is the actual advice.'));
    s.push(parentList('Honest boundaries', 'What an advisor is not', A.parent.notThis,
      'Say this plainly. Parents trust the role more when its edges are clear.'));
    s.push(meme(0));
  } else {
    s.push(ask());
    s.push(roles(false));
    s.push(weather(false));
    s.push(arc());
    s.push(ef());
    s.push(norms());
    s.push(meme(0));
    s.push(firstWeek());
    s.push(iceBreakers());
    s.push(rituals());
    s.push(meme(2));
  }

  s.push(reach());

  s.push(`<section class="cover">
      <p class="eyebrow">Tomorrow</p>
      <h1>8:00 &middot; Room ${esc(S.room)}</h1>
      <p class="kicker-line">${parent ? 'Email me. That is the whole system.' : 'Bring one question. Any question.'}</p>
      <div class="rule"></div>
      <p class="meta-line">${esc(S.email)}</p>
      ${notes(parent ? 'Leave the email on screen while you take questions.' : 'Then run the first ice breaker. Do not let them leave without learning two names.')}
    </section>`);

  return head(`Advisory — ${parent ? 'Parent Night' : 'Orientation'} ${A.year}`, CSS) + '\n' + s.join('\n\n') + '\n' + FOOT;
}

const dir = path.join(root, 'advisory', 'slides');
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
for (const aud of ['student', 'parent']) {
  const out = path.join(dir, `orientation-${aud}.html`);
  const body = deck(aud);
  if (fs.existsSync(out) && fs.readFileSync(out, 'utf8') === body) { console.log(`unchanged advisory/slides/orientation-${aud}.html`); continue; }
  fs.writeFileSync(out, body);
  console.log(`wrote advisory/slides/orientation-${aud}.html (${(body.match(/<section/g) || []).length} slides)`);
}
