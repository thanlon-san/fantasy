#!/usr/bin/env python3
"""
Baseball Savant Leaderboard Fetcher

Pulls pre-aggregated Statcast percentile rankings, Stuff+ scores,
and sprint speed from baseballsavant.mlb.com CSV exports.

Much faster and less rate-limited than computing from raw pitch data.
"""

import logging
import io
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from .cache_manager import get_cache
except ImportError:
    get_cache = None  # type: ignore[assignment]


@dataclass
class HitterPercentiles:
    name: str
    player_id: int
    team: str = ""
    exit_velocity: Optional[int] = None
    hard_hit_pct: Optional[int] = None
    barrel_pct: Optional[int] = None
    xba: Optional[int] = None
    xslg: Optional[int] = None
    xwoba: Optional[int] = None
    sprint_speed: Optional[int] = None
    chase_rate: Optional[int] = None
    whiff_pct: Optional[int] = None
    k_pct: Optional[int] = None
    bb_pct: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name, "player_id": self.player_id, "team": self.team,
            "exit_velocity": self.exit_velocity, "hard_hit_pct": self.hard_hit_pct,
            "barrel_pct": self.barrel_pct, "xba": self.xba, "xslg": self.xslg,
            "xwoba": self.xwoba, "sprint_speed": self.sprint_speed,
            "chase_rate": self.chase_rate, "whiff_pct": self.whiff_pct,
            "k_pct": self.k_pct, "bb_pct": self.bb_pct,
        }


@dataclass
class PitcherPercentiles:
    name: str
    player_id: int
    team: str = ""
    exit_velocity: Optional[int] = None
    hard_hit_pct: Optional[int] = None
    barrel_pct: Optional[int] = None
    xba: Optional[int] = None
    xslg: Optional[int] = None
    xwoba: Optional[int] = None
    xera: Optional[int] = None
    fastball_velo: Optional[int] = None
    extension: Optional[int] = None
    whiff_pct: Optional[int] = None
    k_pct: Optional[int] = None
    bb_pct: Optional[int] = None
    stuff_plus: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name, "player_id": self.player_id, "team": self.team,
            "exit_velocity": self.exit_velocity, "hard_hit_pct": self.hard_hit_pct,
            "barrel_pct": self.barrel_pct, "xba": self.xba, "xslg": self.xslg,
            "xwoba": self.xwoba, "xera": self.xera,
            "fastball_velo": self.fastball_velo, "extension": self.extension,
            "whiff_pct": self.whiff_pct, "k_pct": self.k_pct, "bb_pct": self.bb_pct,
            "stuff_plus": self.stuff_plus,
        }


def _normalize(name: str) -> str:
    return name.strip().lower().replace(".", "").replace("'", "").replace("-", " ")


