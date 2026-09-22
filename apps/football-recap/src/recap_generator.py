#!/usr/bin/env python3
"""
Fantasy Football Recap Generator
Generates weekly roast-style recaps using the API and LLM
"""

import json
import os
from typing import Any, Dict, List, Optional
import requests
from datetime import datetime
from dotenv import load_dotenv

from src.trend_tracker import TrendTracker
from src.ownership_stats import OwnershipStats
from src.context_builder import ContextBuilder
from src.llm_client import LLMClient
from src.fetch_league_data import get_fetcher
from src.yahoo_fetcher import YahooLeagueFetcher
from src.safe_calendar import calendar_hook
from src.constants import format_slack_mention

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
OUTPUT_DIR = "output"
RECAP_HISTORY_FILE = "recap_history.json"


class RecapGenerator:
    """Generates weekly fantasy football recaps in the house voice (The Commissioner's Ghost)."""

    def __init__(self, fetcher: Optional[YahooLeagueFetcher] = None):
        # Lazy — real fetcher connects to Yahoo on first data pull.
        self._fetcher = fetcher
        self.recap_history = self._load_history()
        self.trend_tracker = TrendTracker()
        self.ownership_stats = OwnershipStats()
        self.context_builder = ContextBuilder(self.trend_tracker, self.ownership_stats)
        self.llm_client = LLMClient()

    @property
    def fetcher(self) -> YahooLeagueFetcher:
        if self._fetcher is None:
            self._fetcher = get_fetcher()
        return self._fetcher

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
        Unused. Recaps do not ingest NewsAPI. Current events come from
        the allowlist calendar (``src.safe_calendar``) or ``week_data`` only.
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
        """Fetch all necessary data for the week directly from Yahoo."""
        print(f"📊 Fetching data for Week {week} from Yahoo...")
        try:
            data = self.fetcher.fetch_all_for_week(week)
            print("✅ Data fetched successfully")
            return data
        except Exception as e:
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

    def _pick_bit_of_the_week(self, week_data: Dict[str, Any]) -> Optional[str]:
        """
        Data-picked lede mechanic. Same Ghost, different opening angle.

        Prefers a nail-biter, then a blowout, then an upset. Skip if none fire.
        """
        superlatives = week_data.get("superlatives") or {}
        nail = superlatives.get("nailbiter_of_the_week")
        if nail:
            return (
                f"Lead League Pulse with the nail-biter: {nail['team1']} vs "
                f"{nail['team2']} came down to {nail['margin']} points."
            )
        blowout = superlatives.get("blowout_of_the_week")
        if blowout:
            winner = format_slack_mention(
                team_name=blowout.get("team", ""),
                owner_name=blowout.get("owner") or "",
            )
            loser = format_slack_mention(
                team_name=blowout.get("opponent", ""),
                owner_name=blowout.get("opponent_owner") or "",
            )
            return (
                f"Lead League Pulse with the blowout: {winner}'s {blowout['team']} "
                f"over {loser}'s {blowout['opponent']} by {blowout['margin']} points."
            )
        upset = superlatives.get("upset_of_the_week")
        if upset:
            winner = format_slack_mention(
                team_name=upset.get("winner", ""),
                owner_name=upset.get("winner_owner", ""),
            )
            loser = format_slack_mention(
                team_name=upset.get("loser", ""),
                owner_name=upset.get("loser_owner", ""),
            )
            return (
                f"Lead League Pulse with the upset: {winner}'s {upset['winner']} beat "
                f"{loser}'s {upset['loser']} despite being projected "
                f"{upset['projection_gap']} points lower."
            )
        return None

    def prepare_recap_context(
        self,
        week: int,
        *,
        use_v2_format: bool = True,
        use_v3_format: bool = True,
        include_news: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch Yahoo data and build the full LLM context bundle — no API call.

        Used by the Cursor Automation flow: Python shapes the data; the
        automation agent writes the recap from :func:`save_prepared_context`
        output plus ``docs/COLUMNIST_PROMPT_V3.md``.

        Returns a dict with ``week``, ``week_data``, ``data_context``,
        ``history_context``, ``closing_line``, ``calendar_hook``,
        ``bit_of_the_week``, and ``user_prompt``.
        """
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        data_context = self.context_builder.build_context(
            week_data, week, use_v2_format=(use_v3_format or use_v2_format)
        )

        # Current events: allowlist calendar only. NewsAPI is never injected.
        _ = include_news  # kept for call-site compatibility; unused

        hook = calendar_hook(week=week)
        if hook:
            data_context = (
                data_context
                + "\n\n"
                + "## CALENDAR_HOOK (optional — same Ghost, calendar-aware)\n\n"
                + hook
                + "\n\nUse this at most once (lede or a passing line). "
                + "Do not invent other world events."
            )

        bit = self._pick_bit_of_the_week(week_data)
        if bit:
            data_context = (
                data_context
                + "\n\n"
                + "## BIT_OF_THE_WEEK (lede mechanic — not a new narrator)\n\n"
                + bit
                + "\n\nSame Commissioner's Ghost. Different opening angle."
            )

        closing_line = self._get_unique_closing_line()
        data_context = (
            data_context
            + "\n\n"
            + f'## CLOSING LINE (Use this exact line)\n\n> "{closing_line}"'
        )

        history_context = self.get_previous_recaps_context()
        user_prompt = LLMClient.generate_user_prompt(
            week, data_context, history_context
        )

        return {
            "week": week,
            "week_data": week_data,
            "data_context": data_context,
            "history_context": history_context,
            "closing_line": closing_line,
            "calendar_hook": hook,
            "bit_of_the_week": bit,
            "user_prompt": user_prompt,
        }

    def save_prepared_context(self, bundle: Dict[str, Any]) -> str:
        """
        Persist a :func:`prepare_recap_context` bundle for the automation agent.

        Writes:
          - ``output/week-N-context.md`` — data + history + write instruction
          - ``output/week-N-context.meta.json`` — closing line, calendar hook, etc.
        """
        week = int(bundle["week"])
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        context_path = os.path.join(OUTPUT_DIR, f"week-{week}-context.md")
        with open(context_path, "w") as f:
            f.write(f"# Week {week} Recap — Context Bundle\n\n")
            f.write(
                "The automation agent reads this file together with "
                "`docs/COLUMNIST_PROMPT_V3.md` to write the recap.\n\n"
            )
            f.write("---\n\n")
            f.write(bundle["user_prompt"])
            f.write("\n")

        meta_path = os.path.join(OUTPUT_DIR, f"week-{week}-context.meta.json")
        league = bundle.get("week_data", {}).get("league", {})
        meta = {
            "week": week,
            "house_voice": "The Commissioner's Ghost",
            "closing_line": bundle.get("closing_line"),
            "calendar_hook": bundle.get("calendar_hook"),
            "bit_of_the_week": bundle.get("bit_of_the_week"),
            "league_name": league.get("league_name"),
            "prepared_at": datetime.now().isoformat(),
            "context_file": context_path,
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Persisted separately (not just in history) so `finalize_recap()` can
        # attach the structured week_data to history even when called from a
        # different process than the one that fetched it (the automation
        # flow: prepare -> [agent writes recap] -> finalize are 3 steps).
        weekdata_path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")
        with open(weekdata_path, "w") as f:
            json.dump(bundle.get("week_data", {}), f, indent=2, default=str)

        print(f"✅ Context saved to {context_path}")
        print(f"✅ Metadata saved to {meta_path}")
        return context_path

    def finalize_recap(
        self,
        week: int,
        recap: Optional[str] = None,
        *,
        source: str = "cursor-automation",
        week_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a finished recap in ``recap_history.json``, including the
        structured ``week_data`` so season-long features (leaderboards,
        Canvas) can aggregate across weeks without re-fetching Yahoo.

        Call after the automation agent writes ``output/week-N-recap.md``.
        If ``recap`` is omitted, reads from that file. If ``week_data`` is
        omitted, loads it from ``output/week-N-weekdata.json`` (written by
        :func:`save_prepared_context`) when present.
        """
        recap_path = os.path.join(OUTPUT_DIR, f"week-{week}-recap.md")
        if recap is None:
            if not os.path.exists(recap_path):
                print(f"❌ Recap file not found: {recap_path}")
                return False
            with open(recap_path, "r") as f:
                recap = f.read()

        if not recap or not recap.strip():
            print(f"❌ Recap file is empty: {recap_path}")
            return False

        if week_data is None:
            weekdata_path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")
            if os.path.exists(weekdata_path):
                with open(weekdata_path, "r") as f:
                    week_data = json.load(f)

        context: Dict[str, Any] = {"source": source, "format": "V3"}
        if week_data:
            context["data"] = week_data

        self._save_history(week, recap, context)
        print(f"✅ Recap history updated for week {week}")
        return True

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
    ) -> Optional[str]:
        """
        Generate recap using OpenAI API

        Args:
            week: Week number
            client: OpenAI client instance
            model: OpenAI model to use
            use_v2_format: Kept for call-site compatibility; context always uses V3 structure
            use_v3_format: Kept for call-site compatibility; always True in practice
        """
        bundle = self.prepare_recap_context(
            week,
            use_v2_format=use_v2_format,
            use_v3_format=use_v3_format,
        )
        if not bundle:
            return None

        recap = self.llm_client.generate_with_openai(
            week,
            bundle["data_context"],
            bundle["history_context"],
            client,
            model,
        )

        if recap:
            self._save_history(
                week,
                recap,
                {
                    "model": model,
                    "format": "V3",
                    "data": bundle["week_data"],
                },
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
    ) -> Optional[str]:
        """
        Generate recap using Anthropic API

        Args:
            week: Week number
            client: Anthropic client instance
            model: Anthropic model to use
            use_v2_format: Kept for call-site compatibility; context always uses V3 structure
            use_v3_format: Kept for call-site compatibility; always True in practice
        """
        bundle = self.prepare_recap_context(
            week,
            use_v2_format=use_v2_format,
            use_v3_format=use_v3_format,
        )
        if not bundle:
            return None

        recap = self.llm_client.generate_with_anthropic(
            week,
            bundle["data_context"],
            bundle["history_context"],
            client,
            model,
        )

        if recap:
            self._save_history(
                week,
                recap,
                {
                    "model": model,
                    "format": "V3",
                    "data": bundle["week_data"],
                },
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
    parser.add_argument(
        "--context-only", action="store_true", help="Only generate context, no LLM call"
    )

    args = parser.parse_args()

    generator = RecapGenerator()

    if args.context_only:
        bundle = generator.prepare_recap_context(args.week, include_news=False)
        if not bundle:
            print("❌ Failed to prepare context")
            return
        context_path = generator.save_prepared_context(bundle)
        print("\n" + "=" * 80)
        print("CONTEXT FOR LLM / CURSOR AGENT")
        print("=" * 80)
        print(bundle["user_prompt"][:2000])
        if len(bundle["user_prompt"]) > 2000:
            print(f"\n... ({len(bundle['user_prompt'])} chars total — see file)")
        print("\n" + "=" * 80)
        print(f"\n✅ Full context saved to {context_path}")
        print("   Pair with docs/COLUMNIST_PROMPT_V3.md to write the recap.")
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
