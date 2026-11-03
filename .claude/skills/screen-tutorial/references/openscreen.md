# OpenScreen reference
OpenScreen is the recorder/editor behind the `screen-tutorial` skill. Drive it
from the CLI (`record` → edit the `.openscreen` project JSON → `export`); the
MCP server is for interactive polish, not the automated pipeline. Facts below
come from OpenScreen 2.2.1 on macOS, the official docs, and the OpenScreen demo
skill (cited at the bottom).
## 1. Binary paths and the ELECTRON_RUN_AS_NODE gotcha
| OS | Executable |
|---|---|
| macOS | `/Applications/Openscreen.app/Contents/MacOS/Openscreen` |
| Windows installer | `Openscreen.exe` in `%LOCALAPPDATA%\Programs\Openscreen\` (per-user) or `C:\Program Files\Openscreen\` (all users) |
| Microsoft Store | No fixed path; its folder changes with each Store update. Use the installer when a script must point at the CLI |
| Linux `.deb`/`.rpm`/`.pacman` | `openscreen` |
| Linux AppImage | `./Openscreen-Linux-<version>.AppImage` |
| Nix | `openscreen` |

**The gotcha.** Inside Claude Code / T3 Code sessions `ELECTRON_RUN_AS_NODE=1`
is set, and the OpenScreen binary then behaves like plain Node. Always clear it:

```bash
env -u ELECTRON_RUN_AS_NODE /Applications/Openscreen.app/Contents/MacOS/Openscreen sources --json
```

The repo's `.mcp.json` does the same for MCP (`"ELECTRON_RUN_AS_NODE": ""`).
`tutorial.py` and `scripts/setup.sh` use `env -u …` for you. CLI runs do not
take the app's single-instance lock, so they work while the desktop app is open.
Every command starts Electron, so a display server is required even though no
window appears; recording also needs a real desktop session.
## 2. CLI commands
`openscreen help`, `--help` or `-h` prints usage. With `--json`, stdout is
NDJSON and stderr carries diagnostics only. Rely on the exit code.

```text
openscreen export <project.openscreen> [options]   # render MP4/GIF, or WAV/M4A
openscreen record [options]                        # record headlessly
openscreen sources [--json] [-o <file>]            # displays/windows/mics/cameras
openscreen pack <project.openscreen> --out <dir>   # project + media, one folder
openscreen captions <project.openscreen> [--min-words <1-12>] [--max-words <1-12>]
openscreen info <project.openscreen> [--json]      # inspect a project
openscreen mcp                                     # MCP tools on stdio
openscreen help
```
### `sources`
Lists the displays, windows, microphones and cameras the app can see, so a
script can choose `--display`, `--window`, `--mic-device`, `--camera-device`.
`sources` is human-readable; `sources --json` is NDJSON; `sources -o s.json`
writes the payload alone (no `done` envelope). The `--json` payload arrives
inside the final `done` event:

```json
{"event":"done","success":true,"sources":{
 "displays":[{"index":0,"id":"screen:1:0","name":"Entire screen"}],
 "windows":[{"id":"window:210:0","name":"My App"}],
 "microphones":[…], "cameras":[…]}}
