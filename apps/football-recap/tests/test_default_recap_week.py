"""Tests for :func:`src.constants.default_recap_week` and final-week detection."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401

from src.constants import default_recap_week
from src.yahoo_fetcher import latest_final_week, week_data_is_final


def _wd(status, scores):
    teams = lambda s: {"home_team": {"score": s}, "away_team": {"score": s}}
    return {"matchups": {"matchups": [{**teams(s), "status": status} for s in scores]}}


class DefaultRecapWeekTests(unittest.TestCase):
    def test_explicit_week_wins(self):
        self.assertEqual(default_recap_week(6, yahoo_current_week=5), 6)

    def test_current_week_not_final_steps_back(self):
        self.assertEqual(default_recap_week(None, yahoo_current_week=10, current_week_final=False), 9)
        self.assertEqual(default_recap_week(None, yahoo_current_week=10), 9)

    def test_current_week_final_kept(self):
        self.assertEqual(default_recap_week(None, yahoo_current_week=10, current_week_final=True), 10)

    def test_never_below_one(self):
        self.assertEqual(default_recap_week(None, yahoo_current_week=1, current_week_final=False), 1)


class FinalDetectionTests(unittest.TestCase):
    def test_preevent_not_final(self):
        self.assertFalse(week_data_is_final(_wd("preevent", [0.0, 0.0])))

    def test_postevent_final(self):
        self.assertTrue(week_data_is_final(_wd("postevent", [100.0])))

    def test_no_status_zeros_not_final(self):
        self.assertFalse(week_data_is_final(_wd("", [0.0])))

    def test_latest_final_week_wednesday(self):
        f = MagicMock()
        f.league_info.return_value = {"current_week": 10}
        f.week_matchups.return_value = _wd("preevent", [0.0])["matchups"]
        self.assertEqual(latest_final_week(f), 9)

    def test_latest_final_week_when_current_done(self):
        f = MagicMock()
        f.league_info.return_value = {"current_week": 10}
        f.week_matchups.return_value = _wd("postevent", [90.0])["matchups"]
        self.assertEqual(latest_final_week(f), 10)


if __name__ == "__main__":
    unittest.main()
