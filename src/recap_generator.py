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
        """
        Save recap to history for future callbacks.

        If a recap for this week already exists, it will be **replaced**
        rather than duplicated. This ensures that regenerating a recap for
        the same week updates history instead of appending another entry.
        """
        # CRITICAL: Reload from disk first since RecapGenerator is instantiated per-request
        if os.path.exists(RECAP_HISTORY_FILE):
            with open(RECAP_HISTORY_FILE, "r") as f:
                current_history = json.load(f)
        else:
            current_history = []

        entry = {
            "week": week,
            "date": datetime.now().isoformat(),
            "recap": recap,
            "context": context,
        }

        # Remove any existing entries for this week
        filtered_history = [e for e in current_history if e.get("week") != week]

        # Append the new version
        filtered_history.append(entry)

        # Write back to disk
        with open(RECAP_HISTORY_FILE, "w") as f:
            json.dump(filtered_history, f, indent=2)

        # Update in-memory copy
        self.recap_history = filtered_history

    def fetch_news_context(self, max_per_category: int = 5) -> Optional[Dict]:
        """
        Fetch a small set of recent headlines for use as metaphors / callbacks.

        Uses NewsAPI.org if NEWSAPI_API_KEY is configured. If not configured or
        any error occurs, returns None and the recap will be generated without
        news context.
        """
        api_key = os.getenv("NEWSAPI_API_KEY")
        if not api_key:
            return None

        base_url = "https://newsapi.org/v2/top-headlines"
        categories = ["sports", "entertainment", "technology"]
        headers = {"X-Api-Key": api_key}

        context: Dict[str, Dict[str, List[str]]] = {"categories": {}}

        # Use today's date; NewsAPI top-headlines are already "current"
        today = datetime.utcnow().date().isoformat()
        context["as_of"] = today
        context["source"] = "newsapi.org top-headlines"

        for category in categories:
            try:
                resp = requests.get(
                    base_url,
                    params={
                        "country": "us",
                        "category": category,
                        "pageSize": max_per_category,
                    },
                    headers=headers,
                    timeout=10,
                )
                resp.raise_for_status()
                articles = resp.json().get("articles", [])
                titles = [a.get("title") for a in articles if a.get("title")]
                if titles:
                    context["categories"][category] = titles[:max_per_category]
            except Exception as e:
                print(f"⚠️  Error fetching {category} headlines from NewsAPI: {e}")

        # If we didn't get any categories, treat as no context
        if not context["categories"]:
            return None

        return context

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

            print("✅ Data fetched successfully")
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
                    line
                    for line in lines[2:10]
                    if line.strip() and not line.startswith("#")
                ]
                if roast_lines:
                    context += "Sample roasts:\n"
                    for line in roast_lines[:3]:
                        context += f"- {line[:100]}...\n"
            context += "\n"

        return context

    # Closing lines to rotate through (avoids repetition)
    CLOSING_LINES = [
        "Fantasy football: where every lineup is a confession of your worst instincts.",
        "See you next week, when someone's bench will once again outscore their entire starting roster.",
        "Until next time—may your projections be less fictional than usual.",
        "Another week, another reminder that we're all just guessing with extra steps.",
        "Fantasy football: the only sport where doing nothing might be the optimal strategy.",
        "Remember: the pain is temporary, but the screenshots are forever.",
        "Next week's disasters are already loading. See you then.",
        "The only thing more unpredictable than fantasy football is why we keep playing it.",
        "May your waiver claims clear and your opponents' stars rest.",
        "Fantasy football: turning Sundays into therapy sessions since 1963.",
        "Same time next week, when we'll pretend we learned something from this.",
        "Your bench thanks you for the rest. Your starters do not.",
        "Until then, may your boom players actually boom.",
        "Fantasy football: proving that confidence and competence are unrelated.",
        "See you next week, assuming your playoff hopes survive that long.",
        "The algorithm giveth, and the algorithm taketh away. Mostly taketh.",
        "Another week closer to accepting that projections are just suggestions.",
        "Fantasy football: where hope meets spreadsheets and loses.",
        "Next week's bad decisions are already forming. Stay tuned.",
        "May your studs stud and your duds... well, they're going to dud.",
    ]

    def _get_unique_closing_line(self) -> str:
        """
        Get a closing line that hasn't been used in recent recaps.
        Ensures variety in weekly recaps.
        """
        import random
        
        # Get recently used closing lines from history
        used_lines = set()
        for entry in self.recap_history[-5:]:  # Check last 5 recaps
            recap_text = entry.get("recap", "")
            # Try to find which closing line was used
            for line in self.CLOSING_LINES:
                if line.lower() in recap_text.lower():
                    used_lines.add(line)
        
        # Get available lines (not recently used)
        available = [line for line in self.CLOSING_LINES if line not in used_lines]
        
        # If all lines have been used, just pick randomly
        if not available:
            available = self.CLOSING_LINES
        
        return random.choice(available)

    # Seasonal persona mappings (month, day_start, day_end) -> personas
    SEASONAL_PERSONAS = {
        # Thanksgiving week (Nov 20-30)
        "thanksgiving": {
            "dates": [(11, 20, 30)],
            "personas": [
                "Thanksgiving Host Ghost",
                "Drunk Uncle at Thanksgiving",
                "Food Critic Ghost",
            ],
        },
        # Black Friday (Nov 25-30)
        "black_friday": {
            "dates": [(11, 25, 30)],
            "personas": ["Black Friday Shopper Ghost"],
        },
        # Christmas/Holiday season (Dec 15-26)
        "christmas": {
            "dates": [(12, 15, 26)],
            "personas": ["Holiday Mall Santa Ghost"],
        },
        # New Year's (Dec 27 - Jan 5)
        "new_years": {
            "dates": [(12, 27, 31), (1, 1, 5)],
            "personas": ["New Year's Eve Host Ghost"],
        },
        # Valentine's (Feb 10-15)
        "valentines": {
            "dates": [(2, 10, 15)],
            "personas": ["Valentine's Cupid Ghost"],
        },
        # March Madness (Mar 14 - Apr 8)
        "march_madness": {
            "dates": [(3, 14, 31), (4, 1, 8)],
            "personas": ["March Madness Bracket Ghost"],
        },
        # Tax season (Apr 1-18)
        "tax_season": {
            "dates": [(4, 1, 18)],
            "personas": ["Tax Season Auditor Ghost"],
        },
        # Fantasy playoffs (typically weeks 14-17, Dec)
        "fantasy_playoffs": {
            "dates": [(12, 1, 31)],
            "personas": ["Playoff Elimination Ghost"],
        },
        # Summer/offseason (Jun-Aug)
        "summer": {
            "dates": [(6, 1, 30), (7, 1, 31), (8, 1, 31)],
            "personas": ["Summer Intern Ghost"],
        },
        # Draft season (Aug 15 - Sep 10)
        "draft_season": {
            "dates": [(8, 15, 31), (9, 1, 10)],
            "personas": ["Fantasy Draft Auctioneer"],
        },
    }

    # Standard (non-seasonal) personas
    STANDARD_PERSONAS = [
        # Pop Culture (universally relatable)
        "True-Crime Narrator Ghost",
        "Reality TV Host Ghost",
        "Nature Documentary Ghost",
        "Film Noir Detective Ghost",
        "Infomercial Pitchman Ghost",
        "Local News Anchor Ghost",
        # Sports
        "Vegas Bookie Ghost",
        "Beat Reporter Ghost",
        "NFL Films Narrator Ghost",
        # Everyday Characters (everyone knows these people)
        "Therapist Ghost",
        "Disappointed Dad Ghost",
        "Yelp Reviewer Ghost",
        "Passive-Aggressive Coworker",
        "Food Critic Ghost",
        "Frustrated Dasher Ghost",
    ]

    def get_seasonal_personas(self) -> List[str]:
        """
        Get personas that match the current date/season.
        Returns empty list if no seasonal match.
        """
        today = datetime.now()
        month, day = today.month, today.day
        
        seasonal = []
        for season_name, config in self.SEASONAL_PERSONAS.items():
            for date_range in config["dates"]:
                range_month, range_start, range_end = date_range
                if month == range_month and range_start <= day <= range_end:
                    seasonal.extend(config["personas"])
        
        return list(set(seasonal))  # Dedupe

    def get_next_persona_seed(self, prefer_seasonal: bool = True) -> str:
        """
        Determine which persona to use for this week's recap.
        
        Args:
            prefer_seasonal: If True (default), prefer seasonal personas when available.
        
        Returns:
            Persona name string.
        """
        import random
        
        # Check if user explicitly set a persona via env var
        env_persona = os.getenv("COLUMNIST_PERSONA_SEED")
        if env_persona:
            return env_persona

        # Get seasonal personas if applicable
        seasonal_personas = self.get_seasonal_personas() if prefer_seasonal else []
        
        # Combine with standard personas (seasonal get priority in selection)
        if seasonal_personas:
            # 70% chance to pick seasonal, 30% standard
            if random.random() < 0.7:
                personas = seasonal_personas
            else:
                personas = self.STANDARD_PERSONAS
        else:
            personas = self.STANDARD_PERSONAS

        # Try to pick one different from last week
        if self.recap_history:
            last_recap = self.recap_history[-1].get("recap", "")
            last_persona = None
            all_personas = seasonal_personas + self.STANDARD_PERSONAS
            for persona in all_personas:
                if persona in last_recap or persona.replace(" Ghost", "") in last_recap:
                    last_persona = persona
                    break

            # Pick a different one
            available = [p for p in personas if p != last_persona]
            if available:
                return random.choice(available)

        # Default: pick randomly from chosen pool
        return random.choice(personas)

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
        print(
            f"recap = generator.generate_recap_with_openai(week={week}, client=client)"
        )
        print("\n# Option 2: Anthropic")
        print("from anthropic import Anthropic")
        print("client = Anthropic(api_key='your-key')")
        print(
            f"recap = generator.generate_recap_with_anthropic(week={week}, client=client)"
        )
        return None

    def generate_recap_with_openai(
        self,
        week: int,
        client,
        model: str = "gpt-4",
        use_v2_format: bool = True,
        use_v3_format: bool = True,
        persona: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate recap using OpenAI API

        Args:
            week: Week number
            client: OpenAI client instance
            model: OpenAI model to use
            use_v2_format: If True and use_v3_format is False, use V2 structured format
            use_v3_format: If True, use V3 lean comedy-focused format (recommended)
            persona: Optional persona to use (overrides auto-rotation)
        """
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        data_context = self.context_builder.build_context(
            week_data, week, use_v2_format=(use_v3_format or use_v2_format)
        )

        # Optionally enrich with recent news / pop culture context
        news_context = self.fetch_news_context()
        if news_context:
            news_lines: List[str] = []
            news_lines.append("## NEWS_CONTEXT (Recent headlines for metaphors only)")
            news_lines.append(
                f"As of {news_context.get('as_of')}, sourced from {news_context.get('source')}."
            )
            for category, titles in news_context.get("categories", {}).items():
                if not titles:
                    continue
                label = category.capitalize()
                news_lines.append(f"- {label}:")
                for title in titles:
                    news_lines.append(f"  - {title}")
            data_context = data_context + "\n\n" + "\n".join(news_lines)

        # Add persona seed to ensure variety week-to-week
        # Use provided persona if specified, otherwise auto-rotate
        persona_seed = persona if persona else self.get_next_persona_seed()
        persona_lines = [
            "## PERSONA_SEED (This week's columnist mode)",
            f"Use this persona for the entire recap: **{persona_seed}**",
            "",
            "**CRITICAL PERSONA REQUIREMENTS:**",
            "1. Use this persona's specific vocabulary 6+ times minimum.",
            "2. Make the persona evident in: League Pulse (immediately), at least 3 matchup writeups, and Power Rankings.",
            "3. DO NOT announce the persona in the text. Show it through language and style.",
            "4. DO NOT break character or slip into generic sports writing.",
            "5. Frame disasters through YOUR persona's lens: How would THIS specific persona describe this failure?",
            "",
            f"Remember: You are {persona_seed}. Commit fully to this mode's vocabulary and tone.",
        ]
        data_context = data_context + "\n\n" + "\n".join(persona_lines)

        # Add closing line instruction to avoid repetition
        closing_line = self._get_unique_closing_line()
        data_context = data_context + "\n\n" + f"## CLOSING LINE (Use this exact line)\n\n> \"{closing_line}\""

        history_context = self.get_previous_recaps_context()

        recap = self.llm_client.generate_with_openai(
            week,
            data_context,
            history_context,
            client,
            model,
            use_v2=use_v2_format,
            use_v3=use_v3_format,
            persona_seed=None,  # Already injected into data_context
        )

        if recap:
            # Save to history and output
            if use_v3_format:
                format_type = "V3"
            elif use_v2_format:
                format_type = "V2"
            else:
                format_type = "V1"
            self._save_history(
                week, recap, {"model": model, "format": format_type, "data": week_data}
            )
            self._save_recap_to_file(week, recap)

        return recap

    def generate_recap_with_anthropic(
        self,
        week: int,
        client,
        model: str = "claude-sonnet-4-5-20250929",
        use_v2_format: bool = True,
        use_v3_format: bool = True,
        persona: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate recap using Anthropic API

        Args:
            week: Week number
            client: Anthropic client instance
            model: Anthropic model to use
            use_v2_format: If True and use_v3_format is False, use V2 structured format
            use_v3_format: If True, use V3 lean comedy-focused format (recommended)
            persona: Optional persona to use (overrides auto-rotation)
        """
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        data_context = self.context_builder.build_context(
            week_data, week, use_v2_format=(use_v3_format or use_v2_format)
        )

        # Optionally enrich with recent news / pop culture context
        news_context = self.fetch_news_context()
        if news_context:
            news_lines: List[str] = []
            news_lines.append("## NEWS_CONTEXT (Recent headlines for metaphors only)")
            news_lines.append(
                f"As of {news_context.get('as_of')}, sourced from {news_context.get('source')}."
            )
            for category, titles in news_context.get("categories", {}).items():
                if not titles:
                    continue
                label = category.capitalize()
                news_lines.append(f"- {label}:")
                for title in titles:
                    news_lines.append(f"  - {title}")
            data_context = data_context + "\n\n" + "\n".join(news_lines)

        # Add persona seed to ensure variety week-to-week
        # Use provided persona if specified, otherwise auto-rotate
        persona_seed = persona if persona else self.get_next_persona_seed()
        persona_lines = [
            "## PERSONA_SEED (This week's columnist mode)",
            f"Use this persona for the entire recap: **{persona_seed}**",
            "",
            "**CRITICAL PERSONA REQUIREMENTS:**",
            "1. Use this persona's specific vocabulary 6+ times minimum.",
            "2. Make the persona evident in: League Pulse (immediately), at least 3 matchup writeups, and Power Rankings.",
            "3. DO NOT announce the persona in the text. Show it through language and style.",
            "4. DO NOT break character or slip into generic sports writing.",
            "5. Frame disasters through YOUR persona's lens: How would THIS specific persona describe this failure?",
            "",
            f"Remember: You are {persona_seed}. Commit fully to this mode's vocabulary and tone.",
        ]
        data_context = data_context + "\n\n" + "\n".join(persona_lines)

        # Add closing line instruction to avoid repetition
        closing_line = self._get_unique_closing_line()
        data_context = data_context + "\n\n" + f"## CLOSING LINE (Use this exact line)\n\n> \"{closing_line}\""

        history_context = self.get_previous_recaps_context()

        recap = self.llm_client.generate_with_anthropic(
            week,
            data_context,
            history_context,
            client,
            model,
            use_v2=use_v2_format,
            use_v3=use_v3_format,
            persona_seed=None,  # Already injected into data_context
        )

        if recap:
            # Save to history and output
            if use_v3_format:
                format_type = "V3"
            elif use_v2_format:
                format_type = "V2"
            else:
                format_type = "V1"
            self._save_history(
                week, recap, {"model": model, "format": format_type, "data": week_data}
            )
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
