# Skill: sub-plan-builder

Produce a substitute plan for one course meeting: a print-ready PDF (and
optionally a webpage link) that a sub can run the class from. The canon is
code, not this doc: before writing anything, read
`assets/css/sub.css` (shared sub-plan components),
`assets/css/syllabus.css` (the sheet theme it layers on), and the pattern
plan kept in the vault at
`~/Vault/teaching/engineering-fundamentals/sub-2026-09-09-grand-challenge-work-day.html`.

## Inputs you need before starting

**Intake first — never build on guesses.** Run the intake in one of two ways:

1. **The form (preferred):** point Willie at the intake form —
   `tools/sub-intake.html` (serve the repo or use
   `class.avendano.xyz/tools/sub-intake.html`). It pre-fills the course's
   Meets line from `calendar/syllabi.json`, checks the date against
   `calendar/2026-27.json` (no-school days, A/B/single altered days,
   1:45/noon dismissals, whether the course even meets that day), and emits
   a structured `INTAKE` prompt. When a message contains that `INTAKE`
   block, it is the source of truth — parse it and go.
2. **Agent-run intake:** no form output? Ask for the missing fields in ONE
   batched round (never drip questions): course + date, room, what's
   happening, the deliverable + due date, special notes, peer-work y/n,
   public-webpage y/n. Everything time-related you look up yourself below.

Regardless of source, **verify, don't trust**:

1. **Course + date + block**: from the course README's `**Meets (2026–27)**`
   line / `calendar/courses.json`. **Never guess clock times.** (Burned once:
   the first sub plan printed Wed/Fri Block 8 as 12:57–2:17; the published
   schedule says **1:40–3:00** — 12:57–1:37 is Advisory. Block times live in
   the published HS Time Schedule, mirrored in the Meets lines; Monday single
   periods use the author-corrected durations already in the Meets lines.)
   The intake form's displayed times are advisory — re-check them.
2. **Room**: from Willie (orientation decks say "Room 503" for EngFund).
3. **The run**: what students do, broken into timed blocks that fill the
   period exactly (start → end, no gaps, no overflow). Time calls land
   mid-block where the sub must intervene.
4. **The deliverable students owe** and **when it's due** — the plan exists
   to protect real graded work, not to babysit.

## Structure rules (from the pattern plan)

- `<div class="sub-banner">` strip (COURSE · BLOCK) → `syl-head` header
  (eyebrow = school + curriculum, h1 = the day's name, year-line = date ·
  times · room).
- **What's happening today**: `syl-contact` grid — Course / Project / Today /
  What's-next. The "Today" row states in one line what students produce.
- **The run of the period**: `run-table` with Time / Block / What-you-do.
  Every row's window sums to the period. Attendance + launch in row 1; wrap
  + next-deadline reminder in the last row.
- **The assignment, in one box**: `sub-box` with a numbered checklist of the
  deliverable's must-haves (what Willie would grade).
- **Practice/feedback prompts** (if the day has peer work): `sub-box` with
  the exact questions the audience answers — the sub reads them off the page.
- **Notes for you**: short list of seating, devices, what's off-limits,
  stuck/early-finisher moves, and how to log incidents.
- **Leave for Mr. Avendano**: `sub-box action` — numbered blanks for
  attendance confirmation + follow-ups. Close with thanks + where the
  roster/emergency folder is.
- Target **2 pages** hard cap (one sheet front/back). Trim copy, not
  structure, to get there. No student names anywhere.

## Style rules

- `<link rel="stylesheet" href="/assets/css/syllabus.css">` +
  `<link rel="stylesheet" href="/assets/css/sub.css">`; one-off styles stay
  inline in the page head and must be genuinely page-specific. `body class="syllabus"`,
  content in `<main class="sheet">`.
- Fonts: Familjen Grotesk display / Atkinson Hyperlegible Next body /
  Fragment Mono for times + labels — via the Google Fonts link in the head.
- Tone: direct, second-person to the sub, zero irony. State expectations as
  instructions ("hold them to it"), never apologies.

## Placement + privacy

- **Default is PRIVATE**: HTML + PDF live in the vault at
  `~/Vault/teaching/<course>/` (never in the site repo — the repo is public;
  "unlinked" is not private).
- **Webpage option**: only when the plan contains nothing private (no names,
  no roster references beyond "see sub folder", no assessment keys) AND
  Willie approves. Then it may live in the repo, e.g.
  `<course>/notes/sub-YYYY-MM-DD-<slug>.html`, linked from the course README
  Notes table; say in the plan that students may also read it.
- **PDF build** (the copy-into-repo dance, because the builder serves the
  repo so `/assets/...` resolve):
  ```
  cp <vault>/sub-plan.html <repo>/<course>/_tmp-sub-plan.html
  node tools/build-handout-pdf.mjs <course>/_tmp-sub-plan.html /tmp/sub-plan.pdf
  mv /tmp/sub-plan.pdf <vault>/teaching/<course>/sub-YYYY-MM-DD-<slug>.pdf
  rm <repo>/<course>/_tmp-sub-plan.html
  ```

## Verification (non-negotiable)

1. `pdftotext -layout` the PDF: header date/times/room match the Meets line;
   run-table windows sum exactly to the period; no stray page 3
   (split on `\f` and count).
2. Times in the plan == times in the course README Meets line — diff by eye.
3. Grep the plan for student names / grade data → must be zero.
4. `node --test tests/*.test.cjs` passes (only matters if repo files changed).

## Commit + sync

- Vault plan: `git -C ~/Vault add -A && git -C ~/Vault commit -m "teaching: <course> sub plan <date>" && git -C ~/Vault push`.
- Repo changes (sub.css, skill, public sub page): commit message
  `"Add sub-plan workflow: sub.css + sub-plan-builder skill"` (or `Revise …`).
- Update the vault memory note for the course/project so the next agent finds it.
