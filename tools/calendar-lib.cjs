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

var BLOCK_DAYS = { 2: [1, 2, 3, 4], 4: [1, 2, 3, 4], 3: [5, 6, 7, 8], 5: [5, 6, 7, 8] };

// Per the 2026-27 HS Time Schedule (with corrections from the schedule's
// author — the published PDF has errors): Monday runs single periods, with
// Period 1 at 8:10-8:51 (41m), Period 3 a 40m period between Periods 2 and
// 4, and the rest 44m. All Tue-Fri blocks are 80m (Thursday mirrors Tuesday,
// Friday mirrors Wednesday).
function meetingFor(day, period) {
  if (day.weekday === 1) {
    if (day.type !== 'normal') throw new Error('Unsupported non-normal Monday: ' + day.date);
    var minutes = period === 1 ? 41 : period === 3 ? 40 : 44;
    return { minutes: minutes, kind: 'single' };
  }
  if (day.type === 'noon') return { minutes: 55, kind: 'short-block' };
  if (day.type === 'early145') return { minutes: 72, kind: 'short-block' };
  return { minutes: 80, kind: 'block' };
}

function meetingsForCourse(days, period, override) {
  if (!Number.isInteger(period) || period < 1 || period > 8) throw new Error('Bad period: ' + period);
  var out = [];
  days.forEach(function (day) {
    // A patternOverride replaces the period-derived meeting days from a
    // given date onward (e.g. a course whose schedule changes at semester 2).
    var meets = override && day.date >= override.from
      ? override.weekdays.indexOf(day.weekday) !== -1
      : day.weekday === 1 || BLOCK_DAYS[day.weekday].indexOf(period) !== -1;
    if (!meets) return;
    var m = meetingFor(day, period);
    out.push({ date: day.date, weekday: day.weekday, minutes: m.minutes, kind: m.kind });
  });
  return out;
}

function buildCourseWeeks(days, period, override) {
  var meetings = meetingsForCourse(days, period, override);
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
      return '`' + DOW[m.weekday] + ' ' + fmtShort(m.date) + ' (' + m.minutes + 'm)' + '`';
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

module.exports = { parseDate: parseDate, iso: iso, addDays: addDays, expandSchoolDays: expandSchoolDays, mondayOf: mondayOf, meetingsForCourse: meetingsForCourse, buildCourseWeeks: buildCourseWeeks, applyPlan: applyPlan, renderCalendarMd: renderCalendarMd, spliceCalendarSection: spliceCalendarSection, START_MARK: START_MARK, END_MARK: END_MARK };
