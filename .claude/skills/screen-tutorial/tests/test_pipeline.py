"""Unit tests for the pure parts of the screen-tutorial pipeline.

    python3 -m unittest discover -s .claude/skills/screen-tutorial/tests

Covers script validation, timing arithmetic, check comparison, cell-reference
parsing, OpenScreen project editing and the Excel driver's AppleScript
generation (with osascript stubbed out). No app, recorder or voice is used.
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import openscreen  # noqa: E402
import tutorial  # noqa: E402
from drivers import base  # noqa: E402
from drivers import excel  # noqa: E402

EXAMPLE = SKILL / "templates" / "tutorial-script.example.json"


def example():
    return json.loads(EXAMPLE.read_text())


class CellRefTests(unittest.TestCase):
    def test_columns(self):
        self.assertEqual(base.col_to_num("A"), 1)
        self.assertEqual(base.col_to_num("Z"), 26)
        self.assertEqual(base.col_to_num("AA"), 27)
        self.assertEqual(base.col_to_num("XFD"), 16384)
        for n in (1, 26, 27, 52, 703, 16384):
            self.assertEqual(base.col_to_num(base.num_to_col(n)), n)

    def test_parse(self):
        self.assertEqual(base.parse_range("B6"), (None, (2, 6, 2, 6)))
        self.assertEqual(base.parse_range("Savings!A2:B9"), ("Savings", (1, 2, 2, 9)))
        self.assertEqual(base.parse_range("$B$3"), (None, (2, 3, 2, 3)))
        self.assertEqual(base.parse_range("B9:A2"), (None, (1, 2, 2, 9)))   # normalised
        self.assertEqual(base.parse_range("A:A"), (None, (1, 1, 1, None)))
        self.assertEqual(base.parse_range("3:5"), (None, (1, 3, None, 5)))
        self.assertEqual(base.parse_range("'My Sheet'!c4"), ("My Sheet", (3, 4, 3, 4)))

    def test_bad_refs(self):
        for bad in ("", "B", "6", "B6:", "Sheet!", "B6:C", "ABCD1"):
            self.assertFalse(base.is_valid_ref(bad), bad)

    def test_cell_and_address(self):
        self.assertEqual(base.parse_cell("Loan!B7"), ("Loan", 2, 7))
        with self.assertRaises(ValueError):
            base.parse_cell("A1:B2")
        self.assertEqual(base.range_address((1, 2, 2, 9)), "A2:B9")
        self.assertEqual(base.range_address((2, 6, 2, 6)), "B6")
        self.assertEqual(base.range_address((1, 1, 1, None)), "A:A")
        self.assertEqual(base.shift_range("Savings!A12:F12", 1), "Savings!A13:F13")


class ValidationTests(unittest.TestCase):
    def test_example_is_valid(self):
        errors, warnings = tutorial.validate_script(example())
        self.assertEqual(errors, [])

    def test_doc_example_is_valid(self):
        """The example printed in references/script-format.md must validate."""
        text = (SKILL / "references" / "script-format.md").read_text()
        block = text.split("## Example (three scenes)")[1].split("```json")[1].split("```")[0]
        errors, _ = tutorial.validate_script(json.loads(block))
        self.assertEqual(errors, [])

    def errors_for(self, mutate):
        script = example()
        mutate(script)
        return tutorial.validate_script(script)[0]

    def test_unknown_action(self):
        errs = self.errors_for(lambda s: s["scenes"][0]["actions"].append({"do": "dance"}))
        self.assertTrue(any("unknown action" in e for e in errs))

    def test_missing_and_unknown_fields(self):
        errs = self.errors_for(lambda s: s["scenes"][0]["actions"].append({"do": "type", "cell": "A1"}))
        self.assertTrue(any("missing `text`" in e for e in errs))
        errs = self.errors_for(lambda s: s["scenes"][0]["actions"].append(
            {"do": "type", "cell": "A1", "text": "x", "colour": "red"}))
        self.assertTrue(any("unknown field `colour`" in e for e in errs))

    def test_one_of(self):
        errs = self.errors_for(lambda s: s["scenes"][0]["actions"].append(
            {"do": "set", "cell": "A1", "value": 1, "formula": "=1"}))
        self.assertTrue(any("exactly one of value / formula" in e for e in errs))

    def test_bad_refs_and_ranges(self):
        errs = self.errors_for(lambda s: s["scenes"][0]["actions"].append(
            {"do": "type", "cell": "A1:B2", "text": "x"}))
        self.assertTrue(any("expected one cell" in e for e in errs))
        errs = self.errors_for(lambda s: s["scenes"][1].update(zoom="nope"))
        self.assertTrue(any("bad cell/range" in e for e in errs))

    def test_duplicate_ids_and_code(self):
        def dup(s):
            s["scenes"][1]["id"] = "inputs"
            s["code"] = "lowercase-code"
        errs = self.errors_for(dup)
        self.assertTrue(any("duplicate id" in e for e in errs))
        self.assertTrue(any(e.startswith("code:") for e in errs))

    def test_checks(self):
        errs = self.errors_for(lambda s: s["scenes"][0]["checks"].append(
            {"cell": "B3", "equals": 1, "text": "1"}))
        self.assertTrue(any("exactly one of `equals` / `text`" in e for e in errs))

    def test_chapters(self):
        errs = self.errors_for(lambda s: s["chapters"].append({"id": "x", "scenes": ["ghost"]}))
        self.assertTrue(any("unknown scene 'ghost'" in e for e in errs))
        errs = self.errors_for(lambda s: s["chapters"].append({"id": "y", "scenes": ["rate"]}))
        self.assertTrue(any("already in chapter" in e for e in errs))

    def test_warnings(self):
        script = example()
        script["scenes"][0]["say"] = "Type 4.5% into B3 " + "word " * 50
        _, warnings = tutorial.validate_script(script)
        self.assertTrue(any("words" in w and "45" in w for w in warnings))
        self.assertTrue(any("digits or symbols" in w for w in warnings))

    def test_every_action_has_a_driver_method(self):
        for do in base.ACTIONS:
            if do not in base.TIMING_ACTIONS:
                self.assertTrue(hasattr(excel.ExcelDriver, "do_" + do), do)


class TimingTests(unittest.TestCase):
    def test_narration_estimate(self):
        self.assertAlmostEqual(tutorial.estimate_narration("one two three " * 10), 30 / 2.9)
        self.assertEqual(tutorial.estimate_narration("hi"), 1.5)

    def test_narration_sets_duration(self):
        plan = tutorial.plan_scene(10.0, [{"do": "wait", "seconds": 2}])
        self.assertAlmostEqual(plan["actions"], 2.0)
        self.assertAlmostEqual(plan["duration"], 10.0 + tutorial.BREATH)

    def test_actions_set_duration(self):
        plan = tutorial.plan_scene(3.0, [{"do": "wait", "seconds": 5}])
        self.assertAlmostEqual(plan["duration"], 5.0 + tutorial.BREATH)

    def test_at_jumps_forward_not_back(self):
        actions = [{"do": "wait", "seconds": 1}, {"do": "at", "fraction": 0.5},
                   {"do": "wait", "seconds": 1}]
        self.assertAlmostEqual(tutorial.plan_scene(8.0, actions)["actions"], 5.0)
        actions = [{"do": "wait", "seconds": 6}, {"do": "at", "fraction": 0.5}]
        self.assertAlmostEqual(tutorial.plan_scene(8.0, actions)["actions"], 6.0)

    def test_type_cost_scales_with_length(self):
        short = base.estimate_seconds({"do": "type", "cell": "A1", "text": "APY"})
        long_ = base.estimate_seconds({"do": "type", "cell": "A1", "text": "=(1+B3)^(1/12)-1"})
        self.assertAlmostEqual(long_ - short, 13 * base.DEFAULT_PACE)
        slow = base.estimate_seconds({"do": "type", "cell": "A1", "text": "APY", "pace": 0.2})
        self.assertGreater(slow, short)

    def test_cues_follow_timeline(self):
        timeline = [{"start": 1.0, "narration": 4.0, "caption": "a"},
                    {"start": 6.0, "narration": 2.5, "caption": "b"}]
        self.assertEqual(tutorial.narration_cues(timeline), [(1.0, 5.0, "a"), (6.0, 8.5, "b")])

    def test_chapter_selection(self):
        script = example()
        script["chapters"] = [{"id": "one", "scenes": ["inputs"]},
                              {"id": "two", "scenes": ["rate", "recap"]}]
        before, sel, after = tutorial.chapter_scenes(script, "two")
        self.assertEqual([s["id"] for s in before], ["inputs"])
        self.assertEqual([s["id"] for s in sel], ["rate", "recap"])
        self.assertEqual(after, [])
        before, sel, after = tutorial.chapter_scenes(script, None)
        self.assertEqual(len(sel), 3)
        with self.assertRaises(SystemExit):
            tutorial.chapter_scenes(script, "three")

    def test_zoom_scale(self):
        self.assertEqual(tutorial.zoom_scale_for((0, 0, 0.9, 0.9)), 1.25)   # big range: gentle
        self.assertEqual(tutorial.zoom_scale_for((0, 0, 0.01, 0.01)), 2.0)  # tiny range: capped
        self.assertAlmostEqual(tutorial.zoom_scale_for((0, 0, 0.3, 0.2)), 0.55 / 0.3)


class CheckTests(unittest.TestCase):
    def test_equals(self):
        res = tutorial.evaluate_check({"cell": "B6", "equals": 0.0036748, "tol": 1e-6}, value=0.0036748094)
        self.assertTrue(res["pass"])
        res = tutorial.evaluate_check({"cell": "B6", "equals": 0.0036748, "tol": 1e-9}, value=0.0036748094)
        self.assertFalse(res["pass"])
        res = tutorial.evaluate_check({"cell": "E12", "equals": 651.84, "tol": 0.005}, value=651.8449)
        self.assertTrue(res["pass"])

    def test_equals_non_number(self):
        res = tutorial.evaluate_check({"cell": "B6", "equals": 1}, value="#DIV/0!")
        self.assertFalse(res["pass"])

    def test_text(self):
        self.assertTrue(tutorial.evaluate_check({"cell": "B7", "text": "$231.63"}, text="$231.63 ")["pass"])
        self.assertFalse(tutorial.evaluate_check({"cell": "B7", "text": "$231.63"}, text="231.63")["pass"])


class ProjectEditingTests(unittest.TestCase):
    SAMPLE = {
        "version": 2,
        "media": {"screenVideoPath": "/tmp/x.mp4", "cursorCaptureMode": "editable-overlay"},
        "editor": {"wallpaper": "/wallpapers/wallpaper11.jpg", "borderRadius": 40, "padding": 50,
                   "zoomRegions": [], "annotationRegions": [], "aspectRatio": "auto",
                   "autoZoomEnabled": True},
    }

    def test_style(self):
        p = openscreen.apply_tutorial_style(copy.deepcopy(self.SAMPLE))
        ed = p["editor"]
        self.assertEqual(ed["aspectRatio"], "16:9")
        self.assertEqual(ed["padding"], 24)
        self.assertEqual(ed["borderRadius"], 12)
        self.assertFalse(ed["autoZoomEnabled"])
        self.assertEqual(ed["wallpaper"], "/wallpapers/wallpaper11.jpg")   # kept

    def test_zoom_region_shape(self):
        z = openscreen.zoom_region("z1", 1.2345, 4.0, 0.3, 1.7, depth=9)
        self.assertEqual(z["startMs"], 1234)
        self.assertEqual(z["endMs"], 4000)
        self.assertEqual(z["depth"], 2)         # invalid depth falls back
        self.assertEqual(z["focus"], {"cx": 0.3, "cy": 1.0})
        self.assertEqual(z["focusMode"], "manual")
        self.assertEqual(set(z), {"id", "startMs", "endMs", "depth", "focus", "focusMode", "source"})
        self.assertGreater(openscreen.zoom_region("z", 2, 2, .5, .5)["endMs"], 2000)

    def test_depth_for_scale(self):
        self.assertEqual(openscreen.depth_for_scale(1.0), 1)
        self.assertEqual(openscreen.depth_for_scale(1.5), 2)
        self.assertEqual(openscreen.depth_for_scale(1.79), 2)
        self.assertEqual(openscreen.depth_for_scale(2.0), 3)
        self.assertEqual(openscreen.depth_for_scale(9.0), 6)

    def test_frame_focus(self):
        # Full-frame window: centre stays, edges clamp to half the view.
        self.assertEqual(openscreen.frame_focus(0.5, 0.5, 2.0), (0.5, 0.5))
        self.assertEqual(openscreen.frame_focus(0.0, 1.0, 2.0, slack=0), (0.25, 0.75))
        # Window filling 0.8 x 0.9 of the frame, centred: a top-left point
        # clamps so the view's edge sits on the window's edge.
        fx, fy = openscreen.frame_focus(0.0, 0.0, 2.0, box=(0.8, 0.9), slack=0)
        self.assertAlmostEqual(fx, 0.1 + 0.25)
        self.assertAlmostEqual(fy, 0.05 + 0.25)
        # Middle of the window maps to the middle of the frame.
        self.assertEqual(openscreen.frame_focus(0.5, 0.5, 1.5, box=(0.8, 0.9)), (0.5, 0.5))
        # Slack lets the view reach a little past the window edge.
        fx, _ = openscreen.frame_focus(0.0, 0.0, 2.0, box=(0.8, 0.9), slack=0.03)
        self.assertAlmostEqual(fx, 0.1 + 0.25 - 0.03)
        # A view wider than the window just centres.
        self.assertEqual(openscreen.frame_focus(0.1, 0.1, 1.1, box=(0.8, 0.9))[0], 0.5)

    def test_content_box(self):
        w, h = openscreen.content_box(1600, 923, padding=24)
        self.assertAlmostEqual(h, 0.9)
        self.assertAlmostEqual(w, 0.9 * (1600 / 923) / (16 / 9))
        w, h = openscreen.content_box(1920, 800, padding=0)     # wider than 16:9
        self.assertAlmostEqual(w, 1.0)
        self.assertLess(h, 1.0)

    def test_text_annotation(self):
        a = openscreen.text_annotation("c", 2.0, 5.0, "12th root", x=150, style={"fontSize": 50})
        self.assertEqual(a["type"], "text")
        self.assertEqual(a["content"], "12th root")
        self.assertEqual(a["position"]["x"], 100)
        self.assertEqual(a["style"]["fontSize"], 50)
        self.assertEqual(a["style"]["fontFamily"], "Inter")
        self.assertEqual((a["startMs"], a["endMs"]), (2000, 5000))

    def test_set_regions_and_round_trip(self):
        p = copy.deepcopy(self.SAMPLE)
        openscreen.set_regions(p, [openscreen.zoom_region("z", 0, 1, .5, .5)], None)
        self.assertEqual(len(p["editor"]["zoomRegions"]), 1)
        self.assertEqual(p["editor"]["annotationRegions"], [])
        with tempfile.TemporaryDirectory() as tmp:
            path = openscreen.save_project(p, Path(tmp) / "t.openscreen")
            self.assertEqual(openscreen.load_project(path), p)
            (Path(tmp) / "bad.openscreen").write_text("{}")
            with self.assertRaises(openscreen.OpenScreenError):
                openscreen.load_project(Path(tmp) / "bad.openscreen")

    def test_adopt_take_hides_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "rec").mkdir()
            src = tmp / "rec" / "recording-1.mp4"
            src.write_bytes(b"video")
            Path(str(src) + ".cursor.json").write_text(json.dumps(
                {"version": 2, "samples": [{"timeMs": 0, "cx": .5, "cy": .5, "visible": True}]}))
            p = copy.deepcopy(self.SAMPLE)
            p["media"]["screenVideoPath"] = str(src)
            video = openscreen.adopt_take(p, tmp / "out")
            self.assertEqual(video, tmp / "out" / "take.mp4")
            self.assertFalse(src.exists())
            self.assertEqual(p["media"]["screenVideoPath"], str(video))
            track = json.loads(Path(str(video) + ".cursor.json").read_text())
            self.assertFalse(track["samples"][0]["visible"])

    def test_env_drops_electron_flag(self):
        import os
        os.environ["ELECTRON_RUN_AS_NODE"] = "1"
        try:
            self.assertNotIn("ELECTRON_RUN_AS_NODE", openscreen.cli_env())
        finally:
            del os.environ["ELECTRON_RUN_AS_NODE"]


class ExcelScriptTests(unittest.TestCase):
    """The Excel driver's AppleScript, with osascript replaced by a recorder."""

    def setUp(self):
        self.scripts = []
        self._orig = excel.run_osascript

        def fake(script, timeout=60):
            self.scripts.append(script)
            if "visible range" in script:
                return "$A$1:$M$26"
            return ""
        excel.run_osascript = fake
        self.d = excel.ExcelDriver(log=lambda *_: None)
        self.d.workbook = "Book7"
        self.d.active = "Savings"

    def tearDown(self):
        excel.run_osascript = self._orig

    def test_quote(self):
        self.assertEqual(excel.q('say "hi" \\'), '"say \\"hi\\" \\\\"')
        self.assertEqual(excel.as_literal([1, "a", True]), '{1, "a", true}')

    def test_type_animates_then_commits(self):
        self.d.perform({"do": "type", "cell": "B6", "text": "=1+2"})
        script = self.scripts[-1]
        self.assertIn('set wb to workbook "Book7"', script)
        self.assertIn('set formula of r to "\'=1+"', script)        # partial, as text
        self.assertIn('set formula of r to "=1+2"', script)         # real commit
        self.assertIn('select range "B7"', script)                  # Enter moves down
        self.assertEqual(script.count("delay"), 4)

    def test_type_fast_has_no_animation(self):
        self.d.perform({"do": "type", "cell": "B6", "text": "4.5%", "commit": "none"}, fast=True)
        script = self.scripts[-1]
        self.assertNotIn("delay", script)
        self.assertNotIn("'4", script)
        self.assertNotIn('select range "B7"', script)

    def test_other_sheet_is_activated(self):
        self.d.perform({"do": "type", "cell": "Loan!B2", "text": "1"}, fast=True)
        self.assertTrue(any('activate object worksheet "Loan"' in s for s in self.scripts))
        self.assertEqual(self.d.active, "Loan")

    def test_fill_down(self):
        self.d.perform({"do": "fill_down", "range": "A13:F71", "from": "A12:F12"}, fast=True)
        self.assertIn('fill down range "A12:F71"', self.scripts[-1])
        with self.assertRaises(base.DriverError):
            self.d.perform({"do": "fill_down", "range": "A13:F71", "from": "A10:F10"})

    def test_set_formula_over_range_fills(self):
        self.d.perform({"do": "set", "range": "A13:B20", "formula": "=A12+1"})
        s = self.scripts[-1]
        self.assertIn('set formula of range "A13"', s)
        self.assertIn('fill right range "A13:B13"', s)
        self.assertIn('fill down range "A13:B20"', s)

    def test_chart(self):
        self.d.perform({"do": "chart", "type": "line", "x": "A12:A20",
                        "series": [{"range": "B12:B20", "name": "Balance"},
                                   {"range": "Loan!C12:C20"}],
                        "title": "Growth", "y_min": 0, "at": "H2"})
        s = self.scripts[-1]
        self.assertIn("line chart", s)
        self.assertIn("\"='Savings'!$B$12:$B$20\"", s)
        self.assertIn("\"='Loan'!$C$12:$C$20\"", s)
        self.assertIn('set name of series 1 of ch to "Balance"', s)
        self.assertIn("set minimum scale of ax to 0.0", s)

    def test_timing_action_rejected(self):
        with self.assertRaises(base.DriverError):
            self.d.perform({"do": "wait", "seconds": 1})


if __name__ == "__main__":
    unittest.main()
