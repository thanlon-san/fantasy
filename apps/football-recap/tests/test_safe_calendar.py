"""
Allowlist calendar: 0–1 holiday/NFL-milestone notes, never invented news.
"""

from __future__ import annotations

import unittest
from datetime import date

from tests import _bootstrap  # noqa: F401

from src.safe_calendar import calendar_hook, week_for_date


class SafeCalendarTests(unittest.TestCase):

    def test_week_1_is_labor_day_kickoff(self):
        note = calendar_hook(week=1)
        self.assertIsNotNone(note)
        self.assertIn("Labor Day", note)

    def test_week_13_is_thanksgiving(self):
        note = calendar_hook(week=13)
        self.assertIsNotNone(note)
        self.assertIn("Thanksgiving", note)

    def test_week_16_and_17_are_christmas(self):
        for week in (16, 17):
            note = calendar_hook(week=week)
            self.assertIsNotNone(note, week)
            self.assertIn("Christmas", note)

    def test_week_18_is_new_year(self):
        note = calendar_hook(week=18)
        self.assertIsNotNone(note)
        self.assertIn("New Year", note)

    def test_ordinary_week_returns_none(self):
        self.assertIsNone(calendar_hook(week=5))
        self.assertIsNone(calendar_hook(week=9))

    def test_explicit_week_wins_over_date(self):
        # A holiday date must not override a non-holiday recap week.
        self.assertIsNone(
            calendar_hook(week=5, when=date(2026, 11, 26))
        )

    def test_preseason_date_returns_draft_hook(self):
        note = calendar_hook(when=date(2026, 8, 20))
        self.assertIsNotNone(note)
        self.assertIn("preseason", note.lower())

    def test_super_bowl_week_date(self):
        note = calendar_hook(when=date(2027, 2, 7))
        self.assertIsNotNone(note)
        self.assertIn("Super Bowl", note)

    def test_midseason_date_maps_to_week_then_maybe_none(self):
        # Oct 15 2026 is week 7 — no holiday.
        self.assertEqual(week_for_date(date(2026, 10, 15)), 7)
        self.assertIsNone(calendar_hook(when=date(2026, 10, 15)))

    def test_thanksgiving_date_maps_to_week_13(self):
        self.assertEqual(week_for_date(date(2026, 11, 26)), 13)
        note = calendar_hook(when=date(2026, 11, 26))
        self.assertIsNotNone(note)
        self.assertIn("Thanksgiving", note)

    def test_never_returns_news_or_politics(self):
        for week in range(1, 19):
            note = calendar_hook(week=week)
            if note:
                lowered = note.lower()
                self.assertNotIn("election", lowered)
                self.assertNotIn("scandal", lowered)
                self.assertNotIn("newsapi", lowered)


if __name__ == "__main__":
    unittest.main()
