"""
Modular prompt system for the fantasy football columnist
Builds prompts dynamically based on what data is available
"""

import os
from typing import Dict, List, Optional


class PromptBuilder:
    """Builds prompts from modular components"""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self._ensure_prompts_directory()

    def _ensure_prompts_directory(self):
        """Create prompts directory if it doesn't exist"""
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)

    def _load_section(self, filename: str) -> str:
        """Load a prompt section from file"""
        filepath = os.path.join(self.prompts_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return f.read()
        return ""

    def build_columnist_prompt(
        self,
        include_examples: bool = True,
        include_advanced_stats: bool = True,
        include_trends: bool = True,
        include_memory: bool = True,
    ) -> str:
        """
        Build the columnist prompt from modular components

        Args:
            include_examples: Include example roasts and structures
            include_advanced_stats: Include advanced stats guidance
            include_trends: Include multi-week trend guidance
            include_memory: Include memory system instructions
        """

        sections = []

        # Core persona (ALWAYS included)
        sections.append(self._load_section("00_core_persona.md"))

        # Content structure (ALWAYS included)
        sections.append(self._load_section("01_structure.md"))

        # Safety rails (ALWAYS included)
        sections.append(self._load_section("02_safety_rails.md"))

        # Data grounding (ALWAYS included)
        sections.append(self._load_section("03_data_grounding.md"))

        # Optional: Examples
        if include_examples:
            sections.append(self._load_section("04_examples.md"))

        # Optional: Advanced stats guidance
        if include_advanced_stats:
            sections.append(self._load_section("05_advanced_stats.md"))

        # Optional: Trend analysis
        if include_trends:
            sections.append(self._load_section("06_trends.md"))

        # Optional: Memory system
        if include_memory:
            sections.append(self._load_section("07_memory.md"))

        # League-specific context (ALWAYS included)
        sections.append(self._load_section("08_league_context.md"))

        # Final reminder (ALWAYS included)
        sections.append(self._load_section("09_final_reminder.md"))

        # Join all sections with double newlines
        full_prompt = "\n\n".join(filter(None, sections))

        return full_prompt

    def get_prompt_stats(self, prompt: str) -> Dict:
        """Get statistics about a prompt"""
        return {
            "characters": len(prompt),
            "lines": len(prompt.splitlines()),
            "estimated_tokens": len(prompt) // 4,
            "sections": prompt.count("##"),
            "examples": prompt.count("**Example"),
        }

    def create_fallback_prompt(self) -> str:
        """
        Create a fallback prompt if modular files don't exist
        Uses the original COLUMNIST_PROMPT.md as fallback
        """
        fallback_path = "COLUMNIST_PROMPT.md"
        if os.path.exists(fallback_path):
            with open(fallback_path, "r") as f:
                return f.read()

        # If no fallback exists, return a minimal prompt
        return """You are a mean but funny fantasy football columnist.
Write a weekly recap that roasts bad decisions and celebrates great plays.
Be cutting but safe. Keep it short and punchy. Use CRM jargon as easter eggs."""


# Convenience function for backward compatibility
def get_columnist_prompt(use_modular: bool = True, **kwargs) -> str:
    """
    Get the columnist prompt (backward compatible)

    Args:
        use_modular: If True, use modular prompt system. If False, use monolithic file.
        **kwargs: Additional arguments passed to PromptBuilder.build_columnist_prompt()
    """
    if use_modular:
        try:
            builder = PromptBuilder()
            return builder.build_columnist_prompt(**kwargs)
        except Exception:
            # Fallback to monolithic if modular fails
            builder = PromptBuilder()
            return builder.create_fallback_prompt()
    else:
        # Use original monolithic file
        with open("COLUMNIST_PROMPT.md", "r") as f:
            return f.read()


if __name__ == "__main__":
    # Test the builder
    builder = PromptBuilder()

    print("Testing Prompt Builder\n" + "=" * 50)

    # Build minimal prompt (no examples, no trends)
    minimal = builder.build_columnist_prompt(
        include_examples=False, include_trends=False
    )
    minimal_stats = builder.get_prompt_stats(minimal)
    print(f"\n📊 Minimal Prompt:")
    print(f"  Characters: {minimal_stats['characters']:,}")
    print(f"  Estimated tokens: {minimal_stats['estimated_tokens']:,}")

    # Build full prompt
    full = builder.build_columnist_prompt()
    full_stats = builder.get_prompt_stats(full)
    print(f"\n📊 Full Prompt:")
    print(f"  Characters: {full_stats['characters']:,}")
    print(f"  Estimated tokens: {full_stats['estimated_tokens']:,}")
    print(f"  Sections: {full_stats['sections']}")

    # Show savings
    savings = (
        1 - minimal_stats["estimated_tokens"] / full_stats["estimated_tokens"]
    ) * 100
    print(f"\n💰 Token Savings (minimal vs full): {savings:.1f}%")
