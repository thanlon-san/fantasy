"""
Tests for :mod:`src.canvas_builder` — League HQ Canvas markdown.
"""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.canvas_builder import (
    build_league_hq_canvas_markdown,
    build_preseason_league_hq_canvas_markdown,
)
from src.constants import DRAFT_ORDER_2026, PRESEASON_MANAGERS_2026, TEAM_OWNERS, resolve_owner


def _week_data():
    return {
        "league": {"league_name": "CX Retention Fantasy Football"},
        "standings": {
            "standings": [
                {
                    "rank": 1,
                    "team_name": "Beacon",
                    "owner": "Han Jang",
                    "wins": 5,
                    "losses": 1,
                    "ties": 0,
                    "points_for": 620.4,
                    "points_against": 540.1,
                },
                {
                    "rank": 2,
                    "team_name": "Purdy Boys",
                    "owner": "tyler.hanlon",
                    "wins": 4,
                    "losses": 2,
                    "ties": 0,
                    "points_for": 590.2,
                    "points_against": 550.0,
                },
            ]
        },
        "power_rankings": {
            "rankings": [
                {
                    "rank": 1,
                    "team_name": "Beacon",
                    "owner": "Han Jang",
                    "wins": 5,
                    "losses": 1,
                    "ties": 0,
                    "pf": 620.4,
                    "movement": "▲1",
                },
                {
                    "rank": 2,
                    "team_name": "Purdy Boys",
                    "owner": "tyler.hanlon",
                    "wins": 4,
                    "losses": 2,
                    "ties": 0,
                    "pf": 590.2,
                    "movement": "▼1",
                },
            ]
        },
    }


class CanvasBuilderTests(unittest.TestCase):

    def test_includes_league_name_and_week(self):
        md = build_league_hq_canvas_markdown(_week_data(), {"weeks_played": 3, "awards": {}}, week=5)
        self.assertIn("CX Retention Fantasy Football", md)
        self.assertIn("Week 5", md)

    def test_includes_standings_table(self):
        md = build_league_hq_canvas_markdown(_week_data(), {"weeks_played": 3, "awards": {}}, week=5)
        self.assertIn("Beacon", md)
        self.assertIn("Purdy Boys", md)
        self.assertIn("Standings", md)

    def test_includes_power_rankings(self):
        md = build_league_hq_canvas_markdown(_week_data(), {"weeks_played": 3, "awards": {}}, week=5)
        self.assertIn("Power Rankings", md)

    def test_includes_season_awards_when_present(self):
        awards = {
            "weeks_played": 5,
            "awards": {
                "iron_stomach": {
                    "label": "💪 Iron Stomach Award",
                    "description": "Most weeks with the low score.",
                    "team": "Purdy Boys",
                    "owner": "tyler.hanlon",
                    "count": 3,
                }
            },
        }
        md = build_league_hq_canvas_markdown(_week_data(), awards, week=5)
        self.assertIn("Iron Stomach Award", md)
        self.assertIn("Purdy Boys", md)

    def test_handles_empty_awards_gracefully(self):
        md = build_league_hq_canvas_markdown(_week_data(), {"weeks_played": 0, "awards": {}}, week=1)
        self.assertIn("Season awards will appear here", md)

    def test_handles_missing_standings_gracefully(self):
        md = build_league_hq_canvas_markdown({"league": {}}, {"weeks_played": 0, "awards": {}})
        self.assertIn("No standings yet", md)
        self.assertIn("No power rankings yet", md)


