# Site Redesign + Qlass Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle willieavendano.github.io into a hybrid editorial + Cushman-blue design, remove dead Jekyll files, extract shared CSS/JS, and add config-driven Qlass gateway links plus a self-hiding Qlass feed embed on course pages.

**Architecture:** Plain static GitHub Pages site, no build step. One shared stylesheet (`assets/css/site.css`) and three small scripts (`qlass-config.js` = data, `site.js` = nav + gateway links, `qlass-feed.js` = feed embed with node-testable pure logic). All 9 course pages become one identical ~60-line shell that derives its course slug from `location.pathname` and reads names/tags/URLs from the config. Course content stays README.md-driven via marked.js.

**Tech Stack:** HTML/CSS, vanilla browser JS (no modules, no framework), Google Fonts (Fraunces + Inter), marked.js CDN, Node ≥18 built-in test runner (`node --test`) for feed logic only.

**Spec:** `docs/superpowers/specs/2026-07-07-site-redesign-qlass-design.md`

**Already satisfied (verified 2026-07-07):** The spec's "course README starter skeleton" requirement — all 9 READMEs already have the Overview/Syllabus/Assignments/Notes/Resources skeleton. No task needed.

## Global Constraints

- No build step. The repo must deploy as-is on GitHub Pages (`.nojekyll` stays).
- Asset URLs are root-absolute: `/assets/css/site.css`, `/assets/js/*.js` (user site served at domain root).
- Browser JS: plain scripts, no ES modules, no dependencies beyond the existing marked.js CDN on course pages.
- Fonts: exactly Fraunces (headings) and Inter (body/labels). Raleway is removed everywhere.
- Palette tokens (exact values): `--paper: #FAF8F4`, `--paper-deep: #F3EFE7`, `--ink: #211E1A`, `--ink-soft: #55504A`, `--blue: #0E406A`, `--navy: #005487`, `--bright: #0071CE`, `--light-blue: #7BADD3`, `--pale-blue: #BDD4E7`, `--line: #E4DFD5`, `--white: #FFFFFF`.
- Qlass base URL: `https://class.avendano.xyz`. Feed endpoint shape: `GET {base}/api/public/classes/{slug}/feed`.
- All `classUrl` values start `null`. Qlass buttons must render ONLY for non-null `classUrl`.
- Feed embed must be invisible on any failure (404, network, CORS, bad JSON, empty feed). Never show an error to students.
- Course slugs = directory names: `ap-statistics`, `engineering-fundamentals`, `intro-to-engineering-design`, `principles-of-engineering`, `computer-science-math`, `ap-research`, `ap-physics-c`, `ap-computer-science-principles`, `ap-computer-science-a`.
- Commit after every task. Do NOT `git push` — the user decides when to push (they asked about push timing earlier).
- Work from repo root: `/Users/willieavendano/Developer/Cushman_Code/willieavendano.github.io`.

---

### Task 1: Delete dead Jekyll legacy files

**Files:**
- Delete: `_config.yml`, `_layouts/post.html`, `_layouts/posts.html`, `_posts/2014-04-07-hello-world.markdown`, `feed.xml`, `assets/css/default.css`, `assets/css/style.css`

**Interfaces:**
- Consumes: nothing
- Produces: a repo where the only HTML/CSS is the live site (verified: the deleted CSS is referenced only by the deleted `_layouts/` files; `.nojekyll` disables Jekyll so none of these files are served with any effect)

- [ ] **Step 1: Delete the files**

```bash
git rm -r _config.yml _layouts _posts feed.xml assets/css/default.css assets/css/style.css
```

- [ ] **Step 2: Verify nothing live references them**

Run: `grep -rn "default.css\|style.css\|feed.xml\|_layouts\|_posts" --include="*.html" . | grep -v .git | grep -v docs/superpowers`
Expected: no output (the only remaining matches in the repo are inside `docs/superpowers/` planning docs, which the grep excludes).

- [ ] **Step 3: Commit**

```bash
git commit -m "Remove dead Jekyll legacy files (Jekyll disabled by .nojekyll)"
```

---

### Task 2: Create shared stylesheet `assets/css/site.css`

**Files:**
- Create: `assets/css/site.css`

