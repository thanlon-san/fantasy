"""Tests for :mod:`src.slack_recap_builder`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from src.slack_recap_builder import (
    SLACK_DIGEST_TARGET_LINES,
    _roastable_swap_line,
    build_slack_recap,
    save_slack_recap,
    snark_line_for_team,
    tier_for_rank,
    week_scores_unfinalized,
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


class SnarkVarietyTests(unittest.TestCase):

    def test_s_tier_teams_get_distinct_snark(self):
        week_data = _SYNTHETIC(week=6)
        rankings = [
            {
                "rank": 1,
                "team_name": "Alpha FC",
                "owner": "a",
                "wins": 5,
                "losses": 1,
                "pf": 700,
                "movement": "▲1",
                "heat": "steady",
            },
            {
                "rank": 2,
                "team_name": "Beta United",
                "owner": "b",
                "wins": 5,
                "losses": 1,
                "pf": 680,
                "movement": "▲2",
                "heat": "steady",
            },
            {
                "rank": 3,
                "team_name": "Gamma City",
                "owner": "c",
                "wins": 4,
                "losses": 2,
                "pf": 650,
                "movement": "—",
                "heat": "steady",
            },
        ]
        lines = [
            snark_line_for_team(row, week_data, tier="S")
            for row in rankings
        ]
        self.assertGreater(len(set(lines)), 1, msg=lines)
        self.assertFalse(all(line == lines[0] for line in lines))


class SlackRecapBuilderTests(unittest.TestCase):

    def test_build_without_recap_uses_tldr_and_rankings_not_templates(self):
        week_data = _SYNTHETIC(week=5)
        md = build_slack_recap(5, week_data, history=[])
        self.assertIn("TL;DR", md)
        self.assertIn("Power rankings", md)
        self.assertNotIn("Power tiers", md)
        self.assertNotIn("📋 Matchup recaps", md)
        self.assertIn("week-5-recap.md", md)
        self.assertIn("https://media.giphy.com/", md)
        self.assertNotIn("![GIF]", md)
        self.assertNotIn("<@U", md)
        gif_pos = md.index("https://media.giphy.com/")
        rank_pos = md.index("Power rankings")
        self.assertLess(gif_pos, rank_pos, "GIF should appear before rankings")
        self.assertLessEqual(md.count("\n"), SLACK_DIGEST_TARGET_LINES + 15)

    def test_tiers_opt_in(self):
        week_data = _SYNTHETIC(week=5)
        md = build_slack_recap(5, week_data, history=[], use_power_tiers=True)
        self.assertIn("Power tiers", md)
        self.assertNotIn("Power rankings", md)

    def test_build_with_recap_file_includes_ghost_matchups(self):
        week_data = _SYNTHETIC(week=5)
        recap_path = Path(__file__).resolve().parent.parent / "output" / "week-2-recap.md"
        if not recap_path.is_file():
            self.skipTest("week-2-recap.md not present")
        ghost = recap_path.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            fake_recap = Path(tmp) / "week-5-recap.md"
            fake_recap.write_text(ghost, encoding="utf-8")
            md = build_slack_recap(
                5,
                week_data,
                history=[],
                full_recap_path=str(fake_recap),
            )
        self.assertIn("League Pulse", md)
        self.assertIn("157.78", md)
        self.assertNotIn("📋 Matchup recaps", md)
        self.assertNotIn("Power rankings", md)

    def test_roastable_swap_line_absent_for_chalk_bust(self):
        week_data = _SYNTHETIC(week=5)
        home = week_data["matchups"]["matchups"][0]["home_team"]
        home["starters"] = [
            {
                "name": "Christian Watson",
                "position": "WR",
                "slot": "WR",
                "actual_points": 0.0,
                "percent_started": 94.9,
            }
        ]
        home["bench"] = [
            {
                "name": "Keenan Allen",
                "position": "WR",
                "slot": "BN",
                "actual_points": 16.2,
                "percent_started": 24.9,
            }
        ]
        self.assertIsNone(_roastable_swap_line(week_data))

    def test_unfinalized_week_shows_banner_and_skips_zero_superlative(self):
        week_data = _SYNTHETIC(week=7)
        week_data["league"]["current_week"] = 7
        for team in week_data["matchups"]["matchups"][0].values():
            if isinstance(team, dict) and "score" in team:
                team["score"] = 0.0
        md = build_slack_recap(7, week_data, history=[])
        self.assertIn("not finalized on Yahoo", md)
        self.assertIn("Matchups still in progress", md)
        self.assertTrue(week_scores_unfinalized(7, week_data))

    def test_save_writes_slack_file(self):
        week_data = _SYNTHETIC(week=3)
        with tempfile.TemporaryDirectory() as tmp:
            path = save_slack_recap(3, week_data, output_dir=tmp, history=[])
            self.assertTrue(Path(path).is_file())
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("Week 3", text)

    def test_full_recap_link_when_file_exists(self):
        week_data = _SYNTHETIC(week=4)
        minimal_recap = (
            "**:heart-8bit: League Pulse**\nPulse.\n\n"
            "**:confused-math-lady: Stat of the Week**\nStat.\n\n"
            "**:right-facing_fist: Matchups :left-facing_fist:**\n"
            "**Team A (100) def. Team B (90)**\nBurn line.\n\n"
            "**:power-up: Power Rankings**\n1. foo\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            recap = Path(tmp) / "week-4-recap.md"
            recap.write_text(minimal_recap, encoding="utf-8")
            md = build_slack_recap(
                4,
                week_data,
                history=[],
                full_recap_path=str(recap),
            )
            self.assertIn("week-4-recap.md", md)
            self.assertIn("Full recap", md)
            self.assertIn("Burn line", md)


if __name__ == "__main__":
    unittest.main()
