"""Unit tests for parts, step captions and voice direction/settings.

    python3 -m unittest discover -s .claude/skills/screen-tutorial/tests

No app, recorder or network: the driver is a fake, ElevenLabs is stubbed.
"""

import argparse
import json
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import narration  # noqa: E402
import openscreen  # noqa: E402
import tutorial  # noqa: E402

EXAMPLE = SKILL / "templates" / "tutorial-script.example.json"


def example():
    return json.loads(EXAMPLE.read_text())


def scene(sid, actions=(), say="Some words here."):
    return {"id": sid, "say": say, "actions": list(actions)}


def parts_script():
    """Five scenes in three chapters; p1 = intro chapter, p2 = the rest."""
    return {
        "code": "DEMO-parts", "title": "Parts", "app": "excel",
        "stage": {"sheets": ["Savings", "Loan"]},
        "chapters": [
            {"id": "a", "scenes": ["s1", "s2"]},
            {"id": "b", "scenes": ["s3"]},
            {"id": "c", "scenes": ["s4", "s5"]},
        ],
        "parts": [
            {"id": "p1", "title": "Part 1", "chapters": ["a"],
             "intro": {"id": "p1-intro", "say": "Welcome to part one."},
             "outro": {"id": "p1-outro", "say": "That is part one."}},
            {"id": "p2", "title": "Part 2", "chapters": ["c", "b"],
             "intro": {"id": "p2-intro", "say": "Part two.",
                       "actions": [{"do": "sheet", "name": "Loan"}]}},
        ],
        "scenes": [scene("s%d" % i, [{"do": "type", "cell": "A%d" % i, "text": "x"}])
                   for i in range(1, 6)],
    }


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
class PartValidationTests(unittest.TestCase):
    def errors(self, script):
        return tutorial.validate_script(script)[0]

    def test_valid(self):
        self.assertEqual(self.errors(parts_script()), [])

    def test_example_template_has_two_parts(self):
        script = example()
        self.assertEqual(len(script.get("parts", [])), 2)
        self.assertEqual(self.errors(script), [])

    def test_bad_and_duplicate_ids(self):
        s = parts_script()
        s["parts"][1]["id"] = "p1"
        self.assertTrue(any("duplicate id" in e for e in self.errors(s)))
        s["parts"][1]["id"] = "Part_2"
        self.assertTrue(any("kebab-case" in e for e in self.errors(s)))

    def test_unknown_chapter(self):
        s = parts_script()
        s["parts"][0]["chapters"].append("ghost")
        self.assertTrue(any("unknown chapter 'ghost'" in e for e in self.errors(s)))

    def test_chapter_in_two_parts(self):
        s = parts_script()
        s["parts"][1]["chapters"].append("a")
        self.assertTrue(any("already in part 'p1'" in e for e in self.errors(s)))

    def test_empty_chapters(self):
        s = parts_script()
        s["parts"][0]["chapters"] = []
        self.assertTrue(any("non-empty list" in e for e in self.errors(s)))

    def test_intro_validated_as_scene(self):
        s = parts_script()
        s["parts"][0]["intro"]["actions"] = [{"do": "dance"}]
        self.assertTrue(any("p1" in e and "unknown action" in e for e in self.errors(s)))
        s = parts_script()
        del s["parts"][0]["outro"]["say"]
        self.assertTrue(any("`say` is required" in e for e in self.errors(s)))

    def test_intro_id_collisions(self):
        s = parts_script()
        s["parts"][0]["intro"]["id"] = "s3"
        self.assertTrue(any("collides" in e for e in self.errors(s)))
        s = parts_script()
        s["parts"][1]["intro"]["id"] = "p1-outro"
        self.assertTrue(any("collides" in e for e in self.errors(s)))

    def test_unknown_part_field(self):
        s = parts_script()
        s["parts"][0]["colour"] = "red"
        self.assertTrue(any("unknown field" in e for e in self.errors(s)))

    def test_gap_warning(self):
        s = parts_script()
        s["chapters"][2]["scenes"] = ["s4"]
        s["chapters"].append({"id": "d", "scenes": ["s5"]})
        s["parts"][1]["chapters"] = ["b", "d"]     # s4 sits between s3 and s5
        errors, warnings = tutorial.validate_script(s)
        self.assertEqual(errors, [])
        self.assertTrue(any("'p2'" in w and "s4" in w for w in warnings))


