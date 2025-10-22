#!/usr/bin/env python3
"""
Fantasy Football Recap Generator
Generates weekly roast-style recaps using the API and LLM
"""

import json
import os
from typing import Dict, List, Optional
import requests
from datetime import datetime
from dotenv import load_dotenv

from src.trend_tracker import TrendTracker
from src.ownership_stats import OwnershipStats
from src.context_builder import ContextBuilder
from src.llm_client import LLMClient

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
OUTPUT_DIR = "output"
RECAP_HISTORY_FILE = "recap_history.json"


class RecapGenerator:
    """Generates weekly fantasy football recaps with a roasting columnist persona"""

    def __init__(self, api_url: str = API_BASE_URL):
        self.api_url = api_url
        self.recap_history = self._load_history()
        self.trend_tracker = TrendTracker()
        self.ownership_stats = OwnershipStats()
        self.context_builder = ContextBuilder(self.trend_tracker, self.ownership_stats)
        self.llm_client = LLMClient()

    def _load_history(self) -> List[Dict]:
        """Load previous recap history for memory/callbacks"""
        if os.path.exists(RECAP_HISTORY_FILE):
            with open(RECAP_HISTORY_FILE, "r") as f:
                return json.load(f)
        return []

    def _save_history(self, week: int, recap: str, context: Dict):
        """Save recap to history for future callbacks"""
        entry = {
            "week": week,
            "date": datetime.now().isoformat(),
            "recap": recap,
            "context": context,
        }
        self.recap_history.append(entry)

        with open(RECAP_HISTORY_FILE, "w") as f:
            json.dump(self.recap_history, f, indent=2)

    def fetch_week_data(self, week: int) -> Dict:
        """Fetch all necessary data for the week from API"""
        print(f"📊 Fetching data for Week {week}...")

        data = {}

        try:
            # Get league info
            resp = requests.get(f"{self.api_url}/api/league")
            resp.raise_for_status()
            data["league"] = resp.json()

            # Get matchups
            resp = requests.get(f"{self.api_url}/api/matchups/{week}")
            resp.raise_for_status()
            data["matchups"] = resp.json()

            # Get week stats
            resp = requests.get(f"{self.api_url}/api/stats/week/{week}")
            resp.raise_for_status()
            data["week_stats"] = resp.json()

            # Get teams
            resp = requests.get(f"{self.api_url}/api/teams")
            resp.raise_for_status()
            data["teams"] = resp.json()

            # Get standings
            resp = requests.get(f"{self.api_url}/api/standings")
            resp.raise_for_status()
            data["standings"] = resp.json()

            # Store API URL for context builder
            data["api_url"] = self.api_url

            print(f"✅ Data fetched successfully")
            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data: {e}")
            return {}

    def build_context(self, week_data: Dict, week: int = None) -> str:
        """Build context for LLM - delegates to ContextBuilder"""
        return self.context_builder.build_context(week_data, week)

    def get_previous_recaps_context(self, limit: int = 3) -> str:
        """Get context from previous recaps to avoid repetition"""
        if not self.recap_history:
            return "No previous recaps."

        recent = self.recap_history[-limit:]
        context = "## Previous Recaps (for memory - avoid repeating these burns):\n\n"

        for entry in recent:
            context += f"**Week {entry['week']}:**\n"
            # Include just headlines and key phrases to show what's been covered
            lines = entry["recap"].split("\n")
            if lines:
                context += f"Headline: {lines[0]}\n"
                # Sample a few roasts
                roast_lines = [
                    l for l in lines[2:10] if l.strip() and not l.startswith("#")
                ]
                if roast_lines:
                    context += "Sample roasts:\n"
                    for line in roast_lines[:3]:
                        context += f"- {line[:100]}...\n"
            context += "\n"

        return context

    def generate_recap(self, week: int, llm_client=None) -> Optional[str]:
        """
        Generate recap for a week
        
        This is a convenience method that prints instructions.
        Use generate_recap_with_openai() or generate_recap_with_anthropic() directly.
        """
        print("⚠️  Please use one of these methods:")
        print("\n# Option 1: OpenAI")
        print("from openai import OpenAI")
        print("client = OpenAI(api_key='your-key')")
        print(f"recap = generator.generate_recap_with_openai(week={week}, client=client)")
        print("\n# Option 2: Anthropic")
        print("from anthropic import Anthropic")
        print("client = Anthropic(api_key='your-key')")
        print(f"recap = generator.generate_recap_with_anthropic(week={week}, client=client)")
        return None

    def generate_recap_with_openai(
        self, week: int, client, model: str = "gpt-4", use_v2_format: bool = True
    ) -> Optional[str]:
        """
        Generate recap using OpenAI API
        
        Args:
            week: Week number
            client: OpenAI client instance
            model: OpenAI model to use
            use_v2_format: If True, use new V2 structured format
        """
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        data_context = self.context_builder.build_context(week_data, week, use_v2_format=use_v2_format)
        history_context = self.get_previous_recaps_context()

        recap = self.llm_client.generate_with_openai(
            week, data_context, history_context, client, model, use_v2=use_v2_format
        )

        if recap:
            # Save to history and output
            format_type = "V2" if use_v2_format else "V1"
            self._save_history(week, recap, {"model": model, "format": format_type, "data": week_data})
            self._save_recap_to_file(week, recap)

        return recap

    def generate_recap_with_anthropic(
        self, week: int, client, model: str = "claude-sonnet-4-5-20250929", use_v2_format: bool = True
    ) -> Optional[str]:
        """
        Generate recap using Anthropic API
        
        Args:
            week: Week number
            client: Anthropic client instance
            model: Anthropic model to use
            use_v2_format: If True, use new V2 structured format
        """
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        data_context = self.context_builder.build_context(week_data, week, use_v2_format=use_v2_format)
        history_context = self.get_previous_recaps_context()

        recap = self.llm_client.generate_with_anthropic(
            week, data_context, history_context, client, model, use_v2=use_v2_format
        )

        if recap:
            # Save to history and output
            format_type = "V2" if use_v2_format else "V1"
            self._save_history(week, recap, {"model": model, "format": format_type, "data": week_data})
            self._save_recap_to_file(week, recap)

        return recap

    def _save_recap_to_file(self, week: int, recap: str):
        """Save generated recap to markdown file"""
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        filename = os.path.join(OUTPUT_DIR, f"week-{week}-recap.md")
        with open(filename, "w") as f:
            f.write(recap)

        print(f"✅ Recap saved to {filename}")


