---
name: screen-tutorial
description: Build a narrated, captioned software tutorial video (Excel, Google Sheets, or any Mac app) from a JSON script — the agent drives the app, OpenScreen records it, narration is synthesized and mixed in, and the numbers on screen are checked against the handout. Use whenever asked for a screencast, walkthrough, "how to set up the spreadsheet" or software tutorial video for any class.
---

# Screen tutorial builder

Produces an upload-ready `.mp4` + `.srt` of a software walkthrough **without a
human at the keyboard**. The sibling of the Manim pipeline in `videos/manim/`
(same narrator, same house style, same caption format); this one records a
real application instead of drawing one.

```
videos/tutorials/<code>/<code>.tutorial.json   ← the script (committed)
videos/tutorials/out/<code>/                   ← build output (gitignored)
```

**The canon is code, not this doc.** Before building anything read
`references/script-format.md` (the script contract) and
`references/openscreen.md` (recorder CLI, MCP tools, gotchas). The worked
example to copy is `videos/tutorials/CSM-U2-hysa-car-sheets/`.

## Workflow

1. **Setup once per machine** — `scripts/setup.sh` checks Openscreen.app,
   the two macOS permissions (Screen Recording for the terminal/host app;
   Accessibility only for the `sheets` driver), the narrator key, and prints
   a status table. It installs OpenScreen from the GitHub release if missing.
   The project-level `.mcp.json` already registers `openscreen mcp` for
   interactive editing; nothing per-machine is needed for that.
2. **Write the script.** Start from `templates/tutorial-script.example.json`.
   Source of truth for every number and cell address is the student handout
   (for Cornerstone II: `computer-science-math/assignments/q2-hysa-car-bridge.html`)
   — never invent values; the `checks` in the script must match the handout's
   printed checks to the cent.
3. **Validate + draft:** `scripts/tutorial.py validate <script>` (also prints
   the effective voice id/model/settings/direction and each part's length)
   then `scripts/tutorial.py dryrun <script>` (no recording; drives the app
   at full speed, runs every check, prints estimated runtime per scene;
   `--live` uses real pacing). Fix checks before spending voice credits.
   `build --chapter <id>` or `build --part <id>` records one piece — use it
   to review look and sync on a short take before the full run.
4. **Record:** long scripts are split into ~5-minute `parts` (see
   `references/script-format.md` § Parts); build them all with
   `scripts/tutorial.py build <script> --all-parts --voice eleven` — one
   video per part (`<code>-p1.mp4` …), a fresh workbook each, a summary
   table at the end; rerun a failed one with `--part p3`. Use `--voice say`
   for a free pass. ElevenLabs key read from `ELEVENLABS_API_KEY`, else
   `~/.hermes/.env`; clips cached by hash under
   `videos/tutorials/narration_cache/` — reruns are free. The key lives only
   on the Mini; on any other machine pull it into the environment for the
   one command, never onto disk:
   `ELEVENLABS_API_KEY=$(ssh luna@100.121.78.28 "grep -E '^ELEVENLABS_API_KEY=' ~/.hermes/.env | cut -d= -f2-") scripts/tutorial.py build … --voice eleven`.
   Leave the Mac alone while it records (~ script length). Step captions
   (the lower-third naming each action) are on by default; `--no-steps`
   turns them off.
5. **Review each part:** open its contact sheets (`out/<code>/sheet_NN.jpg`
   for a plain build, `out/<code>/<code>-pN-sheets/` for a part), its
   `.checks.json`, and the `steps` in its `.timeline.json`; watch each MP4
   once at 2×. Then publish like any other video (see
   `docs/recording-kit.md` for where uploads go).

## Listen check

Narration can be mis-synthesized even when the script is right: a dropped word,
a delivery tag read out loud, a number spoken wrong. After **every narration
change** — and always before publishing — transcribe the clips with whisper.cpp
and diff the transcript against the intended text:

```
scripts/listen_check.py tutorial videos/tutorials/out/<code>/<code>.timeline.json \
  [--report out.listen.json] [--threshold 0.25]

scripts/listen_check.py manim videos/manim/phy_u1_free_fall.py ... \
  [--report out.listen.json] [--threshold 0.25]
```

The tutorial form reads `scenes[].caption` + `scenes[].clip` from the timeline.
The manim form parses each `SCRIPT` dict with `ast` and maps every beat to its
cached clip with the same identity hash as `cushman.narration_clip()` (voice,
model, settings and `ELEVEN_DIRECTION` from `videos/manim/voice.env`).

Whisper and ffmpeg live on the Mini, so the tool ships local tutorial WAVs there
in one batched ssh session. It prints a per-scene table (WER, flags, first
differing words), writes a JSON report, and exits 1 if anything is flagged:
WER above the threshold, a spoken tag, a letters-vs-word mismatch such as "if"
vs "I F", or an intended number missing from the transcript. Fix the script or
the voice direction and re-run before recording the final take.

## Choosing the driver

| driver | how it drives | needs | use when |
|---|---|---|---|
| `excel` | Microsoft Excel's AppleScript dictionary (no synthetic keystrokes) | Excel for Mac; Automation permission (auto-prompted) | default for CS Math — the course's floor is Excel, and it works on the school-managed Mac without Accessibility |
| `sheets` | Google Chrome + System Events keystrokes | Accessibility permission for the host process; a signed-in Chrome profile | when the lesson is explicitly Google Sheets. **Untested on a device as of 2026-11-03** — its pure parts have unit tests; expect to debug dialogs on first use (see `references/sheets-driver.md`) |

Both drivers implement the same action vocabulary, so one script can be
rendered in either app (menus and dialogs differ; formulas do not).

## House style for narration

Same as `videos/manim/README.md` §4: hook → one idea → worked example with the
deck's numbers → the trap → one-line recap. Tutorials add one rule: **say the
parameter before the formula.** Each input cell gets a sentence on what it
means and where the student finds it; each formula gets *why this formula*,
then *what you should see*. 2.9 words/s; keep scenes under 45 words.

## Gotchas (hard-won)

- `ELECTRON_RUN_AS_NODE=1` is set inside Claude Code / T3 Code sessions and
  makes the Openscreen binary behave like plain Node. Always invoke it as
  `env -u ELECTRON_RUN_AS_NODE /Applications/Openscreen.app/Contents/MacOS/Openscreen …`
  (`tutorial.py` does this for you).
- Excel's first launch after login can take 60 s+; the driver waits for a window.
- Excel AppleScript `set formula of range "A13:A20" to …` does **not** fill
  down; use the driver's `fill_down` (it uses Excel's `fill down`/autofill).
- No ffmpeg on the school Mac: audio is converted with `afconvert`, measured
  with `afinfo`, concatenated with Python's `wave` module.
- Screen Recording permission belongs to the *host* process (Terminal, T3
  Code, Ghostty…), not to Openscreen, when the CLI is used. The first
  System Events call from a new host shows a one-time Accessibility prompt
  and hangs until it is answered — run `scripts/setup.sh` once, by hand.
- Excel's AppleScript `value of range` is rounded to the cell's display
  format; the driver reads numbers through `evaluate name "TEXT(…)"` instead.
- Contact sheets need `swiftc` (Xcode Command Line Tools); without it they
  are skipped with a warning. A 13" screen clamps the 1600×1000 window to
  1600×923; the export is still 16:9.
- A build is real time: an 18-minute script records for 18 minutes. Leave
  Excel alone; the workbook is closed without saving when it finishes.