class PartSelectionTests(unittest.TestCase):
    def ids(self, scenes):
        return [s["id"] for s in scenes]

    def test_first_part(self):
        before, recorded, name = tutorial.select_scenes(parts_script(), part="p1")
        self.assertEqual(before, [])
        self.assertEqual(self.ids(recorded), ["p1-intro", "s1", "s2", "p1-outro"])
        self.assertEqual(name, "DEMO-parts-p1")

    def test_later_part_fast_forwards_and_keeps_script_order(self):
        before, recorded, name = tutorial.select_scenes(parts_script(), part="p2")
        self.assertEqual(self.ids(before), ["s1", "s2"])
        # chapters listed c, b — scenes still play in script order; no outro.
        self.assertEqual(self.ids(recorded), ["p2-intro", "s3", "s4", "s5"])
        self.assertEqual(name, "DEMO-parts-p2")

    def test_plain_build_has_no_intros(self):
        before, recorded, name = tutorial.select_scenes(parts_script())
        self.assertEqual(before, [])
        self.assertEqual(self.ids(recorded), ["s1", "s2", "s3", "s4", "s5"])
        self.assertEqual(name, "DEMO-parts")

    def test_chapter_still_works(self):
        before, recorded, name = tutorial.select_scenes(parts_script(), chapter="b")
        self.assertEqual(self.ids(before), ["s1", "s2"])
        self.assertEqual(self.ids(recorded), ["s3"])
        self.assertEqual(name, "DEMO-parts-b")

    def test_errors(self):
        with self.assertRaises(SystemExit):
            tutorial.select_scenes(parts_script(), part="p9")
        with self.assertRaises(SystemExit):
            tutorial.select_scenes(parts_script(), chapter="a", part="p1")

    def test_runs_for_all_parts(self):
        args = argparse.Namespace(all_parts=True, chapter=None, part=None)
        runs = tutorial._runs(parts_script(), args)
        self.assertEqual([r[0] for r in runs], ["p1", "p2"])
        self.assertEqual([r[3] for r in runs], ["DEMO-parts-p1", "DEMO-parts-p2"])
        args = argparse.Namespace(all_parts=True, chapter=None, part="p1")
        with self.assertRaises(SystemExit):
            tutorial._runs(parts_script(), args)
        s = parts_script()
        del s["parts"]
        with self.assertRaises(SystemExit):
            tutorial._runs(s, argparse.Namespace(all_parts=True, chapter=None, part=None))

    def test_run_each_continues_past_failure(self):
        runs = tutorial._runs(parts_script(),
                              argparse.Namespace(all_parts=True, chapter=None, part=None))
        seen, printed = [], []

        def one(run):
            seen.append(run[0])
            if run[0] == "p1":
                raise SystemExit("check failed in scene 's2'")
            return {"rc": 0, "seconds": 301.0, "checks": "PASS 3", "file": "/x/DEMO-parts-p2.mp4"}

        rc = tutorial._run_each(runs, one, log_line=printed.append)
        self.assertEqual(rc, 1)
        self.assertEqual(seen, ["p1", "p2"])
        table = "\n".join(printed)
        self.assertIn("ERROR", table)
        self.assertIn("5:01", table)
        self.assertIn("DEMO-parts-p2.mp4", table)

    def test_single_run_returns_its_code(self):
        runs = [(None, [], [], "X")]
        self.assertEqual(tutorial._run_each(runs, lambda r: {"rc": 0}), 0)
        self.assertEqual(tutorial._run_each(runs, lambda r: {"rc": 1}), 1)

    def test_validate_prints_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.tutorial.json"
            path.write_text(json.dumps(parts_script()))
            with mock.patch("builtins.print") as out:
                rc = tutorial.cmd_validate(argparse.Namespace(script=str(path)))
        text = "\n".join(" ".join(str(a) for a in c.args) for c in out.call_args_list)
        self.assertEqual(rc, 0)
        self.assertIn("DEMO-parts-p2", text)
        self.assertIn("voice settings:", text)
        self.assertIn("voice direction:", text)