**Interfaces:**
- Consumes: nothing
- Produces: all class names used by Tasks 3–6. Load-bearing selectors later tasks rely on: `.nav-toggle`, `.nav-links.open`, `.card-actions`, `.qlass-btn`, `body.course-page`, `.course-header`, `.course-actions`, `.qlass-feed`, `.qlass-feed-title`, `.qlass-feed ul`, `.muted`, and `body.course-page main > h1:first-of-type { display: none }` (hides the README's duplicate title because the course header already shows it).

- [ ] **Step 1: Write the complete stylesheet**

Create `assets/css/site.css` with exactly this content:

```css
/* ── Design tokens ─────────────────────────────────────── */
:root {
  --paper:      #FAF8F4;
  --paper-deep: #F3EFE7;
  --ink:        #211E1A;
  --ink-soft:   #55504A;
  --blue:       #0E406A;
  --navy:       #005487;
  --bright:     #0071CE;
  --light-blue: #7BADD3;
  --pale-blue:  #BDD4E7;
  --line:       #E4DFD5;
  --white:      #FFFFFF;
  --serif: 'Fraunces', Georgia, serif;
  --sans: 'Inter', -apple-system, sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }

body {
  font-family: var(--sans);
  font-size: 16px;
  color: var(--ink);
  background: var(--paper);
  line-height: 1.65;
}

h1, h2, h3, h4 {
  font-family: var(--serif);
  font-weight: 600;
  line-height: 1.2;
  color: var(--blue);
}

a { color: var(--bright); text-decoration: none; }
a:hover { text-decoration: underline; }

.label {
  font-family: var(--sans);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

/* ── Navigation ────────────────────────────────────────── */
nav {
  position: fixed;
  top: 0;
  width: 100%;
  background: var(--blue);
  z-index: 200;
  padding: 0 2.5rem;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-name {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 1.05rem;
  color: var(--white);
  letter-spacing: 0.02em;
}

.nav-links {
  display: flex;
  gap: 2rem;
  list-style: none;
}

.nav-links a,
.nav-back {
  color: var(--pale-blue);
  font-size: 0.8rem;
  font-family: var(--sans);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.nav-links a:hover, .nav-back:hover { color: var(--white); text-decoration: none; }

.nav-toggle {
  display: none;
  background: none;
  border: none;
  color: var(--white);
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

/* ── Hero ──────────────────────────────────────────────── */
.hero {
  position: relative;
  background: var(--blue);
  padding: 7.5rem 2.5rem 4.5rem;
  text-align: center;
  color: var(--white);
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)' opacity='0.35'/%3E%3C/svg%3E");
  opacity: 0.14;
  pointer-events: none;
}

.hero > * { position: relative; }

.hero-label {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--pale-blue);
  margin-bottom: 1.25rem;
}

.hero h1 {
  font-size: clamp(2.4rem, 5.5vw, 4rem);
  font-weight: 600;
  color: var(--white);
  margin-bottom: 0.75rem;
  letter-spacing: -0.01em;
}

.hero-title {
  font-family: var(--serif);
  font-style: italic;
  font-size: 1.2rem;
  color: var(--light-blue);
  margin-bottom: 0.4rem;
}

.hero-school {
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--pale-blue);
}

.hero-divider { width: 48px; height: 3px; background: var(--bright); margin: 1.75rem auto; }

.hero-tagline {
  max-width: 560px;
  margin: 0 auto;
  color: var(--pale-blue);
  font-size: 1rem;
  line-height: 1.7;
}

/* ── Shared section layout ─────────────────────────────── */
.section-inner { max-width: 1080px; margin: 0 auto; padding: 4.5rem 2.5rem; }

.section-label {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--bright);
  margin-bottom: 0.6rem;
}

.section-heading { font-size: 2rem; margin-bottom: 2.25rem; }
.section-divider { width: 40px; height: 3px; background: var(--light-blue); margin-bottom: 2.25rem; }

/* ── About ─────────────────────────────────────────────── */
#about { background: var(--paper); }

.about-grid { display: grid; grid-template-columns: 260px 1fr; gap: 4rem; align-items: start; }

.about-photo {
  width: 260px;
  height: 300px;
  object-fit: cover;
  object-position: top center;
  border-top: 4px solid var(--blue);
  display: block;
}

.about-text p { color: var(--ink-soft); margin-bottom: 1.25rem; }
.about-text p:last-child { margin-bottom: 0; }
.about-text strong { color: var(--ink); }

.about-links { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 1.75rem; }

.pill {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.45rem 1rem;
  border: 1.5px solid var(--blue);
  color: var(--blue);
  border-radius: 3px;
  transition: all 0.15s;
}

.pill:hover { background: var(--blue); color: var(--white); text-decoration: none; }

/* ── Courses ───────────────────────────────────────────── */
#courses { background: var(--paper-deep); }

.course-subsection { margin-bottom: 3.5rem; }
.course-subsection:last-child { margin-bottom: 0; }

.course-subsection-label {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 1.25rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--line);
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 1.25rem;
}

.course-card {
  background: var(--white);
  border: 1px solid var(--line);
  border-top: 3px solid var(--blue);
  border-radius: 6px;
  padding: 1.5rem 1.5rem 1.25rem;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.15s, transform 0.15s;
}

.course-card:hover { box-shadow: 0 6px 24px rgba(14, 64, 106, 0.12); transform: translateY(-2px); }
.course-card.cotaught { border-top-color: var(--bright); }
.course-card.prev { border-top-color: var(--light-blue); }
.course-card.prev h3 { color: var(--navy); opacity: 0.85; }

.course-tag {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 0.6rem;
}

.course-card h3 { font-size: 1.15rem; margin-bottom: 0.6rem; line-height: 1.3; }
.course-card p { font-size: 0.88rem; color: var(--ink-soft); flex: 1; margin-bottom: 1.25rem; }

.card-actions { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }

.course-link {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--bright);
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.course-link::after { content: '→'; }
.course-link:hover { text-decoration: none; color: var(--navy); }

.qlass-btn {
  display: inline-block;
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.4rem 0.9rem;
  background: var(--blue);
  color: var(--white);
  border-radius: 3px;
  transition: background 0.15s;
}

.qlass-btn:hover { background: var(--navy); color: var(--white); text-decoration: none; }

/* ── Background (blue band) ────────────────────────────── */
#background { background: var(--blue); color: var(--white); }
#background .section-heading { color: var(--white); }
#background .section-label { color: var(--pale-blue); }
#background .section-divider { background: var(--light-blue); }

.background-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3rem; }

.bg-block h3 { font-size: 1.2rem; color: var(--pale-blue); margin-bottom: 0.75rem; }
.bg-block p { font-size: 0.95rem; color: rgba(255, 255, 255, 0.82); line-height: 1.7; }
.bg-block p + p { margin-top: 1rem; }
.bg-block strong { color: var(--white); }

/* ── Talks ─────────────────────────────────────────────── */
#talks { background: var(--paper); }

.talk-list { display: flex; flex-direction: column; gap: 1.5rem; }

.talk-item {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 1.5rem;
  align-items: start;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--line);
}

.talk-item:last-child { border-bottom: none; }

.talk-year {
  font-family: var(--serif);
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--light-blue);
  line-height: 1;
  padding-top: 0.2rem;
}

.talk-content h3 { font-size: 1.1rem; margin-bottom: 0.3rem; }
.talk-content .talk-venue { font-size: 0.85rem; color: var(--ink-soft); margin-bottom: 0.5rem; }
.talk-content p { font-size: 0.9rem; color: var(--ink-soft); }

/* ── Projects ──────────────────────────────────────────── */
#projects { background: var(--paper-deep); }

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
}

.project-card {
  background: var(--white);
  border: 1px solid var(--line);
  border-left: 3px solid var(--bright);
  border-radius: 6px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.15s;
}

.project-card:hover { box-shadow: 0 6px 24px rgba(14, 64, 106, 0.1); }
.project-card h3 { font-size: 1.05rem; margin-bottom: 0.5rem; }
.project-card p { font-size: 0.85rem; color: var(--ink-soft); flex: 1; margin-bottom: 1rem; }

/* ── Footer ────────────────────────────────────────────── */
footer {
  background: var(--blue);
  color: var(--pale-blue);
  text-align: center;
  padding: 2.5rem;
  font-size: 0.82rem;
}

footer a { color: var(--light-blue); }

/* ── Course pages ──────────────────────────────────────── */
body.course-page { background: var(--paper); }

.course-header {
  background: var(--blue);
  color: var(--white);
  margin-top: 60px;
  position: relative;
  overflow: hidden;
}

.course-header::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)' opacity='0.35'/%3E%3C/svg%3E");
  opacity: 0.14;
  pointer-events: none;
}

.course-header .section-inner { position: relative; padding: 2.75rem 2.5rem; max-width: 800px; }

.course-header .course-tag { color: var(--pale-blue); margin-bottom: 0.4rem; }
.course-header h1 { color: var(--white); font-size: 2.1rem; margin-bottom: 0.75rem; }
.course-actions { min-height: 0; }
.course-actions .qlass-btn { background: var(--bright); }
.course-actions .qlass-btn:hover { background: var(--white); color: var(--blue); }

body.course-page main { max-width: 800px; margin: 0 auto; padding: 2.5rem 2.5rem 4rem; }

body.course-page main > h1:first-of-type { display: none; }

body.course-page main h1 { font-size: 2rem; margin-bottom: 0.75rem; padding-bottom: 0.75rem; border-bottom: 3px solid var(--blue); }
body.course-page main h2 { font-size: 1.35rem; margin-top: 2.5rem; margin-bottom: 0.75rem; padding-bottom: 0.4rem; border-bottom: 1px solid var(--line); }
body.course-page main h3 { font-size: 1.1rem; color: var(--navy); margin-top: 1.5rem; margin-bottom: 0.5rem; }
body.course-page main p { margin-bottom: 1rem; color: var(--ink-soft); }
body.course-page main ul, body.course-page main ol { padding-left: 1.5rem; margin-bottom: 1rem; }
body.course-page main li { margin-bottom: 0.3rem; }
body.course-page main strong { color: var(--ink); }
body.course-page main blockquote { border-left: 3px solid var(--light-blue); padding-left: 1rem; color: var(--ink-soft); margin: 1rem 0; }
body.course-page main code { background: var(--paper-deep); padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em; }
body.course-page main pre { background: var(--paper-deep); padding: 1rem; overflow-x: auto; margin-bottom: 1rem; border-left: 3px solid var(--light-blue); }
body.course-page main pre code { background: none; padding: 0; }
body.course-page main table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; font-size: 0.9rem; }
body.course-page main th { background: var(--blue); color: var(--white); font-family: var(--sans); font-size: 0.85rem; padding: 0.6rem 0.75rem; text-align: left; }
body.course-page main td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--line); }
body.course-page main tr:nth-child(even) td { background: var(--paper-deep); }
body.course-page main hr { border: none; border-top: 1px solid var(--line); margin: 2rem 0; }

#loading { color: var(--ink-soft); font-style: italic; }

/* ── Qlass feed panel ──────────────────────────────────── */
.qlass-feed {
  max-width: 800px;
  margin: 2.5rem auto 0;
  padding: 1.5rem 1.75rem;
  background: var(--white);
  border: 1px solid var(--line);
  border-left: 3px solid var(--bright);
  border-radius: 6px;
}

.qlass-feed-title {
  font-size: 1.05rem;
  margin-bottom: 1rem;
}

.qlass-feed h3 {
  font-family: var(--sans);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin: 1rem 0 0.4rem;
}

.qlass-feed ul { list-style: none; }
.qlass-feed li { font-size: 0.9rem; padding: 0.3rem 0; border-bottom: 1px solid var(--paper-deep); }
.qlass-feed li:last-child { border-bottom: none; }
.qlass-feed .muted { color: var(--ink-soft); font-size: 0.82rem; }

@media (max-width: 900px) {
  .qlass-feed { margin-left: 2.5rem; margin-right: 2.5rem; }
}

/* ── Responsive ────────────────────────────────────────── */
@media (max-width: 768px) {
  .nav-toggle { display: block; }

  .nav-links {
    display: none;
    position: absolute;
    top: 60px;
    left: 0;
    right: 0;
    background: var(--blue);
    flex-direction: column;
    gap: 0;
    padding: 0.5rem 0 1rem;
    box-shadow: 0 8px 16px rgba(14, 64, 106, 0.25);
  }

  .nav-links.open { display: flex; }
  .nav-links li { padding: 0.6rem 2.5rem; }

  .about-grid { grid-template-columns: 1fr; }
  .about-photo { width: 100%; height: 280px; }
  .background-grid { grid-template-columns: 1fr; gap: 2rem; }
  .talk-item { grid-template-columns: 60px 1fr; gap: 1rem; }
  .talk-year { font-size: 1.1rem; }

  body.course-page main { padding: 2rem 1.25rem 3rem; }
  .course-header .section-inner { padding: 2rem 1.25rem; }
  .qlass-feed { margin-left: 1.25rem; margin-right: 1.25rem; }
}
```

- [ ] **Step 2: Sanity-check the CSS parses**

Run: `node -e "const css=require('fs').readFileSync('assets/css/site.css','utf8'); const open=(css.match(/{/g)||[]).length, close=(css.match(/}/g)||[]).length; console.log(open===close?'balanced':'UNBALANCED', open, close)"`
Expected: `balanced <n> <n>` (equal open/close brace counts; the data-URI SVGs contain no `{`).

- [ ] **Step 3: Commit**

```bash
git add assets/css/site.css
git commit -m "Add shared stylesheet: hybrid editorial + Cushman blue design system"
```

---

### Task 3: Redesign `index.html` to use the shared stylesheet

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `assets/css/site.css` class names from Task 2.
- Produces: homepage markup that Task 4's `site.js` hooks into — a `<button class="nav-toggle">`, a `<ul class="nav-links">`, and one `<div class="card-actions" data-course="{slug}">` per course card. Script tags for `/assets/js/qlass-config.js` and `/assets/js/site.js` are added here (files created in Task 4; a 404 in between tasks is harmless — `site.js` is additive).

- [ ] **Step 1: Replace the `<head>` font links and inline `<style>` block**

In `index.html`, replace the Raleway/Inter font link and the entire `<style>…</style>` block (currently lines 9–452) with:

```html
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/site.css">
```

(The two `preconnect` links above it stay.)

- [ ] **Step 2: Replace the nav with a hamburger-capable version**

Replace the current `<nav>…</nav>` block with:

```html
  <nav>
    <span class="nav-name">Willie Avendano</span>
    <button class="nav-toggle" aria-label="Menu" aria-expanded="false">☰</button>
    <ul class="nav-links">
      <li><a href="#about">About</a></li>
      <li><a href="#courses">Courses</a></li>
      <li><a href="#background">Background</a></li>
      <li><a href="#talks">Talks</a></li>
      <li><a href="#projects">Projects</a></li>
    </ul>
  </nav>
```

- [ ] **Step 3: Add `card-actions` wrappers with course slugs**

For each of the 9 course cards, wrap the existing `<a class="course-link" …>View Course</a>` in a `card-actions` div. The exact opening tag per card (match card by its `<h3>`):

| Card `<h3>` | Wrapper opening tag |
|---|---|
| AP Statistics | `<div class="card-actions" data-course="ap-statistics">` |
| Engineering Fundamentals | `<div class="card-actions" data-course="engineering-fundamentals">` |
| Introduction to Engineering Design | `<div class="card-actions" data-course="intro-to-engineering-design">` |
| Principles of Engineering | `<div class="card-actions" data-course="principles-of-engineering">` |
| Computer Science Math | `<div class="card-actions" data-course="computer-science-math">` |
| AP Research | `<div class="card-actions" data-course="ap-research">` |
| AP Physics C | `<div class="card-actions" data-course="ap-physics-c">` |
| AP Computer Science Principles | `<div class="card-actions" data-course="ap-computer-science-principles">` |
| AP Computer Science A | `<div class="card-actions" data-course="ap-computer-science-a">` |

Resulting pattern for every card (shown for AP Statistics; apply identically to all 9 with that card's existing href):

```html
            <div class="card-actions" data-course="ap-statistics">
              <a class="course-link" href="https://willieavendano.github.io/ap-statistics/">View Course</a>
            </div>
```

- [ ] **Step 4: Remove the one inline style**

The AP Research card is `<div class="course-card" style="border-top-color: var(--bright);">`. Change it to:

```html
          <div class="course-card cotaught">
```

- [ ] **Step 5: Add script tags before `</body>`**

```html
  <script src="/assets/js/qlass-config.js"></script>
  <script src="/assets/js/site.js"></script>
```

- [ ] **Step 6: Verify structure**

Run: `grep -c 'data-course=' index.html && grep -c 'nav-toggle' index.html && grep -c '<style>' index.html && grep -c 'Raleway' index.html`
Expected: `9`, then `1`, then `0` (grep -c exits 1 on zero matches — `|| true` as needed), then `0`.

Run: `python3 -m http.server 8000 &` then open `http://localhost:8000/` in a browser.
Expected: paper background, Fraunces serif headings, blue hero with grain, all sections styled, cards hover-lift. No Qlass buttons anywhere (config not yet loaded — and all URLs will be null anyway). Kill the server after.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "Redesign homepage: shared stylesheet, mobile nav, card action slots"
```

---

### Task 4: Add `qlass-config.js` and `site.js` (mobile nav + gateway links)

**Files:**
- Create: `assets/js/qlass-config.js`
- Create: `assets/js/site.js`

**Interfaces:**
- Consumes: `[data-course]` elements and `.nav-toggle`/`.nav-links` from Task 3.
- Produces: `window.QLASS = { base, courses: { [slug]: { name, tag, classUrl } } }` — read by Task 5's course shell (for `name`/`tag` in the header) and Task 6's feed script (for `base`). `site.js` appends `<a class="qlass-btn">` into any `[data-course]` element whose config `classUrl` is non-null.

- [ ] **Step 1: Create `assets/js/qlass-config.js`**

```js
// Qlass integration config. When a class exists in Qlass (class.avendano.xyz),
// set its classUrl here — every "Open in Qlass" button lights up from this file.
window.QLASS = {
  base: 'https://class.avendano.xyz',
  courses: {
    'ap-statistics':                  { name: 'AP Statistics',                  tag: 'AP · Mathematics',       classUrl: null },
    'engineering-fundamentals':       { name: 'Engineering Fundamentals',       tag: 'PLTW · Engineering',     classUrl: null },
    'intro-to-engineering-design':    { name: 'Introduction to Engineering Design', tag: 'PLTW · Engineering', classUrl: null },
    'principles-of-engineering':      { name: 'Principles of Engineering',      tag: 'PLTW · Engineering',     classUrl: null },
    'computer-science-math':          { name: 'Computer Science Math',          tag: 'Computer Science',       classUrl: null },
    'ap-research':                    { name: 'AP Research',                    tag: 'AP Capstone',            classUrl: null },
    'ap-physics-c':                   { name: 'AP Physics C',                   tag: 'AP · Science',           classUrl: null },
    'ap-computer-science-principles': { name: 'AP Computer Science Principles', tag: 'AP · Computer Science',  classUrl: null },
    'ap-computer-science-a':          { name: 'AP Computer Science A',          tag: 'AP · Computer Science',  classUrl: null }
  }
};
```

- [ ] **Step 2: Create `assets/js/site.js`**

```js
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
```

- [ ] **Step 3: Verify — no buttons with null URLs, button appears with a URL**

Run: `python3 -m http.server 8000 &` and open `http://localhost:8000/`.
Expected: no `.qlass-btn` anywhere (all classUrl null).

In the browser console run:
```js
window.QLASS.courses['ap-statistics'].classUrl = 'https://class.avendano.xyz/classes/demo';
document.querySelectorAll('[data-course]').forEach(el => { const c = QLASS.courses[el.dataset.course]; if (c && c.classUrl) { const a = document.createElement('a'); a.className='qlass-btn'; a.href=c.classUrl; a.textContent='Open in Qlass ↗'; el.appendChild(a); } });
```
Expected: a styled blue "Open in Qlass ↗" button appears on the AP Statistics card only. Also narrow the window below 768px and click ☰ — the nav dropdown opens and closes. Kill the server after.

- [ ] **Step 4: Commit**

```bash
git add assets/js/qlass-config.js assets/js/site.js
git commit -m "Add Qlass config and site JS (mobile nav, config-driven gateway links)"
```

---

### Task 5: Replace all 9 course pages with one shared shell

**Files:**
- Modify: `ap-statistics/index.html`, `engineering-fundamentals/index.html`, `intro-to-engineering-design/index.html`, `principles-of-engineering/index.html`, `computer-science-math/index.html`, `ap-research/index.html`, `ap-physics-c/index.html`, `ap-computer-science-principles/index.html`, `ap-computer-science-a/index.html` — all get IDENTICAL content.

**Interfaces:**
- Consumes: `window.QLASS.courses[slug].name/.tag` from Task 4's config; `body.course-page`, `.course-header`, `#course-tag`, `#course-name`, `#course-actions` styles from Task 2; `site.js` button injection (the shell sets `data-course` on `#course-actions` before `site.js` runs).
- Produces: course pages whose slug is derived from `location.pathname` — Task 6's feed script uses the same derivation and inserts its panel before `<main>`.

- [ ] **Step 1: Write the canonical shell**

Create the file at `ap-statistics/index.html` (overwriting) with exactly:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Course — Willie Avendano</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/site.css">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body class="course-page">

  <nav>
    <span class="nav-name">Willie Avendano</span>
    <a class="nav-back" href="/">← All Courses</a>
  </nav>

  <header class="course-header">
    <div class="section-inner">
      <p class="course-tag" id="course-tag"></p>
      <h1 id="course-name">Course</h1>
      <div class="course-actions" id="course-actions"></div>
    </div>
  </header>

  <main>
    <p id="loading">Loading course content…</p>
  </main>

  <footer>
    <p>Willie Avendano &mdash; <a href="https://www.cushmanschool.org" target="_blank">The Cushman School</a> &mdash; Miami, FL</p>
    <p style="margin-top:0.5rem;">
      <a href="mailto:wavendano@cushmanschool.org">wavendano@cushmanschool.org</a>
    </p>
  </footer>

  <script src="/assets/js/qlass-config.js"></script>
  <script>
    (function () {
      'use strict';
      var slug = location.pathname.split('/').filter(Boolean)[0] || '';
      var course = (window.QLASS && window.QLASS.courses[slug]) || {};
      if (course.name) {
        document.getElementById('course-name').textContent = course.name;
        document.title = course.name + ' — Willie Avendano';
      }
      if (course.tag) document.getElementById('course-tag').textContent = course.tag;
      document.getElementById('course-actions').setAttribute('data-course', slug);

      fetch('./README.md')
        .then(function (r) { if (!r.ok) throw new Error('missing'); return r.text(); })
        .then(function (md) {
          document.querySelector('main').innerHTML = marked.parse(md);
        })
        .catch(function () {
          document.getElementById('loading').textContent = 'Course content coming soon.';
        });
    })();
  </script>
  <script src="/assets/js/site.js"></script>

</body>
</html>
```

- [ ] **Step 2: Copy the shell to the other 8 course directories**

```bash
for d in engineering-fundamentals intro-to-engineering-design principles-of-engineering computer-science-math ap-research ap-physics-c ap-computer-science-principles ap-computer-science-a; do
  cp ap-statistics/index.html "$d/index.html"
done
```

- [ ] **Step 3: Verify all 9 shells are identical and pages render**

Run: `md5 -q ap-statistics/index.html engineering-fundamentals/index.html intro-to-engineering-design/index.html principles-of-engineering/index.html computer-science-math/index.html ap-research/index.html ap-physics-c/index.html ap-computer-science-principles/index.html ap-computer-science-a/index.html | sort -u | wc -l`
Expected: `1`

Run: `python3 -m http.server 8000 &` and open `http://localhost:8000/ap-statistics/` and `http://localhost:8000/ap-research/`.
Expected: blue course header shows the correct tag + course name from config (e.g. "AP · Mathematics / AP Statistics"), browser tab title updates, README content renders below WITHOUT a duplicate course title (the README's own `# AP Statistics` h1 is hidden by CSS), no Qlass button (classUrl null). Kill the server after.

- [ ] **Step 4: Commit**

```bash
git add ap-statistics engineering-fundamentals intro-to-engineering-design principles-of-engineering computer-science-math ap-research ap-physics-c ap-computer-science-principles ap-computer-science-a
git commit -m "Unify course pages into one shared config-driven shell"
```

---

### Task 6: Qlass feed embed (TDD on the pure logic)

**Files:**
- Create: `assets/js/qlass-feed.js`
- Create: `tests/qlass-feed.test.cjs`
- Modify: all 9 course `index.html` files (add one script tag)

**Interfaces:**
- Consumes: `window.QLASS.base` from Task 4; `.qlass-feed` styles from Task 2; course shell DOM (`<main>`) from Task 5.
- Produces: `module.exports = { buildFeedModel(data, now), readCache(storage, slug, now), writeCache(storage, slug, data, now), escapeHtml(s) }` when loaded under Node; in the browser, fetches `{base}/api/public/classes/{slug}/feed` and inserts a `<section class="qlass-feed">` before `<main>`, or does nothing at all on any failure.

- [ ] **Step 1: Write the failing tests**

Create `tests/qlass-feed.test.cjs`:

```js
const { test } = require('node:test');
const assert = require('node:assert');
const { buildFeedModel, readCache, writeCache, escapeHtml } = require('../assets/js/qlass-feed.js');

const NOW = new Date('2026-07-07T12:00:00Z');
const NOW_MS = NOW.getTime();

function fakeStorage() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v))
  };
}

test('buildFeedModel returns null for garbage input', () => {
  assert.strictEqual(buildFeedModel(null, NOW), null);
  assert.strictEqual(buildFeedModel('nope', NOW), null);
  assert.strictEqual(buildFeedModel({}, NOW), null);
});

test('buildFeedModel returns null when feed is empty', () => {
  assert.strictEqual(buildFeedModel({ announcements: [], upcoming: [] }, NOW), null);
});

test('buildFeedModel keeps 3 newest announcements, newest first', () => {
  const data = {
    announcements: [
      { title: 'a', postedAt: '2026-07-01T00:00:00Z' },
      { title: 'b', postedAt: '2026-07-04T00:00:00Z' },
      { title: 'c', postedAt: '2026-07-02T00:00:00Z' },
      { title: 'd', postedAt: '2026-07-03T00:00:00Z' },
      { notitle: true }
    ]
  };
  const model = buildFeedModel(data, NOW);
  assert.deepStrictEqual(model.announcements.map(a => a.title), ['b', 'd', 'c']);
});

test('buildFeedModel drops past-due items, sorts soonest first, caps at 5', () => {
  const mk = (t, d) => ({ title: t, dueAt: d });
  const data = {
    upcoming: [
      mk('past', '2026-07-01T00:00:00Z'),
      mk('f', '2026-07-14T00:00:00Z'),
      mk('a', '2026-07-08T00:00:00Z'),
      mk('e', '2026-07-13T00:00:00Z'),
      mk('c', '2026-07-10T00:00:00Z'),
      mk('b', '2026-07-09T00:00:00Z'),
      mk('d', '2026-07-12T00:00:00Z')
    ]
  };
  const model = buildFeedModel(data, NOW);
  assert.deepStrictEqual(model.upcoming.map(u => u.title), ['a', 'b', 'c', 'd', 'e']);
});

test('buildFeedModel carries the class name', () => {
  const model = buildFeedModel(
    { class: { name: 'AP Statistics' }, announcements: [{ title: 'hi', postedAt: '2026-07-06T00:00:00Z' }] },
    NOW
  );
  assert.strictEqual(model.className, 'AP Statistics');
});

test('cache roundtrips within TTL and expires after 5 minutes', () => {
  const s = fakeStorage();
  writeCache(s, 'ap-statistics', { announcements: [] }, NOW_MS);
  assert.deepStrictEqual(readCache(s, 'ap-statistics', NOW_MS + 4 * 60 * 1000), { announcements: [] });
  assert.strictEqual(readCache(s, 'ap-statistics', NOW_MS + 6 * 60 * 1000), null);
  assert.strictEqual(readCache(s, 'other-slug', NOW_MS), null);
});

test('readCache tolerates corrupt entries', () => {
  const s = fakeStorage();
  s.setItem('qlass-feed:ap-statistics', '{not json');
  assert.strictEqual(readCache(s, 'ap-statistics', NOW_MS), null);
});

test('escapeHtml neutralizes markup', () => {
  assert.strictEqual(escapeHtml('<script>"x" & \'y\'</script>'),
    '&lt;script&gt;&quot;x&quot; &amp; &#39;y&#39;&lt;/script&gt;');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/`
Expected: FAIL — `Cannot find module '../assets/js/qlass-feed.js'`

- [ ] **Step 3: Implement `assets/js/qlass-feed.js`**

```js
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
        var title = u.url
          ? '<a href="' + escapeHtml(u.url) + '" target="_blank" rel="noopener">' + escapeHtml(u.title) + '</a>'
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
  var cached = readCache(window.sessionStorage, slug, nowMs);
  if (cached) {
    render(buildFeedModel(cached, new Date(nowMs)));
    return;
  }

  fetch(cfg.base + '/api/public/classes/' + encodeURIComponent(slug) + '/feed')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data) return;
      writeCache(window.sessionStorage, slug, data, nowMs);
      render(buildFeedModel(data, new Date(nowMs)));
    })
    .catch(function () { /* endpoint absent / CORS / offline — render nothing */ });
})();
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/`
Expected: all tests PASS (8 pass, 0 fail).

- [ ] **Step 5: Add the feed script to all 9 course shells**

```bash
for d in ap-statistics engineering-fundamentals intro-to-engineering-design principles-of-engineering computer-science-math ap-research ap-physics-c ap-computer-science-principles ap-computer-science-a; do
  perl -0pi -e 's{  <script src="/assets/js/site.js"></script>}{  <script src="/assets/js/site.js"></script>\n  <script src="/assets/js/qlass-feed.js"></script>}' "$d/index.html"
done
grep -l 'qlass-feed.js' */index.html | wc -l
```
Expected: `9`

- [ ] **Step 6: Verify browser behavior — silent against dead endpoint, renders with mock data**

Run: `python3 -m http.server 8000 &` and open `http://localhost:8000/ap-statistics/`.
Expected: page renders normally; NO `.qlass-feed` panel; no visible error (a failed network request in devtools console is fine — that's the graceful path).

Then in the browser console, verify the render path with mock data:
```js
sessionStorage.setItem('qlass-feed:ap-statistics', JSON.stringify({ t: Date.now(), data: {
  class: { name: 'AP Statistics' },
  announcements: [{ title: 'Welcome back!', body: 'First lab Friday.', postedAt: new Date().toISOString() }],
  upcoming: [{ title: 'Problem Set 1', dueAt: new Date(Date.now() + 3 * 864e5).toISOString(), url: 'https://class.avendano.xyz' }]
}}));
location.reload();
```
Expected: after reload, a "This week in Qlass" panel appears between the course header and the README content, styled as a white card with a bright-blue left rule, showing the announcement and the due item. Then run `sessionStorage.clear(); location.reload();` — the panel disappears. Kill the server after.

- [ ] **Step 7: Commit**

```bash
git add assets/js/qlass-feed.js tests/qlass-feed.test.cjs ap-statistics engineering-fundamentals intro-to-engineering-design principles-of-engineering computer-science-math ap-research ap-physics-c ap-computer-science-principles ap-computer-science-a
git commit -m "Add self-hiding Qlass feed embed with node-tested feed logic"
```

---

### Task 7: Document the Qlass API contract

**Files:**
- Create: `docs/qlass-integration.md`

**Interfaces:**
- Consumes: the contract implemented by Task 6.
- Produces: the spec the future qlass-lms endpoint will be built against.

- [ ] **Step 1: Write `docs/qlass-integration.md`**

```markdown
# Qlass ↔ willieavendano.github.io Integration Contract

This static site (GitHub Pages) is the public front door; Qlass
(https://class.avendano.xyz, repo `willieavendano/qlass-lms`) is the
logged-in classroom. Two integration points, both driven by
`assets/js/qlass-config.js`.

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
  `Access-Control-Allow-Origin: https://willieavendano.github.io`.
- **404** for unknown or non-opted-in slugs.
- Body text should be truncated server-side (e.g. 280 chars) — the site
  renders it as plain text.

### Testing the embed without the endpoint

Seed the cache in the browser console on any course page:

    sessionStorage.setItem('qlass-feed:ap-statistics', JSON.stringify({
      t: Date.now(),
      data: { class: { name: 'AP Statistics' },
              announcements: [{ title: 'Hello', postedAt: new Date().toISOString() }],
              upcoming: [] }
    }));
    location.reload();

Logic tests: `node --test tests/`
```

- [ ] **Step 2: Commit**

```bash
git add docs/qlass-integration.md
git commit -m "Document Qlass feed API contract and integration points"
```

---

### Task 8: Full-site verification

**Files:**
- No new files. Verification only.

**Interfaces:**
- Consumes: everything above.
- Produces: a verified, committed working tree ready for the user's push decision.

- [ ] **Step 1: Run the logic tests**

Run: `node --test tests/`
Expected: all PASS.

- [ ] **Step 2: Check every page serves and is wired correctly**

```bash
python3 -m http.server 8000 & sleep 1
for p in "" ap-statistics/ engineering-fundamentals/ intro-to-engineering-design/ principles-of-engineering/ computer-science-math/ ap-research/ ap-physics-c/ ap-computer-science-principles/ ap-computer-science-a/; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/$p")
  echo "$code /$p"
done
curl -s http://localhost:8000/assets/css/site.css -o /dev/null -w "css %{http_code}\n"
curl -s http://localhost:8000/assets/js/qlass-config.js -o /dev/null -w "config %{http_code}\n"
curl -s http://localhost:8000/assets/js/site.js -o /dev/null -w "site %{http_code}\n"
curl -s http://localhost:8000/assets/js/qlass-feed.js -o /dev/null -w "feed %{http_code}\n"
kill %1
```
Expected: `200` for all ten pages and all four assets.

- [ ] **Step 3: Browser spot-check**

With the server running, in a real browser check:
- Homepage at desktop width: paper background, Fraunces headings, grain on hero, hover-lift cards, no Qlass buttons.
- Homepage at < 768px: ☰ toggle opens/closes nav; no horizontal scroll.
- `ap-physics-c/` (a previously-taught course): header shows "AP · Science / AP Physics C", README renders, no duplicate title, no feed panel, no errors visible on the page.

- [ ] **Step 4: Confirm clean tree and report**

Run: `git status --short`
Expected: empty. Report to the user that all tasks are committed locally and NOT pushed — pushing to `master` deploys to GitHub Pages, so that's their call (they asked about push timing earlier).
