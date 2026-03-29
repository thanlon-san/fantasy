#!/usr/bin/env python3
"""
Sprint Speed & Stolen Base Modeling
Uses Statcast sprint speed data + MLB Stats API game logs to identify SB upside.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import requests

from .cache_manager import get_cache

logger = logging.getLogger(__name__)

SPRINT_SPEED_ELITE = 28.5   # ft/s — 90th percentile
SPRINT_SPEED_FAST = 27.5    # ft/s — 75th percentile
SPRINT_SPEED_AVG = 26.5     # ft/s — 50th percentile

MLB_API = "https://statsapi.mlb.com/api/v1"


@dataclass
class SpeedProfile:
    """Sprint speed and stolen base profile for a player."""
    name: str
    mlb_id: Optional[int]
    sprint_speed: Optional[float]
    sb: int = 0
    cs: int = 0
    sb_attempts: int = 0
    sb_success_rate: float = 0.0
    sb_upside_score: float = 0.0
    tier: str = "UNKNOWN"  # ELITE / FAST / AVERAGE / SLOW / UNKNOWN

    @property
    def is_buy_low(self) -> bool:
        """Elite speed + low SB totals = buy-low SB target."""
        return (
            self.sprint_speed is not None
            and self.sprint_speed >= SPRINT_SPEED_FAST
            and self.sb < 5
        )


class SpeedTracker:
    """Fetches and scores sprint speed + SB upside for MLB players."""

    def __init__(self):
        self.cache = get_cache()
        self._speed_data: Dict[str, float] = {}
        self._loaded = False

    def load(self, season: Optional[int] = None) -> None:
        """Load the sprint speed leaderboard from Baseball Savant via pybaseball."""
        if self._loaded:
            return
        season = season or datetime.now().year
        cache_key = f"sprint_speed_{season}"
        cached = self.cache.get(cache_key, max_age_hours=24)
        if cached:
            self._speed_data = cached
            self._loaded = True
            return

        try:
            from pybaseball import statcast_sprint_speed
            df = statcast_sprint_speed(season)
            if df is not None and not df.empty:
                name_col = "last_name, first_name" if "last_name, first_name" in df.columns else None
                speed_col = "hp_to_1b" if "hp_to_1b" in df.columns else "sprint_speed"
                if speed_col not in df.columns:
                    for c in df.columns:
                        if "speed" in c.lower():
                            speed_col = c
                            break

                if name_col and speed_col in df.columns:
                    for _, row in df.iterrows():
                        raw = row[name_col]
                        parts = raw.split(", ")
                        if len(parts) == 2:
                            full_name = f"{parts[1].strip()} {parts[0].strip()}"
                        else:
                            full_name = raw.strip()
                        val = row.get(speed_col)
                        if val is not None:
                            try:
                                self._speed_data[full_name.lower()] = float(val)
                            except (ValueError, TypeError):
                                pass
                elif speed_col in df.columns:
                    # Newer pybaseball versions may have player_name column
                    for col_name in ("player_name", "name", "Name"):
                        if col_name in df.columns:
                            name_col = col_name
                            break
                    if name_col:
                        for _, row in df.iterrows():
                            full_name = str(row[name_col]).strip()
                            val = row.get(speed_col)
                            if val is not None:
                                try:
                                    self._speed_data[full_name.lower()] = float(val)
                                except (ValueError, TypeError):
                                    pass

                logger.info(f"Loaded sprint speed data for {len(self._speed_data)} players")
                self.cache.set(cache_key, self._speed_data)
            else:
                logger.warning("Sprint speed leaderboard returned empty — pybaseball may need season data")
        except Exception as e:
            logger.warning(f"Could not load sprint speed data: {e}")
        self._loaded = True

    def get_sprint_speed(self, player_name: str) -> Optional[float]:
        """Get a player's sprint speed (ft/s). Returns None if unknown."""
        self.load()
        return self._speed_data.get(player_name.lower())

    def _fetch_sb_from_game_logs(self, player_name: str) -> tuple:
        """Fetch SB/CS from MLB Stats API game logs for the current season.

        Returns (sb, cs).
        """
        cache_key = f"sb_gamelog_{player_name}_{datetime.now().year}"
        cached = self.cache.get(cache_key, max_age_hours=12)
        if cached is not None:
            return cached

        sb, cs = 0, 0
        try:
            resp = requests.get(
                f"{MLB_API}/people/search",
                params={"names": player_name},
                timeout=10,
            )
            resp.raise_for_status()
            people = resp.json().get("people", [])
            if not people:
                self.cache.set(cache_key, (0, 0))
                return 0, 0
            pid = people[0]["id"]

            season = datetime.now().year
            resp2 = requests.get(
                f"{MLB_API}/people/{pid}/stats",
                params={"stats": "season", "season": season, "group": "hitting"},
                timeout=10,
            )
            resp2.raise_for_status()
            stats_list = resp2.json().get("stats", [])
            if stats_list:
                splits = stats_list[0].get("splits", [])
                if splits:
                    s = splits[0].get("stat", {})
                    sb = s.get("stolenBases", 0)
                    cs = s.get("caughtStealing", 0)
        except Exception as e:
            logger.debug(f"SB lookup failed for {player_name}: {e}")

        self.cache.set(cache_key, (sb, cs))
        return sb, cs

    def get_profile(self, player_name: str) -> SpeedProfile:
        """Build a full speed + SB profile for a player."""
        speed = self.get_sprint_speed(player_name)
        sb, cs = self._fetch_sb_from_game_logs(player_name)
        attempts = sb + cs
        success_rate = sb / attempts if attempts > 0 else 0.0

        # Tier classification
        if speed is None:
            tier = "UNKNOWN"
        elif speed >= SPRINT_SPEED_ELITE:
            tier = "ELITE"
        elif speed >= SPRINT_SPEED_FAST:
            tier = "FAST"
        elif speed >= SPRINT_SPEED_AVG:
            tier = "AVERAGE"
        else:
            tier = "SLOW"

        # SB Upside Score (0-100)
        # Heavily weighted toward raw speed because sprint speed is the #1
        # predictor of future SB, more so than past SB totals.
        upside = 0.0
        if speed is not None:
            # Speed component (0-60): maps 25.0-30.0 ft/s → 0-60
            speed_pct = max(0.0, min(1.0, (speed - 25.0) / 5.0))
            upside += speed_pct * 60

            # Current SB output component (0-20): more SBs = higher floor
            sb_pct = min(1.0, sb / 20.0) if sb > 0 else 0.0
            upside += sb_pct * 20

            # Success rate component (0-10): high success = green light
            if attempts >= 3:
                upside += success_rate * 10

            # Opportunity component (0-10): many attempts = manager trusts them
            attempt_pct = min(1.0, attempts / 15.0)
            upside += attempt_pct * 10

        return SpeedProfile(
            name=player_name,
            mlb_id=None,
            sprint_speed=speed,
            sb=sb,
            cs=cs,
            sb_attempts=attempts,
            sb_success_rate=round(success_rate, 3),
            sb_upside_score=round(upside, 1),
            tier=tier,
        )

    def get_buy_low_targets(self, player_names: List[str]) -> List[SpeedProfile]:
        """Return players with elite speed but low SB totals (buy-low SB targets)."""
        profiles = [self.get_profile(name) for name in player_names]
        return sorted(
            [p for p in profiles if p.is_buy_low],
            key=lambda p: p.sprint_speed or 0,
            reverse=True,
        )
