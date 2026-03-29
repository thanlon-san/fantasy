#!/usr/bin/env python3
"""
Two-Start Pitcher Streamer Planner

Every Thursday–Saturday, scans next week's MLB schedule to identify SPs
with two scheduled starts. Filters to waiver-wire-viable pitchers and
scores matchups by opponent team K%, park factors, and pitcher live FIP.

Usage:
    planner = StreamerPlanner()
    streamers = planner.find_two_start_streamers()
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache_manager import get_cache
from .daily_matchups import MLBStatsAPI, get_park_factor, get_next_week_schedule, get_week_range

logger = logging.getLogger(__name__)

MLB_API = "https://statsapi.mlb.com/api/v1"
TIMEOUT = 20
CACHE_TTL_HOURS = 6

# 2025 team strikeout rates (K% of PA) — higher = friendlier for streaming SPs
# Source: FanGraphs 2025 season + spring 2026 projections
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


@dataclass
class ScheduledStart:
    """One start in a two-start week."""
    date: str
    opponent: str
    home_away: str
    venue: Optional[str] = None
    opp_k_pct: float = 22.0
    park_factor: float = 1.0


@dataclass
class TwoStartStreamer:
    """A two-start pitcher streaming candidate."""
    pitcher: str
    team: str
    starts: List[ScheduledStart] = field(default_factory=list)
    pitcher_fip: Optional[float] = None
    composite_score: float = 0.0
    reason: str = ""


class StreamerPlanner:
    """Finds and scores two-start pitcher streaming opportunities."""

    def __init__(self):
        self.cache = get_cache()
        self.session = self._create_session()
        self.mlb_api = MLBStatsAPI()

    @staticmethod
    def _create_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def get_next_week_range(self) -> dict:
        return get_week_range()

    def _get_next_week_games(self) -> List:
        cached = self.cache.get("next_week_schedule", max_age_hours=CACHE_TTL_HOURS)
        if cached is not None:
            return cached

        games = get_next_week_schedule(api=self.mlb_api)
        serialized = [
            {
                "game_id": g.game_id,
                "game_date": g.game_date,
                "game_time": g.game_time,
                "away_team": g.away_team,
                "home_team": g.home_team,
                "away_pitcher": g.away_pitcher,
                "home_pitcher": g.home_pitcher,
                "venue": g.venue,
            }
            for g in games
        ]
        self.cache.set("next_week_schedule", serialized)
        return serialized

    def _identify_two_start_pitchers(self, games: List[dict]) -> Dict[str, List[dict]]:
        """Group games by probable pitcher, keep only those with 2+ starts."""
        pitcher_games: Dict[str, List[dict]] = defaultdict(list)

        for g in games:
            for side in ("away", "home"):
                pitcher = g.get(f"{side}_pitcher")
                if not pitcher:
                    continue
                team = g[f"{side}_team"]
                opponent = g["home_team"] if side == "away" else g["away_team"]
                pitcher_games[pitcher].append({
                    "date": g["game_date"],
                    "team": team,
                    "opponent": opponent,
                    "home_away": "away" if side == "away" else "home",
                    "venue": g.get("venue"),
                })

        return {p: starts for p, starts in pitcher_games.items() if len(starts) >= 2}

    def _score_matchup(self, opponent: str, venue: Optional[str]) -> float:
        """Score a single start matchup (0-100). Higher = better stream."""
        opp_k = TEAM_K_PCT.get(opponent, 22.0)
        pf = get_park_factor(venue) if venue else 1.0

        k_score = min(100, max(0, (opp_k - 18.0) / 8.0 * 100))
        park_score = min(100, max(0, (1.15 - pf) / 0.30 * 100))

        return k_score * 0.65 + park_score * 0.35

    def _get_pitcher_season_fip(self, pitcher_name: str) -> Optional[float]:
        """Try to fetch FIP from Statcast. Falls back to None."""
        try:
            from .statcast_client import StatcastClient
            sc = StatcastClient()
            parts = pitcher_name.split()
            if len(parts) < 2:
                return None
            pid = sc.get_player_id(parts[0], " ".join(parts[1:]))
            if not pid:
                return None
            result = sc.calculate_pitcher_fip(pid, days_back=45)
            return result["fip"] if result else None
        except Exception:
            return None

    def find_two_start_streamers(self) -> List[TwoStartStreamer]:
        """
        Main entry point. Returns scored two-start pitchers for next week,
        sorted by composite score (best streamers first).
        """
        cached = self.cache.get("two_start_streamers", max_age_hours=CACHE_TTL_HOURS)
        if cached is not None:
            return [self._deserialize(c) for c in cached]

        games = self._get_next_week_games()
        two_starters = self._identify_two_start_pitchers(games)

        streamers: List[TwoStartStreamer] = []
        for pitcher, start_list in two_starters.items():
            team = start_list[0]["team"]
            starts = []
            matchup_scores = []
            for s in start_list[:2]:
                opp = s["opponent"]
                venue = s.get("venue")
                ms = self._score_matchup(opp, venue)
                matchup_scores.append(ms)
                starts.append(ScheduledStart(
                    date=s["date"],
                    opponent=opp,
                    home_away=s["home_away"],
                    venue=venue,
                    opp_k_pct=TEAM_K_PCT.get(opp, 22.0),
                    park_factor=get_park_factor(venue) if venue else 1.0,
                ))

            avg_matchup = sum(matchup_scores) / len(matchup_scores) if matchup_scores else 0
            fip = self._get_pitcher_season_fip(pitcher)
            fip_bonus = 0.0
            if fip is not None:
                fip_bonus = max(0, (5.0 - fip) * 10)

            composite = avg_matchup * 0.70 + fip_bonus * 0.30

            opps = [s.opponent for s in starts]
            k_vals = [TEAM_K_PCT.get(o, 22.0) for o in opps]
            reason_parts = [f"Two starts: vs {' and '.join(opps)}"]
            if any(k > 24.0 for k in k_vals):
                reason_parts.append("high-K opponents")
            if fip is not None and fip < 3.80:
                reason_parts.append(f"strong FIP ({fip:.2f})")
            elif fip is not None:
                reason_parts.append(f"FIP {fip:.2f}")

            streamers.append(TwoStartStreamer(
                pitcher=pitcher,
                team=team,
                starts=starts,
                pitcher_fip=fip,
                composite_score=round(composite, 1),
                reason=" — ".join(reason_parts),
            ))

        streamers.sort(key=lambda s: s.composite_score, reverse=True)

        self.cache.set("two_start_streamers", [self._serialize(s) for s in streamers])
        return streamers

    @staticmethod
    def _serialize(s: TwoStartStreamer) -> dict:
        return {
            "pitcher": s.pitcher,
            "team": s.team,
            "starts": [
                {
                    "date": st.date, "opponent": st.opponent,
                    "home_away": st.home_away, "venue": st.venue,
                    "opp_k_pct": st.opp_k_pct, "park_factor": st.park_factor,
                }
                for st in s.starts
            ],
            "pitcher_fip": s.pitcher_fip,
            "composite_score": s.composite_score,
            "reason": s.reason,
        }

    @staticmethod
    def _deserialize(d: dict) -> TwoStartStreamer:
        return TwoStartStreamer(
            pitcher=d["pitcher"],
            team=d["team"],
            starts=[
                ScheduledStart(**st) for st in d.get("starts", [])
            ],
            pitcher_fip=d.get("pitcher_fip"),
            composite_score=d.get("composite_score", 0),
            reason=d.get("reason", ""),
        )
