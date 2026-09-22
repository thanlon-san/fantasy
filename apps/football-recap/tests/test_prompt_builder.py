"""House-voice prompt loader: V3 only, no costume files."""

from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401

from src.llm_client import LLMClient
from src.prompt_builder import build_columnist_prompt


class PromptBuilderTests(unittest.TestCase):

    def test_v3_is_the_only_prompt(self):
        prompt = build_columnist_prompt()
        self.assertIn("The Commissioner's Ghost", prompt)
        self.assertIn("Bill Simmons", prompt)
        self.assertIn("4/10", prompt)
        self.assertNotIn("PERSONA_SEED", prompt)
        self.assertNotIn("This Week's Persona", prompt)
        self.assertNotIn("Must-Use Words", prompt)
        self.assertNotIn("6+ times minimum", prompt)

    def test_structure_requirements_still_present(self):
        prompt = build_columnist_prompt()
        for section in (
            "League Pulse",
            "Stat of the Week",
            "Power Rankings",
            "Closing",
            "GIF of the Week",
        ):
            self.assertIn(section, prompt)
        lowered = prompt.lower()
        self.assertIn("this exact order", lowered)
        self.assertIn("do not reorder", lowered)

    def test_llm_client_loads_same_v3(self):
        prompt = LLMClient.load_columnist_prompt()
        self.assertIn("The Commissioner's Ghost", prompt)
        self.assertNotIn("PERSONA_SEED", prompt)

    def test_user_prompt_has_no_persona_seed(self):
        user = LLMClient.generate_user_prompt(4, "DATA", "HISTORY")
        self.assertNotIn("PERSONA_SEED", user)
        self.assertIn("Now write the Week 4 recap", user)


if __name__ == "__main__":
    unittest.main()
