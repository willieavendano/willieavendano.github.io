# Tutorial script format (`*.tutorial.json`)

One JSON file describes one narrated screen tutorial: what the narrator says,
what happens on screen while they say it, and what must be true afterwards.
`scripts/tutorial.py` turns it into an MP4 + SRT. The format is app-agnostic;
the `app` field picks the driver that performs the actions.

JSON, not YAML — Python 3.9 stdlib only, no PyYAML on the school Macs.

## Top level

```jsonc
{
  "code": "CSM-U2-hysa-car-sheets",        // output basename; upper-case, hyphenated
  "title": "Save for the Car — building the model",
  "subtitle": "Computer Science Math · Cornerstone II",
  "app": "excel",                           // "excel" | "sheets" (driver name)
  "window": { "width": 1600, "height": 1000 },   // staged app window size (px)
  "stage": {                                // driver-specific staging, optional
    "zoom": 160,                            // sheet zoom % so cells read at 720p/1080p
    "sheets": ["Savings", "Loan"]           // worksheets to create, in order (excel/sheets)
  },
  "voice": {
    "mode": "eleven",                       // default narration mode; CLI --voice overrides
    "direction": "[dry, wry, understated]"  // optional Eleven v4 audio tag, prepended to every scene's spoken text
  },
  "chapters": [                             // optional grouping; lets you export one chapter
    { "id": "savings", "title": "The Savings sheet", "scenes": ["hook", "inputs", "..."] }
  ],
  "parts": [ /* optional; see § Parts */ ],
  "scenes": [ /* ordered */ ]
}
```

## Scene

A scene is one spoken beat plus the on-screen actions that happen *while* it
is spoken. Its duration is `max(narration, actions)` + a short breath.

```jsonc
{
  "id": "monthly-rate",                     // unique, kebab-case
  "say": "A P Y already includes compounding, so we take the twelfth root ...",
  "caption": "APY already includes compounding, so we take the 12th root …",   // optional: SRT text if it differs from the spoken text
  "actions": [ /* ordered, see below */ ],
  "zoom": "A2:B9",                          // optional: keep this range in view (driver scrolls) and request a camera zoom on it in the export
  "checks": [                               // optional: asserted after the actions; a failed check fails the build unless --no-check
    { "cell": "Savings!B6", "equals": 0.0036748, "tol": 1e-6 },
    { "cell": "Savings!E12", "equals": 651.84, "tol": 0.005 },
    { "cell": "Loan!B7", "text": "$231.63" }   // compares the displayed text
  ],
  "callout": { "text": "12th root, not ÷ 12", "at": 0.4 },  // optional on-video annotation; `at` = fraction of the scene
  "voice_direction": "[warm]"               // optional: replaces voice.direction for this scene ("" = none)
}
```

Voice direction (`voice.direction`, per-scene `voice_direction`) is sent to
ElevenLabs only, as `"<direction> <say>"`; it is part of the narration cache
key (changing it re-voices), and never reaches captions or the SRT. `say`
and draft modes ignore it. Voice settings come from `videos/manim/voice.env`
or the environment: `ELEVEN_STABILITY`, `ELEVEN_SIMILARITY`, `ELEVEN_STYLE`
(0–1), `ELEVEN_SPEAKER_BOOST` (true/false); v4 honours only the first two
but all are sent. `validate` prints the effective voice id, model, settings
and direction.

## Parts

A long build split into ~5-minute videos. Each part is its own recording
(fresh workbook), output `<code>-<part id>.mp4/.srt/.checks.json/.timeline.json`.

```jsonc
"parts": [
  { "id": "p1", "title": "Part 1 · Savings inputs and the monthly rate",
    "chapters": ["intro", "savings-inputs"],          // chapter ids; each chapter in at most one part
    "intro": { "id": "p1-intro", "say": "...", "actions": [], "caption": "..." },  // optional scene
    "outro": { "id": "p1-outro", "say": "..." } }                                  // optional scene
]
```

- `build --part p2` fast-forwards every script scene before the part's first
  scene, then records intro + the part's chapter scenes (script order) + outro.
- `build --all-parts` does that for each part in order, keeps going past a
  failed part, prints a table (part, duration, checks, file) and exits
  non-zero if any part failed. `dryrun` takes the same flags.
- Intro/outro are ordinary scenes (narration, caption, zoom, callout, step
  captions, checks optional); their ids must not collide with any scene.
- Plain `build` (no `--part`) records every scene, never the intros/outros.
- Per-part logs and contact sheets: `<name>.build.log`, `<name>-sheets/`.

## Step captions

A burned-in lower third (IBM Plex Mono, light on dark, centred at 50 %, 93 %
of the frame, 76 × 7 %) names the action on screen so students can follow.
One caption per `type`, `set`, `fill_down`, `format`, `header_row`, `chart`,
`sheet`, `rename_sheet`, `zoom`; it runs from the action's start to the next
caption's start or the scene's end. Text is ≤ 60 chars, no trailing period:

| action | caption |
|---|---|
| `type` / `set` | `B6 ← =(1+B3)^(1/12)-1` (consecutive ones merge: `A3 ← APY   B3 ← 4.5%`) |
| `fill_down` | `Fill down A12:F12 → A13:F71  (⌘D)` |
| `format` | `Format B6 as 0.00000%` · `Bold A10:F10` · `Width E: 14` · `Format B6: 0.00000%, bold` |
| `header_row` | `Row 10 headers: Month · Opening balance · …` |
| `chart` | `Insert line chart: <title>` |
| `sheet` / `rename_sheet` | `Sheet: Savings` / `Rename sheet Sheet1 → Savings` |
| `zoom` | `Zoom 160%` |