```

`microphoneLabelsUnavailable` / `cameraLabelsUnavailable` are `true` when the
labels need a permission that has not been granted.
### `record`
```bash
openscreen record --window "My App" --mic --duration 30 --project demo.openscreen --json
openscreen record --display 0 --mic --system-audio
```

| Option | Meaning |
|---|---|
| `--display <n>` | Screen index from `sources` (default 0) |
| `--window <title>` | Record the first window whose title contains `<title>` (case-insensitive); takes precedence over `--display` |
| `--mic` | Capture the default microphone |
| `--mic-device <name>` | Microphone label contains `<name>` (implies `--mic`) |
| `--system-audio` | Capture system audio |
| `--camera` / `--camera-device <name>` | Default webcam beside the screen (`--camera-device` implies `--camera`) |
| `--cursor <editable-overlay\|system>` | `editable-overlay` (default) records the pointer as data; `system` burns it in |
| `--duration <seconds>` | Stop automatically after this long |
| `--project <out.openscreen>` | Write a ready-to-export project when done (must end in `.openscreen`) |
| `--json` | NDJSON events on stdout |

**Stopping.** Without `--duration`, stop with Ctrl+C (SIGINT), SIGTERM, or by
typing `stop`, `q` or `quit` and Enter on stdin. Closing stdin does **not** stop
it. A forced kill skips the normal finish, so no `done` event and no project
file. On macOS, takes land in the app's recordings directory,
`~/Library/Application Support/openscreen/recordings/`, as the screen video plus
a `<video>.cursor.json` when pointer data was captured.

**NDJSON (record):**

```json
{"event":"started","command":"record"}
{"event":"log","message":"Recording started"}
{"event":"done","success":true,"screenVideoPath":"/…/recording.mp4","cursorDataPath":"/…/recording.cursor.json","durationMs":12345,"projectData":{…},"projectPath":"/…/demo.openscreen"}
```
### `export`
```bash
openscreen export demo.openscreen                                  # project settings
openscreen export demo.openscreen -o out.mp4 --quality source
openscreen export demo.openscreen -o out.gif --gif-fps 20 --gif-size large
openscreen export demo.openscreen -o out.mp4 --auto-zoom --json
openscreen export demo.openscreen -o mix.m4a                       # audio only
openscreen export demo.openscreen -o voice.wav --track audio_1234   # one track
```

| Option | Meaning |
|---|---|
| `-o, --out <path>` | Output file; extension (`.mp4`, `.gif`, `.wav`, `.m4a`) sets the format. Default: project path with the format's extension |
| `--format <mp4\|gif\|wav\|m4a>` | Override the project's format; must agree with `--out`. `wav`/`m4a` write the project's audio only |
| `--track <audioId>` | WAV/M4A only: one imported track alone, where it plays, with its offset/trims/gain/fades |
| `--quality <medium\|good\|source>` | `medium` = 720p, `good` = 1080p, `source` = smallest clip after cropping (never upscales). MP4 only |
| `--fps <24\|30\|60>` | MP4 frame rate (default 60) |
| `--gif-fps <15\|20\|25\|30>` | GIF frame rate |
| `--gif-size <small\|medium\|large\|original>` | GIF height cap: 480, 720, 1080, or none |
| `--gif-loop` / `--no-gif-loop` | GIF loops forever or plays once (default: from project) |
| `--auto-zoom` | Add zooms on the recorded clicks before rendering, clear of existing zooms |
| `--audio <file>` | Mix a voiceover (mp3/wav/m4a) into the MP4 |
| `--audio-mode <mix\|replace>` | `mix` (default) keeps the recording under the voiceover at 40% gain; `replace` drops it |
| `--audio-offset <seconds>` | Delay before the voiceover starts (default 0) |
| `--json` | NDJSON progress and result on stdout |

MP4 exports are always H.264; there is no codec option. `--audio` works after
the render—the video is copied and a new AAC track is mixed over the same file.
A `.wav`/`.m4a` export renders as the MP4 would at 720p and keeps only its
audio.

**NDJSON (export):**

```json
{"event":"started","command":"export"}
{"event":"progress","percentage":50,"currentFrame":60,"totalFrames":120,"estimatedTimeRemaining":3}
{"event":"done","success":true,"outputPath":"/…/out.mp4","format":"mp4","width":1920,"height":1080}
```
### `captions`, `pack`, `info`, `mcp`
- `captions <project> [--min-words <1-12>] [--max-words <1-12>]` transcribes on
  the machine with Whisper (nothing uploaded, language auto-detected). The
  **first run downloads the model once, about 264 MB**. The screen video must
  have an audio track (e.g. `record --mic`). Captions are **burned into the
  export; there is no subtitle file**. Running it again keeps the transcript and
  changes only the words per caption. `done` carries `projectPath`,
  `captionCount`.
- `pack <project> --out <dir>` (`-o` accepted) copies the project and everything
  it references into one folder, rewriting media paths. No `started` event;
  `done` carries `projectPath`, `files`, `cursorData`.
- `info <project> [--json]` prints references, export settings and effect counts.
  It exits **1** when the screen video is missing. `--json` is one summary
  object with no `event` field.
- `mcp` serves OpenScreen's MCP tools on stdio; the agent starts it.
### NDJSON events and exit codes
| Event | Sent when | Fields |
|---|---|---|
| `started` | `record`, `sources`, `export`, `captions` begins | `command` |
| `log` | Status line, e.g. `Recording started` | `message` |
| `progress` | Export frames encode; `--audio` mixing / audio extraction | `percentage`, `currentFrame`, `totalFrames`, `estimatedTimeRemaining`; `phase` |
| `stopping` | `record` got a stop request | `reason`: `SIGINT`, `SIGTERM` or `stdin` |
| `warning` / `error` | Succeeded with a caveat / failed | `message` |
| `done` | Finished | `success`, then the result or `error` |

Exit codes: `0` success; `1` failure (including `info` with a missing screen
video); `2` bad arguments (plain-text usage on stderr, even with `--json`).
## 3. The project file (`*.openscreen`)
A project is JSON with `"version": 2`, a `media` block, and an `editor` block:

```json
{"version": 2,
 "media": {"screenVideoPath": "/Users/me/Library/Application Support/openscreen/recordings/recording.mp4"},
 "editor": {"padding": 50, "borderRadius": 40, "aspectRatio": "auto",
   "cursorTheme": "default", "wallpaper": "…", "cropRegion": null,
   "zoomRegions": [], "trimRegions": [], "speedRegions": [], "annotationRegions": [],
   "exportQuality": "medium", "exportFormat": "mp4"}}
