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
  assert.ok(!p8.has('2027-09-01'), '1:45 Tuesdays do not involve periods 5-8');
});

test('invalid period throws', () => {
  assert.throws(() => lib.meetingsForCourse(DAYS, 0));
  assert.throws(() => lib.meetingsForCourse(DAYS, 9));
});
