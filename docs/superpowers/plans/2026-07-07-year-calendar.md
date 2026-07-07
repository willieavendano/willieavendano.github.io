# 2026–27 Year Calendar System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate meeting-level, week-topic year calendars for Willie's six 2026–27 courses from one JSON source of truth, rendered into each course README — AP Statistics fully populated from the Fall 2026 CED.

**Architecture:** Two data files (`calendar/2026-27.json` school year, `calendar/courses.json` courses + plans) feed pure logic in `tools/calendar-lib.cjs` (school-day expansion → per-course meetings → week grouping → plan zip → markdown), driven by a thin CLI `tools/generate-calendars.mjs` that splices output into READMEs between markers. Generator runs manually; output is committed (GitHub Pages stays build-free).

**Tech Stack:** Plain Node ≥18 (zero dependencies), `node --test` built-in runner, JSON data, markdown output rendered by the existing marked.js course shell.

**Spec:** `docs/superpowers/specs/2026-07-07-year-calendar-design.md`

## Global Constraints

- No build step; generated README sections are committed. `.nojekyll` untouched.
- Zero npm dependencies. Tests run with `node --test tests/*.test.cjs` (NEVER bare `node --test tests/` — it fails on this machine's Node 22.22.3).
- Rotation rules (from the HS Time Schedule): Mon = all 8 periods, 44 min singles. Tue/Thu = blocks 1–4, Wed/Fri = blocks 5–8, 80 min. 1:45-dismissal Tuesdays = blocks 1–4 at 72 min. Noon-dismissal days = the day's normal blocks at 55 min. A non-`normal` Monday is unsupported → throw (none exist in 2026–27).
- Course periods: POE 1, Physics 2, CS Math 3, AP Statistics 4, Intro to Engineering Design 6, Engineering Fundamentals 8.
- The 2026–27 year has exactly **37 teaching weeks** (weeks containing ≥1 school day); AP Statistics' plan MUST have exactly 37 week entries.
- Fall 2026 CED units (exact titles/weights, from the official CED): Unit 1 "Exploring One-Variable Data and Collecting Data" 20–30% (~26 periods); Unit 2 "Probability, Random Variables, and Probability Distributions" 15–25% (~24); Unit 3 "Inference for Categorical Data: Proportions" 15–25% (~30); Unit 4 "Inference for Quantitative Data: Means" 10–20% (~18); Unit 5 "Regression Analysis" 10–20% (~9).
- Removed-in-2026 topics must not appear anywhere in the AP Statistics plan: no geometric distribution, no chi-square goodness-of-fit, no inference for slopes. (`grep -i 'geometric\|goodness\|slope' calendar/courses.json` must return nothing.)
- The May 2027 AP Statistics exam date is NOT yet published — model it as the window 2027-05-03…2027-05-14 labeled "exact date TBA (College Board publishes the 2027 schedule in fall 2026)".
- Markers in READMEs: exactly `<!-- calendar:start -->` and `<!-- calendar:end -->`.
- Execute in an isolated worktree (superpowers:using-git-worktrees) — not directly on master. Commit per task; do NOT push (pushing master deploys the live site; the user decides).
- Work from the repo root: /Users/willieavendano/Developer/Cushman_Code/willieavendano.github.io (or its worktree).

---

### Task 1: Year data + `expandSchoolDays`

**Files:**
- Create: `calendar/2026-27.json`
- Create: `tools/calendar-lib.cjs`
- Test: `tests/calendar-lib.test.cjs`

**Interfaces:**
- Consumes: nothing.
- Produces: `calendar/2026-27.json` (shape below); `tools/calendar-lib.cjs` exporting `expandSchoolDays(year) -> [{date:'YYYY-MM-DD', weekday:1..5, type:'normal'|'early145'|'noon'}]` (school days only, chronological). Internal helpers `parseDate`, `iso`, `addDays`, `mondayOf(dateStr) -> 'YYYY-MM-DD'` are also exported (later tasks and tests use `mondayOf`).

- [ ] **Step 1: Create `calendar/2026-27.json`** with exactly:

```json
{
  "label": "2026-27",
  "firstDay": "2026-08-24",
  "lastDay": "2027-06-03",
  "noSchool": [
    "2026-09-07",
    "2026-09-21",
    "2026-11-11",
    { "from": "2026-11-23", "to": "2026-11-27" },
    { "from": "2026-12-21", "to": "2027-01-04" },
    "2027-01-18",
    "2027-02-15",
    { "from": "2027-03-22", "to": "2027-03-29" },
    "2027-05-31"
  ],
  "early145": [
    "2026-09-01", "2026-10-06", "2026-12-01", "2027-01-05",
    "2027-02-02", "2027-04-06", "2027-05-04", "2027-06-01"
  ],
  "noonDismissal": [
    "2026-11-03", "2026-11-20", "2026-12-11", "2026-12-18",
    "2027-01-22", "2027-02-12", "2027-03-02", "2027-04-02",
    "2027-05-28", "2027-06-03"
  ]
}
```

- [ ] **Step 2: Write the failing tests**

Create `tests/calendar-lib.test.cjs`:

```js
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const lib = require('../tools/calendar-lib.cjs');

const YEAR = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'calendar', '2026-27.json'), 'utf8'));
const DAYS = lib.expandSchoolDays(YEAR);
const byDate = new Map(DAYS.map(d => [d.date, d]));

test('year starts Mon Aug 24 and ends Thu Jun 3 (noon)', () => {
  assert.strictEqual(DAYS[0].date, '2026-08-24');
  assert.strictEqual(DAYS[0].weekday, 1);
  assert.strictEqual(DAYS[0].type, 'normal');
  const last = DAYS[DAYS.length - 1];
  assert.strictEqual(last.date, '2027-06-03');
  assert.strictEqual(last.weekday, 4);
  assert.strictEqual(last.type, 'noon');
});

test('holidays and breaks are excluded', () => {
  for (const d of ['2026-09-07', '2026-11-11', '2026-11-25', '2026-12-28', '2027-01-01', '2027-01-18', '2027-03-24', '2027-03-29', '2027-05-31']) {
    assert.ok(!byDate.has(d), d + ' should not be a school day');
  }
  assert.ok(byDate.has('2027-03-30'), 'school resumes Tue 2027-03-30');
  assert.ok(byDate.has('2027-01-05'), 'school resumes Tue 2027-01-05');
});

test('dismissal day types are tagged', () => {
  assert.strictEqual(byDate.get('2026-09-01').type, 'early145');
  assert.strictEqual(byDate.get('2026-11-20').type, 'noon');
  assert.strictEqual(byDate.get('2026-11-20').weekday, 5);
  assert.strictEqual(byDate.get('2026-08-25').type, 'normal');
});

test('weekends never appear', () => {
  assert.ok(DAYS.every(d => d.weekday >= 1 && d.weekday <= 5));
});

test('mondayOf maps any date to its civil-week Monday', () => {
  assert.strictEqual(lib.mondayOf('2026-08-27'), '2026-08-24'); // Thu -> Mon
  assert.strictEqual(lib.mondayOf('2026-08-24'), '2026-08-24');
  assert.strictEqual(lib.mondayOf('2027-01-05'), '2027-01-04'); // Tue -> (off) Mon
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: FAIL — `Cannot find module '../tools/calendar-lib.cjs'`

- [ ] **Step 4: Implement `tools/calendar-lib.cjs`**

```js
// Pure calendar logic for the 2026-27 year calendar generator.
// No dependencies; consumed by tools/generate-calendars.mjs and node --test.
'use strict';

function parseDate(s) {
  var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) throw new Error('Bad date: ' + s);
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function iso(d) {
  function p(n) { return String(n).padStart(2, '0'); }
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}

function addDays(d, n) {
  var c = new Date(d);
  c.setDate(c.getDate() + n);
  return c;
}

function expandNoSchool(list) {
  var set = new Set();
  (list || []).forEach(function (entry) {
    if (typeof entry === 'string') { set.add(entry); return; }
    var d = parseDate(entry.from);
    var end = parseDate(entry.to);
    while (d <= end) { set.add(iso(d)); d = addDays(d, 1); }
  });
  return set;
}

function expandSchoolDays(year) {
  var noSchool = expandNoSchool(year.noSchool);
  var early = new Set(year.early145 || []);
  var noon = new Set(year.noonDismissal || []);
  var days = [];
  var d = parseDate(year.firstDay);
  var last = parseDate(year.lastDay);
  while (d <= last) {
    var dow = d.getDay(); // 0=Sun .. 6=Sat
    var s = iso(d);
    if (dow >= 1 && dow <= 5 && !noSchool.has(s)) {
      days.push({
        date: s,
        weekday: dow,
        type: noon.has(s) ? 'noon' : early.has(s) ? 'early145' : 'normal'
      });
    }
    d = addDays(d, 1);
  }
  return days;
}

function mondayOf(dateStr) {
  var d = parseDate(dateStr);
  return iso(addDays(d, -((d.getDay() + 6) % 7)));
}

module.exports = { parseDate: parseDate, iso: iso, addDays: addDays, expandSchoolDays: expandSchoolDays, mondayOf: mondayOf };
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: 5 tests PASS (existing `tests/qlass-feed.test.cjs` unaffected: `node --test tests/*.test.cjs` → 13 pass total).

- [ ] **Step 6: Commit**

```bash
git add calendar/2026-27.json tools/calendar-lib.cjs tests/calendar-lib.test.cjs
git commit -m "Add 2026-27 school year data and school-day expansion"
```

---

### Task 2: `meetingsForCourse` — rotation + dismissal rules

**Files:**
- Modify: `tools/calendar-lib.cjs`
- Test: `tests/calendar-lib.test.cjs` (append)

**Interfaces:**
- Consumes: `expandSchoolDays` output from Task 1.
- Produces: `meetingsForCourse(days, period) -> [{date, weekday, minutes, kind:'single'|'block'|'short-block'}]`, exported from the lib.

- [ ] **Step 1: Append failing tests** to `tests/calendar-lib.test.cjs`:

```js
test('period 4 meets Mon/Tue/Thu; period 8 meets Mon/Wed/Fri', () => {
  const p4 = lib.meetingsForCourse(DAYS, 4);
  const p8 = lib.meetingsForCourse(DAYS, 8);
  assert.ok(p4.every(m => [1, 2, 4].includes(m.weekday)));
  assert.ok(p8.every(m => [1, 3, 5].includes(m.weekday)));
  // first week of school
  assert.deepStrictEqual(p4.filter(m => m.date < '2026-08-31').map(m => m.date),
    ['2026-08-24', '2026-08-25', '2026-08-27']);
  assert.deepStrictEqual(p8.filter(m => m.date < '2026-08-31').map(m => m.date),
    ['2026-08-24', '2026-08-26', '2026-08-28']);
});

test('minutes: Mon single 44, full block 80, 1:45 Tue 72, noon 55', () => {
  const p4 = lib.meetingsForCourse(DAYS, 4);
  const by = new Map(p4.map(m => [m.date, m]));
  assert.strictEqual(by.get('2026-08-24').minutes, 44);
  assert.strictEqual(by.get('2026-08-24').kind, 'single');
  assert.strictEqual(by.get('2026-08-25').minutes, 80);
  assert.strictEqual(by.get('2027-01-05').minutes, 72);  // 1:45 dismissal Tuesday
  assert.strictEqual(by.get('2026-11-03').minutes, 55);  // noon-dismissal Tuesday
  assert.ok(!by.has('2026-11-20'), 'P4 does not meet Fridays even on noon dismissal');
  const p8 = new Map(lib.meetingsForCourse(DAYS, 8).map(m => [m.date, m]));
  assert.strictEqual(p8.get('2026-11-20').minutes, 55);  // noon Friday, block 8 shortened
  assert.ok(!p8.has('2026-09-01'), '1:45 Tuesdays do not involve periods 5-8');
});

test('invalid period throws', () => {
  assert.throws(() => lib.meetingsForCourse(DAYS, 0));
  assert.throws(() => lib.meetingsForCourse(DAYS, 9));
});
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: FAIL — `lib.meetingsForCourse is not a function`

- [ ] **Step 3: Implement** — add to `tools/calendar-lib.cjs` (before `module.exports`) and export:

```js
var BLOCK_DAYS = { 2: [1, 2, 3, 4], 4: [1, 2, 3, 4], 3: [5, 6, 7, 8], 5: [5, 6, 7, 8] };

function meetingsForCourse(days, period) {
  if (!Number.isInteger(period) || period < 1 || period > 8) throw new Error('Bad period: ' + period);
  var out = [];
  days.forEach(function (day) {
    if (day.weekday === 1) {
      if (day.type !== 'normal') throw new Error('Unsupported non-normal Monday: ' + day.date);
      out.push({ date: day.date, weekday: 1, minutes: 44, kind: 'single' });
      return;
    }
    if (BLOCK_DAYS[day.weekday].indexOf(period) === -1) return;
    if (day.type === 'noon') out.push({ date: day.date, weekday: day.weekday, minutes: 55, kind: 'short-block' });
    else if (day.type === 'early145') out.push({ date: day.date, weekday: day.weekday, minutes: 72, kind: 'short-block' });
    else out.push({ date: day.date, weekday: day.weekday, minutes: 80, kind: 'block' });
  });
  return out;
}
```

Update the export line to include it:

```js
module.exports = { parseDate: parseDate, iso: iso, addDays: addDays, expandSchoolDays: expandSchoolDays, mondayOf: mondayOf, meetingsForCourse: meetingsForCourse };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/calendar-lib.cjs tests/calendar-lib.test.cjs
git commit -m "Add per-course meeting derivation from rotation and dismissal rules"
```

---

### Task 3: `buildCourseWeeks` + `applyPlan`

**Files:**
- Modify: `tools/calendar-lib.cjs`
- Test: `tests/calendar-lib.test.cjs` (append)

**Interfaces:**
- Consumes: Task 1–2 functions.
- Produces (exported): `buildCourseWeeks(days, period) -> [{weekStart, schoolDays:[dates], meetings:[Task-2 meeting objects]}]` — one entry per teaching week (weeks with zero school days don't appear; a week appears even if this course happens not to meet). `applyPlan(weeks, plan) -> {rows, warnings}` where `plan = {weeks:[{unit, topic}], events:[{date, label}]}` and each row is `{index, weekStart, schoolDays, meetings, unit, topic, notes:[labels]}` — plan weeks zip by index, events attach to the row whose civil week contains `event.date`.

- [ ] **Step 1: Append failing tests**

```js
test('the 2026-27 year has exactly 37 teaching weeks', () => {
  const weeks = lib.buildCourseWeeks(DAYS, 4);
  assert.strictEqual(weeks.length, 37);
  assert.strictEqual(weeks[0].weekStart, '2026-08-24');
  assert.strictEqual(weeks[weeks.length - 1].weekStart, '2027-05-31');
  const starts = weeks.map(w => w.weekStart);
  assert.ok(!starts.includes('2026-11-23'), 'Thanksgiving week has no school days');
  assert.ok(!starts.includes('2026-12-21') && !starts.includes('2026-12-28') && !starts.includes('2027-03-22'));
});

test('short weeks carry the right meetings', () => {
  const weeks = lib.buildCourseWeeks(DAYS, 4);
  const jan = weeks.find(w => w.weekStart === '2027-01-04');
  assert.deepStrictEqual(jan.meetings.map(m => m.date), ['2027-01-05', '2027-01-07']);
  const resume = weeks.find(w => w.weekStart === '2027-03-29');
  assert.deepStrictEqual(resume.meetings.map(m => m.date), ['2027-03-30', '2027-04-01']);
});

test('applyPlan zips weeks by index and attaches events by date', () => {
  const weeks = lib.buildCourseWeeks(DAYS, 4);
  const plan = {
    weeks: weeks.map((w, i) => ({ unit: 'U', topic: 'T' + (i + 1) })),
    events: [{ date: '2026-10-08', label: 'Unit 1 Test' }]
  };
  const { rows, warnings } = lib.applyPlan(weeks, plan);
  assert.strictEqual(warnings.length, 0);
  assert.strictEqual(rows.length, 37);
  assert.strictEqual(rows[0].topic, 'T1');
  const oct = rows.find(r => r.weekStart === '2026-10-05');
  assert.deepStrictEqual(oct.notes, ['Unit 1 Test']);
});

test('applyPlan warns on week-count mismatch and tolerates empty plans', () => {
  const weeks = lib.buildCourseWeeks(DAYS, 4);
  const { warnings } = lib.applyPlan(weeks, { weeks: [{ unit: '1', topic: 'only one' }], events: [] });
  assert.strictEqual(warnings.length, 1);
  const empty = lib.applyPlan(weeks, { weeks: [], events: [] });
  assert.strictEqual(empty.warnings.length, 0);
  assert.strictEqual(empty.rows[0].topic, '');
});
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: FAIL — `lib.buildCourseWeeks is not a function`

- [ ] **Step 3: Implement** — add to the lib and export both:

```js
function buildCourseWeeks(days, period) {
  var meetings = meetingsForCourse(days, period);
  var byWeek = new Map();
  days.forEach(function (day) {
    var wk = mondayOf(day.date);
    if (!byWeek.has(wk)) byWeek.set(wk, { weekStart: wk, schoolDays: [], meetings: [] });
    byWeek.get(wk).schoolDays.push(day.date);
  });
  meetings.forEach(function (m) { byWeek.get(mondayOf(m.date)).meetings.push(m); });
  return Array.from(byWeek.values());
}

function applyPlan(weeks, plan) {
  var planWeeks = (plan && plan.weeks) || [];
  var events = (plan && plan.events) || [];
  var warnings = [];
  if (planWeeks.length > 0 && planWeeks.length !== weeks.length) {
    warnings.push('plan has ' + planWeeks.length + ' week entries but the year has ' + weeks.length + ' teaching weeks');
  }
  var rows = weeks.map(function (w, i) {
    var p = planWeeks[i] || {};
    return {
      index: i + 1,
      weekStart: w.weekStart,
      schoolDays: w.schoolDays,
      meetings: w.meetings,
      unit: p.unit || '',
      topic: p.topic || '',
      notes: events.filter(function (e) { return mondayOf(e.date) === w.weekStart; }).map(function (e) { return e.label; })
    };
  });
  return { rows: rows, warnings: warnings };
}
```

Add `buildCourseWeeks: buildCourseWeeks, applyPlan: applyPlan` to `module.exports`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/calendar-lib.cjs tests/calendar-lib.test.cjs
git commit -m "Add week grouping and plan zipping"
```

---

### Task 4: `renderCalendarMd` + `spliceCalendarSection`

**Files:**
- Modify: `tools/calendar-lib.cjs`
- Test: `tests/calendar-lib.test.cjs` (append)

**Interfaces:**
- Consumes: `applyPlan` rows from Task 3.
- Produces (exported): `renderCalendarMd(courseName, rows) -> string` (a `## Year Calendar (2026–27)` markdown section); `spliceCalendarSection(readmeText, sectionMd) -> string` (replaces content between `<!-- calendar:start -->` / `<!-- calendar:end -->`, appends markers+section at end if absent, throws if exactly one marker present). Constants `START_MARK`/`END_MARK` exported.

- [ ] **Step 1: Append failing tests**

```js
test('renderCalendarMd produces a table row per week with meetings and notes', () => {
  const rows = [{
    index: 1, weekStart: '2026-08-24', schoolDays: ['2026-08-24', '2026-08-25'],
    meetings: [
      { date: '2026-08-24', weekday: 1, minutes: 44, kind: 'single' },
      { date: '2026-08-25', weekday: 2, minutes: 80, kind: 'block' }
    ],
    unit: '1', topic: '1.1–1.2 — Intro', notes: ['First day']
  }];
  const md = lib.renderCalendarMd('AP Statistics', rows);
  assert.ok(md.startsWith('## Year Calendar (2026–27)'));
  assert.ok(md.includes('| 1 | Aug 24 | Mon 8/24 (44m) · Tue 8/25 (80m) | 1 | 1.1–1.2 — Intro | First day |'));
});

test('spliceCalendarSection appends markers when absent and replaces idempotently', () => {
  const section = '## Year Calendar (2026–27)\n\n| a |\n';
  const once = lib.spliceCalendarSection('# Course\n\nBody\n', section);
  assert.ok(once.includes(lib.START_MARK) && once.includes(lib.END_MARK));
  assert.ok(once.includes('| a |'));
  const twice = lib.spliceCalendarSection(once, section);
  assert.strictEqual(twice, once, 'second splice is a no-op');
  const updated = lib.spliceCalendarSection(once, '## Year Calendar (2026–27)\n\n| b |\n');
  assert.ok(updated.includes('| b |') && !updated.includes('| a |'));
});

test('spliceCalendarSection throws on a lone marker', () => {
  assert.throws(() => lib.spliceCalendarSection('x\n<!-- calendar:start -->\ny', 'S'));
});
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: FAIL — `lib.renderCalendarMd is not a function`

- [ ] **Step 3: Implement** — add to the lib and export (plus `START_MARK`, `END_MARK`):

```js
var START_MARK = '<!-- calendar:start -->';
var END_MARK = '<!-- calendar:end -->';
var DOW = { 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri' };

function fmtShort(dateStr) {
  var d = parseDate(dateStr);
  return (d.getMonth() + 1) + '/' + d.getDate();
}

function fmtWeekOf(dateStr) {
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var d = parseDate(dateStr);
  return MON[d.getMonth()] + ' ' + d.getDate();
}

function renderCalendarMd(courseName, rows) {
  var lines = [
    '## Year Calendar (2026–27)',
    '',
    '_Generated from `calendar/2026-27.json` — do not edit between the markers; edit the JSON and rerun `node tools/generate-calendars.mjs`._',
    '',
    '| Wk | Week of | Class meetings | Unit | Focus | Notes |',
    '|----|---------|----------------|------|-------|-------|'
  ];
  rows.forEach(function (r) {
    var meetings = r.meetings.map(function (m) {
      return DOW[m.weekday] + ' ' + fmtShort(m.date) + ' (' + m.minutes + 'm)';
    }).join(' · ') || '—';
    lines.push('| ' + r.index + ' | ' + fmtWeekOf(r.weekStart) + ' | ' + meetings + ' | ' +
      (r.unit || '') + ' | ' + (r.topic || '') + ' | ' + r.notes.join('; ') + ' |');
  });
  return lines.join('\n') + '\n';
}

function spliceCalendarSection(text, sectionMd) {
  var hasStart = text.indexOf(START_MARK) !== -1;
  var hasEnd = text.indexOf(END_MARK) !== -1;
  if (hasStart !== hasEnd) throw new Error('Malformed calendar markers: found one of START/END but not both');
  var payload = START_MARK + '\n' + sectionMd + END_MARK;
  if (!hasStart) {
    return text.replace(/\s*$/, '\n\n') + payload + '\n';
  }
  var start = text.indexOf(START_MARK);
  var end = text.indexOf(END_MARK) + END_MARK.length;
  if (end - END_MARK.length < start) throw new Error('Malformed calendar markers: END before START');
  return text.slice(0, start) + payload + text.slice(end);
}
```

Add `renderCalendarMd: renderCalendarMd, spliceCalendarSection: spliceCalendarSection, START_MARK: START_MARK, END_MARK: END_MARK` to `module.exports`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/calendar-lib.test.cjs`
Expected: 15 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/calendar-lib.cjs tests/calendar-lib.test.cjs
git commit -m "Add markdown rendering and marker-based README splicing"
```

---

### Task 5: `calendar/courses.json` (full AP Statistics plan) + CLI + generate

**Files:**
- Create: `calendar/courses.json`
- Create: `tools/generate-calendars.mjs`
- Modify (generated): `ap-statistics/README.md`, `physics/README.md`, `principles-of-engineering/README.md`, `computer-science-math/README.md`, `intro-to-engineering-design/README.md`, `engineering-fundamentals/README.md`

**Interfaces:**
- Consumes: every lib function from Tasks 1–4.
- Produces: committed generated calendar sections; `node tools/generate-calendars.mjs` as the regeneration command.

- [ ] **Step 1: Create `calendar/courses.json`** with exactly:

```json
{
  "courses": [
    {
      "slug": "ap-statistics",
      "name": "AP Statistics",
      "period": 4,
      "plan": {
        "weeks": [
          { "unit": "1", "topic": "1.1–1.2 — Introducing statistics: investigative questions; variables" },
          { "unit": "1", "topic": "1.3–1.5 — One-variable displays: categorical tables and graphs; quantitative graphs" },
          { "unit": "1", "topic": "1.6–1.7 — Describing distributions; summary statistics for one quantitative variable" },
          { "unit": "1", "topic": "1.8–1.9 — Graphs of summary statistics; comparing distributions" },
          { "unit": "1", "topic": "1.10–1.12 — The investigative question revisited; random sampling; sampling problems" },
          { "unit": "1", "topic": "1.13 — Experimental design; Progress Check 1; Unit 1 review" },
          { "unit": "2", "topic": "2.1–2.2 — Two categorical variables: representations and summary statistics" },
          { "unit": "2", "topic": "2.3–2.4 — Estimating probabilities using simulation; introduction to probability" },
          { "unit": "2", "topic": "2.5–2.7 — Mutually exclusive events; conditional probability; independence and unions" },
          { "unit": "2", "topic": "2.8–2.9 — Random variables, probability distributions, and their parameters" },
          { "unit": "2", "topic": "2.10–2.11 — The binomial distribution; the normal distribution" },
          { "unit": "2", "topic": "2.12 — Sampling distributions and the Central Limit Theorem" },
          { "unit": "2", "topic": "Progress Check 2; Unit 2 review" },
          { "unit": "1–2", "topic": "FRQ practice (10-point format); semester data investigation kickoff" },
          { "unit": "1–2", "topic": "Semester data investigation — design and data collection" },
          { "unit": "1–2", "topic": "Semester data investigation — analysis and presentations" },
          { "unit": "3", "topic": "3.1–3.2 — Estimators; sampling distributions for sample proportions" },
          { "unit": "3", "topic": "3.3–3.4 — Confidence intervals for a population proportion; justifying claims" },
          { "unit": "3", "topic": "3.5–3.7 — Tests for a population proportion: setup, p-values, carrying out" },
          { "unit": "3", "topic": "3.8 — Potential errors when performing tests; inference practice" },
          { "unit": "3", "topic": "3.9–3.11 — Two proportions: sampling distributions and confidence intervals" },
          { "unit": "3", "topic": "3.12–3.13 — Tests for the difference between two proportions" },
          { "unit": "3", "topic": "3.14–3.15 — Chi-square tests for homogeneity or independence" },
          { "unit": "3", "topic": "Progress Check 3; Unit 3 review" },
          { "unit": "4", "topic": "4.1–4.2 — Sampling distributions for sample means; confidence intervals" },
          { "unit": "4", "topic": "4.3–4.5 — Justifying claims; tests for a population mean" },
          { "unit": "4", "topic": "4.6–4.8 — Two means: sampling distributions and confidence intervals" },
          { "unit": "4", "topic": "4.9–4.10 — Tests for the difference between two population means" },
          { "unit": "4", "topic": "Progress Check 4; Unit 4 review" },
          { "unit": "5", "topic": "5.1–5.3 — Scatterplots; correlation; linear regression models" },
          { "unit": "5", "topic": "5.4–5.5 — Residuals; least-squares regression; Progress Check 5" },
          { "unit": "R", "topic": "AP review I — mixed multiple choice; FRQ practice in the new 10-point format" },
          { "unit": "R", "topic": "AP review II — full digital practice exam in Bluebook" },
          { "unit": "R", "topic": "AP review III — targeted gap review; exam window" },
          { "unit": "P", "topic": "Capstone data project — question, design, and data collection" },
          { "unit": "P", "topic": "Capstone data project — analysis and write-up" },
          { "unit": "P", "topic": "Capstone presentations; year wrap-up" }
        ],
        "events": [
          { "date": "2026-10-01", "label": "**Unit 1 Test** (Thu)" },
          { "date": "2026-11-19", "label": "**Unit 2 Test** (Thu)" },
          { "date": "2027-01-22", "label": "End of Semester 1" },
          { "date": "2027-02-25", "label": "**Unit 3 Test** (Thu)" },
          { "date": "2027-04-08", "label": "**Unit 4 Test** (Thu)" },
          { "date": "2027-04-22", "label": "**Unit 5 Test** (Thu)" },
          { "date": "2027-04-26", "label": "AP review begins" },
          { "date": "2027-05-03", "label": "**AP Exam window May 3–14** — exact AP Statistics date TBA (College Board publishes the 2027 schedule in fall 2026)" },
          { "date": "2027-06-03", "label": "Last day of school" }
        ]
      }
    },
    { "slug": "principles-of-engineering", "name": "Principles of Engineering", "period": 1, "plan": { "weeks": [], "events": [] } },
    { "slug": "physics", "name": "Physics", "period": 2, "plan": { "weeks": [], "events": [] } },
    { "slug": "computer-science-math", "name": "Computer Science Math", "period": 3, "notes": "SIS shows a T/W/R pattern for semester 2 (HSTHSWHSR) — revisit when semester 2 plans are added.", "plan": { "weeks": [], "events": [] } },
    { "slug": "intro-to-engineering-design", "name": "Introduction to Engineering Design", "period": 6, "plan": { "weeks": [], "events": [] } },
    { "slug": "engineering-fundamentals", "name": "Engineering Fundamentals", "period": 8, "plan": { "weeks": [], "events": [] } }
  ]
}
```

- [ ] **Step 2: Create `tools/generate-calendars.mjs`**

```js
#!/usr/bin/env node
// Regenerates the "Year Calendar" section of every course README from
// calendar/2026-27.json + calendar/courses.json. Run from the repo root:
//   node tools/generate-calendars.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const lib = require('./calendar-lib.cjs');

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const year = JSON.parse(fs.readFileSync(path.join(root, 'calendar', '2026-27.json'), 'utf8'));
const { courses } = JSON.parse(fs.readFileSync(path.join(root, 'calendar', 'courses.json'), 'utf8'));

const days = lib.expandSchoolDays(year);
let failed = false;

for (const course of courses) {
  const readmePath = path.join(root, course.slug, 'README.md');
  if (!fs.existsSync(readmePath)) {
    console.error(`ERROR: ${course.slug}: no README at ${readmePath}`);
    failed = true;
    continue;
  }
  const weeks = lib.buildCourseWeeks(days, course.period);
  const { rows, warnings } = lib.applyPlan(weeks, course.plan);
  for (const w of warnings) console.warn(`WARN: ${course.slug}: ${w}`);
  const section = lib.renderCalendarMd(course.name, rows);
  const readme = fs.readFileSync(readmePath, 'utf8');
  let next;
  try {
    next = lib.spliceCalendarSection(readme, section);
  } catch (e) {
    console.error(`ERROR: ${course.slug}: ${e.message}`);
    failed = true;
    continue;
  }
  if (next !== readme) {
    fs.writeFileSync(readmePath, next);
    console.log(`updated ${course.slug}/README.md (${rows.length} weeks, ${weeks.reduce((n, w) => n + w.meetings.length, 0)} meetings)`);
  } else {
    console.log(`unchanged ${course.slug}/README.md`);
  }
}

if (failed) process.exit(1);
```

- [ ] **Step 3: Run the generator**

Run: `node tools/generate-calendars.mjs`
Expected: six `updated <slug>/README.md (37 weeks, N meetings)` lines, zero WARN/ERROR lines (AP Statistics' plan is exactly 37 entries; the other five have empty plans, which do not warn).

- [ ] **Step 4: Verify the generated content**

Run: `grep -c '^| ' ap-statistics/README.md`
Expected: `38` (header separator row is `|--…`, so 1 header + 37 week rows begin with `| `).

Run: `grep -n 'Unit 1 Test' ap-statistics/README.md | head -1`
Expected: one row — the week of Sep 28 (test Thu Oct 1).

Run: `grep -i 'geometric\|goodness\|slope' calendar/courses.json || echo "clean"`
Expected: `clean` (removed-in-2026 topics absent).

Run: `node --test tests/*.test.cjs`
Expected: all tests pass (8 feed + 15 calendar = 23).

- [ ] **Step 5: Commit**

```bash
git add calendar/courses.json tools/generate-calendars.mjs ap-statistics/README.md physics/README.md principles-of-engineering/README.md computer-science-math/README.md intro-to-engineering-design/README.md engineering-fundamentals/README.md
git commit -m "Generate 2026-27 year calendars; full AP Statistics plan from Fall 2026 CED"
```

---

### Task 6: Full verification

**Files:** none new — verification only.

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Idempotence**

Run: `node tools/generate-calendars.mjs && git status --short`
Expected: six `unchanged …` lines; `git status --short` empty.

- [ ] **Step 2: Rendered page check**

Run: `python3 -m http.server 8000 &`, then fetch `http://localhost:8000/ap-statistics/` in a browser (or `curl -s http://localhost:8000/ap-statistics/README.md | grep -c 'Year Calendar'` → `1`).
Expected: the AP Statistics page renders the Year Calendar table under the existing README content, styled by the site's table CSS; no horizontal page scroll (the table scrolls inside `main` if wide). Kill the server after.

- [ ] **Step 3: Sanity-check spot dates against the source calendar**

Run: `grep 'Jan 4' ap-statistics/README.md`
Expected: the week-of-Jan-4 row shows exactly `Tue 1/5 (72m) · Thu 1/7 (80m)` (Jan 5 is a 1:45 Tuesday; no Monday — school resumes Jan 5).

Run: `grep 'Mar 29' ap-statistics/README.md`
Expected: row shows `Tue 3/30 (80m) · Thu 4/1 (80m)` (spring-break return week).

- [ ] **Step 4: Report**

Confirm clean tree (`git status --short` empty) and report: all tasks committed locally, NOT pushed — pushing master deploys the live site, the user decides when.
