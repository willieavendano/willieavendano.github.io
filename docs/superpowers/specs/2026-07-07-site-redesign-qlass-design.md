# Site Redesign + Qlass Integration — Design

**Date:** 2026-07-07
**Repo:** willieavendano.github.io (GitHub Pages, static, `.nojekyll`)
**Related:** Qlass (`github.com/willieavendano/qlass-lms`), August 2026 pilot at `class.avendano.xyz`

## Goal

Reorganize and visually refresh the site, and integrate it with Qlass so the
GitHub Pages site is the public front door and Qlass is the logged-in classroom.
Three integration modes, all approved: gateway links, shared design language
(hybrid), and a live-data feed embed built site-side against a documented API
contract (the Qlass endpoint itself is later, separate work in qlass-lms).

## Decisions (from brainstorming)

- **Integration:** gateway links + live feed embeds + shared design language.
  No dedicated "Qlass showcase" section.
- **Visual direction:** hybrid — Qlass editorial typography and warmth
  (Fraunces headings, paper background) with Cushman blue as the primary accent.
  No gradient banners; blue top rules on cards.
- **Homepage organization:** portfolio-first order unchanged
  (Hero → About → Courses → Background → Talks → Projects).
- **Embed scope:** site side only. Build against an agreed API shape with a
  graceful self-hiding fallback; the qlass-lms endpoint is future work.
- **Architecture:** Approach A — shared static assets, no build step.
  Course pages stay README.md-driven (marked.js client-side rendering).

## Visual design system

**Typography.** Fraunces (Google Fonts) for all headings and the hero name;
Inter for body. Raleway is removed. Micro-labels (section labels, course tags,
buttons) use Inter uppercase with letter-spacing.

**Palette.**

| Token | Value | Role |
|---|---|---|
| `--paper` | warm off-white, `#FAF8F4` family | page background |
| `--paper-deep` | slightly deeper warm tone | alternating sections |
| `--ink` | `#211E1A` family | body text |
| `--blue` | `#0E406A` | primary accent: headings, nav, card rules, buttons |
| `--bright` | `#0071CE` | links |
| pale blues | existing | subtle tints only |

**Components.**
- *Hero:* blue band kept; subtle grain texture; Fraunces display sizing;
  tighter vertical rhythm.
- *Course cards:* paper-white card, blue top rule, uppercase tag, hover
  lift + shadow. Footer row: "Course Site" link and, when configured,
  "Open in Qlass ↗" button. Previously-taught cards render muted (as today).
- *Mobile nav:* hamburger + dropdown below 768px (links currently just
  disappear).
- *Course pages:* shared theme; proper course header (name, tag, blue rule,
  Qlass button) above rendered README content.

## Content organization & cleanup

- Homepage section order unchanged; three course subsections kept
  (Current 2026–27 / Co-Taught / Previously Taught).
- **Delete dead files:** `_config.yml`, `_layouts/`, `_posts/`, `feed.xml`
  (Jekyll is disabled by `.nojekyll`). Delete `assets/css/default.css` and
  `assets/css/style.css` after verifying nothing references them.
- **Extract shared CSS:** all inline styles from `index.html` and the 9 course
  pages move to `assets/css/site.css`. Course pages become a ~40-line shell.
- **Course READMEs:** all 9 get a consistent starter skeleton — Overview,
  Syllabus & Pacing, Resources, Assignments — replacing empty/placeholder
  content. `assignments/`, `resources/`, `notes/` folders stay.

## Qlass integration

### Config — `assets/js/qlass-config.js`

```js
window.QLASS = {
  base: 'https://class.avendano.xyz',
  courses: {
    'ap-statistics':                  { classUrl: null },
    'engineering-fundamentals':       { classUrl: null },
    'intro-to-engineering-design':    { classUrl: null },
    'principles-of-engineering':      { classUrl: null },
    'computer-science-math':          { classUrl: null },
    'ap-research':                    { classUrl: null },
    'ap-physics-c':                   { classUrl: null },
    'ap-computer-science-principles': { classUrl: null },
    'ap-computer-science-a':          { classUrl: null }
  }
};
```

### Gateway links

Homepage cards and course-page headers render "Open in Qlass ↗" only when
that course's `classUrl` is non-null. All start null → no dead links. When
pilot classes exist in August, fill URLs in this one file.

### Feed embed — `assets/js/qlass-feed.js`

Course pages fetch `GET {base}/api/public/classes/{slug}/feed` where `{slug}`
is the course directory name. Expected response (this is the contract the
future qlass-lms endpoint implements):

```json
{
  "class": { "name": "AP Statistics" },
  "announcements": [{ "title": "...", "body": "...", "postedAt": "ISO-8601" }],
  "upcoming":      [{ "title": "...", "dueAt": "ISO-8601", "url": "..." }]
}
```

Behavior:
- Renders a "This week in Qlass" panel (latest 3 announcements, next 5 due
  dates) between the course header and README content.
- On 404 / network error / CORS failure / malformed JSON: the panel does not
  render at all. No error text, no placeholder.
- 5-minute `sessionStorage` cache per slug.

The full contract, including server-side requirements for the future endpoint
(CORS `Access-Control-Allow-Origin: https://willieavendano.github.io`,
opt-in per class, unauthenticated read-only data only), is documented in
`docs/qlass-integration.md` in this repo.

## Error handling

All JS is additive. With JS disabled/failing: homepage fully works; course
pages show nav/header/footer (README rendering already requires marked.js —
unchanged behavior). Feed embed failures are invisible to students.

## Testing / verification

Serve locally with `python3 -m http.server`; verify:
- Homepage and all 9 course pages render with the new theme.
- Feed embed stays invisible against the dead endpoint (current reality).
- Feed embed renders correctly against a mocked response.
- Qlass buttons appear only for non-null `classUrl` entries.
- Mobile nav works at phone width; no horizontal scroll.

## Out of scope

- The qlass-lms public feed endpoint (separate repo, future work; contract
  documented here).
- A Qlass showcase/marketing section on the site.
- Restructuring homepage audience priority or splitting pages.
