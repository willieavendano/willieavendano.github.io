# Manim pipeline

How Willie renders course-explainer videos with [Manim Community Edition](https://www.manim.community/)
on his Mac, and how a finished render gets from a `.mp4` on disk to an embedded video on a
course page. Pairs with `docs/recording-kit.md`, which covers the two live-recorded formats
(tablet screencasts and phone demos) — this doc covers the third format: fully-animated,
code-generated scenes.

## 1. One-time setup

**Install Manim.** Preferred path — [`uv`](https://docs.astral.sh/uv/) as an isolated tool
install, so Manim's dependencies never touch your regular Python environment:

```
uv tool install manim
```

If `uv` isn't installed, get it with `brew install uv`, or fall back to plain pip:

```
pip3 install --user manim
```

**Install ffmpeg**, if you don't already have it (Manim shells out to it to encode video):

```
brew install ffmpeg
```

Check both landed:

```
manim --version
ffmpeg -version
```

**If `manim tool install` fails building `pycairo`** with an error mentioning
`Pkg-config for machine host machine not found`, you're missing `pkg-config` (a build
dependency of `pycairo`, one of Manim's rendering backends) even if `cairo` itself is
already installed via Homebrew. Fix:

```
brew install pkg-config
```

...then retry `uv tool install manim`. This was the one snag hit setting up this pipeline;
`cairo` was already present but `pkg-config` wasn't, so `pycairo`'s build system couldn't
find it.

**No LaTeX required.** Scenes in this folder use Manim's `Text` (Pango-rendered) for every
label, never `MathTex`/`Tex` — see the comment block at the top of `phy_u0_vectors.py` for
why. That means you do **not** need MacTeX/BasicTeX to render anything here. If a future
scene needs real typeset math, that's a deliberate, documented trade-off to make at the
time — don't install a LaTeX distribution "just in case."

## 2. Rendering

From this directory (`videos/manim/`):

```
manim -pqh phy_u0_vectors.py VectorComponents
```

- `-p` opens the finished file in your default player when done.
- `-qh` = quality **h**igh — 1080p at 60fps. This is the export quality for anything going
  to YouTube.
- `VectorComponents` is the Scene class name inside the file — one `.py` file can hold
  several scenes; name the one you want on the command line.

**Fast draft preview** while you're iterating on a scene (much quicker to render, visibly
blockier, fine for checking blocking/timing/typos — never for the final export):

```
manim -pql phy_u0_vectors.py VectorComponents
```

`-ql` = quality **l**ow — 480p15. Drop the `-p` too (`manim -ql ...`) if you don't want a
player window popping open every time, e.g. when rendering in a loop while tweaking code.

**Output location:** Manim writes into `media/` next to the scene file, mirroring the
quality flag:

```
videos/manim/media/videos/phy_u0_vectors/1080p60/VectorComponents.mp4   # from -qh
videos/manim/media/videos/phy_u0_vectors/480p15/VectorComponents.mp4    # from -ql
```

`media/` is generated output (partial movie files, cached frames, the final `.mp4`) — treat
it like a build directory, not a source directory.

## 3. Upload (YouTube)

Once you have the final `-qh` render, hand it to Willie's account for upload — follow the
**Upload workflow (YouTube)** section of `docs/recording-kit.md` exactly (title format,
description template, Unlisted-by-default visibility). Use the naming-convention slug as
both the export filename and the video's identity everywhere else.

This video's code: **`PHY-U0-vectors-components`**.

- Suggested export filename: `PHY-U0-vectors-components.mp4` (copy/rename the `-qh` output
  before uploading — the raw Manim output filename is just the Scene class name).
- Title: `Physics Unit 0 — Vectors & Components`
- After upload, copy the video ID from the share URL and drop it into the embed snippet in
  `docs/recording-kit.md` § **Embed snippet (course READMEs)**, then paste the filled-in
  `<iframe>` into `physics/README.md` under **Materials → Unit 0**, replacing the
  HTML-comment placeholder left there for exactly this purpose.

## 4. This folder's scenes

| File | Scene class | Video code | Status |
|------|-------------|------------|--------|
| `phy_u0_vectors.py` | `VectorComponents` | `PHY-U0-vectors-components` | Scene complete; render/upload pending |

`phy_u0_vectors.py` is also the **template** for every future scene in this pipeline — it's
commented generously on purpose. Read the module docstring and the per-method comments
before starting a new scene; the palette constants, the no-LaTeX rule, and the
`keep_in_frame()` helper are all meant to be reused, not re-derived.

## 5. Palette reference

Every scene should render on the site's light palette, not Manim's default dark theme —
these constants live at the top of each scene file and mirror `assets/css/site.css`:

| Constant | Hex | CSS token | Use |
|----------|-----|-----------|-----|
| `PAPER` | `#F7F7F4` | `--paper` | Scene background |
| `PAPER_DEEP` | `#EFEFEA` | `--paper-deep` | Subtle panels |
| `INK` | `#141412` | `--ink` | Primary text, strokes |
| `INK_SOFT` | `#6E6E68` | `--ink-soft` | Secondary/caption text |
| `BLUE` | `#0E406A` | `--blue` | Accent — the "hero" element, title card band |
