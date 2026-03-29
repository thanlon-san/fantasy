"""
Multi-week trend tracking for fantasy football teams and players
Stores historical data to identify patterns and trends
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from shared.logger import get_logger
from src.constants import TREND_HISTORY_FILE, TREND_HISTORY_BACKUP, MAX_TREND_HISTORY_WEEKS

logger = get_logger(__name__)


class TrendTracker:
    def __init__(self, history_file: str = TREND_HISTORY_FILE):
        self.history_file = history_file
        self.history = self._load_history()
        logger.info(
            f"TrendTracker initialized with {len(self.history.get('teams', {}))} teams"
        )

    def _load_history(self) -> Dict:
        """Load historical data from file with error handling"""
        if not os.path.exists(self.history_file):
            logger.info(f"No history file found at {self.history_file}, starting fresh")
            return {"teams": {}, "players": {}, "last_updated": None}

        try:
            with open(self.history_file, "r") as f:
                history = json.load(f)
                logger.info(f"Loaded history from {self.history_file}")
                return history
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted history file: {e}")
            # Try to load backup
            return self._load_backup()
        except IOError as e:
            logger.error(f"Error reading history file: {e}")
            return self._load_backup()

    def _load_backup(self) -> Dict:
        """Attempt to load backup history file"""
        backup_file = TREND_HISTORY_BACKUP
        if os.path.exists(backup_file):
            try:
                logger.warning(f"Attempting to load backup from {backup_file}")
                with open(backup_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Backup also corrupted: {e}")

        logger.warning("Starting with empty history")
        return {"teams": {}, "players": {}, "last_updated": None}

    def _save_history(self):
        """Save historical data to file with backup"""
        try:
            # Create backup of existing file before overwriting
            if os.path.exists(self.history_file):
                shutil.copy2(self.history_file, TREND_HISTORY_BACKUP)
                logger.debug(f"Created backup at {TREND_HISTORY_BACKUP}")

            # Clean old data before saving
            self._clean_old_data()

            # Save new version
            self.history["last_updated"] = datetime.now().isoformat()
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)

            logger.info(f"History saved successfully to {self.history_file}")

        except IOError as e:
            logger.error(f"Failed to save history: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving history: {e}", exc_info=True)
            raise

    def _clean_old_data(self):
        """Remove data older than MAX_TREND_HISTORY_WEEKS"""
        current_weeks = set()

        # Collect all week numbers
        for team_data in self.history.get("teams", {}).values():
            current_weeks.update(int(w) for w in team_data.keys())

        if not current_weeks:
            return

        # Keep only recent weeks
        max_week = max(current_weeks)
        min_week_to_keep = max(1, max_week - MAX_TREND_HISTORY_WEEKS + 1)

        weeks_removed = 0
        # Clean team data
        for team_name in list(self.history.get("teams", {}).keys()):
            team_data = self.history["teams"][team_name]
            for week in list(team_data.keys()):
                if int(week) < min_week_to_keep:
                    del team_data[week]
                    weeks_removed += 1

        # Clean player data
        for player_name in list(self.history.get("players", {}).keys()):
            player_data = self.history["players"][player_name]
            for week in list(player_data.keys()):
                if int(week) < min_week_to_keep:
                    del player_data[week]

        if weeks_removed > 0:
            logger.info(
                f"Cleaned {weeks_removed} old week entries (keeping weeks {min_week_to_keep}-{max_week})"
            )

    def record_week(self, week: int, matchups_data: Dict):
        """Record data for a specific week"""
        for matchup in matchups_data["matchups"]:
            # Record home team data
            self._record_team_week(
                matchup["home_team"]["team_name"], week, matchup["home_team"]
            )

            # Record away team data
            self._record_team_week(
                matchup["away_team"]["team_name"], week, matchup["away_team"]
            )

            # Record player data
            for player in matchup["home_team"]["starters"]:
                self._record_player_week(player["name"], week, player)
            for player in matchup["away_team"]["starters"]:
                self._record_player_week(player["name"], week, player)

        self._save_history()

    def _record_team_week(self, team_name: str, week: int, team_data: Dict):
        """Record team performance for a week"""
        if team_name not in self.history["teams"]:
            self.history["teams"][team_name] = {}

        self.history["teams"][team_name][str(week)] = {
            "score": team_data["score"],
            "position_aggregates": team_data.get("position_aggregates", {}),
            "optimal_score": team_data.get("optimal_lineup", {}).get(
                "optimal_score", 0
            ),
            "management_gap": team_data.get("management_gap", 0),
            "bench_points": sum(p["actual_points"] for p in team_data.get("bench", [])),
        }

    def _record_player_week(self, player_name: str, week: int, player_data: Dict):
        """Record player performance for a week"""
        if player_name not in self.history["players"]:
            self.history["players"][player_name] = {}

        self.history["players"][player_name][str(week)] = {
            "position": player_data["position"],
            "actual_points": player_data["actual_points"],
            "projected_points": player_data["projected_points"],
            "stats": player_data.get("stats", {}),
        }

    def get_team_trends(self, team_name: str, weeks: int = 3) -> Dict:
        """Get trends for a specific team over recent weeks"""
        if team_name not in self.history["teams"]:
            return {}

        team_history = self.history["teams"][team_name]
        week_numbers = sorted([int(w) for w in team_history.keys()], reverse=True)[
            :weeks
        ]

        if not week_numbers:
            return {}

        scores = [team_history[str(w)]["score"] for w in week_numbers]
        management_gaps = [
            team_history[str(w)].get("management_gap", 0) for w in week_numbers
        ]

        trends = {
            "recent_weeks": week_numbers,
            "scores": scores,
            "average_score": round(sum(scores) / len(scores), 2),
            "score_trend": "improving"
            if len(scores) > 1 and scores[0] > scores[-1]
            else "declining"
            if len(scores) > 1 and scores[0] < scores[-1]
            else "stable",
            "average_management_gap": round(
                sum(management_gaps) / len(management_gaps), 2
            ),
            "consecutive_management_fails": self._count_consecutive_bad_management(
                team_name, week_numbers
            ),
        }

        return trends

    def get_player_trends(self, player_name: str, weeks: int = 3) -> Dict:
        """Get trends for a specific player over recent weeks"""
        if player_name not in self.history["players"]:
            return {}

        player_history = self.history["players"][player_name]
        week_numbers = sorted([int(w) for w in player_history.keys()], reverse=True)[
            :weeks
        ]

        if not week_numbers:
            return {}

        scores = [player_history[str(w)]["actual_points"] for w in week_numbers]
        projections = [player_history[str(w)]["projected_points"] for w in week_numbers]
        misses = [scores[i] - projections[i] for i in range(len(scores))]

        trends = {
            "recent_weeks": week_numbers,
            "scores": scores,
            "projections": projections,
            "average_score": round(sum(scores) / len(scores), 2),
            "average_projection_miss": round(sum(misses) / len(misses), 2),
            "consecutive_underperformances": self._count_consecutive_underperformances(
                player_name, week_numbers
            ),
            "consistency": "high"
            if max(scores) - min(scores) < 10
            else "medium"
            if max(scores) - min(scores) < 20
            else "low",
        }

        return trends
    
    def get_player_recent_average(self, player_name: str, weeks: int = 3) -> Optional[float]:
        """
        Get simple average points over last N weeks for a player
        Returns None if insufficient history
        
        This is used for "recent form" roasting
        """
        if player_name not in self.history["players"]:
            return None
        
        player_history = self.history["players"][player_name]
        week_numbers = sorted([int(w) for w in player_history.keys()], reverse=True)[:weeks]
        
        if len(week_numbers) < weeks:
            # Need at least N weeks of history
            return None
        
        scores = [player_history[str(w)]["actual_points"] for w in week_numbers]
        return round(sum(scores) / len(scores), 2)

    def _count_consecutive_bad_management(
        self, team_name: str, recent_weeks: List[int]
    ) -> int:
        """Count consecutive weeks with bad lineup management (gap > 15)"""
        count = 0
        team_history = self.history["teams"][team_name]

        for week in recent_weeks:
            gap = team_history[str(week)].get("management_gap", 0)
            if gap > 15:
                count += 1
            else:
                break

        return count

    def _count_consecutive_underperformances(
        self, player_name: str, recent_weeks: List[int]
    ) -> int:
        """Count consecutive weeks player underperformed projection"""
        count = 0
        player_history = self.history["players"][player_name]

        for week in recent_weeks:
            week_data = player_history[str(week)]
            if week_data["actual_points"] < week_data["projected_points"]:
                count += 1
            else:
                break

        return count

    def get_notable_trends(self, current_week: int) -> Dict:
        """Get notable trends across the league"""
        notable = {
            "hot_teams": [],
            "cold_teams": [],
            "consistent_underperformers": [],
            "management_disasters": [],
        }

        # Analyze team trends
        for team_name in self.history["teams"].keys():
            trends = self.get_team_trends(team_name, weeks=3)
            if trends:
                # Hot teams (improving scores)
                if (
                    trends["score_trend"] == "improving"
                    and trends["average_score"] > 110
                ):
                    notable["hot_teams"].append(
                        {"team": team_name, "average_score": trends["average_score"]}
                    )

                # Cold teams (declining scores)
                if trends["score_trend"] == "declining":
                    notable["cold_teams"].append(
                        {"team": team_name, "average_score": trends["average_score"]}
                    )

                # Management disasters (consistently leaving points)
                if trends["consecutive_management_fails"] >= 2:
                    notable["management_disasters"].append(
                        {
                            "team": team_name,
                            "average_gap": trends["average_management_gap"],
                            "consecutive_fails": trends["consecutive_management_fails"],
                        }
                    )

        # Analyze player trends (top targets only)
        for player_name in self.history["players"].keys():
            trends = self.get_player_trends(player_name, weeks=3)
            if trends and trends.get("consecutive_underperformances", 0) >= 3:
                notable["consistent_underperformers"].append(
                    {
                        "player": player_name,
                        "average_miss": trends["average_projection_miss"],
                    }
                )

        return notable
