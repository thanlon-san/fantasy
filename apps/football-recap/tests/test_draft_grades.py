"""
Tests for :mod:`src.draft_grades` — pure formatting, no live Yahoo needed.
"""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.draft_grades import (
    build_draft_grades_context,
    group_picks_by_round,
    group_picks_by_team,
    position_counts_by_team,
)


def _synthetic_draft_results():
    picks = [
        {"round": 1, "pick": 1, "team_key": "t1", "team_name": "Beacon", "owner": "Han",
         "player_key": "p1", "player_name": "Bijan Robinson", "position": "RB"},
        {"round": 1, "pick": 2, "team_key": "t2", "team_name": "Purdy Boys", "owner": "Tyler",
         "player_key": "p2", "player_name": "CeeDee Lamb", "position": "WR"},
        {"round": 2, "pick": 3, "team_key": "t2", "team_name": "Purdy Boys", "owner": "Tyler",
         "player_key": "p3", "player_name": "Josh Allen", "position": "QB"},
        {"round": 2, "pick": 4, "team_key": "t1", "team_name": "Beacon", "owner": "Han",
         "player_key": "p4", "player_name": "Travis Kelce", "position": "TE"},
    ]
    return {"picks": picks, "total_picks": len(picks)}


class DraftGradesTests(unittest.TestCase):

    def test_group_by_team(self):
        by_team = group_picks_by_team(_synthetic_draft_results())
        self.assertEqual(set(by_team.keys()), {"Beacon", "Purdy Boys"})
        self.assertEqual(len(by_team["Beacon"]), 2)
        self.assertEqual(len(by_team["Purdy Boys"]), 2)

    def test_group_by_team_preserves_draft_order(self):
        by_team = group_picks_by_team(_synthetic_draft_results())
        names = [p["player_name"] for p in by_team["Beacon"]]
        self.assertEqual(names, ["Bijan Robinson", "Travis Kelce"])

    def test_group_by_round(self):
        by_round = group_picks_by_round(_synthetic_draft_results())
        self.assertEqual(set(by_round.keys()), {1, 2})
        self.assertEqual(len(by_round[1]), 2)

    def test_group_by_round_sorted_by_pick(self):
        by_round = group_picks_by_round(_synthetic_draft_results())
        picks_in_round_1 = [p["pick"] for p in by_round[1]]
        self.assertEqual(picks_in_round_1, sorted(picks_in_round_1))

    def test_position_counts_by_team(self):
        by_team = group_picks_by_team(_synthetic_draft_results())
        counts = position_counts_by_team(by_team)
        self.assertEqual(counts["Beacon"], {"RB": 1, "TE": 1})
        self.assertEqual(counts["Purdy Boys"], {"WR": 1, "QB": 1})

    def test_build_context_includes_all_teams_and_picks(self):
        ctx = build_draft_grades_context(_synthetic_draft_results(), league_name="Test League")
        self.assertIn("Test League", ctx)
        self.assertIn("Beacon", ctx)
        self.assertIn("Purdy Boys", ctx)
        self.assertIn("Bijan Robinson", ctx)
        self.assertIn("Josh Allen", ctx)
        self.assertIn("Round 1", ctx)
        self.assertIn("Round 2", ctx)

    def test_build_context_includes_writer_instructions(self):
        ctx = build_draft_grades_context(_synthetic_draft_results())
        self.assertIn("letter grade", ctx.lower())
        self.assertIn("do not invent", ctx.lower())

    def test_empty_draft_results_does_not_crash(self):
        ctx = build_draft_grades_context({"picks": [], "total_picks": 0})
        self.assertIn("Total picks: 0", ctx)


if __name__ == "__main__":
    unittest.main()
