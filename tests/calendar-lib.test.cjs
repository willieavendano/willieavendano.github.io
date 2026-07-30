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

test('minutes: Mon single 44 (P1 41), full block 80, Thu B4 / Fri B8 40, 1:45 Tue 72, noon 55', () => {
  const p4 = lib.meetingsForCourse(DAYS, 4);
  const by = new Map(p4.map(m => [m.date, m]));
  assert.strictEqual(by.get('2026-08-24').minutes, 44);
  assert.strictEqual(by.get('2026-08-24').kind, 'single');
  assert.strictEqual(by.get('2026-08-25').minutes, 80);
  assert.strictEqual(by.get('2026-08-27').minutes, 40);  // Thursday Block 4 is 2:20-3:00
  assert.strictEqual(by.get('2027-01-05').minutes, 72);  // 1:45 dismissal Tuesday
  assert.strictEqual(by.get('2026-11-03').minutes, 55);  // noon-dismissal Tuesday
  assert.ok(!by.has('2026-11-20'), 'P4 does not meet Fridays even on noon dismissal');
  const p8 = new Map(lib.meetingsForCourse(DAYS, 8).map(m => [m.date, m]));
  assert.strictEqual(p8.get('2026-08-26').minutes, 80);  // Wednesday Block 8 full length
  assert.strictEqual(p8.get('2026-08-28').minutes, 40);  // Friday Block 8 is 12:57-1:37
  assert.strictEqual(p8.get('2026-11-20').minutes, 55);  // noon Friday, block 8 shortened
  assert.ok(!p8.has('2026-09-01'), '1:45 Tuesdays do not involve periods 5-8');
  const p1 = new Map(lib.meetingsForCourse(DAYS, 1).map(m => [m.date, m]));
  assert.strictEqual(p1.get('2026-08-24').minutes, 41);  // Monday Period 1 is 8:10-8:51
  const p3 = lib.meetingsForCourse(DAYS, 3);
  assert.ok(p3.every(m => m.weekday !== 1), 'Monday has no Period 3');
  assert.ok(p3.every(m => [2, 4].includes(m.weekday)), 'P3 meets Tue/Thu only');
});

test('invalid period throws', () => {
  assert.throws(() => lib.meetingsForCourse(DAYS, 0));
  assert.throws(() => lib.meetingsForCourse(DAYS, 9));
});

test('patternOverride switches meeting days from a given date', () => {
  // No 2026-27 course uses an override; the feature stays for mid-year
  // schedule changes. Hypothetical: a P4 course moving to T/W/R from Jan 25.
  const override = { from: '2027-01-25', weekdays: [2, 3, 4] };
  const m = new Map(lib.meetingsForCourse(DAYS, 4, override).map(x => [x.date, x]));
  assert.ok(m.has('2027-01-11'), 'still meets Mondays before the switch');
  assert.ok(!m.has('2027-01-25'), 'no Monday meeting after the switch');
  assert.strictEqual(m.get('2027-01-27').minutes, 80, 'meets Wednesdays after the switch');
  assert.strictEqual(m.get('2027-01-28').minutes, 40, 'Thursday Block 4 stays 40m after the switch');
  assert.strictEqual(m.get('2027-02-02').minutes, 72, '1:45 Tuesday still shortens');
  assert.ok(!m.has('2026-09-02'), 'no Wednesday meetings before the switch');
});

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

test('applyPlan warns when an event falls outside every teaching week', () => {
  const weeks = lib.buildCourseWeeks(DAYS, 4);
  const { warnings } = lib.applyPlan(weeks, {
    weeks: [],
    events: [{ date: '2026-11-25', label: 'Typo Test' }]  // Thanksgiving week — no teaching week
  });
  assert.strictEqual(warnings.length, 1);
  assert.ok(warnings[0].includes('Typo Test'));
});

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
  assert.ok(md.includes('| 1 | Aug 24 | `Mon 8/24 (44m)` · `Tue 8/25 (80m)` | 1 | 1.1–1.2 — Intro | First day |'));
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
