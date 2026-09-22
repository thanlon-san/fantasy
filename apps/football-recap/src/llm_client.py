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
    def load_columnist_prompt() -> str:
        """Load the single house-voice columnist prompt (V3 only)."""
        try:
            from src.prompt_builder import build_columnist_prompt

            return build_columnist_prompt()
        except FileNotFoundError:
            pass

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

        raise FileNotFoundError(
            "Could not find docs/COLUMNIST_PROMPT_V3.md — that file is the "
            "only columnist prompt source."
        )

    @staticmethod
    def generate_user_prompt(
        week: int,
        data_context: str,
        history_context: str,
    ) -> str:
        """Generate the user prompt for LLM"""
        return f"""## DATA FOR THIS WEEK

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
            temperature: Sampling temperature (default 0.95 for creative output)

        Returns:
            Generated recap text or None if error
        """
        try:
            system_prompt = LLMClient.load_columnist_prompt()
            user_prompt = LLMClient.generate_user_prompt(
                week, data_context, history_context
            )

            temp = (
                temperature
                if temperature is not None
                else LLMClient.DEFAULT_TEMPERATURE
            )
            print(
                f"🤖 Generating recap with OpenAI ({model}, V3, temp={temp})..."
            )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temp,
                max_tokens=4096,
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
            temperature: Sampling temperature (default 0.95 for creative output)

        Returns:
            Generated recap text or None if error
        """
        try:
            system_prompt = LLMClient.load_columnist_prompt()
            user_prompt = LLMClient.generate_user_prompt(
                week, data_context, history_context
            )

            temp = (
                temperature
                if temperature is not None
                else LLMClient.DEFAULT_TEMPERATURE
            )
            print(
                f"🤖 Generating recap with Anthropic ({model}, V3, temp={temp})..."
            )

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temp,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            return response.content[0].text

        except Exception as e:
            print(f"❌ Error generating recap with Anthropic: {e}")
            return None
