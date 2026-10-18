"""Tests for Slack manager mention formatting."""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.constants import (
    format_slack_digest_label,
    format_slack_mention,
    resolve_slack_id,
)


class SlackMentionTests(unittest.TestCase):
    def test_resolve_slack_id_by_current_team_name(self):
        self.assertEqual(resolve_slack_id(team_name="Purdy Boys"), "U03FE7P8EEP")

    def test_resolve_slack_id_by_owner_display_name(self):
        self.assertEqual(resolve_slack_id(owner_name="Tyler Hanlon"), "U03FE7P8EEP")

    def test_format_slack_mention_known_manager(self):
        self.assertEqual(
            format_slack_mention(team_name="Purdy Boys"),
            "<@U03FE7P8EEP>",
        )

    def test_format_slack_mention_unknown_falls_back_to_display_name(self):
        self.assertEqual(
            format_slack_mention(team_name="Mystery Squad", owner_name="Jane Doe"),
            "Jane Doe",
        )

    def test_curly_apostrophe_team_name_resolves(self):
        self.assertEqual(
            format_slack_mention(team_name="Scott\u2019s Tots", owner_name="Marissa"),
            "<@U032LD8RMK8>",
        )

    def test_digest_label_uses_bold_team_not_mention_token(self):
        self.assertEqual(
            format_slack_digest_label(team_name="Purdy Boys", owner_name="Tyler Hanlon"),
            "*Purdy Boys* (Tyler Hanlon)",
        )

    def test_digest_label_falls_back_to_owner_when_no_team(self):
        self.assertEqual(
            format_slack_digest_label(team_name="", owner_name="Jane Doe"),
            "*Jane Doe*",
        )


if __name__ == "__main__":
    unittest.main()