class PreseasonCanvasBuilderTests(unittest.TestCase):

    def test_banner_marks_preseason_and_all_locked(self):
        md = build_preseason_league_hq_canvas_markdown()
        self.assertIn("Preseason preview", md)
        self.assertIn("Yahoo Fantasy API", md)
        self.assertIn("All 14 managers are locked", md)
        self.assertIn("Draft order is set", md)
        self.assertNotIn("TBD — still recruiting", md)

    def test_includes_draft_order_section(self):
        md = build_preseason_league_hq_canvas_markdown()
        self.assertIn("## 🎯 Draft Order", md)
        self.assertIn("| Pick | Team | Manager |", md)
        self.assertIn("| 1 | Scott's Tots |", md)
        self.assertIn("| 14 | Morgan's Team! |", md)
        for team in DRAFT_ORDER_2026:
            self.assertIn(team, md)

    def test_draft_order_matches_constant(self):
        self.assertEqual(len(DRAFT_ORDER_2026), 14)
        self.assertEqual(DRAFT_ORDER_2026[0], "Scott's Tots")
        self.assertEqual(DRAFT_ORDER_2026[-1], "Morgan's Team!")

    def test_omits_league_roster_section(self):
        md = build_preseason_league_hq_canvas_markdown()
        self.assertNotIn("## 👥 League Roster", md)
        self.assertNotIn("Managers so far", md)
        self.assertNotIn("| # | Manager | Team | Status |", md)

    def test_lists_known_managers_without_inventing_people(self):
        md = build_preseason_league_hq_canvas_markdown()
        self.assertIn("Tyler Hanlon", md)
        self.assertIn("Danielle DiRaddo", md)
        self.assertIn("Luis Islas", md)
        self.assertIn("Gregory Stewart", md)
        self.assertIn("Sachin Phadkar", md)
        self.assertIn("Adam Strutynski", md)
        self.assertNotIn("Han Jang", md)
        self.assertNotIn("Kristin Mendez", md)
        self.assertNotIn("Tiffany Wong", md)

    def test_standings_and_awards_are_empty_placeholders(self):
        md = build_preseason_league_hq_canvas_markdown()
        self.assertIn("Placeholders until Yahoo box scores exist", md)
        self.assertIn("The Bench Whisperer", md)
        self.assertIn("Iron Stomach Award", md)
        self.assertIn("_vacant_", md)
        self.assertIn("through 0 weeks", md)

    def test_omits_h1_title_for_slack_canvas_field(self):
        md = build_preseason_league_hq_canvas_markdown()
        self.assertFalse(md.startswith("# "))

    def test_plain_owners_when_slack_mentions_off(self):
        md = build_preseason_league_hq_canvas_markdown(slack_mentions=False)
        self.assertNotIn("![](@", md)
        self.assertEqual(len(PRESEASON_MANAGERS_2026), 14)

    def test_uses_2026_yahoo_team_names(self):
        md = build_preseason_league_hq_canvas_markdown()
        for name in (
            "Purdy Boys",
            "Monster of the Midway",
            "Scott's Tots",
            "Hut Hut Eich",
            "The Blackberries",
            "Morgan's Team!",
            "High Quality TD Rate",
            "Blitz Squad Joseph",
            "Game of Throws",
            "Stiff Arm tim",
            "big d's fantasy",
            "Goal Line Stand Jesse",
            "Penalty Flag Sachin",
            "Dasher Mafia",
        ):
            self.assertIn(name, md)
        self.assertNotIn("Hut, Hut, Eich", md)
        self.assertNotIn("High Qual Completion Deliv Rate", md)
        self.assertNotIn("New Vertical Threats", md)
        self.assertNotIn("We're More Than Delivery", md)
        self.assertNotIn("Team Tang", md)
        self.assertNotIn("Last known team", md)

    def test_weekly_canvas_prefers_live_week_data_names(self):
        data = _week_data()
        data["standings"]["standings"][0]["team_name"] = "Renamed In Yahoo"
        md = build_league_hq_canvas_markdown(data, {"weeks_played": 1, "awards": {}}, week=1)
        self.assertIn("Renamed In Yahoo", md)
        self.assertNotIn("Hut Hut Eich", md)


class TeamOwnerMappingTests(unittest.TestCase):

    def test_2026_yahoo_names_resolve_to_owners(self):
        self.assertEqual(resolve_owner("Hut Hut Eich"), "Adam Eichorn")
        self.assertEqual(resolve_owner("High Quality TD Rate"), "Peter Van Oot")
        self.assertEqual(resolve_owner("Morgan's Team!"), "Morgan Nelson")
        self.assertEqual(resolve_owner("Blitz Squad Joseph"), "Joe Barry")
        self.assertEqual(resolve_owner("The Blackberries"), "Gregory Stewart")
        self.assertEqual(resolve_owner("big d's fantasy"), "Danielle DiRaddo")
        self.assertEqual(resolve_owner("Game of Throws"), "Luis Islas")
        self.assertEqual(resolve_owner("Penalty Flag Sachin"), "Sachin Phadkar")
        self.assertEqual(resolve_owner("Dasher Mafia"), "Adam Strutynski")
        self.assertEqual(resolve_owner("Stiff Arm tim"), "Tim Tang")

    def test_unknown_yahoo_name_uses_manager_nickname(self):
        # After a mid-season rename, TEAM_OWNERS has no alias — nickname wins.
        self.assertEqual(resolve_owner("Brand New Name", "Morgan"), "Morgan")
        self.assertNotIn("Hut, Hut, Eich", TEAM_OWNERS)
        self.assertNotIn("High Qual Completion Deliv Rate", TEAM_OWNERS)

    def test_preseason_fallback_has_fourteen_locked(self):
        locked = [m for m in PRESEASON_MANAGERS_2026 if m.get("status") == "locked"]
        open_slots = [m for m in PRESEASON_MANAGERS_2026 if m.get("status") == "open"]
        self.assertEqual(len(locked), 14)
        self.assertEqual(len(open_slots), 0)
        owners = {m["owner"] for m in locked}
        self.assertIn("Jesse Chou", owners)
        self.assertIn("Sachin Phadkar", owners)
        self.assertIn("Adam Strutynski", owners)


if __name__ == "__main__":
    unittest.main()
