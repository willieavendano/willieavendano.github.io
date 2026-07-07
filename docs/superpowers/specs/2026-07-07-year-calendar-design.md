# 2026–27 Year Calendar System — Design

**Date:** 2026-07-07
**Repo:** willieavendano.github.io (static GitHub Pages at class.avendano.xyz, no build step)
**First course:** AP Statistics (Fall 2026 CED). Remaining five courses reuse the machinery.

## Goal

Calendar out the 2026–27 school year for Willie's six courses from one source of
truth: the Cushman school calendar + HS rotation schedule + class periods. Output
is a meeting-level, week-topic calendar rendered into each course's README (and
therefore its page on class.avendano.xyz), structured so the same data can seed
Qlass course content later. ICS/Google Calendar feeds are future work.

## Decisions (from brainstorming)

- **Deliverable:** machine-readable calendar data + generated course-page tables
  (options 1+3); calendar feeds linked later.
- **Granularity "1.5":** every meeting gets a dated row (with day-type and
  minutes), topics are assigned per week and flow across that week's meetings;
  hard dates only for fixed events (tests, review start, AP exam, last day).
- **Approach:** data + generator (A). No build step — the generator runs
  manually and its output is committed.
- **CED:** the revised AP Statistics CED effective Fall 2026 (5 units,
  consolidated from old units 1–8; old Unit 9 and several topics removed;
  fully digital Bluebook exam May 2027, 42 MC / 4 FRQs × 10 pts).

## Inputs (verified)

**Rotation (from "HS Time Schedule", 2025-26 template — assumed to carry into
2026-27 until a new sheet appears):**
- Monday: all 8 single periods, 44 min each.
- Tue/Thu: blocks 1–4, 80 min. Wed/Fri: blocks 5–8, 80 min.
- 1:45-dismissal Tuesdays: blocks 1–4 shortened to 72 min.
- Noon-dismissal days: the day keeps its normal rotation, blocks shortened to
  55 min (assumption from the "Block 1/5 … 4/8" combined sheet — flagged to
  Willie, unchallenged).

**Willie's periods (from SIS screenshot):** POE P1, Physics P2, CS Math P3,
AP Statistics P4, Intro to Engineering Design P6, Engineering Fundamentals P8.
Periods 1–4 meet Mon/Tue/Thu; periods 5–8 meet Mon/Wed/Fri. (SIS codes
HSMHSTHSR / HSMHSWHSF corroborate. CS Math shows HSTHSWHSR for semester 2 —
encode per-semester patterns if needed; default is period-derived.)

**2026–27 Cushman calendar:**
- First HS day Mon **2026-08-24**; last day Thu **2027-06-03** (noon dismissal).
- No school: 2026-09-07, 2026-09-21, 2026-11-11, 2026-11-23…11-27,
  2026-12-21…2027-01-04, 2027-01-18, 2027-02-15, 2027-03-22…03-29, 2027-05-31.
- 1:45 dismissal (all Tuesdays): 2026-09-01, 2026-10-06, 2026-12-01,
  2027-01-05, 2027-02-02, 2027-04-06, 2027-05-04, 2027-06-01.
- Noon dismissal: 2026-11-03, 2026-11-20, 2026-12-11, 2026-12-18, 2027-01-22,
  2027-02-12, 2027-03-02, 2027-04-02, 2027-05-28, 2027-06-03.
  (2027-03-19 is PS/ES only — a normal HS day.)

## Architecture

Three units, one-way data flow: **year JSON + course JSON → generator →
README calendar sections**.

### 1. `calendar/2026-27.json`
School-year definition: `firstDay`, `lastDay`, `noSchool[]` (dates and ranges),
`early145[]`, `noonDismissal[]`, and `rotation` (weekday → which periods meet
at what minutes, including dismissal-day overrides). Nothing course-specific.

### 2. `calendar/courses.json`
Per course: `slug` (site directory), `name`, `period`, optional per-semester
`pattern` override, and `plan`:
- `weeks[]`: ordered `{unit, topic}` entries — poured over generated school
  weeks in order.
