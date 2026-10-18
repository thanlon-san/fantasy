"""
Ownership & Roster % Stats for Fantasy Football
Uses Sleeper API (free) to get roster/start rates across all leagues
"""

from __future__ import annotations

import requests
from typing import Any, Dict, Iterable, List, Optional, Tuple

from shared.logger import get_logger
from src.constants import (
    NFL_SEASON_START_DATE,
    ROASTABLE_START_PERCENTAGE,
    SIGNIFICANT_MANAGEMENT_GAP,
)

logger = get_logger(__name__)

INVALID_START_PERCENTAGE = -1.0
_FLEX_SLOTS = frozenset({"W/R/T", "FLEX", "RB/WR/T"})


def _normalize_position(position: str) -> str:
    pos = (position or "").upper()
    if pos in ("D/ST", "DST"):
        return "DEF"
    return pos


def _valid_start_pct(value: Optional[float]) -> bool:
    try:
        return value is not None and float(value) >= 0
    except (TypeError, ValueError):
        return False


def _positions_match_for_swap(bench_player: Dict[str, Any], starter: Dict[str, Any]) -> bool:
    """True if the benched player could have filled the starter's lineup slot."""
    bench_pos = _normalize_position(bench_player.get("position", ""))
    starter_pos = _normalize_position(starter.get("position", ""))
    slot = (starter.get("slot") or "").upper()
    if bench_pos == starter_pos:
        return True
    if slot in _FLEX_SLOTS and bench_pos in ("RB", "WR", "TE"):
        return bench_pos == starter_pos
    return False


def is_swap_roastable_by_consensus(
    bench_percent_started: float,
    starter_percent_started: float,
) -> bool:
    """
    Bench mistake is roast-worthy when consensus favored the benched player
    (high start %) or clearly favored the starter over the bench option.
    """
    if not _valid_start_pct(bench_percent_started) and not _valid_start_pct(
        starter_percent_started
    ):
        return False
    if _valid_start_pct(bench_percent_started) and bench_percent_started >= ROASTABLE_START_PERCENTAGE:
        return True
    if (
        _valid_start_pct(bench_percent_started)
        and _valid_start_pct(starter_percent_started)
        and bench_percent_started > starter_percent_started
    ):
        return True
    return False


