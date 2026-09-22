"""Unit tests for :mod:`src.power_rankings` — no Yahoo required."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from src.power_rankings import (
    EARLY_WEIGHTS,
    LATE_WEIGHTS,
    compute_power_rankings,
    format_movement,
    heat_from_ranks,
    load_ranking_inputs,
    prior_rankings_reliable,
    reconcile_prior_rankings,
    weights_for_week,
)


def _team(
    team_id: int,
    name: str,
    *,
    wins: int,
    losses: int,
    pf: float,
    pa: float,
    owner: str = "",
    ties: int = 0,
) -> dict:
    return {
        "team_id": team_id,
        "team_name": name,
        "owner": owner or name,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "points_for": pf,
        "points_against": pa,
        "point_differential": round(pf - pa, 2),
    }


def _matchup(home: dict, away: dict, home_score: float, away_score: float) -> dict:
    winner = home["team_name"] if home_score >= away_score else away["team_name"]
    return {
        "home_team": {**home, "score": home_score},
        "away_team": {**away, "score": away_score},
        "winner": winner,
        "margin": abs(home_score - away_score),
    }


def _names_in_order(payload: dict) -> list:
    return [r["team_name"] for r in payload["rankings"]]


def _row(payload: dict, name: str) -> dict:
    for r in payload["rankings"]:
        if r["team_name"] == name:
            return r
    raise AssertionError(f"{name} missing from {payload['rankings']}")


# High-PF loser vs low-PF winner — used for early vs late weight tests.
_WINNER = _team(1, "Winner", wins=1, losses=0, pf=80.0, pa=70.0, owner="A")
_LOSER = _team(2, "Loser", wins=0, losses=1, pf=150.0, pa=160.0, owner="B")


class WeightsTests(unittest.TestCase):

    def test_early_week_weights(self):
        for week in (1, 2, 3):
            self.assertEqual(weights_for_week(week), EARLY_WEIGHTS)
        self.assertEqual(EARLY_WEIGHTS, (0.20, 0.70, 0.10))

    def test_late_week_weights(self):
        for week in (4, 5, 14):
            self.assertEqual(weights_for_week(week), LATE_WEIGHTS)
        self.assertEqual(LATE_WEIGHTS, (0.45, 0.50, 0.05))


class EarlyVsLateRankingTests(unittest.TestCase):

    def test_early_week_prefers_points_for(self):
        # Week 2: 70% PF. The 0-1 / 150-PF team should outrank 1-0 / 80-PF.
        payload = compute_power_rankings(2, [_WINNER, _LOSER])
        self.assertEqual(_names_in_order(payload), ["Loser", "Winner"])

    def test_late_week_prefers_win_pct(self):
        # Week 5, no L3 history → 100% season with late weights (45% W%).
        payload = compute_power_rankings(5, [_WINNER, _LOSER])
        self.assertEqual(_names_in_order(payload), ["Winner", "Loser"])


class L3BlendTests(unittest.TestCase):

    def setUp(self):
        # Season: Alpha is clearly ahead. L3: Bravo has been on a tear.
        self.alpha = _team(1, "Alpha", wins=3, losses=1, pf=480.0, pa=450.0, owner="Al")
        self.bravo = _team(2, "Bravo", wins=2, losses=2, pf=470.0, pa=460.0, owner="Bo")
        self.standings = [self.alpha, self.bravo]
        # Last 3 weeks of box scores: Bravo blows Alpha out every time.
        self.current = {
            "week": 5,
            "matchups": [_matchup(self.alpha, self.bravo, 80.0, 150.0)],
        }
        self.history = [
            {"week": 4, "matchups": [_matchup(self.alpha, self.bravo, 90.0, 140.0)]},
            {"week": 3, "matchups": [_matchup(self.alpha, self.bravo, 70.0, 130.0)]},
        ]

    def test_week_5_without_history_is_season_only(self):
        payload = compute_power_rankings(5, self.standings)
        self.assertEqual(_names_in_order(payload), ["Alpha", "Bravo"])
        self.assertEqual(_row(payload, "Alpha")["heat"], "steady")
        self.assertEqual(_row(payload, "Bravo")["heat"], "steady")

    def test_week_5_with_history_blends_l3(self):
        payload = compute_power_rankings(
            5,
            self.standings,
            current_matchups=self.current,
            historical_matchups=self.history,
        )
        # Bravo's L3 dominance flips the blended order.
        self.assertEqual(_names_in_order(payload), ["Bravo", "Alpha"])

    def test_week_3_ignores_l3_even_when_history_exists(self):
        payload = compute_power_rankings(
            3,
            self.standings,
            current_matchups=self.current,
            historical_matchups=self.history,
        )
        self.assertEqual(_names_in_order(payload), ["Alpha", "Bravo"])
        self.assertEqual(_row(payload, "Alpha")["heat"], "steady")
        self.assertEqual(_row(payload, "Bravo")["heat"], "steady")

    def test_heat_from_two_spot_l3_swing(self):
        # Three teams so a team can jump season #3 → L3 #1 (threshold is 2).
        alpha = _team(1, "Alpha", wins=4, losses=0, pf=520.0, pa=400.0, owner="Al")
        charlie = _team(3, "Charlie", wins=2, losses=2, pf=460.0, pa=450.0, owner="Ch")
        bravo = _team(2, "Bravo", wins=0, losses=4, pf=350.0, pa=520.0, owner="Bo")
        current = {"week": 5, "matchups": [_matchup(alpha, bravo, 70.0, 160.0)]}
        history = [
            {"week": 4, "matchups": [_matchup(alpha, charlie, 80.0, 130.0)]},
            {"week": 3, "matchups": [_matchup(bravo, charlie, 150.0, 90.0)]},
        ]
        payload = compute_power_rankings(
            5,
            [alpha, bravo, charlie],
            current_matchups=current,
            historical_matchups=history,
        )
        self.assertEqual(_row(payload, "Bravo")["heat"], "surging")
        self.assertEqual(_row(payload, "Alpha")["heat"], "sliding")
        self.assertEqual(_row(payload, "Charlie")["heat"], "steady")


class MovementTests(unittest.TestCase):

    def test_format_movement_arrows(self):
        self.assertEqual(format_movement(1, 3), "▲2")
        self.assertEqual(format_movement(4, 3), "▼1")
        self.assertEqual(format_movement(2, 2), "—")
        self.assertEqual(format_movement(1, None), "—")

    def test_movement_wired_from_prior_rankings_by_team_id(self):
        standings = [
            _team(1, "Alpha", wins=2, losses=0, pf=200.0, pa=150.0),
            _team(2, "Bravo", wins=0, losses=2, pf=120.0, pa=170.0),
        ]
        # Last week Bravo was #1; this week Alpha is #1.
        prior = [
            {"rank": 1, "team_id": 2, "team_name": "Bravo"},
            {"rank": 2, "team_id": 1, "team_name": "Alpha"},
        ]
        payload = compute_power_rankings(2, standings, prior_rankings=prior)
        self.assertEqual(_row(payload, "Alpha")["movement"], "▲1")
        self.assertEqual(_row(payload, "Alpha")["previous_rank"], 2)
        self.assertEqual(_row(payload, "Bravo")["movement"], "▼1")
        self.assertEqual(_row(payload, "Bravo")["previous_rank"], 1)

    def test_movement_falls_back_to_team_name(self):
        standings = [_team(0, "Alpha", wins=1, losses=0, pf=100.0, pa=80.0)]
        prior = [{"rank": 3, "team_name": "Alpha"}]
        payload = compute_power_rankings(1, standings, prior_rankings=prior)
        self.assertEqual(_row(payload, "Alpha")["movement"], "▲2")
        self.assertEqual(_row(payload, "Alpha")["previous_rank"], 3)

    def test_no_prior_is_em_dash(self):
        standings = [_team(1, "Alpha", wins=1, losses=0, pf=100.0, pa=80.0)]
        payload = compute_power_rankings(1, standings)
        self.assertEqual(_row(payload, "Alpha")["movement"], "—")
        self.assertIsNone(_row(payload, "Alpha")["previous_rank"])


class HeatTests(unittest.TestCase):

    def test_surging_sliding_steady(self):
        self.assertEqual(heat_from_ranks(4, 1), "surging")
        self.assertEqual(heat_from_ranks(1, 3), "sliding")
        self.assertEqual(heat_from_ranks(3, 2), "steady")
        self.assertEqual(heat_from_ranks(2, 2), "steady")
        self.assertEqual(heat_from_ranks(1, None), "steady")
        self.assertEqual(heat_from_ranks(None, 1), "steady")


class PriorRankingsReliabilityTests(unittest.TestCase):

    def test_unreliable_when_all_zeros(self):
        junk = [{"rank": 1, "team_id": 1, "wins": 0, "losses": 0, "pf": 0.0}]
        self.assertFalse(prior_rankings_reliable(junk))

    def test_reliable_when_pf_present(self):
        rows = [{"rank": 1, "team_id": 1, "wins": 0, "losses": 0, "pf": 120.0}]
        self.assertTrue(prior_rankings_reliable(rows))

    def test_reconcile_recomputes_from_week_one_matchups(self):
        winner = {"team_id": 1, "team_name": "Alpha", "owner": "A"}
        loser = {"team_id": 2, "team_name": "Bravo", "owner": "B"}
        history = [{
            "week": 1,
            "context": {
                "data": {
                    "power_rankings": {
                        "rankings": [
                            {"rank": 1, "team_id": 2, "team_name": "Bravo", "wins": 0, "losses": 0, "pf": 0.0},
                            {"rank": 2, "team_id": 1, "team_name": "Alpha", "wins": 0, "losses": 0, "pf": 0.0},
                        ]
                    },
                    "matchups": {
                        "week": 1,
                        "matchups": [_matchup(winner, loser, 130.0, 90.0)],
                    },
                }
            },
        }]
        prior = reconcile_prior_rankings(2, history[0]["context"]["data"]["power_rankings"]["rankings"], history=history)
        self.assertEqual(_names_in_order({"rankings": prior}), ["Alpha", "Bravo"])


class HistoryLoaderTests(unittest.TestCase):

    def test_prefers_history_over_weekdata_file(self):
        history_rankings = [
            {"rank": 1, "team_id": 1, "team_name": "FromHistory"},
        ]
        file_rankings = [
            {"rank": 1, "team_id": 1, "team_name": "FromFile"},
        ]
        history = [{
            "week": 4,
            "context": {
                "data": {
                    "power_rankings": {"rankings": history_rankings},
                    "matchups": {
                        "week": 4,
                        "matchups": [_matchup(
                            {"team_id": 1, "team_name": "FromHistory"},
                            {"team_id": 2, "team_name": "Other"},
                            100.0,
                            90.0,
                        )],
                    },
                }
            },
        }]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "week-4-weekdata.json").write_text(json.dumps({
                "power_rankings": {"rankings": file_rankings},
                "matchups": {"week": 4, "matchups": []},
            }))
            prior, historical = load_ranking_inputs(
                5, history=history, output_dir=output_dir
            )
        self.assertEqual(prior[0]["team_name"], "FromHistory")
        self.assertEqual(len(historical), 1)
        self.assertEqual(len(historical[0]["matchups"]), 1)

    def test_falls_back_to_weekdata_file(self):
        file_rankings = [
            {"rank": 2, "team_id": 9, "team_name": "FromFile"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "week-6-weekdata.json").write_text(json.dumps({
                "power_rankings": {"rankings": file_rankings},
                "matchups": {
                    "week": 6,
                    "matchups": [_matchup(
                        {"team_id": 9, "team_name": "FromFile"},
                        {"team_id": 8, "team_name": "Other"},
                        110.0,
                        95.0,
                    )],
                },
            }))
            prior, historical = load_ranking_inputs(
                7, history=[], output_dir=output_dir
            )
        self.assertEqual(prior[0]["team_name"], "FromFile")
        self.assertEqual(len(historical), 1)

    def test_empty_history_week_1_returns_nothing(self):
        prior, historical = load_ranking_inputs(1, history=[], output_dir=None)
        self.assertEqual(prior, [])
        self.assertEqual(historical, [])


if __name__ == "__main__":
    unittest.main()
