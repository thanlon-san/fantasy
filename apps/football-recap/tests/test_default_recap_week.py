"""Tests for :func:`src.constants.default_recap_week`."""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.constants import default_recap_week, get_current_nfl_week


class DefaultRecapWeekTests(unittest.TestCase):

    def test_explicit_week_wins(self):
        self.assertEqual(default_recap_week(6, yahoo_current_week=5), 6)

    def test_prefers_yahoo_over_calendar(self):
        calendar = get_current_nfl_week()
        if calendar != 6:
            self.assertEqual(default_recap_week(None, yahoo_current_week=6), 6)

    def test_falls_back_to_calendar_when_yahoo_missing(self):
        self.assertEqual(default_recap_week(None, yahoo_current_week=None), get_current_nfl_week())

    def test_invalid_yahoo_week_falls_back(self):
        self.assertEqual(default_recap_week(None, yahoo_current_week=99), get_current_nfl_week())


if __name__ == "__main__":
    unittest.main()
