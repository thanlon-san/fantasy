"""
Threshold-boundary tests for :mod:`src.superlatives`.

Each test builds a minimal ``week_data`` payload targeting one award so a
regression in a single threshold is easy to pinpoint. Every assertion pins
either a threshold boundary or a "does not fire" negative case.
"""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401  (side-effect: sys.path)

from src import superlatives as sup
from src.constants import MANAGEMENT_DISASTER_GAP


def _team(
    name: str,
    *,
    score: float,
    owner: str = "manager",
    projected: float = 100.0,
    management_gap: float = 10.0,
    bench: list | None = None,
) -> dict:
    starters = [{"projected_points": projected, "actual_points": score, "position": "QB", "name": "QB1"}]
    return {
        "team_name": name,
        "owner": owner,
        "score": score,
        "management_gap": management_gap,
        "starters": starters,
        "bench": bench or [],
    }


def _matchup(home: dict, away: dict, matchup_id: int = 1) -> dict:
    return {"matchup_id": matchup_id, "home_team": home, "away_team": away}


def _week_data(*matchups) -> dict:
    return {"matchups": {"matchups": list(matchups)}}


class SuperlativesTests(unittest.TestCase):

    def test_empty_week_data_returns_empty_awards(self):
        self.assertEqual(sup.compute_superlatives({}), {})
        self.assertEqual(sup.compute_superlatives({"matchups": {"matchups": []}}), {})

    def test_blowout_fires_at_threshold(self):
        # Margin exactly 30 → BLOWOUT_MARGIN >= 30 fires.
        wd = _week_data(_matchup(_team("A", score=130), _team("B", score=100)))
        awards = sup.compute_superlatives(wd)
        self.assertIn("blowout_of_the_week", awards)
        self.assertEqual(awards["blowout_of_the_week"]["team"], "A")
        self.assertEqual(awards["blowout_of_the_week"]["opponent"], "B")
        self.assertEqual(awards["blowout_of_the_week"]["margin"], 30.0)

    def test_blowout_does_not_fire_below_threshold(self):
        # Margin 29.9 → no blowout.
        wd = _week_data(_matchup(_team("A", score=129.9), _team("B", score=100)))
        self.assertNotIn("blowout_of_the_week", sup.compute_superlatives(wd))

    def test_nailbiter_fires_when_margin_under_five(self):
        wd = _week_data(_matchup(_team("A", score=100.0), _team("B", score=97.0)))
        awards = sup.compute_superlatives(wd)
        self.assertIn("nailbiter_of_the_week", awards)
        self.assertEqual(awards["nailbiter_of_the_week"]["margin"], 3.0)

    def test_nailbiter_does_not_fire_at_exact_boundary(self):
        # Margin exactly 5.0 → NAILBITER_MARGIN uses strict < so 5.0 is out.
        wd = _week_data(_matchup(_team("A", score=105.0), _team("B", score=100.0)))
        self.assertNotIn("nailbiter_of_the_week", sup.compute_superlatives(wd))

    def test_shootout_fires_above_combined_threshold(self):
        wd = _week_data(_matchup(_team("A", score=130.0), _team("B", score=125.0)))
        awards = sup.compute_superlatives(wd)
        self.assertIn("shootout_of_the_week", awards)
        self.assertEqual(awards["shootout_of_the_week"]["combined"], 255.0)

    def test_cold_war_fires_below_combined_threshold(self):
        wd = _week_data(_matchup(_team("A", score=80.0), _team("B", score=85.0)))
        awards = sup.compute_superlatives(wd)
        self.assertIn("cold_war_of_the_week", awards)
        self.assertEqual(awards["cold_war_of_the_week"]["combined"], 165.0)

    def test_coach_of_the_week_picks_smallest_management_gap(self):
        home = _team("A", score=110.0, management_gap=2.0, owner="anna")
        away = _team("B", score=105.0, management_gap=1.0, owner="ben")
        awards = sup.compute_superlatives(_week_data(_matchup(home, away)))
        self.assertIn("coach_of_the_week", awards)
        # Both < 3.0 gap so both qualify; smallest wins.
        self.assertEqual(awards["coach_of_the_week"]["team"], "B")
        self.assertEqual(awards["coach_of_the_week"]["owner"], "ben")

    def test_coach_of_the_week_ignores_zero_scores(self):
        # Zero-score teams are usually preseason placeholders / byes; excluded.
        home = _team("A", score=0.0, management_gap=0.0)
        away = _team("B", score=100.0, management_gap=15.0)
        awards = sup.compute_superlatives(_week_data(_matchup(home, away)))
        self.assertNotIn("coach_of_the_week", awards)

    def test_cooked_picks_biggest_management_gap_with_roastable_swap(self):
        roastable_bench = [
            {
                "name": "Stud",
                "position": "WR",
                "slot": "BN",
                "actual_points": 28.0,
                "percent_started": 80.0,
            }
        ]
        home_starters = [
            {
                "name": "Bust",
                "position": "WR",
                "slot": "WR",
                "actual_points": 6.0,
                "percent_started": 15.0,
                "projected_points": 10.0,
            }
        ]
        home = {
            "team_name": "A",
            "owner": "anna",
            "score": 90.0,
            "management_gap": MANAGEMENT_DISASTER_GAP + 2.0,
            "starters": home_starters,
            "bench": roastable_bench,
        }
        away = _team("B", score=100.0, management_gap=MANAGEMENT_DISASTER_GAP + 1.0)
        awards = sup.compute_superlatives(_week_data(_matchup(home, away)))
        self.assertIn("cooked_of_the_week", awards)
        self.assertEqual(awards["cooked_of_the_week"]["team"], "A")
        self.assertEqual(
            awards["cooked_of_the_week"]["management_gap"],
            MANAGEMENT_DISASTER_GAP + 2.0,
        )

    def test_cooked_does_not_fire_for_consensus_sit_bench_boom(self):
        home = {
            "team_name": "A",
            "owner": "anna",
            "score": 90.0,
            "management_gap": MANAGEMENT_DISASTER_GAP + 5.0,
            "starters": [
                {
                    "name": "Bust",
                    "position": "WR",
                    "slot": "WR",
                    "actual_points": 6.0,
                    "percent_started": 15.0,
                    "projected_points": 10.0,
                }
            ],
            "bench": [
                {
                    "name": "Sleeper",
                    "position": "WR",
                    "slot": "BN",
                    "actual_points": 28.0,
                    "percent_started": 2.0,
                }
            ],
        }
        away = _team("B", score=100.0)
        self.assertNotIn(
            "cooked_of_the_week",
            sup.compute_superlatives(_week_data(_matchup(home, away))),
        )

    def test_bench_hero_reports_top_bench_scorer(self):
        bench = [
            {"name": "Cousins", "position": "QB", "actual_points": 15.0},
            {"name": "Studski", "position": "WR", "actual_points": 28.4},
            {"name": "Meh", "position": "TE", "actual_points": 3.1},
        ]
        home = _team("A", score=90.0, bench=bench)
        away = _team("B", score=100.0)
        awards = sup.compute_superlatives(_week_data(_matchup(home, away)))
        self.assertIn("bench_hero_of_the_week", awards)
        entry = awards["bench_hero_of_the_week"]
        self.assertEqual(entry["player"], "Studski")
        self.assertEqual(entry["position"], "WR")
        self.assertEqual(entry["points"], 28.4)
        self.assertEqual(entry["team"], "A")

    def test_upset_fires_when_winner_projected_much_lower(self):
        # Away team projected 20 lower than home; away wins outright.
        home_starters = [{"projected_points": 130.0, "actual_points": 100.0, "position": "QB", "name": "QB1"}]
        away_starters = [{"projected_points": 110.0, "actual_points": 120.0, "position": "QB", "name": "QB2"}]
        home = {"team_name": "H", "owner": "h", "score": 100.0, "management_gap": 10, "starters": home_starters, "bench": []}
        away = {"team_name": "A", "owner": "a", "score": 120.0, "management_gap": 10, "starters": away_starters, "bench": []}
        awards = sup.compute_superlatives(_week_data(_matchup(home, away)))
        self.assertIn("upset_of_the_week", awards)
        self.assertEqual(awards["upset_of_the_week"]["winner"], "A")
        self.assertEqual(awards["upset_of_the_week"]["projection_gap"], 20.0)

    def test_upset_does_not_fire_when_projection_gap_below_threshold(self):
        # 14-point projection gap → below UPSET_PROJECTION_DIFF (15).
        home_starters = [{"projected_points": 124.0, "actual_points": 100.0, "position": "QB", "name": "QB1"}]
        away_starters = [{"projected_points": 110.0, "actual_points": 120.0, "position": "QB", "name": "QB2"}]
        home = {"team_name": "H", "owner": "h", "score": 100.0, "management_gap": 10, "starters": home_starters, "bench": []}
        away = {"team_name": "A", "owner": "a", "score": 120.0, "management_gap": 10, "starters": away_starters, "bench": []}
        awards = sup.compute_superlatives(_week_data(_matchup(home, away)))
        self.assertNotIn("upset_of_the_week", awards)


if __name__ == "__main__":
    unittest.main()
