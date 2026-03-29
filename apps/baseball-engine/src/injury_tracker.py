#!/usr/bin/env python3
"""
Injury Tracker
Fetch current IL and DTD statuses from the MLB Stats API.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache_manager import get_cache

logger = logging.getLogger(__name__)

MLB_INJURIES_URL = "https://statsapi.mlb.com/api/v1/injuries"


@dataclass
class InjuryRecord:
    player_name: str
    team: str
    status: str        # "10-Day IL", "60-Day IL", "DTD", "Paternity", "Bereavement", etc.
    injury: str        # e.g. "Right shoulder inflammation"
    date: Optional[str] = None  # date placed on IL

    @property
    def badge(self) -> str:
        """Short badge label for dashboard display."""
        s = self.status.upper()
        if "60" in s:
            return "IL-60"
        if "15" in s:
            return "IL-15"
        if "10" in s:
            return "IL-10"
        if "7" in s:
            return "IL-7"
        if "DTD" in s or "DAY" in s:
            return "DTD"
        return "IL"


class InjuryTracker:
    """Fetch and cache the current MLB injury list."""

    CACHE_KEY = "mlb_injuries"
    CACHE_TTL_HOURS = 2  # refresh every 2 hours

    def __init__(self):
        self._cache = get_cache()
        self._session = self._build_session()
        self._injuries: Dict[str, InjuryRecord] = {}
        self._loaded = False

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    def _fetch(self) -> List[dict]:
        """Hit the MLB Stats API injuries endpoint."""
        try:
            resp = self._session.get(MLB_INJURIES_URL, timeout=15)
            resp.raise_for_status()
            return resp.json().get("row", [])
        except Exception as e:
            logger.warning(f"MLB injuries API failed: {e}")
            return []

    def load(self, force: bool = False) -> None:
        """Load injury data (from cache or API)."""
        if self._loaded and not force:
            return

        cached = self._cache.get(self.CACHE_KEY, max_age_hours=self.CACHE_TTL_HOURS)
        if cached and not force:
            self._injuries = {k: InjuryRecord(**v) for k, v in cached.items()}
            self._loaded = True
            logger.info(f"Loaded {len(self._injuries)} injuries from cache")
            return

        rows = self._fetch()
        injuries: Dict[str, InjuryRecord] = {}
        for row in rows:
            name = row.get("name_display_first_last") or row.get("display_name", "")
            if not name:
                continue
            rec = InjuryRecord(
                player_name=name,
                team=row.get("team_abbrev", row.get("team_name", "")),
                status=row.get("injuries_display_name", row.get("status", "IL")),
                injury=row.get("injuries_description", row.get("injury", "")),
                date=row.get("injuries_date", None),
            )
            injuries[name.lower()] = rec

        self._injuries = injuries
        serializable = {k: v.__dict__ for k, v in injuries.items()}
        self._cache.set(self.CACHE_KEY, serializable)
        self._loaded = True
        logger.info(f"Fetched {len(injuries)} injuries from MLB API")

    def is_injured(self, player_name: str) -> bool:
        self.load()
        return player_name.lower() in self._injuries

    def get_injury(self, player_name: str) -> Optional[InjuryRecord]:
        self.load()
        return self._injuries.get(player_name.lower())

    def get_badge(self, player_name: str) -> Optional[str]:
        rec = self.get_injury(player_name)
        return rec.badge if rec else None

    def get_all_injuries(self) -> Dict[str, InjuryRecord]:
        self.load()
        return dict(self._injuries)
