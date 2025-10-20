"""
Context Builder for Fantasy Football Recaps
Builds comprehensive context from weekly data for LLM recap generation
"""

from typing import Dict, List
from src.trend_tracker import TrendTracker
from src.ownership_stats import OwnershipStats


class ContextBuilder:
    """Builds rich context from fantasy football data for LLM roasting"""
    
    def __init__(self, trend_tracker: TrendTracker, ownership_stats: OwnershipStats):
        self.trend_tracker = trend_tracker
        self.ownership_stats = ownership_stats
    
    def build_context(self, week_data: Dict) -> str:
        """
        Build comprehensive context from week data
        
        Args:
            week_data: Dict containing league, matchups, week_stats, teams, standings
        
        Returns:
            Formatted context string for LLM
        """
        context_parts = []
        
        # Header
        league = week_data["league"]
        context_parts.append(f"# Week {league['current_week']} Recap Data")
        context_parts.append(f"\nLeague: {league['league_name']}")
        context_parts.append(f"Season: {league.get('season_year', league.get('year', 'N/A'))}")
        context_parts.append("")
        
        # Matchups - the meat of the recap
        context_parts.append("## Matchups")
        
        for matchup in week_data["matchups"]["matchups"]:
            home = matchup["home_team"]
            away = matchup["away_team"]
            
            context_parts.append(
                f"\n### {home['team_name']} ({home['score']}) vs {away['team_name']} ({away['score']})"
            )
            
            # Home team analytics
            self._add_team_analytics(context_parts, home, "home")
            self._add_starters(context_parts, home)
            self._add_bench_stars(context_parts, home)
            
            # Away team analytics  
            self._add_team_analytics(context_parts, away, "away")
            self._add_starters(context_parts, away)
            self._add_bench_stars(context_parts, away)
            
            context_parts.append("")
        
        # Current standings
        self._add_standings(context_parts, week_data)
        
        # Team activity metrics
        self._add_team_metrics(context_parts, week_data)
        
        # Multi-week trends
        self._add_trends(context_parts, week_data)
        
        return "\n".join(context_parts)
    
    def _add_team_analytics(self, context_parts: List[str], team: Dict, label: str):
        """Add team-level analytics"""
        context_parts.append(f"\n**{team['team_name']} Analytics:**")
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
        context_parts.append(f"\n**{team['team_name']} Starters:**")
        
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
                    recent_avg = self.trend_tracker.get_player_recent_average(player["name"], weeks=3)
                    if recent_avg is not None:
                        # Only add if it's a COLD STREAK being started (<8 avg, bust again)
                        if recent_avg < 8 and player["actual_points"] < 10:
                            starter_line += f"\n    ❄️  COLD STREAK: L3W avg {recent_avg}, still started him"
                except Exception:
                    pass  # Fail silently
                
                # Check for ownership roast on starters (STRICT - only <3% ownership who bust)
                start_pct = player.get("percent_started", 0)
                if start_pct < 3 and player["actual_points"] < 5:
                    try:
                        ownership_roast = self.ownership_stats.generate_ownership_roast(
                            player["name"],
                            was_started=True,
                            points_scored=player["actual_points"],
                            percent_started=start_pct
                        )
                        if ownership_roast:
                            starter_line += f"\n    💣 OWNERSHIP ROAST: {ownership_roast}"
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
                
                bench_line = (
                    f"  - BENCHED: {player['name']}: {player['actual_points']:.1f} pts "
                    f"(started {start_pct}% on ESPN - {roastable})"
                )
                
                # Check for recent form (STRICT - only hot streaks benched)
                try:
                    recent_avg = self.trend_tracker.get_player_recent_average(player["name"], weeks=3)
                    if recent_avg is not None:
                        # Only add if it's a HOT STREAK being benched (>18 avg, scored 20+ again)
                        if recent_avg > 18 and player["actual_points"] > 20:
                            bench_line += f"\n    🔥 HOT STREAK BENCHED: L3W avg {recent_avg}, benched anyway"
                except Exception:
                    pass  # Fail silently
                
                # Check for ownership roast (STRICT thresholds - only when really bad)
                ownership_roast = None
                try:
                    # Only roast benching if player has >75% ownership AND scored 20+
                    if start_pct > 75 and player["actual_points"] > 20:
                        ownership_roast = self.ownership_stats.generate_ownership_roast(
                            player["name"],
                            was_started=False,
                            points_scored=player["actual_points"],
                            percent_started=start_pct
                        )
                except Exception:
                    pass  # Fail silently
                
                if ownership_roast:
                    bench_line += f"\n    💣 OWNERSHIP ROAST: {ownership_roast}"
                context_parts.append(bench_line)
    
    def _add_standings(self, context_parts: List[str], week_data: Dict):
        """Add current standings"""
        context_parts.append("## Current Standings (Top 5)")
        for team in week_data["standings"]["standings"][:5]:
            context_parts.append(
                f"{team['rank']}. {team['team_name']}: {team['wins']}-{team['losses']} "
                f"({team['points_for']:.1f} PF)"
            )
    
    def _add_team_metrics(self, context_parts: List[str], week_data: Dict):
        """Add team activity and efficiency metrics"""
        context_parts.append("\n## Team Activity & Efficiency Metrics (for roasting)")
        try:
            import requests
            teams_response = requests.get(f"{week_data.get('api_url', 'http://localhost:8000')}/api/teams")
            teams_response.raise_for_status()
            all_teams = teams_response.json()["teams"]
            
            league = week_data["league"]
            week_num = league["current_week"]
            total_teams = len(all_teams)
            
            for team_data in all_teams:
                team_name = team_data["team_name"]
                wins = team_data["wins"]
                losses = team_data["losses"]
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
                context_parts.append(f"  - Waiver moves: {acquisitions} adds, {drops} drops")
                if week_num > 0:
                    context_parts.append(f"  - Churn rate: {drops / week_num:.1f} drops per week")
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
    
    def _add_trends(self, context_parts: List[str], week_data: Dict):
        """Add multi-week trends"""
        context_parts.append("\n## Multi-Week Trends (for deeper roasts)")
        
        try:
            league = week_data["league"]
            
            # Record this week's data for trend tracking
            self.trend_tracker.record_week(
                league["current_week"], week_data["matchups"]
            )
            notable_trends = self.trend_tracker.get_notable_trends(league["current_week"])
            
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
                context_parts.append("\n**Management Disasters (consistently leaving points):**")
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

