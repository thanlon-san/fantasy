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

    def _load_history(self) -> List[Dict]:
        """Load previous recap history for memory/callbacks"""
        if os.path.exists(RECAP_HISTORY_FILE):
            with open(RECAP_HISTORY_FILE, "r") as f:
                return json.load(f)
        return []

    def _format_player_stats(self, player: Dict) -> str:
        """Format detailed player stats for context"""
        stats = player.get("stats", {})
        if not stats or all(v == 0 for v in stats.values()):
            return ""

        parts = []
        # Passing
        if stats.get("passing_yards", 0) > 0:
            parts.append(
                f"{stats['passing_yards']} pass yds, {stats['passing_tds']} TD, {stats['passing_ints']} INT"
            )
        # Rushing
        if stats.get("rushing_attempts", 0) > 0:
            parts.append(
                f"{stats['rushing_attempts']} car, {stats['rushing_yards']} rush yds, {stats['rushing_tds']} rush TD"
            )
        # Receiving
        if stats.get("receiving_targets", 0) > 0:
            rec = stats["receiving_receptions"]
            tgt = stats["receiving_targets"]
            catch_rate = (rec / tgt * 100) if tgt > 0 else 0
            parts.append(
                f"{rec}/{tgt} rec ({catch_rate:.0f}%), {stats['receiving_yards']} rec yds, {stats['receiving_tds']} rec TD"
            )

        return f" [{'; '.join(parts)}]" if parts else ""

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
            data["stats"] = resp.json()

            # Get standings
            resp = requests.get(f"{self.api_url}/api/standings")
            resp.raise_for_status()
            data["standings"] = resp.json()

            print(f"✅ Fetched {len(data['matchups']['matchups'])} matchups")
            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data: {e}")
            print(f"   Make sure the API is running at {self.api_url}")
            return None

    def build_context(self, week_data: Dict) -> str:
        """Build detailed context for the LLM from API data"""

        context_parts = []

        # League info
        league = week_data["league"]
        context_parts.append(
            f"# {league['league_name']} - Week {league['current_week']}"
        )
        context_parts.append("")

        # Week highlights
        stats = week_data["stats"]
        context_parts.append("## Week Highlights")
        context_parts.append(
            f"- 👑 Highest Score: {stats['highest_score']['team']} ({stats['highest_score']['points']} pts)"
        )
        context_parts.append(
            f"- 🗑️ Lowest Score: {stats['lowest_score']['team']} ({stats['lowest_score']['points']} pts)"
        )
        context_parts.append(
            f"- 💥 Biggest Blowout: {stats['biggest_blowout']['winner']} destroyed {stats['biggest_blowout']['loser']} by {stats['biggest_blowout']['margin']} pts"
        )
        context_parts.append(
            f"- 😰 Closest Game: {stats['closest_game']['team1']} vs {stats['closest_game']['team2']} (margin: {stats['closest_game']['margin']} pts)"
        )
        context_parts.append(
            f"- 🪑 Most Bench Points: {stats['most_bench_points']['team']} ({stats['most_bench_points']['points']} pts)"
        )
        context_parts.append("")

        # Matchup details
        context_parts.append("## Matchups")
        for matchup in week_data["matchups"]["matchups"]:
            home = matchup["home_team"]
            away = matchup["away_team"]

            context_parts.append(
                f"\n### Matchup {matchup['matchup_id']}: {home['team_name']} vs {away['team_name']}"
            )
            context_parts.append(
                f"**Final Score:** {home['team_name']} {home['score']} - {away['score']} {away['team_name']}"
            )
            context_parts.append(
                f"**Winner:** {matchup['winner']} (margin: {matchup['margin']} pts)"
            )
            context_parts.append(
                f"**Records:** {home['team_name']} ({home['record']}) | {away['team_name']} ({away['record']})"
            )

            # Home team analytics
            context_parts.append(f"\n**{home['team_name']} Analytics:**")
            context_parts.append(
                f"Score: {home['score']} (Projected: {sum(p['projected_points'] for p in home['starters']):.1f})"
            )

            # Position aggregates
            if "position_aggregates" in home:
                pos_agg = home["position_aggregates"]
                context_parts.append(
                    f"Position breakdown: QB={pos_agg.get('QB', 0)}, RB={pos_agg.get('RB', 0)}, WR={pos_agg.get('WR', 0)}, TE={pos_agg.get('TE', 0)}"
                )

            # Optimal lineup
            if "optimal_lineup" in home and "management_gap" in home:
                context_parts.append(
                    f"Optimal score: {home['optimal_lineup']['optimal_score']} (Management gap: {home['management_gap']} pts)"
                )
                if home["management_gap"] > 20:
                    context_parts.append(
                        f"  🚨 Left {home['management_gap']} points on table - ROASTABLE"
                    )

            context_parts.append(f"\n**{home['team_name']} Starters:**")

            for player in home["starters"]:
                if (
                    player["actual_points"] > 15
                    or abs(player["actual_points"] - player["projected_points"]) > 10
                ):
                    stats_str = self._format_player_stats(player)
                    context_parts.append(
                        f"  - {player['name']} ({player['position']}, {player['slot']}): Proj {player['projected_points']:.1f}, Actual {player['actual_points']:.1f}{stats_str}"
                    )

            # Home bench highlights
            bench_stars = [p for p in home["bench"] if p["actual_points"] > 15]
            if bench_stars:
                total_bench = sum(p["actual_points"] for p in home["bench"])
                context_parts.append(f"**Bench (total: {total_bench:.1f} pts):**")
                for player in bench_stars:
                    # Include start % to avoid roasting deep sleepers
                    start_pct = player.get("percent_started", 0)
                    roastable = "ROASTABLE" if start_pct > 20 else "deep sleeper"
                    context_parts.append(
                        f"  - BENCHED: {player['name']}: {player['actual_points']:.1f} pts (started {start_pct}% on ESPN - {roastable})"
                    )

            # Away team analytics
            context_parts.append(f"\n**{away['team_name']} Analytics:**")
            context_parts.append(
                f"Score: {away['score']} (Projected: {sum(p['projected_points'] for p in away['starters']):.1f})"
            )

            # Position aggregates
            if "position_aggregates" in away:
                pos_agg = away["position_aggregates"]
                context_parts.append(
                    f"Position breakdown: QB={pos_agg.get('QB', 0)}, RB={pos_agg.get('RB', 0)}, WR={pos_agg.get('WR', 0)}, TE={pos_agg.get('TE', 0)}"
                )

            # Optimal lineup
            if "optimal_lineup" in away and "management_gap" in away:
                context_parts.append(
                    f"Optimal score: {away['optimal_lineup']['optimal_score']} (Management gap: {away['management_gap']} pts)"
                )
                if away["management_gap"] > 20:
                    context_parts.append(
                        f"  🚨 Left {away['management_gap']} points on table - ROASTABLE"
                    )

            context_parts.append(f"\n**{away['team_name']} Starters:**")

            for player in away["starters"]:
                if (
                    player["actual_points"] > 15
                    or abs(player["actual_points"] - player["projected_points"]) > 10
                ):
                    stats_str = self._format_player_stats(player)
                    context_parts.append(
                        f"  - {player['name']} ({player['position']}, {player['slot']}): Proj {player['projected_points']:.1f}, Actual {player['actual_points']:.1f}{stats_str}"
                    )

            # Away bench highlights
            bench_stars = [p for p in away["bench"] if p["actual_points"] > 15]
            if bench_stars:
                total_bench = sum(p["actual_points"] for p in away["bench"])
                context_parts.append(f"**Bench (total: {total_bench:.1f} pts):**")
                for player in bench_stars:
                    # Include start % to avoid roasting deep sleepers
                    start_pct = player.get("percent_started", 0)
                    roastable = "ROASTABLE" if start_pct > 20 else "deep sleeper"
                    context_parts.append(
                        f"  - BENCHED: {player['name']}: {player['actual_points']:.1f} pts (started {start_pct}% on ESPN - {roastable})"
                    )

            context_parts.append("")

        # Current standings context
        context_parts.append("## Current Standings (Top 5)")
        for team in week_data["standings"]["standings"][:5]:
            context_parts.append(
                f"{team['rank']}. {team['team_name']}: {team['wins']}-{team['losses']} ({team['points_for']:.1f} PF)"
            )

        # Add interesting team-level metrics for roasting
        context_parts.append("\n## Team Activity & Efficiency Metrics (for roasting)")
        try:
            teams_response = requests.get(f"{self.api_url}/api/teams")
            teams_response.raise_for_status()
            all_teams = teams_response.json()["teams"]

            week_num = league["current_week"]
            total_teams = len(all_teams)

            for team_data in all_teams:
                acquisitions = team_data.get("acquisitions", 0)
                drops = team_data.get("drops", 0)
                trades = team_data.get("trades", 0)
                faab_spent = team_data.get("faab_spent", 0)
                streak_type = team_data.get("streak_type", "NONE")
                streak_length = team_data.get("streak_length", 0)
                standing = team_data.get("standing", 0)
                wins = team_data.get("wins", 0)
                points_for = team_data.get("points_for", 0)

                context_parts.append(f"\n**{team_data['team_name']}:**")
                context_parts.append(f"  - Standing: #{standing} of {total_teams}")
                context_parts.append(f"  - Streak: {streak_type} {streak_length}")
                context_parts.append(
                    f"  - Waiver moves: {acquisitions} adds, {drops} drops"
                )
                if week_num > 0:
                    context_parts.append(
                        f"  - Churn rate: {drops / week_num:.1f} drops per week"
                    )
                context_parts.append(f"  - FAAB spent: ${faab_spent}")
                if wins > 0:
                    context_parts.append(f"  - FAAB per win: ${faab_spent / wins:.1f}")
                context_parts.append(f"  - Trades: {trades}")
                if acquisitions + drops > 0:
                    context_parts.append(
                        f"  - Points per roster move: {points_for / (acquisitions + drops):.1f}"
                    )
        except Exception as e:
            context_parts.append(f"  (Could not fetch team metrics: {e})")

        # Add multi-week trends
        context_parts.append("\n## Multi-Week Trends (for deeper roasts)")

        # Record this week's data for trend tracking
        try:
            self.trend_tracker.record_week(
                league["current_week"], week_data["matchups"]
            )
            notable_trends = self.trend_tracker.get_notable_trends(
                league["current_week"]
            )

            if notable_trends["hot_teams"]:
                context_parts.append("\n**Hot Teams (improving):**")
                for team in notable_trends["hot_teams"][:3]:
                    context_parts.append(
                        f"  - {team['team']}: averaging {team['average_score']} over last 3 weeks"
                    )

            if notable_trends["cold_teams"]:
                context_parts.append("\n**Cold Teams (declining):**")
                for team in notable_trends["cold_teams"][:3]:
                    context_parts.append(
                        f"  - {team['team']}: averaging {team['average_score']} over last 3 weeks"
                    )

            if notable_trends["management_disasters"]:
                context_parts.append(
                    "\n**Management Disasters (consistently leaving points):**"
                )
                for team in notable_trends["management_disasters"]:
                    context_parts.append(
                        f"  - {team['team']}: {team['consecutive_fails']} straight weeks with {team['average_gap']:.1f} avg management gap - ROASTABLE"
                    )

            # Add specific team trends for matchup participants
            context_parts.append("\n**Team-Specific Trends:**")
            for matchup in week_data["matchups"]["matchups"]:
                for team_name in [
                    matchup["home_team"]["team_name"],
                    matchup["away_team"]["team_name"],
                ]:
                    trends = self.trend_tracker.get_team_trends(team_name, weeks=3)
                    if trends:
                        context_parts.append(
                            f"  - {team_name}: {trends['score_trend']} trend, avg {trends['average_score']} over last 3"
                        )
        except Exception as e:
            context_parts.append(f"  (Trend tracking: {e})")

        return "\n".join(context_parts)

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
        Generate the recap using the LLM

        Args:
            week: Week number to generate recap for
            llm_client: Your LLM client (OpenAI, Anthropic, etc.)
                       Should have a generate(prompt) method that returns string

        Returns:
            Generated recap text or None if failed
        """

        # Fetch data
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        # Build context
        print("📝 Building context...")
        data_context = self.build_context(week_data)
        history_context = self.get_previous_recaps_context()

        # Load system prompt
        with open("COLUMNIST_PROMPT.md", "r") as f:
            system_prompt = f.read()

        # Build full prompt
        full_prompt = f"""{system_prompt}