class SavantLeaderboards:
    """Fetches and caches Baseball Savant pre-computed leaderboard data."""

    HITTER_URL = (
        "https://baseballsavant.mlb.com/leaderboard/custom"
        "?year={year}&type=batter&min=50"
        "&columns=player_id,player_name,team,exit_velocity_avg,hard_hit_percent,"
        "barrel_batted_rate,xba,xslg,xwoba,sprint_speed,oz_swing_percent,"
        "whiff_percent,k_percent,bb_percent"
        "&csv=true"
    )

    PITCHER_URL = (
        "https://baseballsavant.mlb.com/leaderboard/custom"
        "?year={year}&type=pitcher&min=50"
        "&columns=player_id,player_name,team,exit_velocity_avg,hard_hit_percent,"
        "barrel_batted_rate,xba,xslg,xwoba,xera,p_fastball_velo,release_extension,"
        "whiff_percent,k_percent,bb_percent"
        "&csv=true"
    )

    STUFF_PLUS_URL = (
        "https://baseballsavant.mlb.com/leaderboard/stuff-plus"
        "?year={year}&min_pa=50&csv=true"
    )

    def __init__(self):
        self._hitters: Dict[str, HitterPercentiles] = {}
        self._pitchers: Dict[str, PitcherPercentiles] = {}
        self._cache = get_cache() if get_cache else None
        self._loaded = False

    def load(self, year: Optional[int] = None) -> None:
        if year is None:
            year = datetime.now().year

        cache_key = f"savant_leaderboards_{year}"
        if self._cache:
            cached = self._cache.get(cache_key, max_age_hours=24)
            if cached:
                self._hitters = {k: HitterPercentiles(**v) for k, v in cached.get("hitters", {}).items()}
                self._pitchers = {k: PitcherPercentiles(**v) for k, v in cached.get("pitchers", {}).items()}
                self._loaded = True
                logger.info(f"Loaded Savant leaderboards from cache: {len(self._hitters)} hitters, {len(self._pitchers)} pitchers")
                return

        self._fetch_hitters(year)
        self._fetch_pitchers(year)
        self._fetch_stuff_plus(year)
        self._loaded = True

        if self._cache:
            self._cache.set(cache_key, {
                "hitters": {k: v.to_dict() for k, v in self._hitters.items()},
                "pitchers": {k: v.to_dict() for k, v in self._pitchers.items()},
            })

        logger.info(f"Fetched Savant leaderboards: {len(self._hitters)} hitters, {len(self._pitchers)} pitchers")

    def _fetch_hitters(self, year: int) -> None:
        import requests
        try:
            url = self.HITTER_URL.format(year=year)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            self._parse_hitter_csv(resp.text)
        except Exception as e:
            logger.warning(f"Failed to fetch hitter leaderboard: {e}")

    def _fetch_pitchers(self, year: int) -> None:
        import requests
        try:
            url = self.PITCHER_URL.format(year=year)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            self._parse_pitcher_csv(resp.text)
        except Exception as e:
            logger.warning(f"Failed to fetch pitcher leaderboard: {e}")

    def _fetch_stuff_plus(self, year: int) -> None:
        import requests
        try:
            url = self.STUFF_PLUS_URL.format(year=year)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            self._parse_stuff_plus_csv(resp.text)
        except Exception as e:
            logger.warning(f"Failed to fetch Stuff+ data: {e}")

    def _safe_int(self, val: str) -> Optional[int]:
        try:
            return int(round(float(val)))
        except (ValueError, TypeError):
            return None

    def _safe_float(self, val: str) -> Optional[float]:
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _pctile(self, value: Optional[float], all_values: List[float], invert: bool = False) -> Optional[int]:
        """Compute percentile rank (0-99) of value within all_values."""
        if value is None or not all_values:
            return None
        below = sum(1 for v in all_values if v < value)
        pct = int(round(below / len(all_values) * 100))
        return (100 - pct) if invert else pct

    def _parse_hitter_csv(self, text: str) -> None:
        import csv
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return

        evs = [float(r.get("exit_velocity_avg", 0) or 0) for r in rows if r.get("exit_velocity_avg")]
        hhs = [float(r.get("hard_hit_percent", 0) or 0) for r in rows if r.get("hard_hit_percent")]
        brls = [float(r.get("barrel_batted_rate", 0) or 0) for r in rows if r.get("barrel_batted_rate")]
        xbas = [float(r.get("xba", 0) or 0) for r in rows if r.get("xba")]
        xslgs = [float(r.get("xslg", 0) or 0) for r in rows if r.get("xslg")]
        xwobas = [float(r.get("xwoba", 0) or 0) for r in rows if r.get("xwoba")]
        speeds = [float(r.get("sprint_speed", 0) or 0) for r in rows if r.get("sprint_speed")]
        chases = [float(r.get("oz_swing_percent", 0) or 0) for r in rows if r.get("oz_swing_percent")]
        whiffs = [float(r.get("whiff_percent", 0) or 0) for r in rows if r.get("whiff_percent")]
        kpcts = [float(r.get("k_percent", 0) or 0) for r in rows if r.get("k_percent")]
        bbpcts = [float(r.get("bb_percent", 0) or 0) for r in rows if r.get("bb_percent")]

        for row in rows:
            name = row.get("player_name", "").strip()
            pid_str = row.get("player_id", "")
            if not name or not pid_str:
                continue
            pid = self._safe_int(pid_str) or 0

            h = HitterPercentiles(
                name=name, player_id=pid, team=row.get("team", ""),
                exit_velocity=self._pctile(self._safe_float(row.get("exit_velocity_avg")), evs),
                hard_hit_pct=self._pctile(self._safe_float(row.get("hard_hit_percent")), hhs),
                barrel_pct=self._pctile(self._safe_float(row.get("barrel_batted_rate")), brls),
                xba=self._pctile(self._safe_float(row.get("xba")), xbas),
                xslg=self._pctile(self._safe_float(row.get("xslg")), xslgs),
                xwoba=self._pctile(self._safe_float(row.get("xwoba")), xwobas),
                sprint_speed=self._pctile(self._safe_float(row.get("sprint_speed")), speeds),
                chase_rate=self._pctile(self._safe_float(row.get("oz_swing_percent")), chases, invert=True),
                whiff_pct=self._pctile(self._safe_float(row.get("whiff_percent")), whiffs, invert=True),
                k_pct=self._pctile(self._safe_float(row.get("k_percent")), kpcts, invert=True),
                bb_pct=self._pctile(self._safe_float(row.get("bb_percent")), bbpcts),
            )
            self._hitters[_normalize(name)] = h

    def _parse_pitcher_csv(self, text: str) -> None:
        import csv
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return

        evs = [float(r.get("exit_velocity_avg", 0) or 0) for r in rows if r.get("exit_velocity_avg")]
        hhs = [float(r.get("hard_hit_percent", 0) or 0) for r in rows if r.get("hard_hit_percent")]
        brls = [float(r.get("barrel_batted_rate", 0) or 0) for r in rows if r.get("barrel_batted_rate")]
        xbas = [float(r.get("xba", 0) or 0) for r in rows if r.get("xba")]
        xslgs = [float(r.get("xslg", 0) or 0) for r in rows if r.get("xslg")]
        xwobas = [float(r.get("xwoba", 0) or 0) for r in rows if r.get("xwoba")]
        xeras = [float(r.get("xera", 0) or 0) for r in rows if r.get("xera")]
        velos = [float(r.get("p_fastball_velo", 0) or 0) for r in rows if r.get("p_fastball_velo")]
        exts = [float(r.get("release_extension", 0) or 0) for r in rows if r.get("release_extension")]
        whiffs = [float(r.get("whiff_percent", 0) or 0) for r in rows if r.get("whiff_percent")]
        kpcts = [float(r.get("k_percent", 0) or 0) for r in rows if r.get("k_percent")]
        bbpcts = [float(r.get("bb_percent", 0) or 0) for r in rows if r.get("bb_percent")]

        for row in rows:
            name = row.get("player_name", "").strip()
            pid_str = row.get("player_id", "")
            if not name or not pid_str:
                continue
            pid = self._safe_int(pid_str) or 0

            p = PitcherPercentiles(
                name=name, player_id=pid, team=row.get("team", ""),
                exit_velocity=self._pctile(self._safe_float(row.get("exit_velocity_avg")), evs, invert=True),
                hard_hit_pct=self._pctile(self._safe_float(row.get("hard_hit_percent")), hhs, invert=True),
                barrel_pct=self._pctile(self._safe_float(row.get("barrel_batted_rate")), brls, invert=True),
                xba=self._pctile(self._safe_float(row.get("xba")), xbas, invert=True),
                xslg=self._pctile(self._safe_float(row.get("xslg")), xslgs, invert=True),
                xwoba=self._pctile(self._safe_float(row.get("xwoba")), xwobas, invert=True),
                xera=self._pctile(self._safe_float(row.get("xera")), xeras, invert=True),
                fastball_velo=self._pctile(self._safe_float(row.get("p_fastball_velo")), velos),
                extension=self._pctile(self._safe_float(row.get("release_extension")), exts),
                whiff_pct=self._pctile(self._safe_float(row.get("whiff_percent")), whiffs),
                k_pct=self._pctile(self._safe_float(row.get("k_percent")), kpcts),
                bb_pct=self._pctile(self._safe_float(row.get("bb_percent")), bbpcts, invert=True),
            )
            self._pitchers[_normalize(name)] = p

    def _parse_stuff_plus_csv(self, text: str) -> None:
        import csv
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            name = row.get("player_name", "").strip()
            stuff = self._safe_float(row.get("stuff_plus") or row.get("run_value_per_100") or "")
            key = _normalize(name)
            if key in self._pitchers and stuff is not None:
                self._pitchers[key].stuff_plus = round(stuff, 1)

    # ── Public API ───────────────────────────────────────────────────────

    def get_hitter(self, name: str) -> Optional[HitterPercentiles]:
        if not self._loaded:
            self.load()
        return self._hitters.get(_normalize(name))

    def get_pitcher(self, name: str) -> Optional[PitcherPercentiles]:
        if not self._loaded:
            self.load()
        return self._pitchers.get(_normalize(name))

    def get_percentiles(self, name: str, is_pitcher: bool = False):
        """Unified lookup — returns HitterPercentiles or PitcherPercentiles."""
        return self.get_pitcher(name) if is_pitcher else self.get_hitter(name)

    def all_hitters(self) -> List[HitterPercentiles]:
        if not self._loaded:
            self.load()
        return list(self._hitters.values())

    def all_pitchers(self) -> List[PitcherPercentiles]:
        if not self._loaded:
            self.load()
        return list(self._pitchers.values())
