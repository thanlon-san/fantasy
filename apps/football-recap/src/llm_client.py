"""
LLM Client for Fantasy Football Recap Generation
Handles communication with various LLM providers (OpenAI, Anthropic)
"""

from typing import Optional
import os


class LLMClient:
    """Handles LLM API calls for recap generation"""

    # Default temperature for creative writing (higher = more creative/varied)
    DEFAULT_TEMPERATURE = 0.95

    @staticmethod
    def load_columnist_prompt(use_v2: bool = True, use_v3: bool = False) -> str:
        """
        Load the columnist system prompt

        Args:
            use_v2: If True, load V2 format. If False, load V1.
            use_v3: If True, load V3 format (lean, comedy-focused). Overrides use_v2.
        """
        # First, try to build from modular prompt files (persona, structure, etc.)
        try:
            from src.prompt_builder import build_columnist_prompt

            return build_columnist_prompt(use_v2=use_v2, use_v3=use_v3)
        except Exception:
            # Fall back to legacy single-file prompts for compatibility
            pass

        # V3: Try the lean prompt first if requested
        if use_v3:
            v3_paths = [
                "COLUMNIST_PROMPT_V3.md",
                "docs/COLUMNIST_PROMPT_V3.md",
                os.path.join(os.path.dirname(__file__), "..", "COLUMNIST_PROMPT_V3.md"),
                os.path.join(
                    os.path.dirname(__file__), "..", "docs", "COLUMNIST_PROMPT_V3.md"
                ),
            ]

            for path in v3_paths:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        return f.read()

        if use_v2:
            # Try V2 prompt first
            v2_paths = [
                "COLUMNIST_PROMPT_V2.md",
                "docs/COLUMNIST_PROMPT_V2.md",
                os.path.join(os.path.dirname(__file__), "..", "COLUMNIST_PROMPT_V2.md"),
                os.path.join(
                    os.path.dirname(__file__), "..", "docs", "COLUMNIST_PROMPT_V2.md"
                ),
            ]

            for path in v2_paths:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        return f.read()

        # Fallback to V1 prompt
        v1_paths = [
            "COLUMNIST_PROMPT.md",
            "docs/COLUMNIST_PROMPT.md",
            os.path.join(os.path.dirname(__file__), "..", "COLUMNIST_PROMPT.md"),
            os.path.join(
                os.path.dirname(__file__), "..", "docs", "COLUMNIST_PROMPT.md"
            ),
        ]

        for path in v1_paths:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read()

        raise FileNotFoundError(
            "Could not find columnist prompt files. Expected either modular docs "
            "(COLUMNIST_PERSONA.md / COLUMNIST_STRUCTURE_*.md / COLUMNIST_COMEDY_RULES.md / "
            "COLUMNIST_LEAGUE_CONTEXT.md) or legacy COLUMNIST_PROMPT.md / COLUMNIST_PROMPT_V2.md / "
            "COLUMNIST_PROMPT_V3.md."
        )

    @staticmethod
    def generate_user_prompt(
        week: int,
        data_context: str,
        history_context: str,
        persona_seed: Optional[str] = None,
    ) -> str:
        """Generate the user prompt for LLM"""
        seed_block = ""
        if persona_seed:
            seed_block = f"## PERSONA_SEED\n\n{persona_seed}\n\n---\n\n"

        return f"""{seed_block}## DATA FOR THIS WEEK

{data_context}

---

{history_context}

---

Now write the Week {week} recap."""

    @staticmethod
    def generate_with_openai(
        week: int,
        data_context: str,
        history_context: str,
        client,
        model: str = "gpt-4",
        use_v2: bool = True,
        use_v3: bool = True,
        persona_seed: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """
        Generate recap using OpenAI API

        Args:
            week: Week number
            data_context: Context from ContextBuilder
            history_context: Previous recaps context
            client: OpenAI client instance
            model: OpenAI model to use
            use_v2: If True and use_v3 is False, use V2 format
            use_v3: If True, use V3 format (lean, comedy-focused). Recommended.
            temperature: Sampling temperature (default 0.95 for creative output)

        Returns:
            Generated recap text or None if error
        """
        try:
            system_prompt = LLMClient.load_columnist_prompt(
                use_v2=use_v2, use_v3=use_v3
            )
            user_prompt = LLMClient.generate_user_prompt(
                week, data_context, history_context, persona_seed=persona_seed
            )

            if use_v3:
                format_type = "V3 (lean)"
            elif use_v2:
                format_type = "V2 (structured)"
            else:
                format_type = "V1 (classic)"

            temp = (
                temperature
                if temperature is not None
                else LLMClient.DEFAULT_TEMPERATURE
            )
            print(
                f"🤖 Generating recap with OpenAI ({model}, {format_type}, temp={temp})..."
            )

            # V3/V2 format needs ~4000 tokens for full recap with all 16 teams in power rankings
            max_tokens = 4096 if (use_v3 or use_v2) else 2000

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temp,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"❌ Error generating recap with OpenAI: {e}")
            return None

    @staticmethod
    def generate_with_anthropic(
        week: int,
        data_context: str,
        history_context: str,
        client,
        model: str = "claude-sonnet-4-5-20250929",
        use_v2: bool = True,
        use_v3: bool = True,
        persona_seed: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """
        Generate recap using Anthropic API

        Args:
            week: Week number
            data_context: Context from ContextBuilder
            history_context: Previous recaps context
            client: Anthropic client instance
            model: Anthropic model to use
            use_v2: If True and use_v3 is False, use V2 format
            use_v3: If True, use V3 format (lean, comedy-focused). Recommended.
            temperature: Sampling temperature (default 0.95 for creative output)

        Returns:
            Generated recap text or None if error
        """
        try:
            system_prompt = LLMClient.load_columnist_prompt(
                use_v2=use_v2, use_v3=use_v3
            )
            user_prompt = LLMClient.generate_user_prompt(
                week, data_context, history_context, persona_seed=persona_seed
            )

            if use_v3:
                format_type = "V3 (lean)"
            elif use_v2:
                format_type = "V2 (structured)"
            else:
                format_type = "V1 (classic)"

            temp = (
                temperature
                if temperature is not None
                else LLMClient.DEFAULT_TEMPERATURE
            )
            print(
                f"🤖 Generating recap with Anthropic ({model}, {format_type}, temp={temp})..."
            )

            # V3/V2 format needs ~4000 tokens for full recap with all 16 teams in power rankings
            max_tokens = 4096 if (use_v3 or use_v2) else 2000

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temp,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            return response.content[0].text

        except Exception as e:
            print(f"❌ Error generating recap with Anthropic: {e}")
            return None
