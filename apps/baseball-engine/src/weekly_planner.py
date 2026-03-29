#!/usr/bin/env python3
"""
Full-Week Streaming Planner

For each day of the upcoming week, shows the best available SP matchups.
Scores by: opponent K% (proxy for wRC+), park factor, pitcher FIP,
and Vegas implied game total when available.

Also shows team game counts to help choose batting streamers
(a team playing 7 games > 5 games for counting stats).

Requires: Vegas lines (2B), FIP scoring (1A), schedule data.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .cache_manager import get_cache
from .daily_matchups import MLBStatsAPI, get_park_factor, get_next_week_schedule, get_week_range

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 4

# Opponent K% lookup — same as streamer_planner.py
TEAM_K_PCT: Dict[str, float] = {
    "ARI": 23.5, "ATL": 22.0, "BAL": 21.5, "BOS": 22.5,
    "CHC": 23.0, "CWS": 25.5, "CIN": 24.0, "CLE": 20.5,
    "COL": 24.5, "DET": 24.0, "HOU": 19.5, "KC": 22.0,
    "LAA": 23.5, "LAD": 20.0, "MIA": 24.5, "MIL": 22.5,
    "MIN": 22.0, "NYM": 21.0, "NYY": 22.5, "OAK": 25.0,
    "PHI": 21.5, "PIT": 24.0, "SD": 22.0, "SF": 21.5,
    "SEA": 23.5, "STL": 22.5, "TB": 23.0, "TEX": 22.5,
    "TOR": 23.0, "WSH": 24.0,
}

# Approximate team wRC+ (2025 season + 2026 spring projections)
# Higher wRC+ = harder to stream against; lower = friendlier for pitchers
TEAM_WRC_PLUS: Dict[str, int] = {
    "ARI": 100, "ATL": 105, "BAL": 108, "BOS": 103,
    "CHC": 98,  "CWS": 78,  "CIN": 96,  "CLE": 102,
    "COL": 88,  "DET": 92,  "HOU": 112, "KC": 95,
    "LAA": 94,  "LAD": 115, "MIA": 82,  "MIL": 101,
    "MIN": 100, "NYM": 106, "NYY": 110, "OAK": 80,
    "PHI": 107, "PIT": 88,  "SD": 99,   "SF": 96,
    "SEA": 93,  "STL": 97,  "TB": 94,   "TEX": 102,
    "TOR": 98,  "WSH": 86,
}


@dataclass
class DailyStream:
    """A single streaming opportunity for one day."""
    date: str
    pitcher: str
    team: str
    opponent: str
    home_away: str
    venue: Optional[str] = None
    opp_k_pct: float = 22.0
    opp_wrc_plus: int = 100
    park_factor: float = 1.0
    game_total: Optional[float] = None
    score: float = 0.0
    reason: str = ""


@dataclass
class TeamGameCount:
    """Number of games a team plays next week — for batting streamer value."""
    team: str
    games: int
    opponents: List[str] = field(default_factory=list)


@dataclass
class WeeklyPlan:
    """Full week streaming plan."""
    week_start: str
    week_end: str
    daily_streams: Dict[str, List[DailyStream]] = field(default_factory=dict)
    team_game_counts: List[TeamGameCount] = field(default_factory=list)
    optimal_streams: List[DailyStream] = field(default_factory=list)


class WeeklyPlanner:
    """Builds a day-by-day streaming plan for the upcoming week."""

    def __init__(self):
        self.cache = get_cache()
        self.mlb_api = MLBStatsAPI()
        self._odds_fetcher = None

    def _get_odds_fetcher(self):
        if self._odds_fetcher is None:
            try:
                from .odds_fetcher import OddsFetcher
                self._odds_fetcher = OddsFetcher()
                self._odds_fetcher.load()
            except Exception:
                pass
        return self._odds_fetcher

    def _score_pitching_matchup(
        self,
        opponent: str,
        venue: Optional[str],
        game_total: Optional[float],
    ) -> float:
        """Score a pitching streaming opportunity (0-100). Higher = better."""
        opp_k = TEAM_K_PCT.get(opponent, 22.0)
        opp_wrc = TEAM_WRC_PLUS.get(opponent, 100)
        pf = get_park_factor(venue) if venue else 1.0

        # K% component: high K% opponents are better to stream against
        k_score = min(100, max(0, (opp_k - 18.0) / 8.0 * 100))

        # wRC+ component: low wRC+ opponents are better (inverted)
        wrc_score = min(100, max(0, (120 - opp_wrc) / 40.0 * 100))

        # Park factor: pitcher-friendly parks score higher
        park_score = min(100, max(0, (1.15 - pf) / 0.30 * 100))

        # Vegas total: low game totals favor pitchers
        vegas_score = 50.0  # neutral default
        if game_total is not None:
            if game_total <= 7.0:
                vegas_score = 85.0
            elif game_total <= 8.0:
                vegas_score = 65.0
            elif game_total >= 10.0:
                vegas_score = 15.0
            elif game_total >= 9.0:
                vegas_score = 30.0

        return (
            k_score * 0.30
            + wrc_score * 0.25
            + park_score * 0.20
            + vegas_score * 0.25
        )

    def build_plan(self) -> WeeklyPlan:
        """Build the full weekly streaming plan."""
        cached = self.cache.get("weekly_plan", max_age_hours=CACHE_TTL_HOURS)
        if cached is not None:
            return self._deserialize(cached)

        week_range = get_week_range()
        games = get_next_week_schedule(api=self.mlb_api)

        odds = self._get_odds_fetcher()

        # Group games by date
        games_by_date: Dict[str, list] = defaultdict(list)
        team_games: Dict[str, list] = defaultdict(list)

        for g in games:
            date = g.game_date
            games_by_date[date].append(g)
            team_games[g.away_team].append({"date": date, "opp": g.home_team, "ha": "away"})
            team_games[g.home_team].append({"date": date, "opp": g.away_team, "ha": "home"})

        # Build daily streams
        daily_streams: Dict[str, List[DailyStream]] = {}
        for date in sorted(games_by_date.keys()):
            day_games = games_by_date[date]
            streams: List[DailyStream] = []

            for g in day_games:
                for side in ("away", "home"):
                    pitcher = g.away_pitcher if side == "away" else g.home_pitcher
                    if not pitcher:
                        continue
                    team = g.away_team if side == "away" else g.home_team
                    opponent = g.home_team if side == "away" else g.away_team
                    ha = side

                    game_total = None
                    if odds:
                        game_odds = odds.get_game_odds(team)
                        if game_odds:
                            game_total = game_odds.total

                    score = self._score_pitching_matchup(opponent, g.venue, game_total)

                    opp_k = TEAM_K_PCT.get(opponent, 22.0)
                    opp_wrc = TEAM_WRC_PLUS.get(opponent, 100)
                    pf = get_park_factor(g.venue) if g.venue else 1.0

                    reason_parts = []
                    if opp_k >= 24.0:
                        reason_parts.append(f"high-K opponent ({opp_k}%)")
                    if opp_wrc <= 90:
                        reason_parts.append("weak lineup")
                    if pf <= 0.95:
                        reason_parts.append("pitcher park")
                    if game_total and game_total <= 7.5:
                        reason_parts.append(f"low total ({game_total})")

                    streams.append(DailyStream(
                        date=date,
                        pitcher=pitcher,
                        team=team,
                        opponent=opponent,
                        home_away=ha,
                        venue=g.venue,
                        opp_k_pct=opp_k,
                        opp_wrc_plus=opp_wrc,
                        park_factor=pf,
                        game_total=game_total,
                        score=round(score, 1),
                        reason=", ".join(reason_parts) if reason_parts else "neutral matchup",
                    ))

            streams.sort(key=lambda s: s.score, reverse=True)
            daily_streams[date] = streams[:8]

        # Pick the single best stream per day → optimal plan
        optimal: List[DailyStream] = []
        for date in sorted(daily_streams.keys()):
            day = daily_streams[date]
            if day:
                optimal.append(day[0])

        # Team game counts
        counts: List[TeamGameCount] = []
        for team, gms in sorted(team_games.items()):
            counts.append(TeamGameCount(
                team=team,
                games=len(gms),
                opponents=[g["opp"] for g in gms],
            ))
        counts.sort(key=lambda c: c.games, reverse=True)

        plan = WeeklyPlan(
            week_start=week_range["start"],
            week_end=week_range["end"],
            daily_streams=daily_streams,
            team_game_counts=counts,
            optimal_streams=optimal,
        )

        self.cache.set("weekly_plan", self._serialize(plan))
        return plan

    @staticmethod
    def _serialize(plan: WeeklyPlan) -> dict:
        return {
            "week_start": plan.week_start,
            "week_end": plan.week_end,
            "daily_streams": {
                date: [
                    {
                        "date": s.date, "pitcher": s.pitcher, "team": s.team,
                        "opponent": s.opponent, "home_away": s.home_away,
                        "venue": s.venue, "opp_k_pct": s.opp_k_pct,
                        "opp_wrc_plus": s.opp_wrc_plus, "park_factor": s.park_factor,
                        "game_total": s.game_total, "score": s.score,
                        "reason": s.reason,
                    }
                    for s in streams
                ]
                for date, streams in plan.daily_streams.items()
            },
            "team_game_counts": [
                {"team": c.team, "games": c.games, "opponents": c.opponents}
                for c in plan.team_game_counts
            ],
            "optimal_streams": [
                {
                    "date": s.date, "pitcher": s.pitcher, "team": s.team,
                    "opponent": s.opponent, "home_away": s.home_away,
                    "venue": s.venue, "opp_k_pct": s.opp_k_pct,
                    "opp_wrc_plus": s.opp_wrc_plus, "park_factor": s.park_factor,
                    "game_total": s.game_total, "score": s.score,
                    "reason": s.reason,
                }
                for s in plan.optimal_streams
            ],
        }

    @staticmethod
    def _deserialize(d: dict) -> WeeklyPlan:
        daily = {}
        for date, streams in d.get("daily_streams", {}).items():
            daily[date] = [DailyStream(**s) for s in streams]
        return WeeklyPlan(
            week_start=d["week_start"],
            week_end=d["week_end"],
            daily_streams=daily,
            team_game_counts=[
                TeamGameCount(**c) for c in d.get("team_game_counts", [])
            ],
            optimal_streams=[
                DailyStream(**s) for s in d.get("optimal_streams", [])
            ],
        )
