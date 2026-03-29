#!/usr/bin/env python3
"""
Bullpen Depth Chart Tracker

Loads curated bullpen depth charts from data/bullpen_depth.json.
Provides lookup for closer, setup men, and committee status per team.

Update the JSON weekly during the season as closer roles shift.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

APP_ROOT = Path(__file__).parent.parent
DEPTH_FILE = APP_ROOT / "data" / "bullpen_depth.json"


@dataclass
class BullpenEntry:
    team: str
    closer: str
    setup: List[str] = field(default_factory=list)
    committee: bool = False


class BullpenTracker:
    """Loads and queries bullpen depth charts."""

    def __init__(self, depth_file: Path = DEPTH_FILE):
        self._entries: Dict[str, BullpenEntry] = {}
        self._closer_to_team: Dict[str, str] = {}
        self._load(depth_file)

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning(f"Bullpen depth file not found: {path}")
            return
        try:
            raw = json.loads(path.read_text())
        except Exception as e:
            logger.warning(f"Failed to parse bullpen depth file: {e}")
            return

        for team, info in raw.items():
            if team.startswith("_"):
                continue
            entry = BullpenEntry(
                team=team,
                closer=info.get("closer", ""),
                setup=info.get("setup", []),
                committee=info.get("committee", False),
            )
            self._entries[team.upper()] = entry
            if entry.closer:
                self._closer_to_team[entry.closer.lower()] = team.upper()

        logger.info(f"Loaded bullpen depth for {len(self._entries)} teams")

    def get_entry(self, team: str) -> Optional[BullpenEntry]:
        return self._entries.get(team.upper())

    def get_closer(self, team: str) -> Optional[str]:
        entry = self.get_entry(team)
        return entry.closer if entry else None

    def get_setup_men(self, team: str) -> List[str]:
        entry = self.get_entry(team)
        return entry.setup if entry else []

    def get_primary_setup(self, team: str) -> Optional[str]:
        """First setup man in the depth chart — the vulture save candidate."""
        entry = self.get_entry(team)
        return entry.setup[0] if entry and entry.setup else None

    def is_committee(self, team: str) -> bool:
        entry = self.get_entry(team)
        return entry.committee if entry else False

    def find_team_for_closer(self, closer_name: str) -> Optional[str]:
        return self._closer_to_team.get(closer_name.lower())

    def all_closers(self) -> List[Dict]:
        """Return list of all closers with team and committee status."""
        return [
            {
                "team": e.team,
                "closer": e.closer,
                "setup": e.setup,
                "committee": e.committee,
            }
            for e in sorted(self._entries.values(), key=lambda x: x.team)
        ]
