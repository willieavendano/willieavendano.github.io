# Qlass ↔ class.avendano.xyz Integration Contract

This static site (GitHub Pages, custom domain **class.avendano.xyz**, also
reachable at willieavendano.github.io) is the public front door; Qlass
(repo `willieavendano/qlass-lms`, deployed on Railway at
https://qlass-production.up.railway.app — the `base` in
`assets/js/qlass-config.js`) is the logged-in classroom. Two integration
points, both driven by `assets/js/qlass-config.js`.

## 1. Gateway links

`assets/js/qlass-config.js` maps each course slug (its directory name here)
to a `classUrl`. When non-null, "Open in Qlass ↗" buttons render on the
homepage card and course page header. All values are null until the class
exists in Qlass — fill them in and every button lights up. No other change
needed.

## 2. Feed embed (endpoint NOT yet implemented in qlass-lms)

`assets/js/qlass-feed.js` on every course page requests:

    GET {base}/api/public/classes/{slug}/feed

where `{slug}` is the course directory name (e.g. `ap-statistics`).

### Response contract (JSON, 200)

    {
      "class": { "name": "AP Statistics" },
      "announcements": [
        { "title": "string", "body": "string (plain text, optional)", "postedAt": "ISO-8601" }
      ],
      "upcoming": [
        { "title": "string", "dueAt": "ISO-8601", "url": "https://... (optional)" }
      ]
    }

The client shows the 3 newest announcements and the next 5 not-yet-due
items. It renders nothing on 404 / network error / CORS failure / malformed
JSON / empty feed, and caches responses in sessionStorage for 5 minutes.

### Requirements for the qlass-lms endpoint (future work)

- **Public, unauthenticated, read-only.** Only data the teacher explicitly
  marks public. Opt-in per class (e.g. a `publicFeedSlug` field on Class —
  null means 404). Never include student names, submissions, or grades.
- **CORS:** respond with
  `Access-Control-Allow-Origin: https://class.avendano.xyz` (the site's
  canonical domain; also allow `https://willieavendano.github.io` if
  requests may come from the fallback domain).
- **404** for unknown or non-opted-in slugs.
- Body text should be truncated server-side (e.g. 280 chars) — the site
  renders it as plain text.
- `url` values must be absolute `https://` URLs — the client also rejects
  non-https schemes as defense-in-depth.

### Adding a course to this site

A new course needs all three: a directory with an `index.html` (copy any
existing course's — they are byte-identical) and a `README.md`, plus an
entry in `assets/js/qlass-config.js` keyed by the directory name. Without
the config entry the course header shows a literal "Course" placeholder
while the README's own title stays hidden.

### Testing the embed without the endpoint

Seed the cache in the browser console on any course page:

    sessionStorage.setItem('qlass-feed:ap-statistics', JSON.stringify({
      t: Date.now(),
      data: { class: { name: 'AP Statistics' },
              announcements: [{ title: 'Hello', postedAt: new Date().toISOString() }],
              upcoming: [] }
    }));
    location.reload();

Logic tests: `node --test tests/*.test.cjs`
