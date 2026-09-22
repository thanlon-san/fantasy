"""
Pure-helper unit tests for :mod:`src.yahoo_fetcher`.

These cover the parsing/analytics helpers that don't require network access:
Yahoo response shape helpers (``_flatten_props``, ``_numbered_children``) and
the lineup math (``_position_aggregates``, ``_optimal_lineup``). This is the
layer most likely to regress if we ever refactor the fetcher module.
"""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.yahoo_fetcher import (
    _flatten_props,
    _numbered_children,
    _optimal_lineup,
    _position_aggregates,
    _split_team_payload,
    YahooLeagueFetcher,
)


class SplitTeamPayloadTests(unittest.TestCase):

    def test_merges_split_yahoo_stat_blocks(self):
        raw = [
            [{"team_key": "470.l.1.t.1"}, {"team_id": "1"}, {"name": "Ballers"}],
            {"team_points": {"total": "127.40"}},
            {
                "team_standings": {
                    "rank": "1",
                    "outcome_totals": {"wins": "2", "losses": 0, "ties": 0},
                    "streak": {"type": "win", "value": "2"},
                    "points_against": "90.00",
                }
            },
        ]
        props, stats = _split_team_payload(raw)
        self.assertEqual(props["team_key"], "470.l.1.t.1")
        self.assertEqual(stats["team_points"]["total"], "127.40")
        self.assertEqual(stats["team_standings"]["rank"], "1")

    def test_legacy_combined_stat_block(self):
        raw = [
            [{"name": "Legacy"}],
            {
                "team_points": {"total": "100.0"},
                "team_standings": {"rank": "3", "outcome_totals": {"wins": "1"}},
            },
        ]
        props, stats = _split_team_payload(raw)
        self.assertEqual(props["name"], "Legacy")
        self.assertEqual(stats["team_standings"]["rank"], "3")


class ParseTeamEntryTests(unittest.TestCase):

    def test_parse_team_entry_reads_split_standings_block(self):
        fetcher = YahooLeagueFetcher.__new__(YahooLeagueFetcher)
        raw = [
            [
                {"team_key": "470.l.1.t.1"},
                {"team_id": "1"},
                {"name": "Purdy Boys"},
                {"managers": [{"manager": {"nickname": "Tyler"}}]},
            ],
            {"team_points": {"total": "285.18"}},
            {
                "team_standings": {
                    "rank": "1",
                    "outcome_totals": {"wins": "2", "losses": 0, "ties": 0},
                    "streak": {"type": "win", "value": "2"},
                    "points_against": "171.94",
                }
            },
        ]
        team = fetcher._parse_team_entry(raw)
        self.assertEqual(team["wins"], 2)
        self.assertEqual(team["losses"], 0)
        self.assertEqual(team["points_for"], 285.18)
        self.assertEqual(team["points_against"], 171.94)
        self.assertEqual(team["standing"], 1)
        self.assertEqual(team["streak_type"], "W")
        self.assertEqual(team["streak_length"], 2)


class FlattenPropsTests(unittest.TestCase):

    def test_flattens_list_of_dicts(self):
        raw = [
            {"team_key": "461.l.1324751.t.1"},
            {"name": "Ballers"},
            {"score": 120.4},
        ]
        self.assertEqual(
            _flatten_props(raw),
            {"team_key": "461.l.1324751.t.1", "name": "Ballers", "score": 120.4},
        )

    def test_later_keys_override_earlier(self):
        # Yahoo occasionally repeats a key; the later value should win.
        raw = [{"score": 100.0}, {"score": 120.4}]
        self.assertEqual(_flatten_props(raw), {"score": 120.4})

    def test_non_list_input_returns_empty_dict(self):
        self.assertEqual(_flatten_props({}), {})
        self.assertEqual(_flatten_props(None), {})
        self.assertEqual(_flatten_props("string"), {})

    def test_skips_non_dict_entries(self):
        raw = [{"team_key": "abc"}, "junk", 42, {"name": "Ballers"}]
        self.assertEqual(_flatten_props(raw), {"team_key": "abc", "name": "Ballers"})