def main():
    """CLI for generating recaps"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate fantasy football weekly recaps"
    )
    parser.add_argument("week", type=int, help="Week number to generate recap for")
    parser.add_argument("--api-url", default=API_BASE_URL, help="API base URL")
    parser.add_argument(
        "--context-only", action="store_true", help="Only generate context, no LLM call"
    )

    args = parser.parse_args()

    generator = RecapGenerator(api_url=args.api_url)

    if args.context_only:
        # Just generate and print context for manual use
        week_data = generator.fetch_week_data(args.week)
        if week_data:
            context = generator.build_context(week_data, args.week)
            print("\n" + "=" * 80)
            print("CONTEXT FOR LLM")
            print("=" * 80)
            print(context)
            print("\n" + "=" * 80)

            # Also save to file
            if not os.path.exists(OUTPUT_DIR):
                os.makedirs(OUTPUT_DIR)
            context_file = os.path.join(OUTPUT_DIR, f"week-{args.week}-context.txt")
            with open(context_file, "w") as f:
                try:
                    system_prompt = LLMClient.load_columnist_prompt()
                    f.write(system_prompt)
                except Exception as e:
                    f.write(f"# Could not load system prompt: {e}\n\n")
                f.write("\n\n" + "=" * 80 + "\n\n")
                f.write(context)
            print(f"\n✅ Full prompt saved to {context_file}")
            print("   Copy this to your LLM to generate the recap!")
    else:
        print("⚠️  To generate recaps with an LLM, use one of these methods:")
        print("\n# Option 1: OpenAI")
        print("from openai import OpenAI")
        print("from src.recap_generator import RecapGenerator")
        print("")
        print("client = OpenAI(api_key='your-key')")
        print("generator = RecapGenerator()")
        print(
            f"recap = generator.generate_recap_with_openai(week={args.week}, client=client)"
        )
        print("print(recap)")
        print("\n# Option 2: Anthropic")
        print("from anthropic import Anthropic")
        print("from src.recap_generator import RecapGenerator")
        print("")
        print("client = Anthropic(api_key='your-key')")
        print("generator = RecapGenerator()")
        print(
            f"recap = generator.generate_recap_with_anthropic(week={args.week}, client=client)"
        )
        print("print(recap)")
        print("\n# Option 3: Get context for manual use")
        print(f"python -m src.recap_generator {args.week} --context-only")


if __name__ == "__main__":
    main()
