"""Tests for unfinalized guard on :meth:`RecapGenerator.finalize_recap`."""

from __future__ import annotations

import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401

from src.recap_generator import OUTPUT_DIR, RECAP_HISTORY_FILE, RecapGenerator


def _load_synthetic():
    tests_dir = Path(__file__).resolve().parent
    script_path = tests_dir.parent / "scripts" / "validate_pipeline.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("_validate_pipeline", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.synthetic_week_data


_SYNTHETIC = _load_synthetic()


class FinalizeRecapUnfinalizedTests(unittest.TestCase):

    def test_refuses_unfinalized_week_without_force(self):
        week_data = _SYNTHETIC(week=7)
        week_data["league"]["current_week"] = 7
        for m in week_data["matchups"]["matchups"]:
            for side in ("home_team", "away_team"):
                t = m.get(side)
                if isinstance(t, dict):
                    t["score"] = 0.0

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            recap_path = out / "week-7-recap.md"
            recap_path.write_text("# Week 7\n\nGhost recap body.\n", encoding="utf-8")
            weekdata_path = out / "week-7-weekdata.json"
            weekdata_path.write_text(json.dumps(week_data), encoding="utf-8")
            history_path = out / "recap_history.json"
            history_path.write_text("[]", encoding="utf-8")

            gen = RecapGenerator()
            gen.recap_history = []

            with (
                patch("src.recap_generator.OUTPUT_DIR", str(out)),
                patch("src.recap_generator.RECAP_HISTORY_FILE", str(history_path)),
            ):
                buf = StringIO()
                with patch("sys.stdout", buf):
                    ok = gen.finalize_recap(7, force=False)
                self.assertFalse(ok)
                self.assertIn("unfinalized", buf.getvalue().lower())
                self.assertEqual(json.loads(history_path.read_text()), [])

    def test_force_allows_unfinalized_week(self):
        week_data = _SYNTHETIC(week=7)
        week_data["league"]["current_week"] = 7
        for m in week_data["matchups"]["matchups"]:
            for side in ("home_team", "away_team"):
                t = m.get(side)
                if isinstance(t, dict):
                    t["score"] = 0.0

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            recap_path = out / "week-7-recap.md"
            recap_path.write_text("# Week 7\n\nGhost recap body.\n", encoding="utf-8")
            weekdata_path = out / "week-7-weekdata.json"
            weekdata_path.write_text(json.dumps(week_data), encoding="utf-8")
            history_path = out / "recap_history.json"
            history_path.write_text("[]", encoding="utf-8")

            gen = RecapGenerator()
            gen.recap_history = []

            with (
                patch("src.recap_generator.OUTPUT_DIR", str(out)),
                patch("src.recap_generator.RECAP_HISTORY_FILE", str(history_path)),
            ):
                with patch("sys.stdout", StringIO()):
                    ok = gen.finalize_recap(7, force=True)
                self.assertTrue(ok)
                history = json.loads(history_path.read_text())
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["week"], 7)


if __name__ == "__main__":
    unittest.main()
