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