---

## DATA FOR THIS WEEK

{data_context}

---

{history_context}

---

Now write the Week {week} recap. Remember: Be viciously funny, cite specific stats, and avoid repeating previous burns.
"""

        # Generate with LLM
        print("🤖 Generating recap with LLM...")

        if llm_client is None:
            print("⚠️  No LLM client provided. Returning context only.")
            print("\nTo generate recaps, integrate your LLM client:")
            print("Example usage:")
            print("  from openai import OpenAI")
            print("  client = OpenAI()")
            print("  generator = RecapGenerator()")
            print(
                "  recap = generator.generate_recap_with_openai(week=7, client=client)"
            )
            return full_prompt

        try:
            recap = llm_client.generate(full_prompt)

            # Save to history
            self._save_history(
                week, recap, {"data": week_data, "prompt_length": len(full_prompt)}
            )

            return recap

        except Exception as e:
            print(f"❌ Error generating recap: {e}")
            return None

    def generate_recap_with_openai(
        self, week: int, client, model: str = "gpt-4"
    ) -> Optional[str]:
        """Generate recap using OpenAI API"""
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        data_context = self.build_context(week_data)
        history_context = self.get_previous_recaps_context()

        with open("COLUMNIST_PROMPT.md", "r") as f:
            system_prompt = f.read()

        user_prompt = f"""## DATA FOR THIS WEEK

