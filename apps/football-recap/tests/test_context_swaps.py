"""Context builder emits SWAP lines and gates ROASTABLE management gaps."""

from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

os.environ.setdefault(
    "TREND_HISTORY_PATH", "/tmp/football_recap_test_trend_history.json"
)


class ContextSwapTests(unittest.TestCase):

    def _build(self, team):
        from src.context_builder import ContextBuilder
        from src.ownership_stats import OwnershipStats
        from src.trend_tracker import TrendTracker

        week_data = {
            "league": {"league_name": "Test League"},
            "standings": {"standings": []},
            "matchups": {
                "matchups": [
                    {
                        "matchup_id": 1,
                        "home_team": team,
                        "away_team": {
                            "team_name": "Away",
                            "owner": "away",
                            "score": 50.0,
                            "management_gap": 0.0,
                            "starters": [],
                            "bench": [],
                        },
                        "winner": team["team_name"],
                        "margin": 10.0,
                    }
                ]
            },
            "week_stats": {},
            "power_rankings": {"rankings": []},
            "next_week_matchups": {"matchups": []},
        }
        builder = ContextBuilder(
            TrendTracker(history_file=os.environ["TREND_HISTORY_PATH"]),
            OwnershipStats(),
        )
        return builder.build_context(week_data, 5)

    def test_context_includes_roastable_swap_line(self):
        team = {
            "team_name": "Home",
            "owner": "home",
            "score": 90.0,
            "management_gap": 25.0,
            "optimal_lineup": {"optimal_score": 115.0},
            "starters": [
                {
                    "name": "WR Bad",
                    "position": "WR",
                    "slot": "WR",
                    "actual_points": 5.0,
                    "projected_points": 0.0,
                    "percent_started": 12.0,
                }
            ],
            "bench": [
                {
                    "name": "WR Good",
                    "position": "WR",
                    "slot": "BN",
                    "actual_points": 24.0,
                    "projected_points": 0.0,
                    "percent_started": 70.0,
                }
            ],
        }
        ctx = self._build(team)
        self.assertIn("SWAP: benched WR Good", ctx)
        self.assertIn("ROASTABLE", ctx)
        self.assertIn("Left 25.0 points on table - ROASTABLE", ctx)

    def test_context_skips_roastable_when_consensus_sit(self):
        team = {
            "team_name": "Home",
            "owner": "home",
            "score": 90.0,
            "management_gap": 25.0,
            "optimal_lineup": {"optimal_score": 115.0},
            "starters": [
                {
                    "name": "WR Bad",
                    "position": "WR",
                    "slot": "WR",
                    "actual_points": 5.0,
                    "projected_points": 0.0,
                    "percent_started": 12.0,
                }
            ],
            "bench": [
                {
                    "name": "WR Boom",
                    "position": "WR",
                    "slot": "BN",
                    "actual_points": 24.0,
                    "projected_points": 0.0,
                    "percent_started": 4.0,
                }
            ],
        }
        ctx = self._build(team)
        self.assertIn("consensus sit", ctx)
        self.assertNotIn("Left 25.0 points on table - ROASTABLE", ctx)


if __name__ == "__main__":
    unittest.main()
