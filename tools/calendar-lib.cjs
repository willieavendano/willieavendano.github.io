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

// The default rotation: Monday runs all 8 single periods; Tue/Thu are "A"
// days (Blocks 1-4) and Wed/Fri are "B" days (Blocks 5-8). The published A/B
// Schedule overrides individual days in a handful of weeks — most often moving
// a B day onto Monday when that week loses a Wednesday or Friday.
var DEFAULT_MODE = { 1: 'single', 2: 'A', 4: 'A', 3: 'B', 5: 'B' };
var MODE_PERIODS = { A: [1, 2, 3, 4], B: [5, 6, 7, 8] };
var VALID_MODES = ['single', 'A', 'B', 'none'];

function expandSchoolDays(year) {
  var noSchool = expandNoSchool(year.noSchool);
  var early = new Set(year.early145 || []);
  var noon = new Set(year.noonDismissal || []);
  var altered = year.alteredDays || {};
  Object.keys(altered).forEach(function (k) {
    if (VALID_MODES.indexOf(altered[k]) === -1) {
      throw new Error('Bad alteredDays mode for ' + k + ': ' + altered[k]);
    }
  });
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
        type: noon.has(s) ? 'noon' : early.has(s) ? 'early145' : 'normal',
        mode: Object.prototype.hasOwnProperty.call(altered, s) ? altered[s] : DEFAULT_MODE[dow],
        altered: Object.prototype.hasOwnProperty.call(altered, s) && altered[s] !== DEFAULT_MODE[dow]
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


// Per the 2026-27 HS Time Schedule (with corrections from the schedule's
// author — the published PDF has errors): Monday runs single periods, with
// Period 1 at 8:10-8:51 (41m), Period 3 a 40m period between Periods 2 and
// 4, and the rest 44m. All Tue-Fri blocks are 80m (Thursday mirrors Tuesday,
// Friday mirrors Wednesday).
// Duration follows the day's MODE, not its weekday: an altered Monday that
// runs as a B day gets the 80-minute block schedule, and the single-period
// Tuesday in the MLK week gets Monday's 41/40/44-minute periods.
function meetingFor(day, period) {
  if (day.mode === 'single') {
    if (day.type !== 'normal') throw new Error('Unsupported non-normal single-period day: ' + day.date);
    var minutes = period === 1 ? 41 : period === 3 ? 40 : 44;
    return { minutes: minutes, kind: 'single' };
  }
  if (day.type === 'noon') return { minutes: 55, kind: 'short-block' };
  if (day.type === 'early145') return { minutes: 72, kind: 'short-block' };
  return { minutes: 80, kind: 'block' };
}

function meetsOn(day, period) {
  if (day.mode === 'none') return false;
  if (day.mode === 'single') return true;
  return MODE_PERIODS[day.mode].indexOf(period) !== -1;
}

function meetingsForCourse(days, period, override) {
  if (!Number.isInteger(period) || period < 1 || period > 8) throw new Error('Bad period: ' + period);
  var out = [];
  days.forEach(function (day) {
    // A patternOverride replaces the period-derived meeting days from a
    // given date onward (e.g. a course whose schedule changes at semester 2).
    // "No academics" days are dropped either way — nothing meets.
    var meets = override && day.date >= override.from
      ? day.mode !== 'none' && override.weekdays.indexOf(day.weekday) !== -1
      : meetsOn(day, period);
    if (!meets) return;
    var m = meetingFor(day, period);
    out.push({
      date: day.date, weekday: day.weekday,
      minutes: m.minutes, kind: m.kind, altered: !!day.altered
    });
  });
  return out;
}

// Courses that do not sit in the Cushman bell schedule (e.g. the virtual
// section) declare explicit meetings instead of a period: a weekday plus
// wall-clock start/end. Duration comes from those times, so early-dismissal
// and noon-dismissal days do not shorten them — but "no academics" days and
// holidays still cancel the session.
function hhmmToMinutes(t) {
  var m = /^(\d{1,2}):(\d{2})$/.exec(t || '');
  if (!m) throw new Error('Bad time (expected HH:MM): ' + t);
  var h = Number(m[1]), min = Number(m[2]);
  if (h > 23 || min > 59) throw new Error('Bad time: ' + t);
  return h * 60 + min;
}

function meetingsForSchedule(days, schedule) {
  var slots = [];
  (schedule.live || []).forEach(function (s) { slots.push({ s: s, kind: 'live' }); });
  if (schedule.async) slots.push({ s: schedule.async, kind: 'async' });
  if (!slots.length) throw new Error('schedule has no live or async slots');
  slots.forEach(function (x) {
    if (!Number.isInteger(x.s.weekday) || x.s.weekday < 1 || x.s.weekday > 5) {
      throw new Error('Bad schedule weekday: ' + x.s.weekday);
    }
    x.minutes = hhmmToMinutes(x.s.end) - hhmmToMinutes(x.s.start);
    if (x.minutes <= 0) throw new Error('Schedule slot ends before it starts: ' + x.s.start + '-' + x.s.end);
  });
  var out = [];
  days.forEach(function (day) {
    if (day.mode === 'none') return; // no-academics days cancel the session too
    slots.forEach(function (x) {
      if (x.s.weekday !== day.weekday) return;
      out.push({
        date: day.date, weekday: day.weekday, minutes: x.minutes,
        kind: x.kind, start: x.s.start, end: x.s.end, altered: !!day.altered
      });
    });
  });
  out.sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; });
  return out;
}

