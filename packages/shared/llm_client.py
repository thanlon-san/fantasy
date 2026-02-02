"""
LLM Client for Fantasy Applications
Handles communication with various LLM providers (OpenAI, Anthropic)
Generic base that can be extended by individual apps
"""

from typing import Optional


class LLMClient:
    """Base LLM client with common functionality"""

    # Default temperature for creative writing
    DEFAULT_TEMPERATURE = 0.95

    @staticmethod
    def generate_with_openai(
        system_prompt: str,
        user_prompt: str,
        client,
        model: str = "gpt-4o",
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """
        Generate content using OpenAI API

        Args:
            system_prompt: System instructions for the model
            user_prompt: User query/context
            client: OpenAI client instance
            model: OpenAI model to use
            temperature: Sampling temperature (default 0.95)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text or None if error
        """
        try:
            temp = (
                temperature
                if temperature is not None
                else LLMClient.DEFAULT_TEMPERATURE
            )
            print(f"🤖 Generating with OpenAI ({model}, temp={temp})...")

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
            print(f"❌ Error generating with OpenAI: {e}")
            return None

    @staticmethod
    def generate_with_anthropic(
        system_prompt: str,
        user_prompt: str,
        client,
        model: str = "claude-sonnet-4-5-20250929",
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """
        Generate content using Anthropic API

        Args:
            system_prompt: System instructions for the model
            user_prompt: User query/context
            client: Anthropic client instance
            model: Anthropic model to use
            temperature: Sampling temperature (default 0.95)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text or None if error
        """
        try:
            temp = (
                temperature
                if temperature is not None
                else LLMClient.DEFAULT_TEMPERATURE
            )
            print(f"🤖 Generating with Anthropic ({model}, temp={temp})...")

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temp,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            return response.content[0].text

        except Exception as e:
            print(f"❌ Error generating with Anthropic: {e}")
            return None
