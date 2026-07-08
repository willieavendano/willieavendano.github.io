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

module.exports = { parseDate: parseDate, iso: iso, addDays: addDays, expandSchoolDays: expandSchoolDays, mondayOf: mondayOf, meetingsForCourse: meetingsForCourse, buildCourseWeeks: buildCourseWeeks, applyPlan: applyPlan };
