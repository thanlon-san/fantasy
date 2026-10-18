"""Tests for Sleeper ownership enrichment and start/sit swap gating."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401

from src.constants import (
    MANAGEMENT_DISASTER_GAP,
    ROASTABLE_START_PERCENTAGE,
    SIGNIFICANT_MANAGEMENT_GAP,
)
from src.ownership_stats import (
    OwnershipStats,
    compute_start_sit_swaps,
    enrich_week_data_with_ownership,
    is_management_gap_roastable,
    is_swap_roastable_by_consensus,
    team_has_roastable_bench_mistake,
)


def _player(name, position, slot, points, start_pct=-1.0):
    return {
        "name": name,
        "position": position,
        "slot": slot,
        "actual_points": points,
        "projected_points": 0.0,
        "percent_started": start_pct,
        "percent_owned": -1.0,
    }


def _team(starters, bench, management_gap=25.0):
    return {
        "team_name": "Testers",
        "owner": "tester",
        "score": 100.0,
        "management_gap": management_gap,
        "starters": starters,
        "bench": bench,
    }


class OwnershipSwapTests(unittest.TestCase):

    def test_swap_roastable_when_bench_above_threshold(self):
        self.assertTrue(
            is_swap_roastable_by_consensus(
                ROASTABLE_START_PERCENTAGE + 5,
                10.0,
            )
        )

    def test_swap_roastable_when_bench_more_consensus_than_starter(self):
        self.assertTrue(is_swap_roastable_by_consensus(40.0, 5.0))

    def test_swap_not_roastable_for_low_consensus_boom(self):
        self.assertFalse(is_swap_roastable_by_consensus(3.0, 25.0))

    def test_compute_swaps_finds_position_match(self):
        team = _team(
            starters=[_player("WR Bad", "WR", "WR", 8.0, 12.0)],
            bench=[_player("WR Good", "WR", "BN", 22.0, 85.0)],
        )
        swaps = compute_start_sit_swaps(team)
        self.assertEqual(len(swaps), 1)
        self.assertTrue(swaps[0]["roastable"])
        self.assertEqual(swaps[0]["benched_name"], "WR Good")

    def test_management_gap_roastable_requires_consensus_mistake(self):
        roastable_team = _team(
            starters=[_player("WR Bad", "WR", "WR", 8.0, 10.0)],
            bench=[_player("WR Good", "WR", "BN", 22.0, 90.0)],
            management_gap=SIGNIFICANT_MANAGEMENT_GAP + 5,
        )
        consensus_sit_team = _team(
            starters=[_player("WR Bad", "WR", "WR", 8.0, 10.0)],
            bench=[_player("WR Good", "WR", "BN", 22.0, 3.0)],
            management_gap=SIGNIFICANT_MANAGEMENT_GAP + 5,
        )
        self.assertTrue(is_management_gap_roastable(roastable_team))
        self.assertFalse(is_management_gap_roastable(consensus_sit_team))
        self.assertTrue(team_has_roastable_bench_mistake(roastable_team))


class OwnershipEnrichmentTests(unittest.TestCase):

    def test_enrich_sets_percent_started_from_sleeper_research(self):
        week_data = {
            "matchups": {
                "matchups": [
                    {
                        "home_team": _team(
                            [_player("Tyreek Hill", "WR", "WR", 10.0)],
                            [],
                        ),
                        "away_team": _team([], []),
                    }
                ]
            }
        }
        stats = OwnershipStats()
        stats.player_cache = {"tyreek hill": "1234"}
        stats._research_cache[(2026, 5, "regular")] = {
            "1234": {"started": 88.2, "owned": 99.1},
        }

        stats.enrich_week_data_players(week_data, 5, season=2026)
        player = week_data["matchups"]["matchups"][0]["home_team"]["starters"][0]
        self.assertEqual(player["percent_started"], 88.2)
        self.assertEqual(player["percent_owned"], 99.1)

    @patch("src.ownership_stats.requests.get")
    def test_enrich_degrades_when_sleeper_unavailable(self, mock_get):
        mock_get.side_effect = OSError("network down")
        week_data = {
            "matchups": {
                "matchups": [
                    {
                        "home_team": _team(
                            [_player("Anyone", "WR", "WR", 10.0, -1.0)],
                            [],
                        ),
                        "away_team": _team([], []),
                    }
                ]
            }
        }
        enrich_week_data_with_ownership(week_data, 1, OwnershipStats())
        player = week_data["matchups"]["matchups"][0]["home_team"]["starters"][0]
        self.assertEqual(player["percent_started"], -1.0)


if __name__ == "__main__":
    unittest.main()
