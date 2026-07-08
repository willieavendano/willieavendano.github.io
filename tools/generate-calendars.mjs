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
