"""
Tests for :func:`RecapGenerator.prepare_recap_context` using synthetic data.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401

from src.recap_generator import RecapGenerator


def _load_synthetic():
    tests_dir = Path(__file__).resolve().parent
    script_path = tests_dir.parent / "scripts" / "validate_pipeline.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("_validate_pipeline", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.synthetic_week_data


_SYNTHETIC = _load_synthetic()


class PrepareRecapContextTests(unittest.TestCase):

    def test_prepare_includes_house_voice_mechanics_not_persona(self):
        gen = RecapGenerator()
        with patch.object(gen, "fetch_week_data", return_value=_SYNTHETIC(week=5)):
            bundle = gen.prepare_recap_context(5)
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle["week"], 5)
        self.assertNotIn("PERSONA_SEED", bundle["data_context"])
        self.assertNotIn("persona_seed", bundle)
        self.assertIn("CLOSING LINE", bundle["data_context"])
        self.assertIn("Weekly Superlatives", bundle["data_context"])
        self.assertTrue(bundle["closing_line"])
        self.assertIn("Now write the Week 5 recap", bundle["user_prompt"])
        # Week 5 is not a holiday week — no calendar costume, no invented news.
        self.assertIsNone(bundle["calendar_hook"])
        self.assertNotIn("CALENDAR_HOOK", bundle["data_context"])
        self.assertNotIn("NEWS_CONTEXT", bundle["data_context"])

    def test_prepare_injects_calendar_hook_on_holiday_week(self):
        gen = RecapGenerator()
        with patch.object(gen, "fetch_week_data", return_value=_SYNTHETIC(week=13)):
            bundle = gen.prepare_recap_context(13)
        assert bundle is not None
        self.assertIsNotNone(bundle["calendar_hook"])
        self.assertIn("CALENDAR_HOOK", bundle["data_context"])
        self.assertIn("Thanksgiving", bundle["data_context"])
        self.assertNotIn("PERSONA_SEED", bundle["data_context"])

    def test_prepare_picks_bit_of_the_week_from_superlatives(self):
        gen = RecapGenerator()
        week_data = _SYNTHETIC(week=5)
        # Tighten the only matchup so the nail-biter award fires.
        m = week_data["matchups"]["matchups"][0]
        m["home_team"]["score"] = 100.4
        m["away_team"]["score"] = 98.1
        m["margin"] = 2.3
        from src.gif_bank import pick_gif
        from src.superlatives import compute_superlatives

        week_data["superlatives"] = compute_superlatives(week_data)
        week_data["gif_of_the_week"] = pick_gif(
            week_data, 5, superlatives=week_data["superlatives"]
        )

        with patch.object(gen, "fetch_week_data", return_value=week_data):
            bundle = gen.prepare_recap_context(5)
        assert bundle is not None
        self.assertIsNotNone(bundle["bit_of_the_week"])
        self.assertIn("BIT_OF_THE_WEEK", bundle["data_context"])
        self.assertIn("nail-biter", bundle["bit_of_the_week"].lower())

    def test_ordinary_week_can_skip_bit_of_the_week(self):
        gen = RecapGenerator()
        week_data = _SYNTHETIC(week=5)
        # 24-pt margin is neither a nail-biter nor a blowout.
        with patch.object(gen, "fetch_week_data", return_value=week_data):
            bundle = gen.prepare_recap_context(5)
        assert bundle is not None
        if not bundle["bit_of_the_week"]:
            self.assertNotIn("BIT_OF_THE_WEEK", bundle["data_context"])

    def test_save_prepared_context_writes_files(self):
        gen = RecapGenerator()
        with patch.object(gen, "fetch_week_data", return_value=_SYNTHETIC(week=3)):
            bundle = gen.prepare_recap_context(3)
        assert bundle is not None

        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.recap_generator.OUTPUT_DIR", tmp):
                path = gen.save_prepared_context(bundle)
                self.assertTrue(Path(path).exists())
                content = Path(path).read_text()
                self.assertIn("Week 3 Recap", content)
                self.assertIn("Bench Hero of the Week", content)
                self.assertNotIn("PERSONA_SEED", content)
                meta_path = Path(tmp) / "week-3-context.meta.json"
                self.assertTrue(meta_path.exists())
                meta = json.loads(meta_path.read_text())
                self.assertEqual(meta["week"], 3)
                self.assertEqual(meta["house_voice"], "The Commissioner's Ghost")
                self.assertNotIn("persona_seed", meta)
                self.assertEqual(meta["closing_line"], bundle["closing_line"])


if __name__ == "__main__":
    unittest.main()
