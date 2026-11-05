"""Unit tests for listen_check.py (stdlib only, no network, no ssh).

Run from the skill folder:

    cd .claude/skills/screen-tutorial
    python3 -m unittest discover -s tests

The remote path is exercised by checking the generated bash and the marker
parser; nothing here opens an ssh connection or calls whisper.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import listen_check as lc  # noqa: E402


class NumberWordsTests(unittest.TestCase):
    def test_digits(self):
        self.assertEqual(lc.tokenize("24"), lc.tokenize("twenty four"))
        self.assertEqual(lc.tokenize("1971"), lc.tokenize("nineteen seventy one"))

    def test_decimals(self):
        self.assertEqual(lc.tokenize("4.5"), lc.tokenize("four point five"))
        self.assertEqual(lc.tokenize("0.045"), lc.tokenize("zero point zero four five"))
        self.assertEqual(lc.tokenize("1.045"), lc.tokenize("one point oh four five"))
        self.assertEqual(lc.tokenize("9.8"), lc.tokenize("nine point eight"))

    def test_percents(self):
        self.assertEqual(
            lc.tokenize("4.5%"),
            lc.tokenize("four point five percent"),
        )
        self.assertEqual(
            lc.tokenize("0.36748%"),
            lc.tokenize("zero point three six seven four eight percent"),
        )

    def test_dollars(self):
        self.assertEqual(lc.tokenize("$16,000"), lc.tokenize("sixteen thousand dollars"))
        self.assertEqual(lc.tokenize("$651.84"), lc.tokenize("six fifty one eighty four"))
        self.assertEqual(lc.tokenize("$1.84"), lc.tokenize("a dollar eighty four"))
        self.assertEqual(lc.tokenize("$0.84"), lc.tokenize("eighty four cents"))
        self.assertEqual(lc.tokenize("$429.33"), lc.tokenize("four hundred twenty nine thirty three"))

    def test_cell_refs(self):
        self.assertEqual(lc.tokenize("B5"), lc.tokenize("b five"))
        self.assertEqual(lc.tokenize("A11"), lc.tokenize("a eleven"))
        self.assertEqual(lc.tokenize("F71"), lc.tokenize("f seventy one"))

    def test_cents_and_literal_currency(self):
        self.assertEqual(lc.tokenize("$0.04"), lc.tokenize("four cents"))
        self.assertEqual(lc.tokenize("4 cents"), lc.tokenize("four cents"))
        self.assertEqual(lc.tokenize("$4.84"), lc.tokenize("4 dollars and 84 cents"))
        self.assertEqual(lc.tokenize("$0.13"), lc.tokenize("thirteen cents"))

    def test_punctuation_separates_numbers(self):
        # A colon ends the month number; it must not concatenate 24 and 4302.33.
        self.assertEqual(
            lc.tokenize("Month twenty four: four thousand three hundred two thirty three."),
            ["month", "24", "430233"],
        )

    def test_decimal_with_literal_digits(self):
        self.assertEqual(lc.tokenize("four point 5"), lc.tokenize("4.5"))

    def test_article_after_number_is_a_word(self):
        self.assertEqual(
            lc.tokenize("from a hundred fifty a month"),
            ["from", "150", "a", "month"],
        )

    def test_hundreds_and_scales(self):
        self.assertEqual(lc.tokenize("150"), lc.tokenize("a hundred fifty"))
        self.assertEqual(lc.tokenize("4302.33"), lc.tokenize("four thousand three hundred two thirty three"))
        self.assertEqual(lc.tokenize("11697.67"), lc.tokenize("eleven thousand six ninety seven sixty seven"))

    def test_number_to_words_public_function(self):
        self.assertEqual(
            lc.number_to_words(651.84),
            "six hundred fifty one point eight four",
        )
        self.assertEqual(lc.number_to_words("$16,000"), "sixteen thousand")
        self.assertEqual(lc.number_to_words("4.5%"), "four point five")
        self.assertEqual(lc.money_to_words("$16,000"), "sixteen thousand dollars")
        self.assertEqual(lc.money_to_words("$1.84"), "one dollar and eighty four cents")
        self.assertEqual(lc.money_to_words("$0.84"), "eighty four cents")

    def test_negative(self):
        self.assertEqual(lc.tokenize("-9.8"), lc.tokenize("negative nine point eight"))


class NormalizerTests(unittest.TestCase):
    def test_case_and_punctuation(self):
        self.assertEqual(
            lc.tokenize("Press Enter, then B5."),
            lc.tokenize("press enter then b five"),
        )

    def test_spoken_initialisms(self):
        self.assertEqual(lc.tokenize("a p y"), lc.tokenize("APY"))
        self.assertEqual(lc.tokenize("k d e a"), lc.tokenize("KDEA"))

    def test_command_symbol_is_ignored(self):
        self.assertEqual(lc.tokenize("\u2318 D"), lc.tokenize("D"))

    def test_if_is_not_an_initialism(self):
        self.assertNotEqual(lc.tokenize("if"), lc.tokenize("i f"))
        report = lc.analyze_clip("x", "if you save", "I F you save", 0.25)
        self.assertTrue(any("letters" in flag for flag in report["flags"]))

    def test_acronym_does_not_get_a_letter_flag(self):
        report = lc.analyze_clip("x", "a p y is the rate", "APY is the rate", 0.25)
        self.assertFalse(any("letters" in flag for flag in report["flags"]))

    def test_intended_letters_joined_by_whisper_is_fine(self):
        # The script says "v x"; whisper writes "vx". That is not a mismatch.
        report = lc.analyze_clip("x", "v x is the horizontal speed", "vx is the horizontal speed", 0.25)
        self.assertFalse(any("letters" in flag for flag in report["flags"]))


class WerTests(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(lc.word_error_rate(["a", "b", "c"], ["a", "b", "c"]), 0.0)

    def test_substitution(self):
        self.assertAlmostEqual(
            lc.word_error_rate(["a", "b", "c", "d"], ["a", "x", "c", "d"]),
            0.25,
        )

    def test_deletion_and_insertion(self):
        self.assertAlmostEqual(lc.word_error_rate(["a", "b"], ["a"]), 0.5)
        self.assertAlmostEqual(lc.word_error_rate(["a"], ["a", "b"]), 1.0)

    def test_empty(self):
        self.assertEqual(lc.word_error_rate([], []), 0.0)
        self.assertEqual(lc.word_error_rate([], ["a"]), 1.0)


class FlagTests(unittest.TestCase):
    def test_clean_clip(self):
        report = lc.analyze_clip("hook", "Press Enter.", "Press Enter.", 0.25)
        self.assertEqual(report["wer"], 0.0)
        self.assertEqual(report["flags"], [])
        self.assertFalse(report["flagged"])
        self.assertEqual(report["first_difference"], "")

    def test_wer_flag(self):
        report = lc.analyze_clip(
            "x", "the quick brown fox jumps", "the slow brown fox", 0.25,
        )
        self.assertTrue(any(flag.startswith("wer ") for flag in report["flags"]))
        self.assertTrue(report["flagged"])
        self.assertIn("expected", report["first_difference"])

    def test_threshold_is_strictly_greater_than(self):
        report = lc.analyze_clip("x", "a b c d", "a x c d", 0.25)
        self.assertEqual(report["wer"], 0.25)
        self.assertFalse(any(flag.startswith("wer ") for flag in report["flags"]))

    def test_bracketed_tag(self):
        report = lc.analyze_clip("x", "Press Enter.", "[dry] Press Enter.", 0.25)
        self.assertTrue(any("tag" in flag for flag in report["flags"]))
        self.assertTrue(any("dry" in flag for flag in report["flags"]))

    def test_spoken_tag_without_brackets(self):
        report = lc.analyze_clip("x", "Press Enter.", "Dry. Press Enter.", 0.25)
        self.assertTrue(any("dry" in flag for flag in report["flags"]))

    def test_tag_word_that_is_content_is_not_flagged(self):
        report = lc.analyze_clip("x", "The dry air rises.", "The dry air rises.", 0.25)
        self.assertFalse(any(flag.startswith("tag:") for flag in report["flags"]))

    def test_letters_versus_word(self):
        report = lc.analyze_clip("x", "if you save", "I.F. you save", 0.25)
        self.assertTrue(any("letters" in flag for flag in report["flags"]))
        self.assertIn("i f", report["first_difference"])

    def test_missing_number(self):
        report = lc.analyze_clip("x", "twenty four months", "twenty months", 0.25)
        self.assertIn("24", report["missing_numbers"])
        self.assertTrue(any(flag.startswith("number missing") for flag in report["flags"]))

    def test_number_present_in_another_form_is_not_missing(self):
        report = lc.analyze_clip("x", "twenty four months", "24 months", 0.25)
        self.assertEqual(report["missing_numbers"], [])
        self.assertFalse(any(flag.startswith("number missing") for flag in report["flags"]))

    def test_empty_transcript(self):
        report = lc.analyze_clip("x", "Press Enter.", "", 0.25)
        self.assertEqual(report["wer"], 1.0)
        self.assertIn("empty transcript", report["flags"])

    def test_error_short_circuits_comparison(self):
        report = lc.analyze_clip(
            "x", "twenty four", None, 0.25, error="clip not found",
        )
        self.assertIsNone(report["wer"])
        self.assertEqual(report["flags"], ["error: clip not found"])
        self.assertTrue(report["flagged"])
        self.assertEqual(report["missing_numbers"], [])


class ManimHashTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "voice.env").write_text(
            "ELEVEN_VOICE_ID=voice123\n"
            "ELEVEN_MODEL=model-v4\n"
            "ELEVEN_STABILITY=0.5\n"
            'ELEVEN_DIRECTION="[dry, wry]"\n',
            encoding="utf-8",
        )
        (self.root / "cushman.py").write_text(
            "import os\n"
            "ELEVEN_VOICE_ID = os.environ.get('ELEVEN_VOICE_ID', 'fallback')\n"
            "ELEVEN_MODEL = os.environ.get('ELEVEN_MODEL', 'fallback-model')\n"
            "ELEVEN_SETTINGS = {\n"
            "    'stability': float(os.environ.get('ELEVEN_STABILITY', 0.42)),\n"
            "    'speed': 0.94,\n"
            "    'use_speaker_boost': True,\n"
            "}\n"
            "ELEVEN_DIRECTION = os.environ.get('ELEVEN_DIRECTION', '').strip()\n"
            "def narration_clip(text, prev_text=None, next_text=None):\n"
            "    identity = [ELEVEN_VOICE_ID, ELEVEN_MODEL, ELEVEN_SETTINGS,\n"
            "                ELEVEN_DIRECTION, text, prev_text, next_text]\n"
            "    return identity\n",
            encoding="utf-8",
        )
        (self.root / "scene.py").write_text(
            "from cushman import *\n"
            "SCRIPT_TEXT = {'first': 'One two.', 'second': 'Three four.'}\n"
            "class Demo(NarratedScene):\n"
            "    VIDEO_CODE = 'DEMO-1'\n"
            "    SCRIPT = SCRIPT_TEXT\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_settings_direction_and_identity_hash(self):
        config = lc.load_manim_config(self.root)
        self.assertEqual(config.voice_id, "voice123")
        self.assertEqual(config.model, "model-v4")
        self.assertEqual(config.settings["stability"], 0.5)
        self.assertEqual(config.direction, "[dry, wry]")
        self.assertTrue(config.identity_has_direction)

        text = "One two."
        following = "Three four."
        expected = hashlib.sha1(
            json.dumps(
                ["voice123", "model-v4", config.settings, "[dry, wry]",
                 text, None, following],
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:16]
        self.assertEqual(
            lc.manim_identity_hash(text, None, following, config),
            expected,
        )

    def test_scene_script_parsing_and_remote_paths(self):
        config = lc.load_manim_config(self.root)
        scenes = lc.parse_scene_file(self.root / "scene.py")
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0].video_code, "DEMO-1")
        self.assertEqual(
            [key for key, _ in scenes[0].beats],
            ["first", "second"],
        )

        items = lc.load_manim_items(
            [self.root / "scene.py"], config, "$HOME/cache",
        )
        self.assertEqual([item.id for item in items], ["DEMO-1:first", "DEMO-1:second"])
        self.assertTrue(items[0].remote_path.startswith("$HOME/cache/voice123/"))
        self.assertTrue(items[0].remote_path.endswith(".mp3"))

    def test_identity_without_direction_is_supported(self):
        (self.root / "cushman.py").write_text(
            "import os\n"
            "ELEVEN_VOICE_ID = os.environ.get('ELEVEN_VOICE_ID', 'fallback')\n"
            "ELEVEN_MODEL = os.environ.get('ELEVEN_MODEL', 'fallback-model')\n"
            "ELEVEN_SETTINGS = {'stability': float(os.environ.get('ELEVEN_STABILITY', 0.42))}\n"
            "ELEVEN_DIRECTION = os.environ.get('ELEVEN_DIRECTION', '').strip()\n"
            "def narration_clip(text, prev_text=None, next_text=None):\n"
            "    identity = [ELEVEN_VOICE_ID, ELEVEN_MODEL, ELEVEN_SETTINGS,\n"
            "                text, prev_text, next_text]\n"
            "    return identity\n",
            encoding="utf-8",
        )
        config = lc.load_manim_config(self.root)
        self.assertFalse(config.identity_has_direction)
        expected = hashlib.sha1(
            json.dumps(
                ["voice123", "model-v4", config.settings, "Hello.", None, None],
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:16]
        self.assertEqual(
            lc.manim_identity_hash("Hello.", None, None, config),
            expected,
        )


class TutorialInputTests(unittest.TestCase):
    def test_timeline_clips_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.wav").write_bytes(b"fake")
            timeline = root / "demo.timeline.json"
            timeline.write_text(json.dumps({
                "scenes": [
                    {"id": "one", "caption": "Hello.", "clip": "a.wav"},
                    {"id": "two", "say": "Bye.", "clip": str(root / "missing.wav")},
                    {"id": "three", "caption": "Draft.", "clip": None},
                ],
            }), encoding="utf-8")
            items = lc.load_tutorial_items(timeline)
            self.assertEqual(len(items), 3)
            self.assertEqual(items[0].intended, "Hello.")
            self.assertEqual(items[0].local_path, (root / "a.wav").resolve())
            self.assertIsNone(items[0].pre_error)
            self.assertEqual(items[1].intended, "Bye.")
            self.assertIn("clip not found", items[1].pre_error)
            self.assertIn("no clip", items[2].pre_error)


class RemoteBatchTests(unittest.TestCase):
    def test_script_uses_one_loop_and_quotes_paths(self):
        script = lc.build_remote_script(
            [(0, "clips/0.wav"), (1, "$HOME/cache/a b.mp3")],
            "abc123",
        )
        self.assertIn("run_one 0 clips/0.wav", script)
        self.assertIn('run_one 1 "$HOME/cache/a b.mp3"', script)
        self.assertIn("@@LISTEN_BEGIN_abc123:%s@@", script)
        self.assertIn("-ar 16000 -ac 1", script)
        self.assertIn("-np -f", script)
        self.assertNotIn("-nt", script)  # -nt drops trailing segments

    def test_parse_output(self):
        output = (
            "banner\n"
            "@@LISTEN_BEGIN_abc123:0@@\n"
            " Hello there. 651.84 dollars.\n"
            "@@LISTEN_END_abc123:0@@\n"
            "@@LISTEN_BEGIN_abc123:1@@\n"
            "@@LISTEN_ERROR@@ ffmpeg: no such file\n"
            "@@LISTEN_END_abc123:1@@\n"
        )
        parsed = lc.parse_batch_output(output, "abc123", 3)
        self.assertEqual(parsed[0], ("Hello there. 651.84 dollars.", None))
        self.assertIsNone(parsed[1][0])
        self.assertIn("ffmpeg", parsed[1][1])
        self.assertIn("no transcript returned", parsed[2][1])

    def test_run_items_deduplicates_clips_and_keeps_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "one.wav"
            clip.write_bytes(b"fake")
            items = [
                lc.CheckItem("a", "Hello.", local_path=clip, display_path=str(clip)),
                lc.CheckItem("b", "Hello.", local_path=clip, display_path=str(clip)),
                lc.CheckItem("c", "Broken.", pre_error="clip not found"),
            ]
            with mock.patch.object(
                lc, "transcribe_jobs", return_value=[("Hello.", None)],
            ) as transcriber:
                reports = lc.run_items(items, 0.25)
            self.assertEqual(transcriber.call_count, 1)
            jobs = transcriber.call_args[0][0]
            self.assertEqual(len(jobs), 1)
            self.assertFalse(reports[0]["flagged"])
            self.assertFalse(reports[1]["flagged"])
            self.assertTrue(reports[2]["flagged"])
            self.assertEqual(reports[2]["flags"], ["error: clip not found"])


if __name__ == "__main__":
    unittest.main()


class EndingDroppedTests(unittest.TestCase):
    def test_flags_clip_that_stops_early(self):
        intended = ("Interest is charged on what you still owe, so as the balance falls, "
                    "more of each payment reaches principal. Month one: about twenty nine "
                    "percent interest. Month sixty: under one percent.")
        heard = ("Interest is charged on what you still owe, so as the balance falls, "
                 "more of each payment reaches principle.")
        row = lc.analyze_clip("x", intended, heard, 0.25)
        self.assertTrue(any(f.startswith("ending not spoken") for f in row["flags"]))

    def test_full_clip_not_flagged(self):
        intended = "Put the twelfth root back. Six fifty one eighty four."
        heard = "Put the twelfth root back. 651.84."
        row = lc.analyze_clip("x", intended, heard, 0.25)
        self.assertFalse(any(f.startswith("ending not spoken") for f in row["flags"]))
