# Recording Kit

Two video formats, one workflow. This doc is the whole workflow: setup, pacing, naming,
audio, upload, embed. Follow it top to bottom the first few times; after that it's muscle memory.

- **A. Problem walkthroughs** — tablet screencast, keyed to the Protocol, 5-8 min.
- **B. Maker-space demos** — phone video of a lab rig or build, 60-120s.

**Equipment (all of it):** iPad + pencil + USB-C cable, MacBook with OBS, phone,
cheap tripod with phone mount, lav mic (optional until the audio threshold below says otherwise).

## Naming convention

`PHY|CSM-U<unit>-<slug>` — course prefix, unit number, lowercase hyphenated slug. No dates,
no version suffixes; the slug should read as a title on its own.

- `PHY-U1-cart-lab-setup`
- `PHY-U2-friction-problem-1`
- `CSM-U0-vlookup-basics`

Use this exact string as the export filename, the YouTube title's slug, and the embed's
`title` attribute. Deciding it before you record means zero renaming afterward.

## A. Problem walkthroughs (tablet screencast)

**Stack: OBS, one scene, iPad as a capture source.** QuickTime's "New Movie Recording" with
the iPad selected as camera works for a fast one-off, but it only gives you the raw iPad
feed edge-to-edge — no margin, no control over canvas size. OBS gets you the framed,
consistent look every walkthrough should have, for the same zero cost.

**Scene setup ("Walkthrough"):**
- Canvas (Base + Output resolution): **1920×1080**.
- FPS: **30**. Handwriting on a static surface has no fast motion — 30fps keeps files small
  with no visible quality loss.
- Source: `Video Capture Device` → select the iPad (connect via USB cable; macOS exposes it
  as a camera device the same way QuickTime does).
- Scale the iPad source to **full canvas height**, centered. An iPad is ~4:3 in landscape,
  so on a 16:9 canvas you'll get pillar bars of roughly 12% on each side — that's expected.
  Add a **Color Source** at the bottom of the scene's source stack, set to `#F7F7F4` and
  stretched to the canvas, so the pillars read as
  intentional margins. Nothing the pencil touches should ever hit the edge of the frame.
- Audio input: built-in mic by default; switch to a lav mic per the threshold below.
- No facecam, no overlays. One clean writing surface, framed with breathing room.

**Pacing (tied to the Protocol):**
1. **State the problem out loud first** — read it before you touch the pencil.
2. Keep each Protocol step visible on the surface as you go; don't erase step 1 before
   you've referenced it later.
3. **Narrate decisions, not arithmetic.** Say why you picked an equation or substitution.
   Don't narrate "3 times 4 is 12" — let the pencil do that silently.
4. Target length: **5-8 minutes** per problem. If you're past 8, the problem is two problems.

**One-take philosophy + restart rule:** record the whole walkthrough in one take, minor
slips and all — a crossed-out line or a re-checked calculation is fine and looks like real
problem-solving. **Restart the whole take if:** you state a wrong equation or wrong
reasoning step (a conceptual error, not an arithmetic slip), or you lose your place for
more than ~10 seconds. Don't try to patch a conceptual error with an edit — redo the take.

## B. Maker-space demos (phone)

- **Landscape only.** Portrait clips don't fit the 16:9 embed and won't get reframed later.
- **Tripod at demo-table height** (~30-36in), lens level with the apparatus — not shooting
  down at it. Frame the whole rig plus a little headroom; don't crop off the part that moves.
- **Lighting:** put the room's light (windows or overhead) in front of the subject, not
  behind it. Maker-space fluorescents are fine; a backlit window turns the demo into a
  silhouette. If the shot looks dim or yellow on playback, move the rig, not the tripod.
- Target length: **60-120 seconds**. If the demo runs long, cut it into two clips rather
  than narrating faster.
- **Trim-only editing:** cut dead air at the start/end and, if needed, one obvious flub in
  the middle. No transitions, no music, no on-clip text.
- **Title card — only when the clip will be shared outside a labeled course page** (e.g.
  posted to socials or sent to parents directly). Add 3-4 seconds at the start: solid
  course-blue background, white text, unit + demo name. Skip it when the clip is embedded
  under a Materials heading — the page text already labels it.

## Pre-record checklist

1. Slug/filename decided (naming convention above) before you hit record.
2. Both devices charged, notifications off (Do Not Disturb).
3. Correct mic input selected and verified in OBS/QuickTime settings.
4. 10-second test clip recorded — check framing and audio level before the real take.
5. Writing surface / demo table cleared of anything outside the frame.
6. Room quiet check — door closed, obvious noise sources off.
7. Problem stated / demo materials staged and ready — no fumbling once recording starts.
8. For demos: tripod stability checked with a bump-test.
9. Restart rule decided in advance (see one-take philosophy above) — know what triggers a redo.
10. Know your target length before you start (5-8 min walkthrough / 60-120s demo).

## Audio guidance

- **Built-in mic is fine** when the room is quiet, you're within ~3ft of the device
  (tablet mic for walkthroughs), and there's no HVAC/hallway noise bleeding in.
- **Switch to a lav/external mic** when: a phone demo has you standing more than ~3-4ft
  from the device, the maker space has fans or tools running, or your test clip has an
  audible echo or hiss.
- Rule of thumb: if you have to ask "can they hear me," add the mic before you ask again.

## Thumbnails

One template, reused forever: paper background (`#F7F7F4`), the concept title in Familjen
Grotesk bold, a Cushman-blue band along the bottom with the video code (`PHY-U1-…`) in
Fragment Mono. Export 1280×720 PNG. Make the template once (Canva or a Figma frame), then
change two text fields per video — a consistent thumbnail wall is what makes the channel
look like a course library instead of a camera roll.

## Upload workflow (YouTube)

- **Title:** `[Course] Unit N — <Human title>` — e.g. `Physics Unit 1 — Cart Lab Setup Walkthrough`.
- **Description template:**
  ```
  <one-sentence description of what's covered>

  Course page: https://willieavendano.github.io/<course>/
  Part of: Cushman Physics|CS Math — Unit N
  ```
- **Visibility: Unlisted by default**, every upload, no exceptions. Unlisted videos still
  play through an embedded iframe for anyone with the course page — visibility is a separate
  decision from "is it embedded." Only flip to Public once Willie decides a video is ready
  for wider circulation; don't hold up the embed waiting on that call.
- After upload, copy the video ID from the share URL and drop it into the embed snippet below.

## Embed snippet (course READMEs)

```html
<iframe width="560" height="315" src="https://www.youtube.com/embed/VIDEO_ID"
  title="PHY-U1-cart-lab-setup" style="aspect-ratio:16/9;width:100%;height:auto;max-width:800px;"
  frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;
  picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin"
  allowfullscreen></iframe>
```

Plain iframe, 16:9 via `aspect-ratio` + `max-width`. marked.js passes raw HTML straight
through, so this drops directly into a course README's Materials section with no extra
markup. Replace `VIDEO_ID` and `title` (use the naming-convention slug as the title).