```

Defaults that matter for tutorials:

- `padding` defaults to **50**, `borderRadius` to **40**.
- `aspectRatio` defaults to **`"auto"`**; set it to **`"16:9"`** for tutorials so
  the frame is stable.
- `zoomRegions[]`, `trimRegions[]`, `speedRegions[]` and `annotationRegions[]`
  hold timed effects; each region has `startMs`, `endMs` plus type-specific
  fields.
- `cursorTheme`, `wallpaper`, `cropRegion`, `exportQuality` and `exportFormat`
  control the look and render.
- With the defaults a **1600×1000** window exports to **1142×720** at
  `--quality medium` (720p). With `aspectRatio "16:9"` and `padding 24` the
  export is **1920×1080** at `good` and **1280×720** at `medium`; the window
  fills about 90% of the frame's height.

### Region schemas (read from the app's own code in `app.asar`, verified by exporting)

The project loader **drops any key it does not know**, so stick to these.

Zoom region (`editor.zoomRegions[]`):

```json
{"id": "z1", "startMs": 1000, "endMs": 9000, "depth": 3,
 "focus": {"cx": 0.32, "cy": 0.41}, "focusMode": "manual", "source": "manual"}
```

- `depth` sets magnification: 1 = 1.25×, 2 = 1.5×, 3 = 1.8×, 4 = 2.2×,
  5 = 3.5×, 6 = 5×. A `customScale` key is silently discarded.
- `focus` is a fraction of the **output frame** (not of the recorded window);
  at full zoom that point moves to the frame's centre.

Text callout (`editor.annotationRegions[]`):

```json
{"id": "a1", "startMs": 4000, "endMs": 8000, "type": "text",
 "content": "12th root, not ÷ 12", "textContent": "12th root, not ÷ 12",
 "position": {"x": 55, "y": 80}, "size": {"width": 30, "height": 8},
 "style": {"color": "#ffffff", "backgroundColor": "#141412", "fontSize": 28,
           "fontFamily": "Inter", "fontWeight": 700, "textAlign": "center",
           "textAnimation": "pop"},
 "zIndex": 1}
```

- `position` is the box's top-left corner in **percent of the frame (0–100)**;
  `size` is also in percent (1–200).
- `style.fontFamily` ∈ Inter, Lora, Oswald, Caveat, IBM Plex Mono;
  `textAnimation` ∈ none, fade, rise, pop, slide-left, typewriter, pulse.

Hiding the drawn cursor: no project key does it (`cursorShow` is not kept and
`cursorCaptureMode` makes no difference). Mark every sample `"visible": false`
in the take's `<video>.cursor.json` — `openscreen.py adopt_take()` does this
for scripted takes, where the pointer never moves.

Timing: the recorder's `"Recording started"` log line matches frame zero within
0.02 s, so wall-clock offsets from that line are safe scene timestamps.
`info --json` prints one plain JSON object, not NDJSON events.
## 4. MCP
The repo's `.mcp.json` registers the CLI's own stdio MCP server:

```json
{"mcpServers": {"openscreen": {
  "command": "/Applications/Openscreen.app/Contents/MacOS/Openscreen",
  "args": ["mcp"], "env": {"ELECTRON_RUN_AS_NODE": ""}}}}
