"""Tests for Slack manager mention formatting."""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.constants import (
    format_slack_digest_label,
    format_slack_mention,
    resolve_slack_id,
    resolve_slack_mentions_for_paste,
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

    def test_resolve_paste_mention_with_team_possessive(self):
        raw = (
            "<@U03FE7P8EEP>'s Purdy Boys (105.0) def. "
            "<@U03L8KFL1RS>'s Monster of the Midway (60.58)"
        )
        out = resolve_slack_mentions_for_paste(raw)
        self.assertIn("*Purdy Boys* (Tyler Hanlon)", out)
        self.assertIn("*Monster of the Midway* (Elisa Keny (Ambrose))", out)
        self.assertNotIn("<@U", out)

    def test_resolve_paste_mention_prose_possessive(self):
        raw = "Meanwhile, <@U07JPH677ED>'s entire roster produced 51.68."
        out = resolve_slack_mentions_for_paste(raw)
        self.assertIn("*Joe Barry*'s entire roster", out)
        self.assertNotIn("<@U", out)

    def test_resolve_paste_bare_mention(self):
        raw = "Meanwhile, <@U0AV2EB5GUD> benched A.J. Brown."
        out = resolve_slack_mentions_for_paste(raw)
        self.assertIn("*Game of Throws* (Luis Islas)", out)
        self.assertNotIn("<@U", out)


if __name__ == "__main__":
    unittest.main()