# ---------------------------------------------------------------------------
# Step captions
# ---------------------------------------------------------------------------
class StepTextTests(unittest.TestCase):
    def t(self, action, active="Savings"):
        return tutorial.step_text(action, active)

    def test_type_and_set(self):
        self.assertEqual(self.t({"do": "type", "cell": "A1", "text": "Save for the Car"}),
                         "A1 ← Save for the Car")
        self.assertEqual(self.t({"do": "type", "cell": "Savings!B6", "text": "=(1+B3)^(1/12)-1"}),
                         "B6 ← =(1+B3)^(1/12)-1")
        self.assertEqual(self.t({"do": "type", "cell": "Loan!B3", "text": "=MIN(B2,Savings!B8)"}),
                         "Loan!B3 ← =MIN(B2,Savings!B8)")
        self.assertEqual(self.t({"do": "set", "range": "A13:A20", "formula": "=A12+1"}),
                         "A13:A20 ← =A12+1")
        self.assertEqual(self.t({"do": "set", "cell": "B3", "value": 0.045}), "B3 ← 0.045")

    def test_fill_down(self):
        self.assertEqual(self.t({"do": "fill_down", "from": "Savings!A12:F12", "range": "A13:F71"}),
                         "Fill down A12:F12 → A13:F71  (⌘D)")

    def test_format(self):
        self.assertEqual(self.t({"do": "format", "range": "B6", "number": "0.00000%"}),
                         "Format B6 as 0.00000%")
        self.assertEqual(self.t({"do": "format", "range": "A10:F10", "bold": True}), "Bold A10:F10")
        self.assertEqual(self.t({"do": "format", "range": "E:E", "width": 14}), "Width E: 14")
        self.assertEqual(self.t({"do": "format", "range": "B:F", "width": 17}), "Width B:F: 17")
        self.assertEqual(self.t({"do": "format", "range": "B6", "number": "0.00000%", "bold": True}),
                         "Format B6: 0.00000%, bold")
        self.assertIsNone(self.t({"do": "format", "range": "B6"}))

    def test_header_row_truncates(self):
        text = self.t({"do": "header_row", "row": 10,
                       "values": ["Month", "Opening balance", "Interest", "Deposit",
                                  "Closing balance", "Check"]})
        self.assertTrue(text.startswith("Row 10 headers: Month · Opening balance · "))
        self.assertTrue(text.endswith("· …"))
        self.assertLessEqual(len(text), tutorial.STEP_MAX_CHARS)
        self.assertEqual(self.t({"do": "header_row", "row": 1, "values": ["A", "B"]}),
                         "Row 1 headers: A · B")

    def test_chart_sheet_zoom(self):
        self.assertEqual(self.t({"do": "chart", "type": "line", "series": [], "title": "Growth"}),
                         "Insert line chart: Growth")
        self.assertEqual(self.t({"do": "chart", "type": "column", "series": []}),
                         "Insert column chart")
        self.assertEqual(self.t({"do": "sheet", "name": "Savings"}), "Sheet: Savings")
        self.assertEqual(self.t({"do": "rename_sheet", "from": "Sheet1", "to": "Savings"}),
                         "Rename sheet Sheet1 → Savings")
        self.assertEqual(self.t({"do": "zoom", "percent": 160}), "Zoom 160%")

    def test_no_caption_for_other_actions(self):
        for action in ({"do": "select", "cell": "A1"}, {"do": "highlight", "range": "B6"},
                       {"do": "scroll", "cell": "A1"}, {"do": "wait", "seconds": 1}):
            self.assertIsNone(self.t(action))

    def test_no_trailing_period(self):
        self.assertFalse(self.t({"do": "zoom", "percent": 160}).endswith("."))


