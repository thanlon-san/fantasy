"""Tests for :mod:`src.slack_recap_builder`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from src.slack_recap_builder import (
    build_slack_recap,
    save_slack_recap,
    tier_for_rank,
)


def _load_synthetic():
    tests_dir = Path(__file__).resolve().parent
    script_path = tests_dir.parent / "scripts" / "validate_pipeline.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("_validate_pipeline", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.synthetic_week_data


_SYNTHETIC = _load_synthetic()


class TierMappingTests(unittest.TestCase):

    def test_six_teams_spread_across_tiers(self):
        tiers = {tier_for_rank(r, 6) for r in range(1, 7)}
        self.assertEqual(tiers, {"S", "A", "B", "C", "D", "F"})

    def test_rank_one_is_s(self):
        self.assertEqual(tier_for_rank(1, 14), "S")


class SlackRecapBuilderTests(unittest.TestCase):

    def test_build_includes_tldr_tiers_gif(self):
        week_data = _SYNTHETIC(week=5)
        md = build_slack_recap(5, week_data, history=[])
        self.assertIn("TL;DR", md)
        self.assertIn("Power tiers", md)
        self.assertIn("![GIF](https://media.giphy.com/", md)
        self.assertLessEqual(md.count("\n"), 40)

    def test_save_writes_slack_file(self):
        week_data = _SYNTHETIC(week=3)
        with tempfile.TemporaryDirectory() as tmp:
            path = save_slack_recap(3, week_data, output_dir=tmp, history=[])
            self.assertTrue(Path(path).is_file())
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("Week 3", text)

    def test_full_recap_link_when_file_exists(self):
        week_data = _SYNTHETIC(week=4)
        with tempfile.TemporaryDirectory() as tmp:
            recap = Path(tmp) / "week-4-recap.md"
            recap.write_text("# long recap\n", encoding="utf-8")
            md = build_slack_recap(
                4,
                week_data,
                history=[],
                full_recap_path=str(recap),
            )
            self.assertIn("week-4-recap.md", md)


if __name__ == "__main__":
    unittest.main()
