"""
Context Builder for Fantasy Football Recaps
Builds comprehensive context from weekly data for LLM recap generation
"""

from typing import Dict, List, Optional, Tuple
from src.trend_tracker import TrendTracker
from src.ownership_stats import OwnershipStats
from src.constants import TEAM_OWNERS, NFL_PLAYOFF_START_WEEK

# Playoff configuration
PLAYOFF_TEAMS = 6  # Number of teams that make playoffs


class ContextBuilder:
    """Builds rich context from fantasy football data for LLM roasting"""

    def __init__(self, trend_tracker: TrendTracker, ownership_stats: OwnershipStats):
        self.trend_tracker = trend_tracker
        self.ownership_stats = ownership_stats

    def _get_playoff_context(self, week_num: int, standings: List[Dict]) -> Dict:
        """
        Determine playoff context for the given week.

        Returns dict with:
            - is_clinching_week: True if this is the last regular season week
            - is_playoff_week: True if this is a playoff week
            - playoff_round: 1, 2, or 3 (championship) if playoff week
            - playoff_teams: List of teams that made playoffs
            - eliminated_teams: List of teams that missed playoffs
            - playoff_bracket: Dict mapping seeds to teams
            - playoff_team_names: Set of team names in championship bracket
            - alive_teams: Set of teams still alive in championship (tracks eliminations)
        """
        is_clinching_week = week_num == NFL_PLAYOFF_START_WEEK - 1
        is_playoff_week = week_num >= NFL_PLAYOFF_START_WEEK

        # Determine playoff round (Week 15 = Round 1, Week 16 = Round 2, Week 17 = Championship)
        playoff_round = None
        if is_playoff_week:
            playoff_round = week_num - NFL_PLAYOFF_START_WEEK + 1

        # Build playoff bracket from standings
        playoff_teams = []
        eliminated_teams = []
        playoff_bracket = {}
        playoff_team_names = set()

        for i, team in enumerate(standings):
            seed = i + 1
            team_info = {
                "seed": seed,
                "team_name": team["team_name"],
                "owner": TEAM_OWNERS.get(team["team_name"], "Unknown"),
                "record": f"{team['wins']}-{team['losses']}",
                "points_for": team["points_for"],
            }

            if seed <= PLAYOFF_TEAMS:
                playoff_teams.append(team_info)
                playoff_bracket[seed] = team_info
                playoff_team_names.add(team["team_name"])
            else:
                eliminated_teams.append(team_info)

        # Track which teams are still alive in championship bracket
        # For Round 2+, we need to identify who won in previous rounds
        alive_teams = playoff_team_names.copy()  # Start with all playoff teams

        if playoff_round and playoff_round >= 2:
            # For semifinals (Round 2) and beyond, only include teams that advanced
            # We'll determine this from the matchup winners
            alive_teams = self._get_championship_bracket_teams(
                week_num, playoff_team_names
            )

        return {
            "is_clinching_week": is_clinching_week,
            "is_playoff_week": is_playoff_week,
            "playoff_round": playoff_round,
            "playoff_teams": playoff_teams,
            "eliminated_teams": eliminated_teams,
            "playoff_bracket": playoff_bracket,
            "playoff_team_names": playoff_team_names,  # Original top 6
            "alive_teams": alive_teams,  # Teams still in championship hunt
        }

    def _get_championship_bracket_teams(
        self, week_num: int, playoff_team_names: set
    ) -> set:
        """
        For semifinals and later rounds, identify which teams are still alive.

        Strategy: For Round 2 (Week 16), the alive teams are:
        - Seeds #1 and #2 (had byes in Round 1)
        - Winners from Round 1 matchups (#3 vs #6, #4 vs #5)

        We can infer this from the current week's matchups - teams playing each other
        in championship games are the ones still alive.
        """
        # Simple approach: Return the playoff teams for now, but with a note
        # In practice, we'll improve this to read from recap history later
        # For now, return the playoff seeds which will be refined by matchup analysis
        return playoff_team_names

    def _add_playoff_context(
        self, context_parts: List[str], playoff_ctx: Dict, week_num: int
    ):
        """Add playoff-specific context to the recap"""

        if playoff_ctx["is_clinching_week"]:
            context_parts.append("\n## 🏆 PLAYOFF CLINCHING WEEK")
            context_parts.append("**THIS IS THE LAST WEEK OF THE REGULAR SEASON!**")
            context_parts.append("Focus heavily on:")
            context_parts.append("- Who clinched playoff spots")
            context_parts.append(
                "- Who got eliminated and HOW (tiebreakers, heartbreak, etc.)"
            )
            context_parts.append("- Playoff seeding implications")
            context_parts.append(
                "- Teams that backed into the playoffs vs teams that dominated"
            )
            context_parts.append("")

            context_parts.append("### 🎫 PLAYOFF BRACKET (Top 6 make it)")
            for team in playoff_ctx["playoff_teams"]:
                context_parts.append(
                    f"  {team['seed']}. @{team['owner']}'s {team['team_name']} ({team['record']}, {team['points_for']:.2f} PF) ✅ IN"
                )

            context_parts.append("\n### 💀 ELIMINATED (Season over)")
            for team in playoff_ctx["eliminated_teams"][
                :4
            ]:  # Top 4 eliminated for drama
                context_parts.append(
                    f"  {team['seed']}. @{team['owner']}'s {team['team_name']} ({team['record']}, {team['points_for']:.2f} PF) ❌ OUT"
                )
            context_parts.append("")

            # First round matchups preview
            context_parts.append("### 🏈 ROUND 1 MATCHUPS (Next Week)")
            context_parts.append("Standard 6-team playoff bracket:")
            context_parts.append("- #1 and #2 seeds get BYES")
            context_parts.append("- #3 vs #6")
            context_parts.append("- #4 vs #5")
            bracket = playoff_ctx["playoff_bracket"]
            if len(bracket) >= 6:
                context_parts.append(f"\n**ROUND 1:**")
                context_parts.append(
                    f"  @{bracket[3]['owner']}'s {bracket[3]['team_name']} (3) vs @{bracket[6]['owner']}'s {bracket[6]['team_name']} (6)"
                )
                context_parts.append(
                    f"  @{bracket[4]['owner']}'s {bracket[4]['team_name']} (4) vs @{bracket[5]['owner']}'s {bracket[5]['team_name']} (5)"
                )
                context_parts.append(f"\n**BYE WEEK:**")
                context_parts.append(
                    f"  @{bracket[1]['owner']}'s {bracket[1]['team_name']} (1) - Watching from the couch"
                )
                context_parts.append(
                    f"  @{bracket[2]['owner']}'s {bracket[2]['team_name']} (2) - Also resting"
                )
            context_parts.append("")

        elif playoff_ctx["is_playoff_week"]:
            round_num = playoff_ctx["playoff_round"]
            round_names = {1: "ROUND 1", 2: "SEMIFINALS", 3: "CHAMPIONSHIP"}
            round_name = round_names.get(round_num, f"ROUND {round_num}")

            context_parts.append(f"\n## 🏆 PLAYOFF {round_name}")
            context_parts.append(f"**Week {week_num} - {round_name}**")
            context_parts.append("This is WIN OR GO HOME. Focus on:")
            context_parts.append(
                "- **CHAMPIONSHIP BRACKET** teams and their elimination drama"
            )
            context_parts.append("- Championship implications and legacy moments")
            context_parts.append("- Major upsets and chokes in championship games")
            context_parts.append("- Season-long narratives coming to a head")
            context_parts.append("")
            context_parts.append(
                "**CONSOLATION BRACKET** games should get brief, secondary coverage."
            )
            context_parts.append(
                "Teams are playing for pride only (no draft position implications)."
            )
            context_parts.append("")

            if round_num == 3:
                context_parts.append("### 🏆 CHAMPIONSHIP GAME")
                context_parts.append(
                    "THE BIG ONE. One team becomes champion, one becomes a footnote."
                )
                context_parts.append("")

    def build_context(
        self, week_data: Dict, week: int = None, use_v2_format: bool = True
    ) -> str:
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
        week_num = week if week is not None else league["current_week"]
        context_parts.append(f"# Week {week_num} Recap Data")
        context_parts.append(f"\nLeague: {league['league_name']}")
        context_parts.append(
            f"Season: {league.get('season_year', league.get('year', 'N/A'))}"
        )
        context_parts.append("")

        if use_v2_format:
            context_parts.append("## 📋 V2 FORMAT INSTRUCTIONS")
            context_parts.append("Use the updated structure:")
            context_parts.append(
                "- Header → League Pulse → Stat of Week → Matchups (all, drama-ordered)"
            )
            context_parts.append(
                "- 🏆 Power Rankings (all teams, with movement) → 🏈 Preview → 🧘 Closing"
            )
            context_parts.append("")

        # Add playoff context if applicable
        standings = week_data.get("standings", {}).get("standings", [])
        playoff_ctx = self._get_playoff_context(week_num, standings)
        if playoff_ctx["is_clinching_week"] or playoff_ctx["is_playoff_week"]:
            self._add_playoff_context(context_parts, playoff_ctx, week_num)

        # Week highlights (for Stat of the Week section)
        self._add_week_highlights(context_parts, week_data, playoff_ctx)

        # Matchups - organize by tier for V2
        all_matchups = week_data["matchups"]["matchups"]

        if use_v2_format:
            # Check if this is playoffs - separate championship vs consolation
            championship_matchups = []
            consolation_matchups = []

            if playoff_ctx["is_playoff_week"]:
                playoff_team_names = playoff_ctx["playoff_team_names"]
                playoff_round = playoff_ctx["playoff_round"]

                # For Round 2 (semifinals), only 4 teams should be in championship bracket
                # Identify them by finding matchups involving the #1 and #2 seeds (bye teams)
                if playoff_round == 2:
                    # In semifinals: #1 and #2 seeds (had byes) play the Round 1 winners
                    # Strategy: Championship games involve the top 2 seeds
                    bye_teams = set()
                    playoff_bracket = playoff_ctx.get("playoff_bracket", {})
                    if 1 in playoff_bracket:
                        bye_teams.add(playoff_bracket[1]["team_name"])
                    if 2 in playoff_bracket:
                        bye_teams.add(playoff_bracket[2]["team_name"])

                    playoff_matchups_candidates = []
                    for matchup in all_matchups:
                        home_team = matchup["home_team"]["team_name"]
                        away_team = matchup["away_team"]["team_name"]

                        if (
                            home_team in playoff_team_names
                            and away_team in playoff_team_names
                        ):
                            # Both in top 6 - check if involves a bye team
                            if home_team in bye_teams or away_team in bye_teams:
                                # Championship game (involves #1 or #2 seed)
                                championship_matchups.append(matchup)
                            else:
                                # Consolation (neither team had a bye)
                                consolation_matchups.append(matchup)
                        else:
                            # At least one team not in playoffs - definitely consolation
                            consolation_matchups.append(matchup)

                else:
                    # Round 1 or Championship: use original logic
                    for matchup in all_matchups:
                        home_team = matchup["home_team"]["team_name"]
                        away_team = matchup["away_team"]["team_name"]

                        # Championship bracket: both teams were in top 6
                        if (
                            home_team in playoff_team_names
                            and away_team in playoff_team_names
                        ):
                            championship_matchups.append(matchup)
                        else:
                            consolation_matchups.append(matchup)
            else:
                # Regular season - all matchups are equal
                championship_matchups = all_matchups

            # Drama-first ordering (championship games ALWAYS come first in playoffs)
            def matchup_key(m, is_championship=True):
                home = m["home_team"]
                away = m["away_team"]
                margin = abs(home["score"] - away["score"])
                combined = home["score"] + away["score"]
                # Projections
                home_proj = sum(
                    p.get("projected_points", 0) for p in home.get("starters", [])
                )
                away_proj = sum(
                    p.get("projected_points", 0) for p in away.get("starters", [])
                )
                winner = m.get("winner")
                upset_delta = 0
                if winner == home["team_name"] and home_proj < away_proj:
                    upset_delta = away_proj - home_proj
                elif winner == away["team_name"] and away_proj < home_proj:
                    upset_delta = home_proj - away_proj

                # In playoffs, championship games get priority tier (0-5), consolation gets 100+
                tier_offset = 0 if is_championship else 100

                # Categories: 0 nail-biter (<5), 1 upset (proj diff>=10), 2 shootout (both>120), 3 blowout (>=30), 4 disaster (both<90), 5 other
                if margin < 5:
                    return (tier_offset + 0, margin)  # smaller margin first
                if upset_delta >= 10:
                    return (tier_offset + 1, -upset_delta)  # larger upset first
                if home["score"] > 120 and away["score"] > 120:
                    return (tier_offset + 2, -combined)  # higher combined first
                if margin >= 30:
                    return (tier_offset + 3, -margin)  # bigger blowouts later
                if home["score"] < 90 and away["score"] < 90:
                    return (tier_offset + 4, combined)  # lower combined first
                return (tier_offset + 5, -combined)

            # Sort each bracket
            sorted_championship = sorted(
                championship_matchups, key=lambda m: matchup_key(m, True)
            )
            sorted_consolation = sorted(
                consolation_matchups, key=lambda m: matchup_key(m, False)
            )

            # Output matchups with playoff context
            if playoff_ctx["is_playoff_week"]:
                round_num = playoff_ctx["playoff_round"]
                round_names = {1: "ROUND 1", 2: "SEMIFINALS", 3: "CHAMPIONSHIP"}
                round_name = round_names.get(round_num, f"ROUND {round_num}")

                context_parts.append(f"## 🏆 Championship Bracket - {round_name}")
                context_parts.append(
                    "**PRIORITY: These matchups should dominate the League Pulse and Stat of the Week**"
                )
                context_parts.append(
                    "\n**IMPORTANT: For each matchup, use the format: @[owner_name]'s [team_name]**"
                )
                context_parts.append(
                    "Example: @Marissa Tomko's Scott's Tots (109.74) def. @Han Jang's Beacon (87.64)\n"
                )

                for idx, matchup in enumerate(sorted_championship, 1):
                    self._add_matchup_details(context_parts, matchup, is_playoff=True)

                if sorted_consolation:
                    context_parts.append("\n## 🎪 Consolation Bracket")
                    context_parts.append(
                        "**SECONDARY COVERAGE: Brief mentions, shorter writeups (30-40 words)**"
                    )
                    context_parts.append(
                        "These teams are playing for pride only (no draft implications).\n"
                    )

                    for idx, matchup in enumerate(sorted_consolation, 1):
                        self._add_matchup_details(
                            context_parts, matchup, is_playoff=False
                        )
            else:
                # Regular season
                context_parts.append("## Matchups (Drama-ordered)")
                context_parts.append(
                    "\n**IMPORTANT: For each matchup, use the format: @[owner_name]'s [team_name]**"
                )
                context_parts.append(
                    "Example: @Marissa Tomko's Scott's Tots (109.74) def. @Han Jang's Beacon (87.64)\n"
                )

                for idx, matchup in enumerate(sorted_championship, 1):
                    self._add_matchup_details(context_parts, matchup, is_playoff=False)
        else:
            # Original format - just list all matchups
            context_parts.append("## Matchups")
            context_parts.append(
                "\n**IMPORTANT: For each matchup, use the format: @[owner_name]'s [team_name]**"
            )
            context_parts.append(
                "Example: @Marissa Tomko's Scott's Tots 109.74 def. @Han Jang's Beacon 87.64\n"
            )

            is_playoff = playoff_ctx["is_playoff_week"] if playoff_ctx else False
            for matchup in all_matchups:
                self._add_matchup_details(context_parts, matchup, is_playoff=is_playoff)

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

    def _add_week_highlights(
        self, context_parts: List[str], week_data: Dict, playoff_ctx: Dict = None
    ):
        """Add week highlights from stats endpoint - great for Stat of the Week"""
        week_stats = week_data.get("week_stats", {})
        if not week_stats:
            return

        context_parts.append("\n## 🔥 Week Highlights (for Stat of the Week)")

        # Add playoff priority note if applicable
        if playoff_ctx and playoff_ctx.get("is_playoff_week"):
            context_parts.append(
                "**⚠️ PLAYOFF PRIORITY: Strongly prefer stats from CHAMPIONSHIP BRACKET teams**"
            )

        context_parts.append(
            "Use ONE of these as your Stat of the Week - pick the most roastable:\n"
        )

        # Highest score (API returns dict with "team" and "points" keys)
        if week_stats.get("highest_score"):
            high = week_stats["highest_score"]
            team = high.get("team", "Unknown")
            score = high.get("points", 0)
            owner = TEAM_OWNERS.get(team, "Unknown")
            context_parts.append(
                f"**Week Winner:** @{owner}'s {team} scored {score} points"
            )

        # Lowest score (roastable)
        if week_stats.get("lowest_score"):
            low = week_stats["lowest_score"]
            team = low.get("team", "Unknown")
            score = low.get("points", 0)
            owner = TEAM_OWNERS.get(team, "Unknown")
            context_parts.append(
                f"**Dumpster Fire:** @{owner}'s {team} only managed {score} points 🗑️"
            )

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

    def _add_matchup_details(
        self, context_parts: List[str], matchup: Dict, is_playoff: bool = False
    ):
        """Add detailed matchup information for both teams"""
        home = matchup["home_team"]
        away = matchup["away_team"]

        # Use simple team name mapping
        home_owner = TEAM_OWNERS.get(home["team_name"], "Unknown")
        away_owner = TEAM_OWNERS.get(away["team_name"], "Unknown")

        # Calculate combined score for context
        combined_score = home["score"] + away["score"]

        # Determine winner and format header accordingly
        winner = matchup.get("winner")
        margin = matchup.get("margin", abs(home["score"] - away["score"]))

        if winner == home["team_name"]:
            winner_text = f"@{home_owner}'s {home['team_name']} ({home['score']}) def. @{away_owner}'s {away['team_name']} ({away['score']})"
            if is_playoff:
                context_parts.append(f"\n### ✅ WINNER: {winner_text}")
                context_parts.append(
                    f"**Result: @{home_owner} ADVANCES, @{away_owner} ELIMINATED**"
                )
            else:
                context_parts.append(f"\n### {winner_text}")
        else:
            winner_text = f"@{away_owner}'s {away['team_name']} ({away['score']}) def. @{home_owner}'s {home['team_name']} ({home['score']})"
            if is_playoff:
                context_parts.append(f"\n### ✅ WINNER: {winner_text}")
                context_parts.append(
                    f"**Result: @{away_owner} ADVANCES, @{home_owner} ELIMINATED**"
                )
            else:
                context_parts.append(f"\n### {winner_text}")

        context_parts.append(f"Margin of victory: {margin:.2f} points")
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
        owner = TEAM_OWNERS.get(team["team_name"], "Unknown")
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
        owner = TEAM_OWNERS.get(team["team_name"], "Unknown")
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
                    if (
                        start_pct >= 0
                        and start_pct >= 60
                        and player["actual_points"] > 20
                    ):
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

    def _add_standings(
        self, context_parts: List[str], week_data: Dict, enhanced: bool = False
    ):
        """Add current standings"""
        if enhanced:
            context_parts.append("\n## 🏆 Current Standings (For Power Rankings)")
            context_parts.append(
                "Use this to build Power Rankings tiers in the recap.\n"
            )

            all_standings = week_data["standings"]["standings"]

            # Tier 1: Top 4 teams
            context_parts.append("**Tier 1 - The Menaces (Top 4):**")
            for team in all_standings[:4]:
                owner = TEAM_OWNERS.get(team["team_name"], "Unknown")
                context_parts.append(
                    f"  {team['rank']}. @{owner}'s {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )

            # Tier 2: Teams 5-8
            context_parts.append("\n**Tier 2 - The Pretenders (5-8):**")
            for team in all_standings[4:8]:
                owner = TEAM_OWNERS.get(team["team_name"], "Unknown")
                context_parts.append(
                    f"  {team['rank']}. @{owner}'s {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )

            # Tier 3: Teams 9-12
            context_parts.append("\n**Tier 3 - The Bubble (9-12):**")
            for team in all_standings[8:12]:
                owner = TEAM_OWNERS.get(team["team_name"], "Unknown")
                context_parts.append(
                    f"  {team['rank']}. @{owner}'s {team['team_name']}: {team['wins']}-{team['losses']} "
                    f"({team['points_for']:.1f} PF)"
                )

            # Tier 4: Bottom teams (13-16)
            context_parts.append("\n**Tier 4 - The Lost Souls (13-16):**")
            for team in all_standings[12:]:
                owner = TEAM_OWNERS.get(team["team_name"], "Unknown")
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

    def _add_team_metrics(
        self, context_parts: List[str], week_data: Dict, week_num: int
    ):
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

    def _add_power_rankings(
        self, context_parts: List[str], week_data: Dict, week_num: int
    ):
        """Fetch and add power rankings with movement and identity context."""
        context_parts.append("\n## 🏆 Power Rankings (All Teams)")
        context_parts.append(
            "**FORMAT INSTRUCTIONS**: Use these Slack emojis for movement:"
        )
        context_parts.append(
            "- Up: `:triangle_upmaster:` followed by number (e.g., `:triangle_upmaster: 2`)"
        )
        context_parts.append(
            "- Down: `:triangle_downred:` followed by number (e.g., `:triangle_downred: 3`)"
        )
        context_parts.append("- No change: `—`")
        context_parts.append("")
        try:
            import requests

            api_url = week_data.get("api_url", "http://localhost:8000")
            resp = requests.get(f"{api_url}/api/power_rankings/{week_num}")
            resp.raise_for_status()
            rankings = resp.json().get("rankings", [])
            for r in rankings:
                movement_raw = r.get("movement", "—")
                owner = r.get("owner", "Unknown")
                team = r.get("team_name", "Team")
                record = f"{r.get('wins', 0)}–{r.get('losses', 0)}"
                pf = r.get("pf", 0)

                # Format movement with Slack emojis
                if movement_raw.startswith("+"):
                    movement_display = f":triangle_upmaster: {movement_raw[1:]}"
                elif movement_raw.startswith("-"):
                    movement_display = f":triangle_downred: {movement_raw[1:]}"
                else:
                    movement_display = "—"

                context_parts.append(
                    f"{r['rank']}. @{owner}'s {team} ({record}, PF {pf}) [{movement_display}]"
                )
        except Exception as e:
            context_parts.append(f"  (Could not fetch power rankings: {e})")

    def _add_trends(self, context_parts: List[str], week_data: Dict, week_num: int):
        """Add multi-week trends"""
        context_parts.append("\n## Multi-Week Trends (for deeper roasts)")

        try:
            # Record this week's data for trend tracking using the provided week_num
            self.trend_tracker.record_week(week_num, week_data["matchups"])
            notable_trends = self.trend_tracker.get_notable_trends(week_num)

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

    def _add_next_week_preview(
        self, context_parts: List[str], week_data: Dict, current_week: int
    ):
        """Fetch and add next week's matchups for the Preview section"""
        next_week = current_week + 1

        # Get playoff context
        standings = week_data.get("standings", {}).get("standings", [])
        playoff_ctx = self._get_playoff_context(current_week, standings)

        # Handle playoff clinching week - preview should show playoff bracket
        if playoff_ctx["is_clinching_week"]:
            context_parts.append(
                f"\n## 🏆 PLAYOFF PREVIEW - Round 1 (Week {next_week})"
            )
            context_parts.append("**The regular season is OVER. Playoffs begin!**\n")

            bracket = playoff_ctx["playoff_bracket"]
            if len(bracket) >= 6:
                context_parts.append("**ROUND 1 MATCHUPS:**")
                context_parts.append(
                    f"- #3 @{bracket[3]['owner']}'s {bracket[3]['team_name']} vs #6 @{bracket[6]['owner']}'s {bracket[6]['team_name']}"
                )
                context_parts.append(
                    f"- #4 @{bracket[4]['owner']}'s {bracket[4]['team_name']} vs #5 @{bracket[5]['owner']}'s {bracket[5]['team_name']}"
                )
                context_parts.append("")
                context_parts.append("**BYE WEEK (Top 2 seeds rest):**")
                context_parts.append(
                    f"- #1 @{bracket[1]['owner']}'s {bracket[1]['team_name']} - Earned the week off"
                )
                context_parts.append(
                    f"- #2 @{bracket[2]['owner']}'s {bracket[2]['team_name']} - Also watching from the couch"
                )
            context_parts.append("")
            return

        # Handle playoff weeks - show next round
        if playoff_ctx["is_playoff_week"]:
            round_num = playoff_ctx["playoff_round"]
            if round_num == 1:
                context_parts.append(f"\n## 🏆 SEMIFINAL PREVIEW (Week {next_week})")
                context_parts.append("**Winners advance. Losers go home.**\n")
            elif round_num == 2:
                context_parts.append(f"\n## 🏆 CHAMPIONSHIP PREVIEW (Week {next_week})")
                context_parts.append("**THE TITLE IS ON THE LINE.**\n")
            else:
                context_parts.append(f"\n## 🏆 Week {next_week} Preview")
                context_parts.append("")
            # Fall through to fetch actual matchups
        else:
            context_parts.append(
                f"\n## 🏈 Week {next_week} Preview (ACTUAL MATCHUPS - USE THESE)"
            )
            context_parts.append(
                "**CRITICAL: Use these exact matchups for the Preview section. Do NOT make up matchups.**\n"
            )

        try:
            import requests

            api_url = week_data.get("api_url", "http://localhost:8000")
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