class SceneStepsTests(unittest.TestCase):
    def test_merge_short_types_across_at(self):
        sc = scene("x", [{"do": "type", "cell": "A3", "text": "APY"},
                         {"do": "at", "fraction": 0.5},
                         {"do": "type", "cell": "B3", "text": "4.5%"},
                         {"do": "format", "range": "B3", "number": "0.00%"}])
        steps, _ = tutorial.scene_steps(sc, "Savings")
        self.assertEqual(steps, [(0, "A3 ← APY   B3 ← 4.5%"), (3, "Format B3 as 0.00%")])

    def test_no_merge_past_60_chars_or_other_actions(self):
        long_ = "=IF(B5=0,B4/B6,-PMT(B5/12,B6,B4))"
        sc = scene("x", [{"do": "type", "cell": "A7", "text": "Monthly payment ($)"},
                         {"do": "type", "cell": "B7", "text": long_}])
        steps, _ = tutorial.scene_steps(sc, "Loan")
        self.assertEqual([i for i, _ in steps], [0, 1])
        sc = scene("x", [{"do": "type", "cell": "A3", "text": "APY"},
                         {"do": "select", "cell": "B3"},
                         {"do": "type", "cell": "B3", "text": "4.5%"}])
        self.assertEqual(len(tutorial.scene_steps(sc, "Savings")[0]), 2)

    def test_long_text_is_truncated(self):
        sc = scene("x", [{"do": "type", "cell": "A1", "text": "y" * 100}])
        (_, text), = tutorial.scene_steps(sc)[0]
        self.assertEqual(len(text), tutorial.STEP_MAX_CHARS)
        self.assertTrue(text.endswith("…"))

    def test_active_sheet_tracking(self):
        script = {"stage": {"sheets": ["Savings", "Loan"]}}
        before = [scene("a", [{"do": "sheet", "name": "Loan"}])]
        self.assertEqual(tutorial.initial_active(script), "Savings")
        self.assertEqual(tutorial.initial_active(script, before), "Loan")
        sc = scene("x", [{"do": "type", "cell": "Savings!B2", "text": "1"},
                         {"do": "type", "cell": "Savings!B3", "text": "2"},
                         {"do": "rename_sheet", "from": "Savings", "to": "Save"}])
        steps, active = tutorial.scene_steps(sc, "Loan")
        self.assertEqual(steps[0][1], "Savings!B2 ← 1   B3 ← 2")   # second is on the now-active sheet
        self.assertEqual(active, "Save")
        self.assertEqual(tutorial.display_ref("Loan!B2", "Loan"), "B2")
        self.assertEqual(tutorial.display_ref("'My Sheet'!B2", "Loan"), "'My Sheet'!B2")


