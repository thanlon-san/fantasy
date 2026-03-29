#!/usr/bin/env python3
"""
Catcher Framing Integration

Top-3 framing catchers add ~15 called strikes per game, boosting their
pitcher's K rate and suppressing walks. When evaluating pitcher matchups,
check who's catching:
- Elite framers: boost pitcher's "toughness" score by 3–5 points
- Poor framers: reduce by 3–5 points

Data source: Baseball Savant catcher framing leaderboard (public CSV).
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .cache_manager import get_cache

logger = logging.getLogger(__name__)


@dataclass
class FramingProfile:
    """Catcher framing profile from Baseball Savant."""
    name: str
    player_id: int
    team: str
    runs_extra_strikes: float   # runs saved via framing (positive = better)
    strike_rate: float           # called strike rate above average (percentage points)
    shadow_zone_called_strike_pct: float  # called strike % on pitches at the edge of the zone
    games_caught: int
    innings_caught: float
    framing_tier: str            # "ELITE" | "GOOD" | "AVERAGE" | "POOR" | "LIABILITY"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "player_id": self.player_id,
            "team": self.team,
            "runs_extra_strikes": round(self.runs_extra_strikes, 1),
            "strike_rate": round(self.strike_rate, 2),
            "shadow_zone_called_strike_pct": round(self.shadow_zone_called_strike_pct, 1),
            "games_caught": self.games_caught,
            "innings_caught": round(self.innings_caught, 1),
            "framing_tier": self.framing_tier,
        }


# Tier thresholds based on runs_extra_strikes (season pace)
TIER_THRESHOLDS = {
    "ELITE": 8.0,     # top ~5 catchers
    "GOOD": 3.0,      # top ~15
    "AVERAGE": -3.0,   # middle tier
    "POOR": -8.0,      # bottom ~15
    # below POOR → LIABILITY
}

# Pitcher matchup adjustment by catcher framing tier
FRAMING_ADJUSTMENTS: Dict[str, float] = {
    "ELITE": 5.0,      # pitcher gets +5 points
    "GOOD": 3.0,
    "AVERAGE": 0.0,
    "POOR": -3.0,
    "LIABILITY": -5.0,
}

# MLB team abbreviation mapping for Savant data
TEAM_ABBR_MAP = {
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BOS": "BOS", "CHC": "CHC",
    "CWS": "CWS", "CIN": "CIN", "CLE": "CLE", "COL": "COL", "DET": "DET",
    "HOU": "HOU", "KC": "KC", "LAA": "LAA", "LAD": "LAD", "MIA": "MIA",
    "MIL": "MIL", "MIN": "MIN", "NYM": "NYM", "NYY": "NYY", "OAK": "OAK",
    "PHI": "PHI", "PIT": "PIT", "SD": "SD", "SF": "SF", "SEA": "SEA",
    "STL": "STL", "TB": "TB", "TEX": "TEX", "TOR": "TOR", "WSH": "WSH",
}


def _classify_tier(runs_extra: float) -> str:
    if runs_extra >= TIER_THRESHOLDS["ELITE"]:
        return "ELITE"
    elif runs_extra >= TIER_THRESHOLDS["GOOD"]:
        return "GOOD"
    elif runs_extra >= TIER_THRESHOLDS["AVERAGE"]:
        return "AVERAGE"
    elif runs_extra >= TIER_THRESHOLDS["POOR"]:
        return "POOR"
    return "LIABILITY"


class CatcherFraming:
    """Catcher framing data fetched from Baseball Savant."""

    def __init__(self):
        self._cache = get_cache()
        self._profiles: Dict[str, FramingProfile] = {}
        self._by_team: Dict[str, List[FramingProfile]] = {}
        self._loaded = False

    def load(self) -> None:
        """Fetch and parse catcher framing leaderboard from Savant."""
        if self._loaded:
            return

        cache_key = "catcher_framing_leaderboard"
        cached = self._cache.get(cache_key, max_age_hours=24)
        if cached:
            self._deserialize(cached)
            self._loaded = True
            return

        try:
            self._fetch_from_savant()
            if self._profiles:
                self._cache.set(cache_key, self._serialize())
            self._loaded = True
        except Exception as e:
            logger.warning(f"Could not fetch catcher framing data: {e}")
            self._load_fallback()
            self._loaded = True

    def _fetch_from_savant(self) -> None:
        """Fetch framing data from Baseball Savant CSV endpoint."""
        import requests
        import io
        import csv

        url = (
            "https://baseballsavant.mlb.com/leaderboard/catcher-framing"
            "?type=catcher&statType=framing&season=2026&n=qualified&csv=true"
        )

        try:
            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Fantasy Dashboard)"
            })
            resp.raise_for_status()
            content = resp.text
        except Exception:
            url_prev = url.replace("season=2026", "season=2025")
            resp = requests.get(url_prev, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Fantasy Dashboard)"
            })
            resp.raise_for_status()
            content = resp.text

        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            try:
                name = row.get("player_name", row.get("last_name, first_name", "")).strip()
                if not name:
                    continue

                if "," in name:
                    parts = name.split(",", 1)
                    name = f"{parts[1].strip()} {parts[0].strip()}"

                player_id = int(row.get("player_id", row.get("pitcher", 0)))
                team = row.get("team_name_abbr", row.get("team", "")).strip()

                runs_extra = float(row.get("runs_extra_strikes", row.get("framing_runs", 0)))
                strike_rate = float(row.get("strike_rate", row.get("cs_prob_delta", 0)))
                shadow_pct = float(row.get("shadow_zone_cs_pct", row.get("shadow_cs_pct", 0)))
                games = int(float(row.get("n_games", row.get("games", 0))))
                innings = float(row.get("innings", row.get("inn", 0)))

                tier = _classify_tier(runs_extra)

                profile = FramingProfile(
                    name=name,
                    player_id=player_id,
                    team=team,
                    runs_extra_strikes=runs_extra,
                    strike_rate=strike_rate,
                    shadow_zone_called_strike_pct=shadow_pct,
                    games_caught=games,
                    innings_caught=innings,
                    framing_tier=tier,
                )

                self._profiles[name.lower()] = profile
                team_upper = team.upper()
                if team_upper not in self._by_team:
                    self._by_team[team_upper] = []
                self._by_team[team_upper].append(profile)

            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping framing row: {e}")
                continue

        for team in self._by_team:
            self._by_team[team].sort(key=lambda p: p.games_caught, reverse=True)

        logger.info(f"Loaded framing data for {len(self._profiles)} catchers")

    def _load_fallback(self) -> None:
        """Hardcoded top/bottom framing catchers as fallback data."""
        fallback = [
            ("Austin Hedges", 0, "CLE", 12.0, 1.2, 52.0, 80, 700.0, "ELITE"),
            ("Patrick Bailey", 0, "SF", 10.5, 1.0, 51.0, 90, 780.0, "ELITE"),
            ("Jose Trevino", 0, "NYY", 9.0, 0.9, 50.0, 70, 600.0, "ELITE"),
            ("Cal Raleigh", 0, "SEA", 6.0, 0.6, 49.0, 100, 850.0, "GOOD"),
            ("Adley Rutschman", 0, "BAL", 5.0, 0.5, 48.5, 110, 950.0, "GOOD"),
            ("William Contreras", 0, "MIL", -2.0, -0.2, 44.0, 100, 850.0, "AVERAGE"),
            ("Salvador Perez", 0, "KC", -5.0, -0.5, 42.0, 110, 950.0, "POOR"),
            ("Martin Maldonado", 0, "HOU", -9.0, -0.9, 40.0, 80, 680.0, "LIABILITY"),
        ]
        for name, pid, team, runs, rate, shadow, games, innings, tier in fallback:
            profile = FramingProfile(
                name=name, player_id=pid, team=team,
                runs_extra_strikes=runs, strike_rate=rate,
                shadow_zone_called_strike_pct=shadow,
                games_caught=games, innings_caught=innings,
                framing_tier=tier,
            )
            self._profiles[name.lower()] = profile
            if team not in self._by_team:
                self._by_team[team] = []
            self._by_team[team].append(profile)

    def _serialize(self) -> list:
        return [p.to_dict() for p in self._profiles.values()]

    def _deserialize(self, data: list) -> None:
        for d in data:
            profile = FramingProfile(**d)
            self._profiles[profile.name.lower()] = profile
            team = profile.team.upper()
            if team not in self._by_team:
                self._by_team[team] = []
            self._by_team[team].append(profile)
        for team in self._by_team:
            self._by_team[team].sort(key=lambda p: p.games_caught, reverse=True)

    def get_catcher(self, name: str) -> Optional[FramingProfile]:
        """Look up a catcher by name."""
        return self._profiles.get(name.lower())

    def get_primary_catcher(self, team: str) -> Optional[FramingProfile]:
        """Get the primary (most games) catcher for a team."""
        catchers = self._by_team.get(team.upper(), [])
        return catchers[0] if catchers else None

    def get_team_catchers(self, team: str) -> List[FramingProfile]:
        """Get all catchers for a team, sorted by games caught."""
        return self._by_team.get(team.upper(), [])

    def get_pitcher_adjustment(self, opponent_team: str) -> Tuple[float, Optional[str]]:
        """
        Get pitcher matchup adjustment based on the OPPOSING team's catcher.

        When MY pitcher faces a team, the opposing catcher's framing affects
        that catcher's pitchers — but for evaluating whether to START my pitcher,
        we care about MY catcher's framing.

        This method returns the adjustment for a pitcher on `opponent_team`:
        their catcher's framing boosts/hurts their pitchers.
        """
        catcher = self.get_primary_catcher(opponent_team)
        if not catcher:
            return 0.0, None

        adjustment = FRAMING_ADJUSTMENTS.get(catcher.framing_tier, 0.0)
        if adjustment == 0.0:
            return 0.0, None

        reason = f"Catcher {catcher.name} ({catcher.framing_tier.lower()} framing, {catcher.runs_extra_strikes:+.1f} runs)"
        return adjustment, reason

    def get_my_pitcher_boost(self, my_team: str) -> Tuple[float, Optional[str]]:
        """
        Get the framing boost for MY pitchers based on MY team's catcher.

        Elite framing catchers boost their own pitchers' K rate and suppress
        walks, making MY pitchers more effective.
        """
        catcher = self.get_primary_catcher(my_team)
        if not catcher:
            return 0.0, None

        adjustment = FRAMING_ADJUSTMENTS.get(catcher.framing_tier, 0.0)
        if adjustment == 0.0:
            return 0.0, None

        if adjustment > 0:
            reason = f"Elite framing catcher {catcher.name} boosts pitcher K rate"
        else:
            reason = f"Poor framing catcher {catcher.name} hurts pitcher K rate"
        return adjustment, reason

    def get_all_profiles(self) -> List[FramingProfile]:
        """Get all catcher framing profiles, sorted by runs_extra_strikes."""
        profiles = list(self._profiles.values())
        profiles.sort(key=lambda p: p.runs_extra_strikes, reverse=True)
        return profiles
