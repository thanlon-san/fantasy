#!/usr/bin/env python3
"""
Advanced Analytics Module

Sophisticated metrics and indicators for elite-level lineup recommendations.
Now fetches live umpire assignments from MLB Stats API and cross-references
with curated umpire tendencies data.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

APP_ROOT = Path(__file__).parent.parent
UMPIRE_DATA_PATH = APP_ROOT / "data" / "umpire_tendencies.json"

try:
    from .cache_manager import get_cache
except ImportError:
    get_cache = None  # type: ignore[assignment]


def _load_umpire_tendencies() -> Dict[str, dict]:
    """Load curated umpire tendency data from JSON file."""
    try:
        if UMPIRE_DATA_PATH.exists():
            with open(UMPIRE_DATA_PATH, "r") as f:
                data = json.load(f)
            return data.get("umpires", {})
    except Exception as e:
        logger.warning(f"Could not load umpire tendencies: {e}")
    return {}


UMPIRE_TENDENCIES = _load_umpire_tendencies()


@dataclass
class UmpireAssignment:
    """Today's home plate umpire for a specific game."""
    name: str
    game_pk: int
    home_team: str
    away_team: str
    zone_size: int = 100
    accuracy: int = 90
    favor: str = "neutral"
    consistency: int = 90
    run_impact: float = 0.0


@dataclass
class AdvancedMatchupMetrics:
    """Advanced metrics for a matchup"""
    xBA: Optional[float] = None
    xSLG: Optional[float] = None
    xwOBA: Optional[float] = None
    hard_hit_trend: Optional[str] = None
    barrel_trend: Optional[str] = None
    gb_percent: Optional[float] = None
    fb_percent: Optional[float] = None
    ld_percent: Optional[float] = None
    chase_rate: Optional[float] = None
    zone_contact_rate: Optional[float] = None
    umpire_adjustment: float = 0
    pitch_type_advantage: bool = False
    velocity_advantage: bool = False