`Sheet!` is dropped for the active sheet. Callouts move up to y = 78 % so
they clear the bar. `--no-steps` turns them off (`--no-zoom` still controls
only zooms and callouts). Steps go into the timeline JSON
(`scenes[].steps: [{start, end, text}]`), never into the SRT.

Writing rules for `say` (spoken text — the voice engine reads it literally):

- Write words, not symbols: "four point five percent", "B three", "equals MIN of B2 and Savings B8".
  The on-screen cell carries the exact formula; the voice explains it.
- One idea per scene. 15–45 words is a comfortable beat (5–15 s).
- Match the week's slide deck numbers exactly so video and classroom agree.
- Every formula scene says three things: *what* the parameter is, *why* this
  formula, and *what the student should see* after pressing Enter.

## Actions

Actions are objects with a `do` key. Cell references accept `B6` or `Sheet!B6`;
an unqualified reference means the active sheet. All actions are performed
by the driver; durations are in seconds.

| `do` | fields | meaning |
|---|---|---|
| `sheet` | `name` | activate (creating if needed) the worksheet |
| `rename_sheet` | `from`, `to` | rename a worksheet |
| `select` | `cell` or `range` | select; the driver scrolls it into view |
| `type` | `cell`, `text`, `pace` (s/char, default 0.045), `commit` (`"enter"` default) | select the cell, show the text appearing character by character, then commit it. Text starting with `=` is committed as a formula. Values like `4.5%`, `$500` are committed as entered (the app parses them). |
| `set` | `cell` or `range`, `value` or `formula` | instant write, no typing animation (for prep work the narration does not cover) |
| `fill_down` | `range` (e.g. `A13:F71`), `from` (e.g. `A12:F12`) | copy formulas from `from` down through `range`, the way Ctrl-D does |
| `format` | `range`, `number` (format code), `bold`, `width` (column chars), `align` | formatting |
| `header_row` | `row`, `values` (array), `bold` (default true) | write a row of headers starting at column A |
| `chart` | `type` (`line`\|`column`), `x` (range), `series` (array of `{range, name}`), `title`, `x_title`, `y_title`, `at` (anchor cell, e.g. `H2`), `size` ([w,h] px), `y_min` | insert a chart |
| `scroll` | `cell` | scroll so `cell` is top-left |
| `zoom` | `percent` | app zoom level |
| `wait` | `seconds` | hold |
| `at` | `fraction` | wait until this fraction of the scene's narration has played before continuing (pacing, like `b.until()` in the manim engine) |
| `highlight` | `range`, `seconds` (default 1.2) | temporarily select/outline a range for emphasis, then restore the previous selection |

Drivers may support extra `do` values; unknown actions are a validation error.

## Check semantics

`equals` + `tol` compares the numeric value. `text` compares the displayed
string (what the student sees). Checks run after the scene's actions and are
written to `<out>/<code>.checks.json`; the build log prints PASS/FAIL per check.
This is how the video proves its own numbers match the handout.

## Timing model (what the pipeline guarantees)

1. Narration for every scene is synthesized first (cached by content hash), so
   each duration is known before recording starts.
2. Recording starts; `t0` is the wall-clock moment the recorder reports
   "Recording started". For each scene the pipeline logs `start`/`end`
   relative to `t0`, plays the clip (optional, for a human watching), runs the
   actions, then waits out the remainder of the clip plus `breath` (0.6 s).
3. After the take, the narration track is assembled as one WAV: silence up to
   each scene's `start`, then that scene's clip. The MP4 is exported with
   `--audio track.wav --audio-mode replace`, so sync is exact regardless of
   what played during the take.
4. The SRT is generated from the same scene timings (caption text split into
   ≤ 2-line cues of ≤ 7 words/line, proportionally by word count).
5. Scene timings also drive optional OpenScreen `zoomRegions` /
   `annotationRegions` (callouts and step captions) written into the
   project before export.

## Example (three scenes)

```json
{
  "code": "DEMO-excel-smoke",
  "title": "Smoke test",
  "app": "excel",
  "window": { "width": 1600, "height": 1000 },
  "stage": { "zoom": 160, "sheets": ["Savings"] },
  "scenes": [
    { "id": "inputs",
      "say": "Start with the inputs. Column A holds the label, column B holds the number.",
      "actions": [
        { "do": "type", "cell": "A3", "text": "APY" },
        { "do": "type", "cell": "B3", "text": "4.5%" }
      ] },
    { "id": "rate",
      "say": "A P Y already includes compounding, so the monthly rate is the twelfth root of one plus A P Y, minus one.",
      "actions": [
        { "do": "type", "cell": "A6", "text": "Monthly equivalent rate" },
        { "do": "at", "fraction": 0.5 },
        { "do": "type", "cell": "B6", "text": "=(1+B3)^(1/12)-1" },
        { "do": "format", "range": "B6", "number": "0.00000%" }
      ],
      "checks": [ { "cell": "B6", "equals": 0.0036748, "tol": 1e-6 } ] },
    { "id": "recap",
      "say": "That is the one conversion students get wrong most. Twelfth root, not divided by twelve.",
      "actions": [ { "do": "highlight", "range": "B6", "seconds": 1.5 } ] }
  ]
}
```
