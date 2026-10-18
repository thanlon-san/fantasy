"""Tests for :mod:`src.recap_slack_excerpt`."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from src.recap_slack_excerpt import extract_recap_slack_sections


class RecapSlackExcerptTests(unittest.TestCase):

    def test_extracts_matchups_from_week_2_recap_file(self):
        recap_path = (
            Path(__file__).resolve().parent.parent / "output" / "week-2-recap.md"
        )
        if not recap_path.is_file():
            self.skipTest("week-2-recap.md not present locally")
        raw = recap_path.read_text(encoding="utf-8")
        excerpt = extract_recap_slack_sections(raw)
        self.assertIsNotNone(excerpt)
        self.assertIn("League Pulse", excerpt)
        self.assertIn("Stat of the Week", excerpt)
        self.assertIn("Matchups", excerpt)
        self.assertIn("Purdy Boys", excerpt)
        self.assertNotIn("Power Rankings", excerpt)
        self.assertIn("<@U03FE7P8EEP>", excerpt)
        self.assertIn("*<@U03FE7P8EEP>", excerpt)

    def test_returns_none_without_matchups_section(self):
        self.assertIsNone(extract_recap_slack_sections("# hello\nno matchups here"))


if __name__ == "__main__":
    unittest.main()
