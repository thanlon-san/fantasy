"""
Tests for :mod:`src.season_leaderboard` — season-long award aggregation.
"""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.season_leaderboard import compute_season_awards


def _team(name, *, score, owner="mgr", management_gap=10.0, bench=None):
    return {
        "team_name": name,
        "owner": owner,
        "score": score,
        "management_gap": management_gap,
        "bench": bench or [],
    }


def _week_entry(week, home, away, superlatives=None):
    return {
        "week": week,
        "context": {
            "data": {
                "matchups": {"matchups": [{"home_team": home, "away_team": away}]},
                "superlatives": superlatives or {},
            }
        },
    }


class SeasonLeaderboardTests(unittest.TestCase):

    def test_no_history_returns_empty(self):
        result = compute_season_awards([])
        self.assertEqual(result["weeks_played"], 0)
        self.assertEqual(result["awards"], {})

    def test_ignores_entries_without_week_data(self):
        history = [{"week": 1, "context": {"format": "V3"}}]  # no "data" key
        result = compute_season_awards(history)
        self.assertEqual(result["weeks_played"], 0)

    def test_bench_whisperer_picks_highest_cumulative_gap(self):
        history = [
            _week_entry(
                1,
                _team("A", score=100, management_gap=20.0),
                _team("B", score=90, management_gap=5.0),
            ),
            _week_entry(
                2,
                _team("A", score=95, management_gap=15.0),
                _team("B", score=100, management_gap=8.0),
            ),
        ]
        awards = compute_season_awards(history)["awards"]
        self.assertIn("bench_whisperer", awards)
        self.assertEqual(awards["bench_whisperer"]["team"], "A")
        self.assertEqual(awards["bench_whisperer"]["total_points_left"], 35.0)

    def test_iron_fist_picks_lowest_average_gap(self):
        history = [
            _week_entry(
                1,
                _team("A", score=100, management_gap=20.0),
                _team("B", score=90, management_gap=2.0),
            ),
            _week_entry(
                2,
                _team("A", score=95, management_gap=15.0),
                _team("B", score=100, management_gap=1.0),
            ),
        ]
        awards = compute_season_awards(history)["awards"]
        self.assertIn("iron_fist", awards)
        self.assertEqual(awards["iron_fist"]["team"], "B")
        self.assertAlmostEqual(awards["iron_fist"]["avg_points_left"], 1.5)

    def test_nail_biter_of_season_picks_smallest_margin_across_weeks(self):
        history = [
            _week_entry(1, _team("A", score=110), _team("B", score=80)),  # margin 30
            _week_entry(2, _team("C", score=100), _team("D", score=98)),  # margin 2
        ]
        awards = compute_season_awards(history)["awards"]
        self.assertIn("nail_biter_of_the_season", awards)
        self.assertEqual(awards["nail_biter_of_the_season"]["margin"], 2.0)
        self.assertEqual(awards["nail_biter_of_the_season"]["week"], 2)

    def test_blowout_of_season_picks_largest_margin_across_weeks(self):
        history = [
            _week_entry(1, _team("A", score=110), _team("B", score=80)),  # margin 30
            _week_entry(2, _team("C", score=100), _team("D", score=98)),  # margin 2
        ]
        awards = compute_season_awards(history)["awards"]
        self.assertIn("blowout_of_the_season", awards)
        self.assertEqual(awards["blowout_of_the_season"]["margin"], 30.0)
        self.assertEqual(awards["blowout_of_the_season"]["winner"], "A")

    def test_iron_stomach_counts_low_score_weeks(self):
        history = [
            _week_entry(1, _team("A", score=110), _team("B", score=80)),
            _week_entry(2, _team("A", score=90), _team("B", score=70)),
        ]
        awards = compute_season_awards(history)["awards"]
        self.assertIn("iron_stomach", awards)
        self.assertEqual(awards["iron_stomach"]["team"], "B")
        self.assertEqual(awards["iron_stomach"]["count"], 2)

    def test_bench_hero_tally_across_weeks(self):
        history = [
            _week_entry(
                1,
                _team("A", score=100),
                _team("B", score=90),
                superlatives={
                    "bench_hero_of_the_week": {"team": "A", "owner": "mgr-a"}
                },
            ),
            _week_entry(
                2,
                _team("A", score=95),
                _team("B", score=88),
                superlatives={
                    "bench_hero_of_the_week": {"team": "A", "owner": "mgr-a"}
                },
            ),
        ]
        awards = compute_season_awards(history)["awards"]
        self.assertIn("human_highlight_reel", awards)
        self.assertEqual(awards["human_highlight_reel"]["team"], "A")
        self.assertEqual(awards["human_highlight_reel"]["count"], 2)

    def test_weeks_played_counts_entries_with_data(self):
        history = [
            _week_entry(1, _team("A", score=100), _team("B", score=90)),
            _week_entry(2, _team("A", score=95), _team("B", score=88)),
            {"week": 3, "context": {}},  # no data — should be excluded
        ]
        result = compute_season_awards(history)
        self.assertEqual(result["weeks_played"], 2)


if __name__ == "__main__":
    unittest.main()