class AdvancedAnalytics:
    """Advanced analytics with live umpire assignments."""

    def __init__(self):
        self._cache = get_cache() if get_cache else None
        self._umpire_assignments: Dict[str, UmpireAssignment] = {}
        self._assignments_date: Optional[str] = None

    def _fetch_todays_umpires(self) -> Dict[str, UmpireAssignment]:
        """Fetch today's HP umpire assignments from MLB Stats API."""
        today = datetime.now().strftime("%Y-%m-%d")

        if self._assignments_date == today and self._umpire_assignments:
            return self._umpire_assignments

        cache_key = f"umpire_assignments_{today}"
        if self._cache:
            cached = self._cache.get(cache_key, max_age_hours=6)
            if cached:
                assignments = {}
                for team, data in cached.items():
                    assignments[team] = UmpireAssignment(**data)
                self._umpire_assignments = assignments
                self._assignments_date = today
                return assignments

        assignments: Dict[str, UmpireAssignment] = {}
        try:
            import requests
            url = f"https://statsapi.mlb.com/api/v1/schedule?date={today}&sportId=1&hydrate=officials"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for date_entry in data.get("dates", []):
                for game in date_entry.get("games", []):
                    game_pk = game.get("gamePk", 0)
                    home = game.get("teams", {}).get("home", {}).get("team", {}).get("abbreviation", "")
                    away = game.get("teams", {}).get("away", {}).get("team", {}).get("abbreviation", "")

                    hp_ump_name = None
                    for official in game.get("officials", []):
                        if official.get("officialType") == "Home Plate":
                            full = official.get("official", {}).get("fullName")
                            if full:
                                hp_ump_name = full
                                break

                    if hp_ump_name:
                        tendencies = UMPIRE_TENDENCIES.get(hp_ump_name, {})
                        assignment = UmpireAssignment(
                            name=hp_ump_name,
                            game_pk=game_pk,
                            home_team=home,
                            away_team=away,
                            zone_size=tendencies.get("zone_size", 100),
                            accuracy=tendencies.get("accuracy", 90),
                            favor=tendencies.get("favor", "neutral"),
                            consistency=tendencies.get("consistency", 90),
                            run_impact=tendencies.get("run_impact", 0.0),
                        )
                        if home:
                            assignments[home] = assignment
                        if away:
                            assignments[away] = assignment

            logger.info(f"Fetched {len(assignments)} umpire assignments for {today}")

        except Exception as e:
            logger.warning(f"Could not fetch umpire assignments: {e}")

        if self._cache and assignments:
            self._cache.set(cache_key, {
                k: {
                    "name": v.name, "game_pk": v.game_pk,
                    "home_team": v.home_team, "away_team": v.away_team,
                    "zone_size": v.zone_size, "accuracy": v.accuracy,
                    "favor": v.favor, "consistency": v.consistency,
                    "run_impact": v.run_impact,
                }
                for k, v in assignments.items()
            })

        self._umpire_assignments = assignments
        self._assignments_date = today
        return assignments

    def get_umpire_for_team(self, team_abbr: str) -> Optional[UmpireAssignment]:
        """Get today's HP umpire for a specific team."""
        assignments = self._fetch_todays_umpires()
        return assignments.get(team_abbr.upper())

    def get_umpire_adjustment(
        self,
        umpire_name: Optional[str],
        player_type: str,
        team_abbr: Optional[str] = None,
    ) -> Tuple[float, Optional[str]]:
        """
        Get lineup adjustment based on home plate umpire.

        Can be called with an umpire name (legacy) or a team abbreviation
        (new — auto-looks up today's assignment).
        """
        tendencies = None

        if team_abbr and not umpire_name:
            assignment = self.get_umpire_for_team(team_abbr)
            if assignment:
                umpire_name = assignment.name
                tendencies = {
                    "zone_size": assignment.zone_size,
                    "favor": assignment.favor,
                    "consistency": assignment.consistency,
                    "run_impact": assignment.run_impact,
                }

        if umpire_name and not tendencies:
            tendencies = UMPIRE_TENDENCIES.get(umpire_name)

        if not tendencies:
            return 0, None

        zone_size = tendencies.get("zone_size", 100)
        run_impact = tendencies.get("run_impact", 0.0)
        ump_label = umpire_name or "Unknown"

        if zone_size > 102:
            if player_type == "pitcher":
                adjustment = min(5, (zone_size - 100) / 2)
                reason = f"{ump_label}: large zone (pitcher-friendly)"
            else:
                adjustment = -min(5, (zone_size - 100) / 2)
                reason = f"{ump_label}: large zone (hitter-unfriendly)"
        elif zone_size < 98:
            if player_type == "hitter":
                adjustment = min(5, (100 - zone_size) / 2)
                reason = f"{ump_label}: small zone (hitter-friendly)"
            else:
                adjustment = -min(5, (100 - zone_size) / 2)
                reason = f"{ump_label}: small zone (pitcher-unfriendly)"
        else:
            adjustment = 0
            reason = None

        if abs(run_impact) >= 0.08 and reason:
            reason += f" (run impact: {run_impact:+.2f})"

        return adjustment, reason

    def get_all_todays_umpires(self) -> List[UmpireAssignment]:
        """Get all today's HP umpire assignments sorted by game."""
        assignments = self._fetch_todays_umpires()
        seen = set()
        unique = []
        for a in assignments.values():
            if a.game_pk not in seen:
                seen.add(a.game_pk)
                unique.append(a)
        return sorted(unique, key=lambda a: a.game_pk)

    def analyze_contact_quality_trends(
        self,
        recent_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float],
    ) -> Dict[str, str]:
        trends = {}
        for metric, threshold in [("hard_hit_percent", 5.0), ("barrel_percent", 2.0), ("exit_velocity_avg", 1.5)]:
            recent_val = recent_metrics.get(metric)
            baseline_val = baseline_metrics.get(metric)
            if recent_val is not None and baseline_val is not None:
                diff = recent_val - baseline_val
                key = metric.replace("_percent", "_trend").replace("_avg", "_trend")
                if diff > threshold:
                    trends[key] = "improving"
                elif diff < -threshold:
                    trends[key] = "declining"
                else:
                    trends[key] = "stable"
        return trends

    def calculate_expected_stats_boost(
        self, actual_avg: float, xBA: Optional[float]
    ) -> Tuple[float, Optional[str]]:
        if not xBA:
            return 0, None
        diff = xBA - actual_avg
        if diff > 0.030:
            return 5, f"Due for positive regression (xBA: {xBA:.3f})"
        elif diff > 0.015:
            return 3, "Hitting ball better than results show"
        elif diff < -0.020:
            return -3, "Results outpacing contact quality"
        return 0, None

    def analyze_batted_ball_profile(
        self,
        gb_percent: Optional[float],
        fb_percent: Optional[float],
        park_factor: float,
    ) -> Tuple[float, Optional[str]]:
        if not gb_percent or not fb_percent:
            return 0, None
        if fb_percent > 45 and park_factor > 1.05:
            return 3, "Fly ball hitter in HR-friendly park"
        elif gb_percent > 50 and park_factor < 0.95:
            return 2, "Ground ball approach suits park"
        elif fb_percent > 45 and park_factor < 0.95:
            return -2, "Power suppressed in this park"
        return 0, None

    def get_rest_fatigue_adjustment(
        self,
        is_pitcher: bool,
        days_since_last_game: int,
        games_in_last_week: int,
    ) -> Tuple[float, Optional[str]]:
        if is_pitcher:
            if days_since_last_game < 4:
                return -5, "On short rest"
            elif days_since_last_game > 6:
                return -2, "Extra rest (rust factor)"
            return 0, None
        else:
            if games_in_last_week >= 7:
                return -3, "Potential fatigue (7 straight games)"
            elif games_in_last_week <= 3 and days_since_last_game <= 1:
                return 2, "Well-rested"
            return 0, None


def get_advanced_analytics() -> AdvancedAnalytics:
    """Get advanced analytics singleton"""
    return AdvancedAnalytics()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    analytics = AdvancedAnalytics()

    print("\n📊 Advanced Analytics Module")
    print("=" * 70)

    # Test umpire lookup from tendencies file
    adj, reason = analytics.get_umpire_adjustment("Pat Hoberg", "hitter")
    print(f"Umpire adjustment (Pat Hoberg, hitter): {adj:+.1f}")
    if reason:
        print(f"  Reason: {reason}")

    # Test live umpire fetch
    print("\nFetching today's umpire assignments...")
    umps = analytics.get_all_todays_umpires()
    if umps:
        for u in umps[:5]:
            print(f"  {u.away_team} @ {u.home_team}: {u.name} (zone {u.zone_size}, {u.favor})")
    else:
        print("  No games today or API unavailable")

    print("\n✅ Advanced Analytics ready")