- `events[]`: `{date, label}` fixed rows (unit tests, review start, AP exam,
  semester boundary ~2027-01-22, last day).
AP Statistics ships with a complete plan; the other five ship with period-only
entries (empty plan → meeting skeleton only).

### 3. `tools/generate-calendars.mjs`
Zero-dependency Node, split as: pure logic in `tools/calendar-lib.cjs`
(require-able by `node --test tests/*.test.cjs`, matching the repo's existing
test convention) + a thin CLI entry `tools/generate-calendars.mjs` that reads
the JSON, calls the lib, and writes files. Algorithm:
1. Expand the year JSON into an ordered list of school days with day-type.
2. For each course, filter to its meeting days; annotate minutes.
3. Group meetings into school weeks; zip `plan.weeks` onto them in order;
   splice `events` rows by date.
4. Render a markdown table (Week | Dates | Unit | Topic | Notes, with
   meeting dates + minutes in the Dates/Notes columns) and write it into
   `<slug>/README.md` between `<!-- calendar:start -->` and
   `<!-- calendar:end -->` markers (idempotent replace; append section with
   markers if absent).

Tests pin edge weeks: Thanksgiving (no meetings), the week of Nov 20 (P4 does
not meet Fri; P8 meets 55 min), 1:45 Tuesdays (P4 72 min, P8 unaffected),
spring break boundary (resume Tue 2027-03-30 — no Monday that week), first
week (starts Monday Aug 24), last week (ends Thu Jun 3 noon).

## AP Statistics plan content (Fall 2026 CED)

Period 4 → Mon 44 + Tue 80 + Thu 80 ≈ 3.4 hrs/week, ~100 meetings before the
May 2027 exam. Implementation downloads the official CED PDF
(apcentral.collegeboard.org → "AP Statistics Course and Exam Description,
Effective Fall 2026") and extracts exact unit titles, exam weightings, and
suggested pacing; it also verifies the AP Statistics slot in College Board's
May 2027 exam schedule. Allocation skeleton (weeks adjust to the extracted
weights):

| Window | Content |
|---|---|
| Aug 24 → mid-Oct (~7 wks) | Unit 1 — one-variable data + collecting data (20–30% weight) |
| mid-Oct → mid-Dec (~7 wks) | Unit 2 — probability, random variables, normal distribution, CLT |
| Jan 5 → mid-Feb (~6 wks) | Unit 3 — inference for proportions + chi-square |
| mid-Feb → mid-Mar (~4 wks) | Unit 4 — inference for means |
| Mar 30 → mid-Apr (~3 wks) | Unit 5 — scatterplots, correlation, least-squares regression |
| ~Apr 19 → exam | AP review — mixed FRQ practice (new 10-pt format), Bluebook digital practice |
| exam → Jun 3 | Post-exam capstone data project |

Unit tests at unit boundaries; semester split lands between Units 2 and 3
(S1 ends ~Jan 22). Removed-in-2026 topics (old 2.9, 4.9, 4.12, chi-square GOF
8.2–8.3, old Unit 9 slopes inference) must NOT appear in topics.

## Error handling

- Generator refuses to write if markers are malformed (one marker present
  without its pair) — prints the file and exits non-zero.
- Unknown slug in courses.json (no matching directory) → error, exit non-zero.
- More plan weeks than school weeks (or vice versa) → warning listing the
  overflow/underflow so pacing gets fixed consciously, still writes.

## Testing / verification

- `node --test` unit tests for the date/rotation/grouping logic (edge weeks
  listed above).
- Regenerate twice → identical output (idempotence).
- Serve locally; AP Statistics page renders the calendar table correctly in
  the existing README pipeline (marked.js).

## Out of scope

- Filling plans for the other five courses (machinery supports them; each is
  a later data-only task).
- Qlass seeding, ICS/Google Calendar feeds (future work; the JSON is designed
  to be the source for both).
- Daily lesson plans / assignments (the plan is week-topic level).
