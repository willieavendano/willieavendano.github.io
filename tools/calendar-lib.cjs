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
