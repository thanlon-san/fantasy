"""
LLM Client for Fantasy Football Recap Generation
Handles communication with various LLM providers (OpenAI, Anthropic)
"""

from typing import Optional
import os


class LLMClient:
    """Handles LLM API calls for recap generation"""
    
    @staticmethod
    def load_columnist_prompt() -> str:
        """Load the columnist system prompt"""
        # Try multiple possible locations
        possible_paths = [
            "COLUMNIST_PROMPT.md",
            "docs/COLUMNIST_PROMPT.md",
            os.path.join(os.path.dirname(__file__), "..", "COLUMNIST_PROMPT.md"),
            os.path.join(os.path.dirname(__file__), "..", "docs", "COLUMNIST_PROMPT.md"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read()
        
        raise FileNotFoundError(
            "Could not find COLUMNIST_PROMPT.md. Please ensure it exists in the project root or docs/ directory."
        )
    
    @staticmethod
    def generate_user_prompt(week: int, data_context: str, history_context: str) -> str:
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
        model: str = "gpt-4"
    ) -> Optional[str]:
        """
        Generate recap using OpenAI API
        
        Args:
            week: Week number
            data_context: Context from ContextBuilder
            history_context: Previous recaps context
            client: OpenAI client instance
            model: OpenAI model to use
        
        Returns:
            Generated recap text or None if error
        """
        try:
            system_prompt = LLMClient.load_columnist_prompt()
            user_prompt = LLMClient.generate_user_prompt(week, data_context, history_context)
            
            print(f"🤖 Generating recap with OpenAI ({model})...")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=2000,
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
        model: str = "claude-sonnet-4-5-20250929"
    ) -> Optional[str]:
        """
        Generate recap using Anthropic API
        
        Args:
            week: Week number
            data_context: Context from ContextBuilder
            history_context: Previous recaps context
            client: Anthropic client instance
            model: Anthropic model to use
        
        Returns:
            Generated recap text or None if error
        """
        try:
            system_prompt = LLMClient.load_columnist_prompt()
            user_prompt = LLMClient.generate_user_prompt(week, data_context, history_context)
            
            print(f"🤖 Generating recap with Anthropic ({model})...")
            
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0.8,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            
            return response.content[0].text
        
        except Exception as e:
            print(f"❌ Error generating recap with Anthropic: {e}")
            return None

