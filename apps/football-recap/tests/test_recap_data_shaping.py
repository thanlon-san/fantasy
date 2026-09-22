"""
End-to-end shaping tests: ``week_data`` -> ``ContextBuilder`` -> LLM context string.

Uses the synthetic-data helper from :mod:`scripts.validate_pipeline` so this
suite exercises exactly the same path the real Yahoo fetcher feeds into,
without any network calls. If a regression breaks the shape contract between
the fetcher and the context builder, these tests catch it.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


# Ensure the trend_tracker's history file lives in a temp dir so tests
# don't leave junk in the repo root.
os.environ.setdefault("TREND_HISTORY_PATH", "/tmp/football_recap_test_trend_history.json")


def _load_synthetic():
    # validate_pipeline.py lives at apps/football-recap/scripts/validate_pipeline.py.
    # Rather than import as a module (which would trip on its top-level path
    # setup), exec it in a controlled namespace and grab the helper.
    tests_dir = Path(__file__).resolve().parent
    scripts_dir = tests_dir.parent / "scripts"
    script_path = scripts_dir / "validate_pipeline.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_football_recap_validate_pipeline", script_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.synthetic_week_data


# Load once at import time; store outside the TestCase to avoid Python's
# implicit "bound-method" wrapping of class-attribute functions.
_SYNTHETIC = _load_synthetic()


class RecapDataShapingTests(unittest.TestCase):

    def _context_for(self, week: int = 5) -> str:
        wd = _SYNTHETIC(week=week)
        # Fresh trend tracker per invocation — no cross-test bleed.
        from src.context_builder import ContextBuilder
        from src.ownership_stats import OwnershipStats
        from src.trend_tracker import TrendTracker
        tracker = TrendTracker(history_file="/tmp/football_recap_test_trend_history.json")
        ownership = OwnershipStats()
        builder = ContextBuilder(tracker, ownership)
        return builder.build_context(wd, week)

    # ---- shape assertions -------------------------------------------------

    def test_context_starts_with_week_header(self):
        ctx = self._context_for(week=5)
        self.assertTrue(ctx.startswith("# Week 5 Recap Data"), ctx[:200])

    def test_context_includes_league_name(self):
        ctx = self._context_for(week=5)
        self.assertIn("CX Retention Fantasy Football", ctx)

    def test_context_lists_both_teams(self):
        ctx = self._context_for(week=5)
        self.assertIn("Beacon", ctx)
        self.assertIn("Purdy Boys", ctx)

    def test_context_includes_next_week_preview(self):
        ctx = self._context_for(week=5)
        self.assertIn("Week 6 Preview", ctx)

    def test_context_includes_engagement_sections(self):
        ctx = self._context_for(week=5)
        self.assertIn("Weekly Superlatives", ctx)
        self.assertIn("GIF of the Week", ctx)
        self.assertIn("media.giphy.com", ctx)

    def test_bench_hero_award_is_named_by_bench_stud(self):
        # Synthetic home-team bench includes "Bench Stud" at 22.8 pts →
        # sits above the 20-pt bench-hero threshold and should be surfaced.
        ctx = self._context_for(week=5)
        self.assertIn("Bench Stud", ctx)
        self.assertIn("Bench Hero of the Week", ctx)

    def test_context_is_meaningfully_sized(self):
        # If we ever accidentally short-circuit the context builder the string
        # collapses to a few hundred chars. Fail fast on that regression.
        ctx = self._context_for(week=5)
        self.assertGreater(len(ctx), 1500, f"Context too small: {len(ctx)} chars")

    def test_different_week_reflects_in_header(self):
        ctx = self._context_for(week=9)
        self.assertIn("Week 9 Recap Data", ctx)
        self.assertIn("Week 10 Preview", ctx)

    def test_context_includes_power_rankings_canonical_order(self):
        ctx = self._context_for(week=5)
        self.assertIn("Power Rankings", ctx)
        lowered = ctx.lower()
        self.assertIn("do not", lowered)
        self.assertTrue(
            "do not reorder or invent" in lowered
            or "do not invent or reorder" in lowered,
            ctx[ctx.find("Power Rankings"):ctx.find("Power Rankings") + 400]
            if "Power Rankings" in ctx
            else ctx[:400],
        )

    def test_context_prefers_live_yahoo_team_name(self):
        from src.context_builder import ContextBuilder, _owner_for
        from src.ownership_stats import OwnershipStats
        from src.trend_tracker import TrendTracker

        wd = _SYNTHETIC(week=5)
        wd["matchups"]["matchups"][0]["home_team"]["team_name"] = "Renamed In Yahoo"
        wd["matchups"]["matchups"][0]["home_team"]["owner"] = "Han"
        tracker = TrendTracker(history_file="/tmp/football_recap_test_trend_history.json")
        builder = ContextBuilder(tracker, OwnershipStats())
        ctx = builder.build_context(wd, 5)
        self.assertIn("Renamed In Yahoo", ctx)
        self.assertEqual(_owner_for({"team_name": "Renamed In Yahoo", "owner": "Han"}), "Han")


if __name__ == "__main__":
    unittest.main()