def compute_start_sit_swaps(team: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Find benched players who outscored a started player they could have replaced.
    """
    swaps: List[Dict[str, Any]] = []
    starters = team.get("starters") or []
    bench = team.get("bench") or []

    for bench_player in bench:
        bench_pts = float(bench_player.get("actual_points") or 0)
        bench_pct = float(bench_player.get("percent_started", INVALID_START_PERCENTAGE))
        for starter in starters:
            if not _positions_match_for_swap(bench_player, starter):
                continue
            starter_pts = float(starter.get("actual_points") or 0)
            if bench_pts <= starter_pts:
                continue
            starter_pct = float(starter.get("percent_started", INVALID_START_PERCENTAGE))
            roastable = is_swap_roastable_by_consensus(bench_pct, starter_pct)
            swaps.append(
                {
                    "benched_name": bench_player.get("name", ""),
                    "benched_points": bench_pts,
                    "benched_percent_started": bench_pct,
                    "started_name": starter.get("name", ""),
                    "started_points": starter_pts,
                    "started_percent_started": starter_pct,
                    "started_slot": starter.get("slot", ""),
                    "roastable": roastable,
                }
            )
    return swaps


def team_has_roastable_bench_mistake(team: Dict[str, Any]) -> bool:
    return any(s.get("roastable") for s in compute_start_sit_swaps(team))


def is_management_gap_roastable(team: Dict[str, Any]) -> bool:
    gap = float(team.get("management_gap") or 0)
    if gap <= SIGNIFICANT_MANAGEMENT_GAP:
        return False
    return team_has_roastable_bench_mistake(team)


def iter_week_roster_players(week_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for matchup in week_data.get("matchups", {}).get("matchups", []) or []:
        for side in ("home_team", "away_team"):
            team = matchup.get(side) or {}
            for player in (team.get("starters") or []) + (team.get("bench") or []):
                yield player


class OwnershipStats:
    """Fetch roster % and start % from Sleeper API"""

    BASE_URL = "https://api.sleeper.app/v1"
    RESEARCH_URL = "https://api.sleeper.app/players/nfl/research"

    def __init__(self):
        self.player_cache: Dict[str, str] = {}
        self.trending_cache: Dict[str, Any] = {}
        self._research_cache: Dict[Tuple[int, int, str], Dict[str, Dict[str, float]]] = {}

    def get_player_id(self, player_name: str) -> Optional[str]:
        """
        Get Sleeper player ID from name
        Note: Sleeper API uses player IDs, not names
        """
        try:
            self._ensure_player_name_index()
            return self.player_cache.get(player_name.lower())
        except Exception as e:
            logger.warning(f"Failed to get player ID for {player_name}: {e}")
            return None

    def _ensure_player_name_index(self) -> None:
        if self.player_cache:
            return
        response = requests.get(f"{self.BASE_URL}/players/nfl", timeout=30)
        response.raise_for_status()
        players = response.json()
        for player_id, player_data in players.items():
            full_name = (
                f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}"
            ).strip()
            if full_name:
                self.player_cache[full_name.lower()] = player_id

    def fetch_week_research(
        self,
        season: int,
        week: int,
        *,
        season_type: str = "regular",
    ) -> Dict[str, Dict[str, float]]:
        """
        Sleeper weekly ownership/start rates keyed by Sleeper player_id.

        Values are already percentages (0–100).
        """
        cache_key = (season, week, season_type)
        if cache_key in self._research_cache:
            return self._research_cache[cache_key]

        url = f"{self.RESEARCH_URL}/{season_type}/{season}/{week}"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                payload = {}
        except Exception as e:
            logger.warning(
                "Failed to fetch Sleeper research for %s week %s: %s",
                season,
                week,
                e,
            )
            payload = {}

        self._research_cache[cache_key] = payload
        return payload

    def lookup_consensus_rates(
        self,
        player_name: str,
        research: Dict[str, Dict[str, float]],
    ) -> Tuple[float, float]:
        """Return (percent_started, percent_owned), or (-1, -1) when unknown."""
        player_id = self.get_player_id(player_name)
        if not player_id:
            return INVALID_START_PERCENTAGE, INVALID_START_PERCENTAGE
        entry = research.get(str(player_id)) or research.get(player_id) or {}
        try:
            started = float(entry.get("started", INVALID_START_PERCENTAGE))
        except (TypeError, ValueError):
            started = INVALID_START_PERCENTAGE
        try:
            owned = float(entry.get("owned", INVALID_START_PERCENTAGE))
        except (TypeError, ValueError):
            owned = INVALID_START_PERCENTAGE
        return started, owned

    def enrich_week_data_players(
        self,
        week_data: Dict[str, Any],
        week: int,
        *,
        season: Optional[int] = None,
    ) -> None:
        """
        Attach Sleeper consensus start/own % to every roster player in week_data.
        Leaves percent_started at -1 when Sleeper is unavailable.
        """
        season = season or NFL_SEASON_START_DATE.year
        research = self.fetch_week_research(season, week)
        if not research:
            return
        try:
            self._ensure_player_name_index()
        except Exception as e:
            logger.warning("Skipping ownership enrichment (player index): %s", e)
            return

        for player in iter_week_roster_players(week_data):
            started, owned = self.lookup_consensus_rates(player.get("name", ""), research)
            player["percent_started"] = round(started, 1) if _valid_start_pct(started) else INVALID_START_PERCENTAGE
            player["percent_owned"] = round(owned, 1) if _valid_start_pct(owned) else INVALID_START_PERCENTAGE

    def get_trending_players(self, trend_type: str = "add") -> Dict:
        """
        Get trending adds or drops
        trend_type: 'add' or 'drop'
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/players/nfl/trending/{trend_type}",
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.warning(f"Failed to get trending {trend_type}: {e}")
            return {}

    def is_trending_add(self, player_name: str, top_n: int = 50) -> bool:
        """Check if player is in top N trending adds"""
        if not self.trending_cache.get("add"):
            self.trending_cache["add"] = self.get_trending_players("add")

        player_id = self.get_player_id(player_name)
        if not player_id:
            return False

        trending = self.trending_cache["add"]
        for idx, item in enumerate(trending[:top_n]):
            if item.get("player_id") == player_id:
                return True, idx + 1  # Return rank

        return False, None

    def is_trending_drop(self, player_name: str, top_n: int = 50) -> bool:
        """Check if player is in top N trending drops"""
        if not self.trending_cache.get("drop"):
            self.trending_cache["drop"] = self.get_trending_players("drop")

        player_id = self.get_player_id(player_name)
        if not player_id:
            return False

        trending = self.trending_cache["drop"]
        for idx, item in enumerate(trending[:top_n]):
            if item.get("player_id") == player_id:
                return True, idx + 1  # Return rank

        return False, None

    def generate_ownership_roast(
        self,
        player_name: str,
        was_started: bool,
        points_scored: float,
        percent_started: float,
    ) -> Optional[str]:
        """
        Generate roast based on ownership % and start/sit decision

        Args:
            player_name: Player's name
            was_started: Did the manager start this player?
            points_scored: Points the player scored
            percent_started: Consensus % started (0-100)

        Returns:
            Roast string or None
        """
        if percent_started < 0:
            return None

        roasts = []

        # Scenario 1: STARTED a player almost nobody starts
        if was_started and percent_started < 5:
            roasts.append(
                f"{player_name} is started in {percent_started:.1f}% of leagues. "
                f"You're the {percent_started:.1f}%. There's a reason for that."
            )

        # Scenario 2: BENCHED a player almost everyone starts
        if not was_started and percent_started > 70 and points_scored > 15:
            roasts.append(
                f"You benched {player_name} ({percent_started:.0f}% start rate). "
                f"He scored {points_scored:.1f}. The people tried to warn you."
            )

        # Scenario 3: Started a trending DROP
        is_drop, drop_rank = self.is_trending_drop(player_name, top_n=25)
        if was_started and is_drop:
            roasts.append(
                f"{player_name} is the #{drop_rank} trending DROP this week. "
                f"You started him. Contrarian or clueless?"
            )

        # Scenario 4: Dropped/benched a trending ADD
        is_add, add_rank = self.is_trending_add(player_name, top_n=25)
        if not was_started and is_add and points_scored > 20:
            roasts.append(
                f"{player_name} is the #{add_rank} trending ADD. "
                f"You benched {points_scored:.1f} points. Everyone else saw it coming."
            )

        return roasts[0] if roasts else None


def enrich_week_data_with_ownership(
    week_data: Dict[str, Any],
    week: int,
    ownership_stats: Optional[OwnershipStats] = None,
    *,
    season: Optional[int] = None,
) -> None:
    """Convenience wrapper used by the Yahoo fetcher / recap pipeline."""
    stats = ownership_stats or OwnershipStats()
    try:
        stats.enrich_week_data_players(week_data, week, season=season)
    except Exception as e:
        logger.warning("Ownership enrichment failed (non-fatal): %s", e)


def get_ownership_context(
    starter_name: str,
    starter_points: float,
    starter_percent_started: float,
    bench_player_name: str = None,
    bench_points: float = None,
    bench_percent_started: float = None,
) -> str:
    """
    Helper function to get ownership-based roasts

    Example usage in recap_generator.py:
        roast = get_ownership_context(
            starter_name="Gus Edwards",
            starter_points=4.2,
            starter_percent_started=8.3,
            bench_player_name="Jahmyr Gibbs",
            bench_points=27.4,
            bench_percent_started=92.1
        )
    """
    ownership = OwnershipStats()
    roasts = []

    # Check starter
    if starter_percent_started:
        roast = ownership.generate_ownership_roast(
            starter_name,
            was_started=True,
            points_scored=starter_points,
            percent_started=starter_percent_started,
        )
        if roast:
            roasts.append(roast)

    # Check bench (if provided)
    if bench_player_name and bench_percent_started:
        roast = ownership.generate_ownership_roast(
            bench_player_name,
            was_started=False,
            points_scored=bench_points,
            percent_started=bench_percent_started,
        )
        if roast:
            roasts.append(roast)

    return "\n\n".join(roasts) if roasts else None


if __name__ == "__main__":
    # Test the ownership stats
    ownership = OwnershipStats()

    # Test 1: Low ownership start
    print("Test 1: Starting a player nobody else starts")
    roast = ownership.generate_ownership_roast(
        player_name="Gus Edwards",
        was_started=True,
        points_scored=4.2,
        percent_started=3.1,
    )
    print(f"  {roast}\n")

    # Test 2: High ownership bench
    print("Test 2: Benching a player everyone else starts")
    roast = ownership.generate_ownership_roast(
        player_name="Christian McCaffrey",
        was_started=False,
        points_scored=28.4,
        percent_started=99.2,
    )
    print(f"  {roast}\n")

    # Test 3: Trending checks
    print("Test 3: Checking trending adds")
    is_add, rank = ownership.is_trending_add("Tyreek Hill", top_n=50)
    if is_add:
        print(f"  Tyreek Hill is trending ADD (#{rank})\n")
    else:
        print(f"  Not in top 50 trending adds\n")
