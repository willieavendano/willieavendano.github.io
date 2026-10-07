(function () {
  'use strict';

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    // Tapping a link closes the menu so it doesn't cover the section it jumps to.
    links.addEventListener('click', function (e) {
      if (!e.target.closest || !e.target.closest('a')) return;
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  }

  // Qlass gateway links: render a button into any [data-course] slot
  // whose configured classUrl is set. Null classUrl → no button, no dead links.
  var cfg = window.QLASS || { courses: {} };
  var slots = document.querySelectorAll('[data-course]');
  Array.prototype.forEach.call(slots, function (el) {
    var course = cfg.courses[el.getAttribute('data-course')];
    if (!course || !course.classUrl) return;
    var a = document.createElement('a');
    a.className = 'qlass-btn';
    a.href = course.classUrl;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = 'Open in Qlass ↗';
    el.appendChild(a);
  });
})();