```

Verify in an interactive Claude session with `claude mcp list` (or add it with
`claude mcp add openscreen -- "<executable>" mcp`). Tools exposed by the docs
and the demo skill: `listSources`, `startRecording`, `stopRecording`,
`setPointerTrack`, `getCurrentDocument`, `setAspectRatio`, `addTrims`,
`addSpeed`, `addZooms`, `setZoom`, `addAutoZooms`, `setClipRange`,
`addAnnotation`, `setAnnotation`, `addEffect`, `importMedia`, `addAudio`,
`removeMedia`, `setProjectInfo`, `transcribe`, `setCaptionSettings`,
`getCaptionTranslationUnits`, `putCaptionTranslation`, `getCaptions`,
`setWordText`, `setVocabulary`, `getTranscriptWords`, `removeWords`,
`restoreCheckpoint`, `setEditorSettings`, `exportVideo`, `exportAudio`,
`getFrames`, `createProject`.

**Which to use.** Use the **CLI** for the pipeline: record, edit the JSON, export
—scriptable, testable, no app setting. Use **MCP** for interactive polish with a
human watching (move a zoom, restyle a callout, check `getFrames`). Two MCP
flavors: the server the desktop app serves (needs **MCP edits** under *AI
settings → MCP server*; recordings go through the recording bar) and the CLI's
own `openscreen mcp`, which needs no setting and records with the agent's rights.
The committed `.mcp.json` uses the latter.
## 5. macOS permissions
- **Screen Recording** belongs to the **host process** that runs Claude
  (Terminal, Ghostty, T3 Code, VS Code…), not to OpenScreen, when the CLI is
  used. Without it, capture fails and `sources --json` lists no windows. Grant
  it, then quit and reopen the host app.
- **Accessibility** is needed only for the **`sheets` driver** (System Events
  keystrokes) and for recording pointer clicks/shapes as zoom telemetry. The
  **`excel` driver does not need it**—it drives Excel through AppleScript.
  Without Accessibility a real-mouse take gets no click zoom; grant it, or hand
  clicks over with `setPointerTrack` as for a scripted take.
- **Microphone** access is requested by `record --mic` the first time.
- OpenScreen targets **macOS 13+**. On **macOS 15**, macOS re-prompts for the
  privacy permissions after updates; expect to re-grant once after an upgrade.
## 6. Troubleshooting
- **Binary prints Node errors or nothing:** `ELECTRON_RUN_AS_NODE=1` is set.
  Prefix with `env -u ELECTRON_RUN_AS_NODE`.
- **`sources` lists no windows:** Screen Recording is missing for the **host
  app**. Grant it, reopen the host, re-run `sources --json`.
- **No cursor / no click-zooms:** Accessibility is not granted, or a script
  drove the app so the real pointer never moved. Grant Accessibility or add a
  `setPointerTrack` log after `stopRecording`.
- **`record --window` never starts:** the title did not match. Titles match a
  case-insensitive substring; list exact titles with `sources` first.
- **`transcribe` / `captions` fails with `no-audio`:** the take has no audio
  track. Record again with `--mic` or `--system-audio`; `--audio` mixed in at
  export is too late for captions, and the first run downloads a ~264 MB
  Whisper model once.
- **`export` fails or `info` exits 1:** `media.screenVideoPath` no longer
  exists. Use `pack` to bundle project + media, or fix the path.
- **Export is 720p but you wanted 1080p:** `--quality medium` is 720p; use
  `--quality good` (1080p) or `source`.
- **`--audio` did not replace the recording audio:** the default `--audio-mode`
  is `mix` (recording at 40%). Use `--audio-mode replace`.
- **MCP edit refused, mentioning *MCP edits*:** you are on the app-served MCP
  server. Turn on *MCP edits* under *AI settings → MCP server*, or use the CLI
  `openscreen mcp` stdio server instead.
- **Excel check hangs on first run:** first launch can take 60 s+; the setup
  check allows 90 s. If it still fails, open Excel once and allow Automation in
  System Settings → Privacy & Security → Automation.
- **No ffmpeg on the school Mac:** audio is converted with `afconvert`,
  measured with `afinfo`, played with `afplay`; stills use `sips`.
## Sources
- OpenScreen CLI docs: https://getopenscreen.com/docs/cli/
- OpenScreen AI-editing / MCP docs: https://getopenscreen.com/docs/ai-editing/
- OpenScreen demo skill (MCP tool list and workflow):
  https://raw.githubusercontent.com/getopenscreen/openscreen/main/plugin/skills/openscreen-demo/SKILL.md
- Local CLI help and `sources --json` output on OpenScreen 2.2.1 (macOS).
