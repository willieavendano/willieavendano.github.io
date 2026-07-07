// Qlass feed embed. Fetches {QLASS.base}/api/public/classes/{slug}/feed and
// renders a "This week in Qlass" panel above the course README. Contract:
// docs/qlass-integration.md. On ANY failure it renders nothing — students
// must never see an error from this script.
(function () {
  'use strict';

  var TTL_MS = 5 * 60 * 1000;

  function buildFeedModel(data, now) {
    if (!data || typeof data !== 'object') return null;
    var announcements = Array.isArray(data.announcements) ? data.announcements : [];
    var upcoming = Array.isArray(data.upcoming) ? data.upcoming : [];
    var ann = announcements
      .filter(function (a) { return a && a.title; })
      .sort(function (a, b) { return new Date(b.postedAt) - new Date(a.postedAt); })
      .slice(0, 3);
    var due = upcoming
      .filter(function (u) { return u && u.title && new Date(u.dueAt) >= now; })
      .sort(function (a, b) { return new Date(a.dueAt) - new Date(b.dueAt); })
      .slice(0, 5);
    if (!ann.length && !due.length) return null;
    return {
      className: (data.class && data.class.name) || '',
      announcements: ann,
      upcoming: due
    };
  }

  function cacheKey(slug) { return 'qlass-feed:' + slug; }

  function readCache(storage, slug, nowMs) {
    try {
      var raw = storage.getItem(cacheKey(slug));
      if (!raw) return null;
      var entry = JSON.parse(raw);
      if (!entry || typeof entry.t !== 'number' || nowMs - entry.t > TTL_MS) return null;
      return entry.data;
    } catch (e) {
      return null;
    }
  }

  function writeCache(storage, slug, data, nowMs) {
    try {
      storage.setItem(cacheKey(slug), JSON.stringify({ t: nowMs, data: data }));
    } catch (e) { /* storage full/blocked — cache is best-effort */ }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      buildFeedModel: buildFeedModel,
      readCache: readCache,
      writeCache: writeCache,
      escapeHtml: escapeHtml
    };
    return;
  }

  // ── Browser only below ──
  var slug = location.pathname.split('/').filter(Boolean)[0] || '';
  var cfg = window.QLASS || {};
  if (!cfg.base || !slug) return;

  function fmtDate(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function render(model) {
    if (!model) return;
    var main = document.querySelector('main');
    if (!main) return;
    var html = '<h2 class="qlass-feed-title">This week in Qlass</h2>';
    if (model.announcements.length) {
      html += '<h3>Announcements</h3><ul>';
      model.announcements.forEach(function (a) {
        html += '<li><strong>' + escapeHtml(a.title) + '</strong>' +
          (a.postedAt ? ' <span class="muted">· ' + fmtDate(a.postedAt) + '</span>' : '') +
          (a.body ? '<br><span class="muted">' + escapeHtml(a.body) + '</span>' : '') +
          '</li>';
      });
      html += '</ul>';
    }
    if (model.upcoming.length) {
      html += '<h3>Coming up</h3><ul>';
      model.upcoming.forEach(function (u) {
        var safeUrl = typeof u.url === 'string' && /^https:\/\//i.test(u.url) ? u.url : null;
        var title = safeUrl
          ? '<a href="' + escapeHtml(safeUrl) + '" target="_blank" rel="noopener">' + escapeHtml(u.title) + '</a>'
          : escapeHtml(u.title);
        html += '<li>' + title +
          (u.dueAt ? ' <span class="muted">· due ' + fmtDate(u.dueAt) + '</span>' : '') +
          '</li>';
      });
      html += '</ul>';
    }
    var panel = document.createElement('section');
    panel.className = 'qlass-feed';
    panel.innerHTML = html;
    main.parentNode.insertBefore(panel, main);
  }

  var nowMs = Date.now();
  var storage = null;
  try { storage = window.sessionStorage; } catch (e) { /* storage blocked — skip caching */ }
  var cached = storage ? readCache(storage, slug, nowMs) : null;
  if (cached) {
    render(buildFeedModel(cached, new Date(nowMs)));
    return;
  }

  fetch(cfg.base + '/api/public/classes/' + encodeURIComponent(slug) + '/feed')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data) return;
      if (storage) writeCache(storage, slug, data, nowMs);
      render(buildFeedModel(data, new Date(nowMs)));
    })
    .catch(function () { /* endpoint absent / CORS / offline — render nothing */ });
})();
