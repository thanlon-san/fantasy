"""
Context Builder for Fantasy Football Recaps
Builds comprehensive context from weekly data for LLM recap generation
"""

from typing import Dict, List
from src.trend_tracker import TrendTracker
from src.ownership_stats import OwnershipStats
from src.constants import TEAM_OWNERS


class ContextBuilder:
    """Builds rich context from fantasy football data for LLM roasting"""

    def __init__(self, trend_tracker: TrendTracker, ownership_stats: OwnershipStats):
        self.trend_tracker = trend_tracker
        self.ownership_stats = ownership_stats

    def build_context(self, week_data: Dict, week: int = None, use_v2_format: bool = True) -> str:
        """
        Build comprehensive context from week data

        Args:
            week_data: Dict containing league, matchups, week_stats, teams, standings
            week: The actual week number being processed (overrides league current_week)
            use_v2_format: If True, organize matchups by tier (Contenders vs Chaos)

        Returns:
            Formatted context string for LLM
        """
        context_parts = []

        # Header
        league = week_data["league"]
        # Use explicit week parameter if provided, otherwise fall back to league's current_week
        week_num = week if week is not None else league['current_week']
        context_parts.append(f"# Week {week_num} Recap Data")
        context_parts.append(f"\nLeague: {league['league_name']}")
        context_parts.append(
            f"Season: {league.get('season_year', league.get('year', 'N/A'))}"
        )
        context_parts.append("")

        if use_v2_format:
            context_parts.append("## 📋 V2 FORMAT INSTRUCTIONS")
            context_parts.append("Use the updated structure:")
            context_parts.append("- Header → League Pulse → Stat of Week → Matchups (all, drama-ordered)")
            context_parts.append("- 🏆 Power Rankings (all teams, with movement) → 🏈 Preview → 🧘 Closing")
            context_parts.append("")

        # Week highlights (for Stat of the Week section)
        self._add_week_highlights(context_parts, week_data)

        # Matchups - organize by tier for V2
        all_matchups = week_data["matchups"]["matchups"]
        
        if use_v2_format:
            # Drama-first ordering
            def matchup_key(m):
                home = m["home_team"]
                away = m["away_team"]
                margin = abs(home["score"] - away["score"])
                combined = home["score"] + away["score"]
                # Projections
                home_proj = sum(p.get("projected_points", 0) for p in home.get("starters", []))
                away_proj = sum(p.get("projected_points", 0) for p in away.get("starters", []))
                winner = m.get("winner")
                upset_delta = 0
                if winner == home["team_name"] and home_proj < away_proj:
                    upset_delta = (away_proj - home_proj)
                elif winner == away["team_name"] and away_proj < home_proj:
                    upset_delta = (home_proj - away_proj)
                # Categories: 0 nail-biter (<5), 1 upset (proj diff>=10), 2 shootout (both>120), 3 blowout (>=30), 4 disaster (both<90), 5 other
                if margin < 5:
                    return (0, margin)  # smaller margin first
                if upset_delta >= 10:
                    return (1, -upset_delta)  # larger upset first
                if home["score"] > 120 and away["score"] > 120:
                    return (2, -combined)  # higher combined first
                if margin >= 30:
                    return (3, -margin)  # bigger blowouts later
                if home["score"] < 90 and away["score"] < 90:
                    return (4, combined)  # lower combined first
                return (5, -combined)

            sorted_matchups = sorted(all_matchups, key=matchup_key)

            context_parts.append("## Matchups (Drama-ordered)")
            context_parts.append("\n**IMPORTANT: For each matchup, use the format: @[owner_name]'s [team_name]**")
            context_parts.append("Example: @Marissa Tomko's Scott's Tots (109.74) def. @Han Jang's Beacon (87.64)\n")

            for idx, matchup in enumerate(sorted_matchups, 1):
                self._add_matchup_details(context_parts, matchup)
        else:
            # Original format - just list all matchups
            context_parts.append("## Matchups")
            context_parts.append(
                "\n**IMPORTANT: For each matchup, use the format: @[owner_name]'s [team_name]**"
            )
            context_parts.append(
                "Example: @Marissa Tomko's Scott's Tots 109.74 def. @Han Jang's Beacon 87.64\n"
            )
            
            for matchup in all_matchups:
                self._add_matchup_details(context_parts, matchup)

        # Power rankings section (fetch from API)
        if use_v2_format:
            self._add_power_rankings(context_parts, week_data, week_num)
        else:
            self._add_standings(context_parts, week_data, enhanced=False)

        # Team activity metrics (for Coaching Disasters section)
        self._add_team_metrics(context_parts, week_data, week_num)

        # Multi-week trends
        self._add_trends(context_parts, week_data, week_num)

        # Next week matchups (for Preview section)
        self._add_next_week_preview(context_parts, week_data, week_num)

        return "\n".join(context_parts)

    def _add_week_highlights(self, context_parts: List[str], week_data: Dict):
        """Add week highlights from stats endpoint - great for Stat of the Week"""
        week_stats = week_data.get("week_stats", {})
        if not week_stats:
            return

        context_parts.append("\n## 🔥 Week Highlights (for Stat of the Week)")
        context_parts.append("Use ONE of these as your Stat of the Week - pick the most roastable:\n")

        # Highest score (API returns dict with "team" and "points" keys)
        if week_stats.get("highest_score"):
            high = week_stats["highest_score"]
            team = high.get("team", "Unknown")
            score = high.get("points", 0)
            owner = TEAM_OWNERS.get(team, "Unknown")
            context_parts.append(f"**Week Winner:** @{owner}'s {team} scored {score} points")

        # Lowest score (roastable)
        if week_stats.get("lowest_score"):
            low = week_stats["lowest_score"]
            team = low.get("team", "Unknown")
            score = low.get("points", 0)
            owner = TEAM_OWNERS.get(team, "Unknown")
            context_parts.append(f"**Dumpster Fire:** @{owner}'s {team} only managed {score} points 🗑️")

        # Biggest blowout
        if week_stats.get("biggest_blowout"):
            blowout = week_stats["biggest_blowout"]
            winner_owner = TEAM_OWNERS.get(blowout.get("winner", ""), "Unknown")
            loser_owner = TEAM_OWNERS.get(blowout.get("loser", ""), "Unknown")
            context_parts.append(
                f"**Biggest Blowout:** @{winner_owner}'s {blowout.get('winner')} destroyed "
                f"@{loser_owner}'s {blowout.get('loser')} by {blowout.get('margin', 0)} points 💀"
            )

        # Closest game (nail-biter)
        if week_stats.get("closest_game"):
            close = week_stats["closest_game"]
            owner1 = TEAM_OWNERS.get(close.get("team1", ""), "Unknown")
            owner2 = TEAM_OWNERS.get(close.get("team2", ""), "Unknown")
            context_parts.append(
                f"**Nail Biter:** @{owner1}'s {close.get('team1')} vs @{owner2}'s {close.get('team2')} "
                f"decided by just {close.get('margin', 0)} points 😰"
            )

        # Most bench points (lineup mismanagement)
        if week_stats.get("most_bench_points"):
            bench = week_stats["most_bench_points"]
            owner = TEAM_OWNERS.get(bench.get("team", ""), "Unknown")
            context_parts.append(
                f"**Bench MVP:** @{owner}'s {bench.get('team')} left {bench.get('points', 0)} points on the bench 🪑"
            )

        context_parts.append("")
    
    def _add_matchup_details(self, context_parts: List[str], matchup: Dict):
        """Add detailed matchup information for both teams"""
        home = matchup["home_team"]
        away = matchup["away_team"]
        
        # Use simple team name mapping
        home_owner = TEAM_OWNERS.get(home['team_name'], "Unknown")
        away_owner = TEAM_OWNERS.get(away['team_name'], "Unknown")
        
        # Calculate combined score for context
        combined_score = home['score'] + away['score']
        
        context_parts.append(
            f"\n### @{home_owner}'s {home['team_name']} ({home['score']}) vs @{away_owner}'s {away['team_name']} ({away['score']})"
        )
        context_parts.append(f"Combined score: {combined_score:.1f}")

        # Home team analytics
        self._add_team_analytics(context_parts, home, "home")
        self._add_starters(context_parts, home)
        self._add_bench_stars(context_parts, home)

        # Away team analytics
        self._add_team_analytics(context_parts, away, "away")
        self._add_starters(context_parts, away)
        self._add_bench_stars(context_parts, away)

        context_parts.append("")

    def _add_team_analytics(self, context_parts: List[str], team: Dict, label: str):
        """Add team-level analytics"""
        owner = TEAM_OWNERS.get(team['team_name'], "Unknown")
        context_parts.append(f"\n**@{owner}'s {team['team_name']} Analytics:**")
        context_parts.append(
            f"Score: {team['score']} (Projected: {sum(p['projected_points'] for p in team['starters']):.1f})"
        )

        # Position aggregates
        if "position_aggregates" in team:
            pos_agg = team["position_aggregates"]
            context_parts.append(
                f"Position breakdown: QB={pos_agg.get('QB', 0)}, RB={pos_agg.get('RB', 0)}, "
                f"WR={pos_agg.get('WR', 0)}, TE={pos_agg.get('TE', 0)}"
            )

        # Optimal lineup and management gap
        if "optimal_lineup" in team and "management_gap" in team:
            context_parts.append(
                f"Optimal score: {team['optimal_lineup']['optimal_score']} "
                f"(Management gap: {team['management_gap']} pts)"
            )
            if team["management_gap"] > 20:
                context_parts.append(
                    f"  🚨 Left {team['management_gap']} points on table - ROASTABLE"
                )

    def _add_starters(self, context_parts: List[str], team: Dict):
        """Add starter information with ownership and trend checks"""
        owner = TEAM_OWNERS.get(team['team_name'], "Unknown")
        context_parts.append(f"\n**@{owner}'s {team['team_name']} Starters:**")

        for player in team["starters"]:
            if (
                player["actual_points"] > 15
                or abs(player["actual_points"] - player["projected_points"]) > 10
            ):
                stats_str = self._format_player_stats(player)
                starter_line = (
                    f"  - {player['name']} ({player['position']}, {player['slot']}): "
                    f"Proj {player['projected_points']:.1f}, Actual {player['actual_points']:.1f}{stats_str}"
                )

                # Check for recent form (STRICT - only when funny)
                try:
                    recent_avg = self.trend_tracker.get_player_recent_average(
                        player["name"], weeks=3
                    )
                    if recent_avg is not None:
                        # Only add if it's a COLD STREAK being started (<8 avg, bust again)
                        if recent_avg < 8 and player["actual_points"] < 10:
                            starter_line += f"\n    ❄️  COLD STREAK: L3W avg {recent_avg}, still started him"
                except Exception:
                    pass  # Fail silently

                # Check for ownership roast on starters (STRICT - only <3% ownership who bust)
                start_pct = player.get("percent_started", 0)
                # Skip if invalid data (negative values from ESPN API)
                if start_pct >= 0 and start_pct < 3 and player["actual_points"] < 5:
                    try:
                        ownership_roast = self.ownership_stats.generate_ownership_roast(
                            player["name"],
                            was_started=True,
                            points_scored=player["actual_points"],
                            percent_started=start_pct,
                        )
                        if ownership_roast:
                            starter_line += (
                                f"\n    💣 OWNERSHIP ROAST: {ownership_roast}"
                            )
                    except Exception:
                        pass  # Fail silently

                context_parts.append(starter_line)

    def _add_bench_stars(self, context_parts: List[str], team: Dict):
        """Add bench highlights with ownership and trend checks"""
        bench_stars = [p for p in team["bench"] if p["actual_points"] > 15]
        if bench_stars:
            total_bench = sum(p["actual_points"] for p in team["bench"])
            context_parts.append(f"**Bench (total: {total_bench:.1f} pts):**")
            for player in bench_stars:
                # Include start % to avoid roasting deep sleepers
                start_pct = player.get("percent_started", 0)
                roastable = "ROASTABLE" if start_pct > 20 else "deep sleeper"
                
                # Format ownership percentage (skip if invalid)
                start_pct_str = f"{start_pct}%" if start_pct >= 0 else "N/A"

                bench_line = (
                    f"  - BENCHED: {player['name']}: {player['actual_points']:.1f} pts "
                    f"(started {start_pct_str} on ESPN - {roastable})"
                )

                # Check for recent form (STRICT - only hot streaks benched)
                try:
                    recent_avg = self.trend_tracker.get_player_recent_average(
                        player["name"], weeks=3
                    )
                    if recent_avg is not None:
                        # Only add if it's a HOT STREAK being benched (>18 avg, scored 20+ again)
                        if recent_avg > 18 and player["actual_points"] > 20:
                            bench_line += f"\n    🔥 HOT STREAK BENCHED: L3W avg {recent_avg}, benched anyway"
                except Exception:
                    pass  # Fail silently

                # Check for ownership roast (STRICT thresholds - only when really bad)
                ownership_roast = None
                try:
                    # Only roast benching if player has ≥60% start rate AND scored ≥20
                    # Skip if invalid data (negative values from ESPN API)
                    if start_pct >= 0 and start_pct >= 60 and player["actual_points"] > 20:
                        ownership_roast = self.ownership_stats.generate_ownership_roast(
                            player["name"],
                            was_started=False,
                            points_scored=player["actual_points"],
                            percent_started=start_pct,
                        )
                except Exception:
                    pass  # Fail silently

                if ownership_roast:
                    bench_line += f"\n    💣 OWNERSHIP ROAST: {ownership_roast}"
                context_parts.append(bench_line)

    def _add_standings(self, context_parts: List[str], week_data: Dict, enhanced: bool = False):
        """Add current standings"""
        if enhanced:
            context_parts.append("\n## 🏆 Current Standings (For Power Rankings)")
            context_parts.append("Use this to build Power Rankings tiers in the recap.\n")
            
            all_standings = week_data["standings"]["standings"]
            
            # Tier 1: Top 4 teams
            context_parts.append("**Tier 1 - The Menaces (Top 4):**")
            for team in all_standings[:4]:
                owner = TEAM_OWNERS.get(team['team_name'], "Unknown")
                context_parts.append(
                    f"  {team['rank']}. @{owner}'s {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )
            
            # Tier 2: Teams 5-8
            context_parts.append("\n**Tier 2 - The Pretenders (5-8):**")
            for team in all_standings[4:8]:
                owner = TEAM_OWNERS.get(team['team_name'], "Unknown")
                context_parts.append(
                    f"  {team['rank']}. @{owner}'s {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )
            
            # Tier 3: Teams 9-12
            context_parts.append("\n**Tier 3 - The Bubble (9-12):**")
            for team in all_standings[8:12]:
                owner = TEAM_OWNERS.get(team['team_name'], "Unknown")
                context_parts.append(
                    f"  {team['rank']}. @{owner}'s {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )
            
            # Tier 4: Bottom teams (13-16)
            context_parts.append("\n**Tier 4 - The Lost Souls (13-16):**")
            for team in all_standings[12:]:
                owner = TEAM_OWNERS.get(team['team_name'], "Unknown")
                context_parts.append(
                    f"  {team['rank']}. @{owner}'s {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )
        else:
            context_parts.append("\n## Current Standings (Top 5)")
            for team in week_data["standings"]["standings"][:5]:
                context_parts.append(
                    f"{team['rank']}. {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )

    def _add_team_metrics(self, context_parts: List[str], week_data: Dict, week_num: int):
        """Add team activity and efficiency metrics"""
        context_parts.append("\n## Team Activity & Efficiency Metrics (for roasting)")
        try:
            import requests

            teams_response = requests.get(
                f"{week_data.get('api_url', 'http://localhost:8000')}/api/teams"
            )
            teams_response.raise_for_status()
            all_teams = teams_response.json()["teams"]

            # Use the provided week_num instead of league's current_week
            total_teams = len(all_teams)

            for team_data in all_teams:
                wins = team_data["wins"]
                points_for = team_data["points_for"]
                acquisitions = team_data.get("acquisitions", 0)
                drops = team_data.get("drops", 0)
                trades = team_data.get("trades", 0)
                faab_spent = team_data.get("faab_spent", 0)
                streak_type = team_data.get("streak_type", "NONE")
                streak_length = team_data.get("streak_length", 0)
                standing = team_data.get("standing", 0)
                
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

    def _add_power_rankings(self, context_parts: List[str], week_data: Dict, week_num: int):
        """Fetch and add power rankings with movement and identity context."""
        context_parts.append("\n## 🏆 Power Rankings (All Teams)")
        try:
            import requests
            api_url = week_data.get('api_url', 'http://localhost:8000')
            resp = requests.get(f"{api_url}/api/power_rankings/{week_num}")
            resp.raise_for_status()
            rankings = resp.json().get("rankings", [])
            for r in rankings:
                movement = r.get("movement", "—")
                owner = r.get("owner", "Unknown")
                team = r.get("team_name", "Team")
                record = f"{r.get('wins', 0)}–{r.get('losses', 0)}"
                pf = r.get("pf", 0)
                context_parts.append(
                    f"{r['rank']}. @{owner}'s {team} ({record}, PF {pf}) [↕ {movement}]"
                )
        except Exception as e:
            context_parts.append(f"  (Could not fetch power rankings: {e})")

    def _add_trends(self, context_parts: List[str], week_data: Dict, week_num: int):
        """Add multi-week trends"""
        context_parts.append("\n## Multi-Week Trends (for deeper roasts)")

        try:
            # Record this week's data for trend tracking using the provided week_num
            self.trend_tracker.record_week(
                week_num, week_data["matchups"]
            )
            notable_trends = self.trend_tracker.get_notable_trends(
                week_num
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
                        f"  - {team['team']}: {team['consecutive_fails']} straight weeks with "
                        f"{team['average_gap']:.1f} avg management gap - ROASTABLE"
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
                            f"  - {team_name}: {trends['score_trend']} trend, "
                            f"avg {trends['average_score']} over last 3"
                        )
        except Exception as e:
            context_parts.append(f"  (Trend tracking: {e})")

    def _add_next_week_preview(self, context_parts: List[str], week_data: Dict, current_week: int):
        """Fetch and add next week's matchups for the Preview section"""
        next_week = current_week + 1
        context_parts.append(f"\n## 🏈 Week {next_week} Preview (ACTUAL MATCHUPS - USE THESE)")
        context_parts.append("**CRITICAL: Use these exact matchups for the Preview section. Do NOT make up matchups.**\n")
        
        try:
            import requests
            api_url = week_data.get('api_url', 'http://localhost:8000')
            resp = requests.get(f"{api_url}/api/matchups/{next_week}")
            resp.raise_for_status()
            next_matchups = resp.json().get("matchups", [])
            
            if not next_matchups:
                context_parts.append(f"(No Week {next_week} matchups available yet)")
                return
            
            for matchup in next_matchups:
                home = matchup.get("home_team", {})
                away = matchup.get("away_team", {})
                home_name = home.get("team_name", "Unknown")
                away_name = away.get("team_name", "Unknown")
                home_owner = TEAM_OWNERS.get(home_name, "Unknown")
                away_owner = TEAM_OWNERS.get(away_name, "Unknown")
                
                # Get records from API response
                home_record = home.get("record", "?-?")
                away_record = away.get("record", "?-?")
                
                context_parts.append(
                    f"- @{home_owner}'s {home_name} ({home_record}) vs @{away_owner}'s {away_name} ({away_record})"
                )
            
            context_parts.append("")
            
        except Exception as e:
            context_parts.append(f"(Could not fetch Week {next_week} matchups: {e})")

    @staticmethod
    def _format_player_stats(player: Dict) -> str:
        """Format detailed player stats for context"""
        stats = player.get("stats", {})
        if not stats or all(v == 0 for v in stats.values()):
            return ""

        parts = []
        # Passing
        if stats.get("passing_yards", 0) > 0:
            parts.append(
                f"{stats['passing_yards']} pass yds, {stats['passing_tds']} TD, "
                f"{stats['passing_ints']} INT"
            )
        # Rushing
        if stats.get("rushing_attempts", 0) > 0:
            parts.append(
                f"{stats['rushing_attempts']} car, {stats['rushing_yards']} rush yds, "
                f"{stats['rushing_tds']} rush TD"
            )
        # Receiving
        if stats.get("receiving_targets", 0) > 0:
            rec = stats["receiving_receptions"]
            tgt = stats["receiving_targets"]
            catch_rate = (rec / tgt * 100) if tgt > 0 else 0
            parts.append(
                f"{rec}/{tgt} rec ({catch_rate:.0f}%), {stats['receiving_yards']} rec yds, "
                f"{stats['receiving_tds']} rec TD"
            )

        return f" [{'; '.join(parts)}]" if parts else ""