class StepTimingTests(unittest.TestCase):
    ENTRY = {"id": "x", "start": 10.0, "end": 20.0, "actions": [
        {"do": "type", "start": 10.1}, {"do": "at", "start": 11.0},
        {"do": "type", "start": 14.0}, {"do": "format", "start": 16.0},
        {"do": "highlight", "start": 17.0}]}

    def test_each_step_runs_to_the_next_then_scene_end(self):
        steps = [(0, "A3 ← APY"), (3, "Format B3 as 0.00%")]
        out = tutorial.step_timings(self.ENTRY, steps)
        self.assertEqual(out, [{"start": 10.1, "end": 16.0, "text": "A3 ← APY"},
                               {"start": 16.0, "end": 20.0, "text": "Format B3 as 0.00%"}])

    def test_minimum_length(self):
        entry = {"start": 0, "end": 1.0, "actions": [{"start": 1.0}]}
        out = tutorial.step_timings(entry, [(0, "x")])
        self.assertAlmostEqual(out[0]["end"], 1.3)

    def test_add_steps_and_regions(self):
        timeline = [dict(self.ENTRY, actions=list(self.ENTRY["actions"]))]
        sc = scene("x", [{"do": "type", "cell": "A3", "text": "APY"}, {"do": "at", "fraction": .2},
                         {"do": "type", "cell": "B3", "text": "4.5%"},
                         {"do": "format", "range": "B3", "number": "0.00%"},
                         {"do": "highlight", "range": "B3"}])
        tutorial.add_steps(timeline, [sc], "Savings")
        self.assertEqual([s["text"] for s in timeline[0]["steps"]],
                         ["A3 ← APY   B3 ← 4.5%", "Format B3 as 0.00%"])
        notes = tutorial.step_regions(timeline, openscreen)
        self.assertEqual(len(notes), 2)
        a = notes[0]
        self.assertEqual(a["id"], "step-x-1")
        self.assertEqual((a["startMs"], a["endMs"]), (10100, 16000))
        self.assertEqual(a["position"], {"x": 12.0, "y": 89.5})     # centred on (50, 93)
        self.assertEqual(a["size"], {"width": 76, "height": 7})
        self.assertEqual(a["style"]["fontFamily"], "IBM Plex Mono")
        self.assertEqual(a["style"]["backgroundColor"], "#111111")
        self.assertEqual(a["type"], "text")

    def test_font_clamp(self):
        self.assertEqual(tutorial.step_font_size("x"), tutorial.STEP_FONT_MAX)
        sixty = tutorial.step_font_size("x" * 60)
        # A 60-char line fits inside the box at 1080p at the chosen size.
        usable = 1920 * tutorial.STEP_BOX["width"] / 100.0 - 48
        self.assertLessEqual(60 * tutorial.STEP_CHAR_EM * sixty, usable)
        self.assertGreaterEqual(sixty, 32)                     # and stays readable
        self.assertLess(tutorial.step_font_size("x" * 80), sixty)
        self.assertEqual(tutorial.step_font_size("x" * 500), tutorial.STEP_FONT_MIN)

    def test_callouts_move_up_with_steps(self):
        timeline = [{"start": 0.0, "end": 10.0}]
        scenes = [{"id": "r", "callout": {"text": "12th root", "at": 0.3}}]
        _, on = tutorial._regions(timeline, scenes, openscreen, lambda *_: None, steps_on=True)
        _, off = tutorial._regions(timeline, scenes, openscreen, lambda *_: None, steps_on=False)
        self.assertLessEqual(on[0]["position"]["y"], 80)
        self.assertEqual(off[0]["position"]["y"], 86)          # unchanged without steps
        self.assertLess(on[0]["position"]["y"] + on[0]["size"]["height"],
                        tutorial.STEP_BOX["cy"] - tutorial.STEP_BOX["height"] / 2.0)

    def test_srt_stays_narration_only(self):
        timeline = [{"start": 1.0, "narration": 3.0, "caption": "Spoken words.",
                     "steps": [{"start": 1.0, "end": 4.0, "text": "A1 ← x"}]}]
        self.assertEqual(tutorial.narration_cues(timeline), [(1.0, 4.0, "Spoken words.")])

    def test_no_steps_flag(self):
        ap_args = ["build", "x.json", "--no-steps", "--all-parts"]
        with mock.patch.object(tutorial, "cmd_build", lambda a: (a.no_steps, a.all_parts)):
            self.assertEqual(tutorial.main(ap_args), (True, True))
        with mock.patch.object(tutorial, "cmd_dryrun", lambda a: a.part):
            self.assertEqual(tutorial.main(["dryrun", "x.json", "--part", "p2"]), "p2")


# ---------------------------------------------------------------------------
# Voice direction + settings
# ---------------------------------------------------------------------------
def write_wav(path, seconds=0.2):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\0\0" * int(seconds * 44100))


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"mp3"


class DirectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.sent = []

    def tearDown(self):
        self._tmp.cleanup()

    def eleven(self, text, direction=None):
        def fake_urlopen(request, timeout=None):
            self.sent.append(json.loads(request.data.decode("utf-8")))
            return FakeResponse()

        with mock.patch.object(narration.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(narration, "_afconvert", lambda s, d: write_wav(d)), \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k"}):
            return narration.synthesize(text, "eleven", self.tmp, voice="v",
                                        direction=direction)[0]

    def test_spoken_text(self):
        self.assertEqual(narration.spoken_text("Hello.", "[dry]"), "[dry] Hello.")
        self.assertEqual(narration.spoken_text("Hello.", ""), "Hello.")
        self.assertEqual(narration.spoken_text(" Hello. ", None), "Hello.")

    def test_direction_is_sent_and_keys_the_cache(self):
        plain = self.eleven("Hello.")
        dry = self.eleven("Hello.", "[dry, wry]")
        again = self.eleven("Hello.", "[dry, wry]")
        other = self.eleven("Hello.", "[warm]")
        self.assertEqual([p["text"] for p in self.sent],
                         ["Hello.", "[dry, wry] Hello.", "[warm] Hello."])   # `again` was cached
        self.assertEqual(dry, again)
        self.assertEqual(len({plain, dry, other}), 3)

    def test_say_and_draft_ignore_direction(self):
        self.assertEqual(narration.synthesize("Two words", "draft", self.tmp, direction="[dry]"),
                         narration.synthesize("Two words", "draft", self.tmp))
        spoken = []
        with mock.patch.object(narration, "_say_synthesize",
                               lambda text, voice, aiff: spoken.append(text) or aiff.write_bytes(b"")), \
                mock.patch.object(narration, "_afconvert", lambda s, d: write_wav(d)):
            narration.synthesize("Hello.", "say", self.tmp, direction="[dry]")
        self.assertEqual(spoken, ["Hello."])

    def test_scene_override(self):
        script = {"voice": {"direction": "[dry]"}}
        self.assertEqual(tutorial.voice_direction(script, {"say": "x"}), "[dry]")
        self.assertEqual(tutorial.voice_direction(script, {"voice_direction": "[warm]"}), "[warm]")
        self.assertIsNone(tutorial.voice_direction(script, {"voice_direction": ""}))
        self.assertIsNone(tutorial.voice_direction({}, {"say": "x"}))

    def test_synthesize_all_passes_direction_not_caption(self):
        calls = []

        def fake(text, mode, cache, prev_text=None, next_text=None, voice=None, direction=None):
            calls.append((text, prev_text, direction))
            return None, 1.0

        script = {"voice": {"direction": "[dry]"}}
        scenes = [{"id": "a", "say": "One."}, {"id": "b", "say": "Two.", "voice_direction": ""}]
        with mock.patch.object(narration, "synthesize", fake):
            tutorial.synthesize_all(scenes, "eleven", lambda *_: None, script)
        self.assertEqual(calls, [("One.", None, "[dry]"), ("Two.", "One.", None)])

    def test_validation(self):
        s = example()
        s["voice"]["direction"] = 5
        self.assertTrue(any("voice.direction" in e for e in tutorial.validate_script(s)[0]))
        s = example()
        s["scenes"][0]["voice_direction"] = ["dry"]
        self.assertTrue(any("voice_direction" in e for e in tutorial.validate_script(s)[0]))
        s["scenes"][0]["voice_direction"] = ""
        self.assertEqual(tutorial.validate_script(s)[0], [])


class SettingsEnvTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(narration.eleven_settings({}), narration.DEFAULT_ELEVEN_SETTINGS)

    def test_overrides(self):
        s = narration.eleven_settings({"ELEVEN_STABILITY": "0.5", "ELEVEN_SIMILARITY": "0.9",
                                       "ELEVEN_STYLE": "0", "ELEVEN_SPEAKER_BOOST": "false"})
        self.assertEqual(s["stability"], 0.5)
        self.assertEqual(s["similarity_boost"], 0.9)
        self.assertEqual(s["style"], 0.0)
        self.assertIs(s["use_speaker_boost"], False)
        self.assertEqual(s["speed"], narration.DEFAULT_ELEVEN_SETTINGS["speed"])   # still sent

    def test_bad_values_keep_defaults_and_warn(self):
        warnings = []
        s = narration.eleven_settings({"ELEVEN_STABILITY": "lots", "ELEVEN_STYLE": "1.5",
                                       "ELEVEN_SPEAKER_BOOST": "maybe"}, warnings)
        self.assertEqual(s, narration.DEFAULT_ELEVEN_SETTINGS)
        self.assertEqual(len(warnings), 3)

    def test_settings_change_the_cache_key(self):
        a = narration._identity("v", "m", narration.eleven_settings({}), "t", None, None)
        b = narration._identity("v", "m", narration.eleven_settings({"ELEVEN_STABILITY": "0.9"}),
                                "t", None, None)
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
