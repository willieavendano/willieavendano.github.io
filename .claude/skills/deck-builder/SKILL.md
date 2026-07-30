---
name: deck-builder
description: Build a course slide deck (reveal.js) for a class.avendano.xyz course, matching the approved Workshop I/II pattern. Use whenever asked to create or revise slides for any course week — read this fully before writing any deck HTML.
---

# Deck Builder

Produce one reveal.js deck per course calendar week, visually and structurally
identical to the approved pattern decks. The canon is code, not this doc: before
writing anything, **read `assets/slides/deck.css` (including its inline pitfall
comments) and the two pattern decks** `physics/slides/u0-w1-speaking-physics.html`
and `physics/slides/u0-w2-the-protocol.html`. Copy their head block exactly
(fonts URL, reveal.js 5 CDN, deck.css link, `hash: true`, slide numbers) —
plus the Math (KaTeX) block below whenever the deck has real formulas.

## Inputs you need before starting

1. **Course + week**: the topic line from the course's Year Calendar table (in
   `<course>/README.md`) is the deck's contract — cover exactly that scope.
2. **Unit tie-ins**: any claim "you'll see this in Unit N" MUST be verified
   against that course's Course Outline table before it goes on a slide.
3. **Naming**: `<course>/slides/u<unit>-w<week>-<slug>.html`.

## Structure rules (from the approved pattern)

- Cover slide (`class="cover"`, blue, grain, mono eyebrow) → content → recap →
  closer (next session / assessment date pulled from the calendar).
- Mono uppercase eyebrows carry section numbering ("Greek Symbols · 2 of 5").
- Blue divider slides for act breaks; tile grids (`tile-grid`, `--cols`) for
  symbol/menu content; KDEA tables for worked problems (see Workshop II).
- ≤ 26 slides. Speaker notes (`<aside class="notes">`) on ≥ 25% of slides —
  written to the teacher, with the "why" and common student failure modes.
- Slides are prompts, not paragraphs: if a body runs two full sentences,
  convert to bullets/tiles. Grids must balance — no orphan tile alone on a
  final row (move content between slides rather than leaving one).

## Content rules

- Real, teachable content — every slide earns its place; activities (pair
  work, turn-and-talk) get a timing eyebrow. Miami flavor welcome (cafecitos
  have precedent).
- **KDEA** is the house protocol: Know / Don't know / Equations / Algebra —
  "The Way to Solve ANY Problem in the World." Never rename or reorder it.
  Units travel with the math; an answer without units does not count.
- Honest math: rounded values use `≈`, never `=` (this burned us once).
  Identities keep `=`.
- HTML discipline: real `<sup>`/`<sub>` markup (never `&supN;` beyond
  sup1/2/3), standard entities only, balanced sections. Units/symbols/data in
  Fragment Mono via the pattern classes.
- No answer keys in student-facing decks.

## Math (KaTeX)

Formulas with radicals, stacked fractions, or relations are typeset with the
reveal.js math plugin + KaTeX — flat entity math (`&radic;[ p(1&minus;p) / n ]`)
is the retired pattern; never write it in new decks. Lone symbols in prose
(p&#770;, v<sup>2</sup>, units, tile icons) stay as HTML entities in Fragment
Mono. Reference deck: `ap-statistics/slides/u3-w1-estimators-sampling-distributions.html`.

- After the notes.js script tag, add
  `<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/math/math.js"></script>`
  and register `RevealMath.KaTeX` in `plugins` (KaTeX assets auto-load from
  the same CDN).
- Display formulas: `<p class="math-line">\( ... \)</p>`, with this one-off
  style block in the deck head (deck.css stays frozen):
  `.math-line { color: var(--blue); font-size: 1.15em; margin: 0.25em 0 0.4em; }`
  `.katex { white-space: nowrap; }`
- The nowrap rule is load-bearing: without it KaTeX line-breaks inline math at
  relations (`\ge`, `=`), splitting a formula mid-expression. Keep each
  formula whole and put any needed break point between two separate
  `\( ... \)` spans (e.g. one per condition, joined by a comma).
- Honest math carries over: `\approx` for rounded values, `=` for identities.
- Inline math in table rows / bullets is fine (`\( SD(\hat{p}) = \sqrt{p(1-p)/n} \)`);
  use `\dfrac` only in display lines where the extra height fits.

## Verification (non-negotiable, in order)

1. `python3 -m http.server <port>` from repo root; curl the deck URL → 200.
2. Playwright: screenshot the cover + every NEW/CHANGED content slide
   (`…#/N`, fresh tab if navigation glitches) — check overflow, collisions,
   grid balance, fonts (paper bg, Familjen headings, mono eyebrows).
3. Grep: no invalid entities; `<section` count matches intended slide count.
4. Kill the server; delete screenshots.

## Integration + commit

- Add/extend the course README's `## Materials` section with the deck link
  (`/​<course>/slides/<file>.html`) under the right unit heading. NEVER touch
  the `<!-- calendar:start/end -->` block.
- Run `node tools/generate-calendars.mjs` (expect all "unchanged") and
  `node --test tests/*.test.cjs` (expect pass) before committing.
- Commit message: `"Add <Course> <unit/week> deck: <title>"` (or `Revise …`).

## Known pitfalls (learned the hard way)

- reveal.js ignores `--r-*` theme vars outside theme files — deck.css uses
  direct rules; don't "fix" it back.
- reveal sets inline `display:block` on active slides — the cover/divider
  flex layout needs the existing `!important`; keep it.
- Text near the bottom edge: wrap computed/long lines in the deck's
  `keep_in_frame` equivalent (size down before overflowing) and never stack
  two text blocks at the bottom edge.
