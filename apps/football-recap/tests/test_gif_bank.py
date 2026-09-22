"""
Tier-priority + rotation tests for :mod:`src.gif_bank`.

We don't test that the URLs resolve to real GIFs — only that ``pick_gif``
picks the right tier for a given superlatives payload and rotates
deterministically inside a tier.
"""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src import gif_bank


class GifBankTests(unittest.TestCase):

    def test_default_when_no_superlatives(self):
        pick = gif_bank.pick_gif({}, week=1, superlatives={})
        self.assertEqual(pick["tier"], "default")
        self.assertTrue(pick["url"].startswith("https://media.giphy.com/"))
        self.assertTrue(pick["caption"])

    def test_upset_wins_priority_over_blowout(self):
        # If both fire, upset should win — league loves the underdog story.
        sups = {
            "upset_of_the_week": {"label": "u"},
            "blowout_of_the_week": {"label": "b"},
        }
        self.assertEqual(gif_bank.pick_gif({}, week=1, superlatives=sups)["tier"], "upset")

    def test_blowout_wins_over_nailbiter(self):
        sups = {
            "blowout_of_the_week": {"label": "b"},
            "nailbiter_of_the_week": {"label": "n"},
        }
        self.assertEqual(gif_bank.pick_gif({}, week=1, superlatives=sups)["tier"], "blowout")

    def test_management_disaster_tier(self):
        sups = {"cooked_of_the_week": {"label": "c"}}
        self.assertEqual(
            gif_bank.pick_gif({}, week=1, superlatives=sups)["tier"], "management"
        )

    def test_all_tiers_exposed_via_all_gifs(self):
        # Regression guard against renaming a tier bucket without updating
        # ``all_gifs`` (which some future debug scripts may rely on).
        expected = {
            "blowout", "nailbiter", "shootout", "cold_war",
            "upset", "management", "default",
        }
        self.assertEqual(set(gif_bank.all_gifs().keys()), expected)

    def test_rotation_within_tier_is_deterministic(self):
        # Same tier + adjacent weeks → different index in the pool.
        sups = {"blowout_of_the_week": {"label": "b"}}
        w1 = gif_bank.pick_gif({}, week=1, superlatives=sups)
        w2 = gif_bank.pick_gif({}, week=2, superlatives=sups)
        w3 = gif_bank.pick_gif({}, week=3, superlatives=sups)
        pool_size = len(gif_bank.BLOWOUT_GIFS)
        # If pool_size > 1 we should never get the same URL twice in a row.
        if pool_size > 1:
            self.assertNotEqual(w1["url"], w2["url"])
            self.assertNotEqual(w2["url"], w3["url"])
        # And the pick is deterministic given (week, tier).
        w1_again = gif_bank.pick_gif({}, week=1, superlatives=sups)
        self.assertEqual(w1_again["url"], w1["url"])

    def test_rotation_wraps_at_pool_length(self):
        pool_size = len(gif_bank.DEFAULT_GIFS)
        # No superlatives → default tier. week=0 and week=pool_size must match.
        pick_a = gif_bank.pick_gif({}, week=0, superlatives={})
        pick_b = gif_bank.pick_gif({}, week=pool_size, superlatives={})
        self.assertEqual(pick_a["url"], pick_b["url"])


if __name__ == "__main__":
    unittest.main()
