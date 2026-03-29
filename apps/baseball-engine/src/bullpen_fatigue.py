#!/usr/bin/env python3
"""
Bullpen Fatigue Monitor & Vulture Save Alert Engine

Tracks daily pitch counts and appearance streaks for all MLB relievers.
Calculates a fatigue score and cross-references bullpen depth charts
to surface vulture save opportunities when closers are gassed.

Fatigue scoring:
  - Consecutive days pitched: 3+ = high fatigue
  - Pitch count in last 3 days: >45 = high fatigue
  - Innings pitched in last 7 days: tracked for context

Data source: MLB Stats API game logs for relievers.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .bullpen_tracker import BullpenTracker
from .cache_manager import get_cache

logger = logging.getLogger(__name__)

MLB_API = "https://statsapi.mlb.com/api/v1"
TIMEOUT = 20
CACHE_TTL_HOURS = 4


@dataclass
class RelieverFatigue:
    """Fatigue profile for a single reliever."""
    name: str
    team: str
    consecutive_days: int = 0
    pitches_last_3_days: int = 0
    innings_last_7_days: float = 0.0
    appearances_last_7_days: int = 0
    last_outing_date: Optional[str] = None

    @property
    def fatigue_score(self) -> int:
        """0-100 scale. Higher = more fatigued."""
        score = 0
        if self.consecutive_days >= 3:
            score += 45
        elif self.consecutive_days == 2:
            score += 25
        elif self.consecutive_days == 1:
            score += 10

        if self.pitches_last_3_days > 55:
            score += 30
        elif self.pitches_last_3_days > 45:
            score += 20
        elif self.pitches_last_3_days > 30:
            score += 10

        if self.innings_last_7_days > 5.0:
            score += 15
        elif self.innings_last_7_days > 3.5:
            score += 8

        if self.appearances_last_7_days >= 5:
            score += 10
        elif self.appearances_last_7_days >= 4:
            score += 5

        return min(100, score)

    @property
    def fatigue_level(self) -> str:
        s = self.fatigue_score
        if s >= 60:
            return "HIGH"
        if s >= 35:
            return "MODERATE"
        if s >= 15:
            return "LOW"
        return "FRESH"


@dataclass
class VultureAlert:
    """A vulture save opportunity."""
    closer: str
    closer_team: str
    fatigue_score: int
    fatigue_level: str
    consecutive_days: int
    pitches_last_3_days: int
    vulture_candidate: str
    reason: str
    committee: bool = False


class BullpenFatigueMonitor:
    """Monitors reliever fatigue and generates vulture save alerts."""

    def __init__(self, bullpen_tracker: Optional[BullpenTracker] = None):
        self.cache = get_cache()
        self.session = self._create_session()
        self.bullpen = bullpen_tracker or BullpenTracker()
        self._team_id_cache: Dict[str, int] = {}

    @staticmethod
    def _create_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get_team_ids(self) -> Dict[str, int]:
        """Fetch MLB team abbreviation → team ID mapping."""
        if self._team_id_cache:
            return self._team_id_cache
        cached = self.cache.get("mlb_team_ids", max_age_hours=168)
        if cached:
            self._team_id_cache = cached
            return cached
        try:
            resp = self.session.get(f"{MLB_API}/teams", params={"sportId": 1}, timeout=TIMEOUT)
            resp.raise_for_status()
            NORMALIZE = {"AZ": "ARI", "WSN": "WSH"}
            mapping = {}
            for t in resp.json().get("teams", []):
                abbr = NORMALIZE.get(t.get("abbreviation", ""), t.get("abbreviation", ""))
                mapping[abbr] = t["id"]
            self._team_id_cache = mapping
            self.cache.set("mlb_team_ids", mapping)
            return mapping
        except Exception as e:
            logger.warning(f"Failed to fetch team IDs: {e}")
            return {}

    def _get_reliever_game_log(self, player_name: str, team_abbr: str, days: int = 7) -> List[dict]:
        """Fetch recent game log for a reliever from MLB Stats API."""
        cache_key = f"reliever_log_{player_name}_{days}d"
        cached = self.cache.get(cache_key, max_age_hours=CACHE_TTL_HOURS)
        if cached is not None:
            return cached

        team_ids = self._get_team_ids()
        team_id = team_ids.get(team_abbr.upper())
        if not team_id:
            return []

        try:
            roster_resp = self.session.get(
                f"{MLB_API}/teams/{team_id}/roster",
                params={"rosterType": "active"},
                timeout=TIMEOUT,
            )
            roster_resp.raise_for_status()
            roster = roster_resp.json().get("roster", [])
        except Exception as e:
            logger.debug(f"Roster fetch failed for {team_abbr}: {e}")
            return []

        player_id = None
        name_lower = player_name.lower()
        for p in roster:
            full = p.get("person", {}).get("fullName", "")
            if full.lower() == name_lower:
                player_id = p["person"]["id"]
                break
        if player_id is None:
            for p in roster:
                full = p.get("person", {}).get("fullName", "")
                if name_lower in full.lower() or full.lower() in name_lower:
                    player_id = p["person"]["id"]
                    break
        if player_id is None:
            return []

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            resp = self.session.get(
                f"{MLB_API}/people/{player_id}/stats",
                params={
                    "stats": "gameLog",
                    "group": "pitching",
                    "season": datetime.now().year,
                    "startDate": start_date,
                    "endDate": end_date,
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            stats = resp.json().get("stats", [])
            splits = stats[0].get("splits", []) if stats else []
            self.cache.set(cache_key, splits)
            return splits
        except Exception as e:
            logger.debug(f"Game log fetch failed for {player_name}: {e}")
            return []

    def _compute_fatigue(self, name: str, team: str) -> RelieverFatigue:
        """Compute fatigue metrics for a reliever."""
        splits = self._get_reliever_game_log(name, team, days=7)
        fatigue = RelieverFatigue(name=name, team=team)

        if not splits:
            return fatigue

        today = datetime.now().date()
        appearance_dates: list = []
        total_pitches_3d = 0
        total_ip_7d = 0.0

        for split in splits:
            stat = split.get("stat", {})
            game_date_str = split.get("date", "")
            if not game_date_str:
                continue
            try:
                game_date = datetime.strptime(game_date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                continue

            days_ago = (today - game_date).days
            appearance_dates.append(game_date)

            pitches = int(stat.get("numberOfPitches", 0))
            ip_str = str(stat.get("inningsPitched", "0"))
            try:
                whole, frac = (ip_str.split(".") + ["0"])[:2]
                ip = int(whole) + int(frac) / 3.0
            except (ValueError, IndexError):
                ip = 0.0

            if days_ago <= 3:
                total_pitches_3d += pitches
            total_ip_7d += ip

        fatigue.appearances_last_7_days = len(appearance_dates)
        fatigue.pitches_last_3_days = total_pitches_3d
        fatigue.innings_last_7_days = round(total_ip_7d, 1)

        if appearance_dates:
            sorted_dates = sorted(appearance_dates, reverse=True)
            fatigue.last_outing_date = sorted_dates[0].isoformat()
            consecutive = 0
            check = today
            for d in sorted_dates:
                if d == check or d == check - timedelta(days=1):
                    consecutive += 1
                    check = d
                else:
                    break
            fatigue.consecutive_days = consecutive

        return fatigue

    def get_all_closer_fatigue(self) -> List[RelieverFatigue]:
        """Compute fatigue for all closers in the depth chart."""
        cached = self.cache.get("closer_fatigue_all", max_age_hours=CACHE_TTL_HOURS)
        if cached is not None:
            return [RelieverFatigue(**c) for c in cached]

        results = []
        for entry in self.bullpen.all_closers():
            closer = entry["closer"]
            team = entry["team"]
            if not closer:
                continue
            fatigue = self._compute_fatigue(closer, team)
            results.append(fatigue)

        self.cache.set("closer_fatigue_all", [
            {
                "name": r.name, "team": r.team,
                "consecutive_days": r.consecutive_days,
                "pitches_last_3_days": r.pitches_last_3_days,
                "innings_last_7_days": r.innings_last_7_days,
                "appearances_last_7_days": r.appearances_last_7_days,
                "last_outing_date": r.last_outing_date,
            }
            for r in results
        ])
        return results

    def get_vulture_alerts(self) -> List[VultureAlert]:
        """
        Scan all closers for fatigue. Return vulture save alerts
        when a closer is MODERATE or HIGH fatigue.
        """
        fatigues = self.get_all_closer_fatigue()
        alerts: List[VultureAlert] = []

        for f in fatigues:
            if f.fatigue_level not in ("MODERATE", "HIGH"):
                continue
            setup = self.bullpen.get_primary_setup(f.team)
            if not setup:
                continue

            parts = []
            if f.consecutive_days >= 3:
                parts.append(f"{f.consecutive_days} straight days pitched")
            elif f.consecutive_days == 2:
                parts.append("pitched 2 straight days")
            if f.pitches_last_3_days > 45:
                parts.append(f"{f.pitches_last_3_days} pitches in last 3 days")
            if not parts:
                parts.append(f"fatigue score {f.fatigue_score}")

            reason = (
                f"{f.name} is fatigued ({'; '.join(parts)}). "
                f"Add {setup} for a likely vulture save today."
            )

            alerts.append(VultureAlert(
                closer=f.name,
                closer_team=f.team,
                fatigue_score=f.fatigue_score,
                fatigue_level=f.fatigue_level,
                consecutive_days=f.consecutive_days,
                pitches_last_3_days=f.pitches_last_3_days,
                vulture_candidate=setup,
                reason=reason,
                committee=self.bullpen.is_committee(f.team),
            ))

        alerts.sort(key=lambda a: a.fatigue_score, reverse=True)
        return alerts
