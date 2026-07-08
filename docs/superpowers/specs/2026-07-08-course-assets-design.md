# Course Teaching Assets — Design

**Date:** 2026-07-08 (written overnight for morning review — nothing executes until approved)
**Scope:** A production system for teaching assets, starting with Physics, extending to CS Math.
**Requested:** slide decks that introduce concepts; videos à la 3Blue1Brown for concepts,
demos, and problem walkthroughs; CS Math content-building extends the same system.

## Asset taxonomy

| Type | Physics | CS Math |
|---|---|---|
| **Concept decks** | One per calendar week/topic (Unit 0 Workshop I → Unit 9) | Lighter: one per unit kickoff + skill decks (VLOOKUP, Monte Carlo, Solver) |
| **Concept videos** (3B1B-style animation) | Hero concepts only: vectors/components, motion graphs, N2, energy conservation, wave superposition | Compound growth, law of large numbers, regression intuition |
| **Demo videos** (phone + maker space) | Lab setups: cart track, friction rig, collision carts, pendulum | Not needed |
| **Problem walkthroughs** (tablet screencast) | 2–3 per unit, keyed to the protocol | Excel build-alongs per cornerstone skill |
| **Starter workbooks** | — | One per cornerstone: tracker, amortization, budget, casino, stocks, lemonade, capstone dataset |
| **Datasets & rubrics** | Lab data templates | Design District data; Willie's cornerstone rubrics (incoming) |

## Recommended tooling (decision points flagged ⚑)

1. **Decks: reveal.js, in-repo, styled with the site's own tokens.** ⚑
   One shared `assets/slides/deck.css` (Familjen Grotesk / Atkinson / Fragment Mono,
   paper & Cushman blue) + one HTML file per deck under `<course>/slides/`.
   Decks become part of the site: versioned, linkable from calendars, students need
   no account. *Alternatives:* Google Slides (school-familiar, but unversioned,
   off-brand) or Canva (connected via MCP; good for one-off polish, weak for a
   50-deck system).
2. **Concept videos: Manim** (3Blue1Brown's actual engine, open source, Python). ⚑
   Scenes live in a `videos/` dir with a render guide; final MP4s go to a YouTube
   channel (unlisted or public ⚑ — needs a channel/account decision) and embed in
   course pages via plain iframes (marked.js passes raw HTML through).
   **Honest effort note:** a polished Manim minute costs hours. The design therefore
   uses Manim ONLY for ~8–10 hero concepts across both courses; everything else is
   the cheaper formats below.
3. **Problem walkthroughs: tablet screencast** (iPad/pencil or drawing tablet + OBS
   or QuickTime), one take, minimal editing. **Demos: phone video** on a cheap
   tripod in the maker space, trimmed only. A one-page recording kit doc
   standardizes framing, audio, naming.
4. **CS Math workbooks: real .xlsx starter templates** in each course's existing
   `resources/` folder (already scaffolded) — student-facing copies stripped of
   answers; teacher versions stay in Drive.

## Site integration

- Each course README gets a **Materials** section: per-unit lists of decks (links
  into `<course>/slides/`), videos (YouTube embeds/links), and downloads
  (`resources/` files). Manually curated — no generator changes now; a
  `links` field per calendar week is noted as future work.
- Naming convention: `slides/u0-w1-speaking-physics.html`,
  videos `PHY-U1-vectors-components`, workbooks `csm-p1-tracker-starter.xlsx`.

## Production order (calendar-driven)

**Sprint 1 (before Aug 24):** Physics Unit 0 decks ×3 + skills-check materials;
CS Math Toolbox decks ×3 + tracker starter workbook; recording kit assembled;
first Manim hero video (vector components — serves Physics U0 W3 AND feeds
kinematics).
**Sprint 2 (by late Sep):** Kinematics decks ×5, motion-graphs Manim video,
cart-lab demo video + lab-report-writing walkthrough; CS Math tracker
walkthrough screencasts.
**Steady state:** produce ~2 weeks ahead of each calendar; hero videos batched
over breaks.

## Out of scope

- Qlass integration of assets (post-pilot), LMS quizzes, per-week generator
  links field, other four courses (same system applies later).

## Morning decision points ⚑

1. reveal.js in-repo decks vs Google Slides/Canva?
2. Manim yes/no, and YouTube channel: existing account, new channel name, public or unlisted?
3. Effort ceiling for videos: hybrid plan above (8–10 Manim heroes, rest screencasts) OK?
4. Any equipment gaps: drawing tablet? tripod/mic?