class NumberedChildrenTests(unittest.TestCase):

    def test_returns_child_payloads_in_order(self):
        collection = {
            "count": 2,
            "0": {"team": [{"team_key": "t1"}]},
            "1": {"team": [{"team_key": "t2"}]},
        }
        children = _numbered_children(collection, "team")
        self.assertEqual(len(children), 2)
        self.assertEqual([_flatten_props(c) for c in children], [
            {"team_key": "t1"},
            {"team_key": "t2"},
        ])

    def test_ignores_count_key(self):
        collection = {"count": 1, "0": {"team": [{"team_key": "t1"}]}}
        self.assertEqual(len(_numbered_children(collection, "team")), 1)

    def test_ignores_entries_without_child_key(self):
        collection = {"count": 2, "0": {"player": [{}]}, "1": {"team": [{}]}}
        self.assertEqual(len(_numbered_children(collection, "team")), 1)

    def test_non_dict_input_returns_empty(self):
        self.assertEqual(_numbered_children([], "team"), [])
        self.assertEqual(_numbered_children(None, "team"), [])


class PositionAggregatesTests(unittest.TestCase):

    def test_sums_actual_points_per_position(self):
        starters = [
            {"position": "QB", "actual_points": 22.4, "name": "QB1"},
            {"position": "RB", "actual_points": 15.2, "name": "RB1"},
            {"position": "RB", "actual_points": 8.9, "name": "RB2"},
            {"position": "WR", "actual_points": 12.0, "name": "WR1"},
            {"position": "TE", "actual_points": 5.5, "name": "TE1"},
            {"position": "K",  "actual_points": 7.0, "name": "K1"},
            {"position": "DEF", "actual_points": 9.0, "name": "DEF1"},
        ]
        agg = _position_aggregates(starters)
        self.assertEqual(agg["QB"], 22.4)
        self.assertEqual(agg["RB"], 24.1)
        self.assertEqual(agg["WR"], 12.0)
        self.assertEqual(agg["TE"], 5.5)
        self.assertEqual(agg["K"], 7.0)
        # DEF should mirror into D/ST for downstream ESPN-shaped consumers.
        self.assertEqual(agg["DEF"], 9.0)
        self.assertEqual(agg["D/ST"], 9.0)

    def test_unknown_position_is_ignored(self):
        starters = [{"position": "PUNTER", "actual_points": 99.9, "name": "P"}]
        agg = _position_aggregates(starters)
        # All known buckets stay at 0 — unknown position is silently dropped.
        for v in agg.values():
            self.assertEqual(v, 0.0)


class OptimalLineupTests(unittest.TestCase):

    def _pool(self, position: str, name: str, pts: float) -> dict:
        return {"name": name, "position": position, "actual_points": pts}

    def test_selects_best_players_per_slot(self):
        all_players = [
            self._pool("QB", "Josh", 30.0),
            self._pool("QB", "Backup", 8.0),
            self._pool("RB", "Bijan", 25.0),
            self._pool("RB", "Saquon", 22.0),
            self._pool("RB", "Handcuff", 4.0),
            self._pool("WR", "CeeDee", 20.0),
            self._pool("WR", "Chase", 18.0),
            self._pool("WR", "Boom", 15.0),   # Loses starter slot, wins FLEX
            self._pool("TE", "Kelce", 12.0),
            self._pool("K",  "Bass", 9.0),
            self._pool("DEF", "SF", 11.0),
        ]
        optimal = _optimal_lineup(all_players)

        # QB(30) + RB(25+22) + WR(20+18) + TE(12) + FLEX(15) + K(9) + DEF(11) = 162
        self.assertAlmostEqual(optimal["optimal_score"], 162.0, places=2)

        picked_names = {p["name"] for p in optimal["optimal_players"]}
        self.assertEqual(
            picked_names,
            {"Josh", "Bijan", "Saquon", "CeeDee", "Chase", "Boom", "Kelce", "Bass", "SF"},
        )

        # Flex should be labeled distinctly so downstream consumers can render it.
        flex_slots = [p for p in optimal["optimal_players"] if p["position"] == "FLEX"]
        self.assertEqual(len(flex_slots), 1)
        self.assertEqual(flex_slots[0]["name"], "Boom")

    def test_uses_dst_pool_when_no_def_players(self):
        # Yahoo sometimes calls the defense slot "D/ST" instead of "DEF".
        all_players = [
            self._pool("QB", "Josh", 20.0),
            self._pool("RB", "Bijan", 20.0),
            self._pool("RB", "Saquon", 20.0),
            self._pool("WR", "A", 10.0),
            self._pool("WR", "B", 10.0),
            self._pool("TE", "Kelce", 10.0),
            self._pool("K", "Bass", 5.0),
            {"name": "SF", "position": "D/ST", "actual_points": 11.0},
        ]
        optimal = _optimal_lineup(all_players)
        # Only 2 RB / 2 WR / 1 TE, so FLEX will be empty — that's fine.
        # The important check is that the D/ST player was still picked.
        names = {p["name"] for p in optimal["optimal_players"]}
        self.assertIn("SF", names)


if __name__ == "__main__":
    unittest.main()