// Dispatches on which key the course declares. Exactly one of `period` or
// `schedule` is required.
function meetingsForCourseSpec(days, course) {
  var hasPeriod = course.period !== undefined && course.period !== null;
  var hasSchedule = !!course.schedule;
  if (hasPeriod === hasSchedule) {
    throw new Error('Course ' + (course.slug || '?') + ' needs exactly one of `period` or `schedule`');
  }
  return hasSchedule
    ? meetingsForSchedule(days, course.schedule)
    : meetingsForCourse(days, course.period, course.patternOverride);
}

function buildWeeksFromMeetings(days, meetings) {
  var byWeek = new Map();
  days.forEach(function (day) {
    var wk = mondayOf(day.date);
    if (!byWeek.has(wk)) byWeek.set(wk, { weekStart: wk, schoolDays: [], meetings: [] });
    byWeek.get(wk).schoolDays.push(day.date);
  });
  meetings.forEach(function (m) { byWeek.get(mondayOf(m.date)).meetings.push(m); });
  return Array.from(byWeek.values());
}

function buildCourseWeeks(days, period, override) {
  return buildWeeksFromMeetings(days, meetingsForCourse(days, period, override));
}

function buildWeeksForCourse(days, course) {
  return buildWeeksFromMeetings(days, meetingsForCourseSpec(days, course));
}

// `plan: { extends: "<slug>" }` reuses another course's weeks (and its events
// unless this course supplies its own), so the two stay in lockstep.
function resolvePlan(course, allCourses) {
  var plan = course.plan || {};
  if (!plan.extends) return plan;
  var base = (allCourses || []).find(function (c) { return c.slug === plan.extends; });
  if (!base) throw new Error(course.slug + ': plan.extends references unknown course ' + plan.extends);
  if (base.plan && base.plan.extends) throw new Error(course.slug + ': plan.extends may not chain');
  return {
    weeks: (base.plan && base.plan.weeks) || [],
    events: plan.events || (base.plan && base.plan.events) || []
  };
}

function applyPlan(weeks, plan) {
  var planWeeks = (plan && plan.weeks) || [];
  var events = (plan && plan.events) || [];
  var warnings = [];
  if (planWeeks.length > 0 && planWeeks.length !== weeks.length) {
    warnings.push('plan has ' + planWeeks.length + ' week entries but the year has ' + weeks.length + ' teaching weeks');
  }
  var weekStarts = new Set(weeks.map(function (w) { return w.weekStart; }));
  events.forEach(function (e) {
    if (!weekStarts.has(mondayOf(e.date))) {
      warnings.push('event "' + e.label + '" (' + e.date + ') falls outside every teaching week');
    }
  });
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
      var label = m.kind === 'async'
        ? 'async'
        : m.minutes + 'm' + (m.kind === 'live' ? ' live' : '');
      return '`' + DOW[m.weekday] + ' ' + fmtShort(m.date) + ' (' + label + ')' + '`';
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

module.exports = { parseDate: parseDate, iso: iso, addDays: addDays, expandSchoolDays: expandSchoolDays, mondayOf: mondayOf, meetingsForCourse: meetingsForCourse, meetingsForSchedule: meetingsForSchedule, meetingsForCourseSpec: meetingsForCourseSpec, buildCourseWeeks: buildCourseWeeks, buildWeeksForCourse: buildWeeksForCourse, resolvePlan: resolvePlan, applyPlan: applyPlan, renderCalendarMd: renderCalendarMd, spliceCalendarSection: spliceCalendarSection, START_MARK: START_MARK, END_MARK: END_MARK };