{data_context}

---

{history_context}

---

Now write the Week {week} recap."""

        print(f"🤖 Generating recap with OpenAI ({model})...")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=2000,
            )

            recap = response.choices[0].message.content

            # Save to history and output
            self._save_history(week, recap, {"model": model, "data": week_data})
            self._save_recap_to_file(week, recap)

            return recap

        except Exception as e:
            print(f"❌ Error generating recap: {e}")
            return None

    def generate_recap_with_anthropic(
        self, week: int, client, model: str = "claude-sonnet-4-5-20250929"
    ) -> Optional[str]:
        """Generate recap using Anthropic API"""
        week_data = self.fetch_week_data(week)
        if not week_data:
            return None

        data_context = self.build_context(week_data)
        history_context = self.get_previous_recaps_context()

        with open("COLUMNIST_PROMPT.md", "r") as f:
            system_prompt = f.read()

        user_prompt = f"""## DATA FOR THIS WEEK

{data_context}

---

{history_context}

---

Now write the Week {week} recap."""

        print(f"🤖 Generating recap with Anthropic ({model})...")

        try:
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0.8,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            recap = response.content[0].text

            # Save to history and output
            self._save_history(week, recap, {"model": model, "data": week_data})
            self._save_recap_to_file(week, recap)

            return recap

        except Exception as e:
            print(f"❌ Error generating recap: {e}")
            return None

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
            context = generator.build_context(week_data)
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
                with open("COLUMNIST_PROMPT.md", "r") as pf:
                    f.write(pf.read())
                f.write("\n\n" + "=" * 80 + "\n\n")
                f.write(context)
            print(f"\n✅ Full prompt saved to {context_file}")
            print("   Copy this to your LLM to generate the recap!")
    else:
        print("⚠️  To generate recaps with an LLM, use one of these methods:")
        print("\n# Option 1: OpenAI")
        print("from openai import OpenAI")
        print("from recap_generator import RecapGenerator")
        print("")
        print("client = OpenAI(api_key='your-key')")
        print("generator = RecapGenerator()")
        print(
            f"recap = generator.generate_recap_with_openai(week={args.week}, client=client)"
        )
        print("print(recap)")
        print("\n# Option 2: Anthropic")
        print("from anthropic import Anthropic")
        print("from recap_generator import RecapGenerator")
        print("")
        print("client = Anthropic(api_key='your-key')")
        print("generator = RecapGenerator()")
        print(
            f"recap = generator.generate_recap_with_anthropic(week={args.week}, client=client)"
        )
        print("print(recap)")
        print("\n# Option 3: Get context for manual use")
        print(f"python recap_generator.py {args.week} --context-only")


if __name__ == "__main__":
    main()
