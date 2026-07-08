# Course Teaching Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **GATE: do not start until Willie approves the spec's ⚑ decision points** (docs/superpowers/specs/2026-07-08-course-assets-design.md).

**Goal:** Stand up the asset-production system (deck framework, video pipeline, recording kit, workbook conventions) and produce Sprint 1: everything Physics and CS Math need for the first three weeks of school.

**Architecture:** Assets are part of the site: reveal.js decks under `<course>/slides/` styled by one shared `assets/slides/deck.css` using the site's tokens; Manim scenes in `videos/manim/` rendering to a YouTube channel, embedded in course READMEs; starter workbooks in `<course>/resources/`; each course README gains a curated **Materials** section. No build step anywhere — reveal.js loads from CDN like marked.js does.

**Tech Stack:** reveal.js (CDN), Manim Community Edition (local Python), OBS/QuickTime + tablet for screencasts, .xlsx templates, YouTube embeds.

## Global Constraints

- No build step; everything deploys as static files on Vercel. Deck HTML loads reveal.js from CDN.
- Decks use the site tokens exactly: `--paper #F7F7F4`, `--ink #141412`, `--blue #0E406A`, Familjen Grotesk / Atkinson Hyperlegible Next / Fragment Mono via the same Google Fonts URL as the site.
- Naming: decks `<course>/slides/u<unit>-w<week>-<slug>.html`; videos `PHY|CSM-U<unit>-<slug>`; workbooks `csm-p<n>-<slug>-starter.xlsx`.
- Course calendars and `calendar/*.json` are untouched by this plan.
- Student-facing files contain no answer keys; teacher versions live in Drive, not the repo.
- Work on a branch/worktree; push only after Willie's review of the first rendered deck.

---

### Task 1: Deck framework + first Physics deck

**Files:**
- Create: `assets/slides/deck.css` (site-token reveal.js theme)
- Create: `physics/slides/u0-w1-speaking-physics.html` (complete Workshop I deck: SI units, measurement, Greek symbols, scientific notation, estimation — ~18 slides incl. Fermi-problem pair work)
- Modify: `physics/README.md` (add **Materials** section with Unit 0 subsection linking the deck)

Steps: write theme → write deck content (real teaching content, drawn from the Unit 0 topics already on the calendar) → serve locally and screenshot-check at 16:9 and mobile → link from README → commit. **Checkpoint: Willie reviews this deck before Tasks 2–3 proceed** (it sets the visual/content pattern for ~50 future decks).

### Task 2: Remaining Unit 0 + Toolbox decks (×5)

- `physics/slides/u0-w2-the-protocol.html`, `u0-w3-triangles-vectors.html`
- `computer-science-math/slides/u0-w1-notation-estimation.html`, `u0-w2-excel-training-wheels.html`, `u0-w3-lookups-protocol.html`
- Materials sections updated in both READMEs. Same pattern as Task 1's approved deck.

### Task 3: Manim pipeline + hero video #1

- Create `videos/manim/README.md` (env setup: `uv`/pip install manim, render commands, export settings 1080p/60) and `videos/manim/phy_u0_vectors.py` — a complete scene: a displacement arrow decomposing into components, SOH-CAH-TOA appearing as geometry, ending on the site-palette title card.
- Render locally; Willie uploads to the chosen YouTube channel (his account action); embed pattern documented and applied to Physics README Materials (plain `<iframe>` — marked passes it through; verify on the live course page).

### Task 4: Recording kit + walkthrough/demo conventions

- Create `docs/recording-kit.md`: equipment list (tablet, tripod, mic), OBS scene layouts for tablet walkthroughs, phone framing for maker-space demos, audio/naming/thumbnail conventions, a per-video checklist. One trial problem-walkthrough recorded by Willie validates the kit (his action; kit revised from friction encountered).

### Task 5: CS Math starter workbook #1 + dataset staging

- Build `computer-science-math/resources/csm-p1-tracker-starter.xlsx`: structured sheets (Food Table with lookup columns, Daily Log, Dashboard with prebuilt chart shells), instructions tab in course voice, no formulas pre-filled where students should build them.
- Stage `csm-capstone-design-district.csv` from the mdd-popup-forecast repo's data (verify licensing/pii: it's Willie's own class project data).
- Materials section in CS Math README links both.

### Task 6: Sprint-1 backlog freeze + verification

- Write the Sprint 2 backlog table (kinematics decks ×5, motion-graphs Manim scene, cart-lab demo shot list, report-writing walkthrough script outline; CS Math tracker screencast scripts ×3) into `docs/asset-backlog.md` with owner (Willie vs Claude) and due dates keyed to calendar weeks.
- Full check: all decks render locally, links resolve on course pages, tests pass, deploy, verify live.

## Effort honesty

Tasks 1–2 and 5–6 are Claude-executable end-to-end. Task 3 renders locally but
needs Willie's YouTube upload; Task 4's validation needs Willie behind a
microphone. The plan front-loads everything class-critical for Aug 24.
