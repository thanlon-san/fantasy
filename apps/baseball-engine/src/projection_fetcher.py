#!/usr/bin/env python3
"""
FanGraphs Rest-of-Season (ROS) Projection Fetcher

Fetches Steamer ROS projections from the FanGraphs unofficial API.
Hitters: PA, AVG, HR, RBI, SB, OPS, wRC+
Pitchers: IP, ERA, WHIP, K, QS, FIP, K-BB%

Projections update daily on FanGraphs. Cached for 24 hours locally.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache_manager import get_cache

logger = logging.getLogger(__name__)

FANGRAPHS_HITTER_URL = (
    "https://www.fangraphs.com/api/projections"
    "?type=steamerr&stats=bat&pos=all&team=0&players=0"
)
FANGRAPHS_PITCHER_URL = (
    "https://www.fangraphs.com/api/projections"
    "?type=steamerr&stats=pit&pos=all&team=0&players=0"
)
CACHE_TTL_HOURS = 24
TIMEOUT = 30


@dataclass
class HitterProjection:
    name: str
    team: str
    pa: int
    avg: float
    hr: int
    rbi: int
    sb: int
    obp: float
    slg: float
    ops: float
    wrc_plus: int
    war: float

    @property
    def ros_value(self) -> float:
        """Single-number value combining volume and rate stats.
        Weighted toward the 12-cat H2H scoring categories:
        R, H, HR, RBI, SB, OPS."""
        volume = self.pa / 600.0
        return (
            self.hr * 3.0
            + self.rbi * 1.2
            + self.sb * 2.5
            + (self.ops - 0.700) * 500
            + self.wrc_plus * 0.3
        ) * volume


@dataclass
class PitcherProjection:
    name: str
    team: str
    ip: float
    era: float
    whip: float
    k: int
    qs: int
    fip: float
    k_bb_pct: float
    war: float

    @property
    def ros_value(self) -> float:
        """Single-number value for pitchers in 12-cat H2H.
        Scoring cats: SV, HR allowed, K, ERA, WHIP, QS."""
        volume = self.ip / 180.0
        era_bonus = max(0, (4.50 - self.era) * 20)
        whip_bonus = max(0, (1.40 - self.whip) * 80)
        return (
            self.k * 0.8
            + self.qs * 5.0
            + era_bonus
            + whip_bonus
            + self.k_bb_pct * 1.5
        ) * volume


def _normalize(name: str) -> str:
    """Lowercase and strip suffixes for fuzzy matching."""
    import unicodedata
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return name.strip().lower().replace(".", "").replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "")


class ProjectionFetcher:
    """Fetches and caches Steamer ROS projections from FanGraphs."""

    def __init__(self):
        self.cache = get_cache()
        self.session = self._create_session()
        self._hitter_cache: Dict[str, HitterProjection] = {}
        self._pitcher_cache: Dict[str, PitcherProjection] = {}
        self._loaded = False

    @staticmethod
    def _create_session() -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def load(self, force: bool = False) -> None:
        """Load projections from cache or FanGraphs."""
        if self._loaded and not force:
            return

        cached = self.cache.get("fangraphs_projections", max_age_hours=CACHE_TTL_HOURS)
        if cached and not force:
            self._hitter_cache = cached.get("hitters", {})
            self._pitcher_cache = cached.get("pitchers", {})
            self._loaded = True
            logger.info(
                f"Loaded projections from cache: {len(self._hitter_cache)} hitters, "
                f"{len(self._pitcher_cache)} pitchers"
            )
            return

        self._fetch_hitters()
        self._fetch_pitchers()

        self.cache.set("fangraphs_projections", {
            "hitters": self._hitter_cache,
            "pitchers": self._pitcher_cache,
        })
        self._loaded = True

    def _fetch_hitters(self) -> None:
        """Fetch Steamer ROS hitter projections."""
        try:
            resp = self.session.get(FANGRAPHS_HITTER_URL, timeout=TIMEOUT)
            resp.raise_for_status()
            rows = resp.json()
        except Exception as e:
            logger.warning(f"FanGraphs hitter projections fetch failed: {e}")
            return

        count = 0
        for row in rows:
            try:
                name = row.get("PlayerName") or row.get("Name", "")
                if not name:
                    continue
                team = row.get("Team", row.get("TeamName", ""))
                pa = int(row.get("PA", 0))
                if pa < 50:
                    continue

                ab = int(row.get("AB", 1)) or 1
                h = int(row.get("H", 0))
                hr = int(row.get("HR", 0))
                rbi = int(row.get("RBI", 0))
                sb = int(row.get("SB", 0))
                bb = int(row.get("BB", 0))
                hbp = int(row.get("HBP", 0))
                sf = int(row.get("SF", 0))

                avg = h / ab if ab > 0 else 0.0
                obp_denom = ab + bb + hbp + sf
                obp = (h + bb + hbp) / obp_denom if obp_denom > 0 else 0.0
                singles = h - int(row.get("2B", 0)) - int(row.get("3B", 0)) - hr
                total_bases = singles + 2 * int(row.get("2B", 0)) + 3 * int(row.get("3B", 0)) + 4 * hr
                slg = total_bases / ab if ab > 0 else 0.0
                ops = obp + slg

                if "AVG" in row and row["AVG"]:
                    avg = float(row["AVG"])
                if "OBP" in row and row["OBP"]:
                    obp = float(row["OBP"])
                if "SLG" in row and row["SLG"]:
                    slg = float(row["SLG"])
                if "OPS" in row and row["OPS"]:
                    ops = float(row["OPS"])

                wrc_plus = int(row.get("wRC+", 0)) or int(row.get("wRC_plus", 100))
                war = float(row.get("WAR", 0.0))

                proj = HitterProjection(
                    name=name, team=team or "", pa=pa,
                    avg=round(avg, 3), hr=hr, rbi=rbi, sb=sb,
                    obp=round(obp, 3), slg=round(slg, 3), ops=round(ops, 3),
                    wrc_plus=wrc_plus, war=round(war, 1),
                )
                self._hitter_cache[_normalize(name)] = proj
                count += 1
            except Exception as e:
                logger.debug(f"Skipping hitter row: {e}")
                continue

        logger.info(f"Loaded {count} hitter projections from FanGraphs")

    def _fetch_pitchers(self) -> None:
        """Fetch Steamer ROS pitcher projections."""
        try:
            resp = self.session.get(FANGRAPHS_PITCHER_URL, timeout=TIMEOUT)
            resp.raise_for_status()
            rows = resp.json()
        except Exception as e:
            logger.warning(f"FanGraphs pitcher projections fetch failed: {e}")
            return

        count = 0
        for row in rows:
            try:
                name = row.get("PlayerName") or row.get("Name", "")
                if not name:
                    continue
                team = row.get("Team", row.get("TeamName", ""))
                ip = float(row.get("IP", 0))
                if ip < 10:
                    continue

                era = float(row.get("ERA", 0.0))
                whip = float(row.get("WHIP", 0.0))
                k = int(row.get("SO", 0)) or int(row.get("K", 0))
                fip = float(row.get("FIP", 0.0))
                war = float(row.get("WAR", 0.0))

                bb = int(row.get("BB", 0))
                k_pct = k / (ip * 4.3) * 100 if ip > 0 else 0
                bb_pct = bb / (ip * 4.3) * 100 if ip > 0 else 0
                k_bb_pct = k_pct - bb_pct

                if "K-BB%" in row and row["K-BB%"]:
                    k_bb_pct = float(str(row["K-BB%"]).replace("%", ""))
                elif "K_BB_pct" in row and row["K_BB_pct"]:
                    k_bb_pct = float(row["K_BB_pct"])

                # Estimate QS from IP + ERA
                gs = int(row.get("GS", 0))
                qs = max(0, int(gs * max(0, 1 - (era - 3.0) / 3.0))) if gs > 0 else 0

                proj = PitcherProjection(
                    name=name, team=team or "", ip=round(ip, 1),
                    era=round(era, 2), whip=round(whip, 2),
                    k=k, qs=qs, fip=round(fip, 2),
                    k_bb_pct=round(k_bb_pct, 1), war=round(war, 1),
                )
                self._pitcher_cache[_normalize(name)] = proj
                count += 1
            except Exception as e:
                logger.debug(f"Skipping pitcher row: {e}")
                continue

        logger.info(f"Loaded {count} pitcher projections from FanGraphs")

    def get_hitter(self, name: str) -> Optional[HitterProjection]:
        """Look up a hitter projection by name."""
        self.load()
        key = _normalize(name)
        if key in self._hitter_cache:
            return self._hitter_cache[key]
        for k, v in self._hitter_cache.items():
            if key in k or k in key:
                return v
        return None

    def get_pitcher(self, name: str) -> Optional[PitcherProjection]:
        """Look up a pitcher projection by name."""
        self.load()
        key = _normalize(name)
        if key in self._pitcher_cache:
            return self._pitcher_cache[key]
        for k, v in self._pitcher_cache.items():
            if key in k or k in key:
                return v
        return None

    def get_projection(self, name: str, is_pitcher: bool = False):
        """Generic lookup — returns HitterProjection or PitcherProjection."""
        if is_pitcher:
            return self.get_pitcher(name)
        return self.get_hitter(name)

    def get_all_hitters(self) -> List[HitterProjection]:
        self.load()
        return sorted(self._hitter_cache.values(), key=lambda p: p.ros_value, reverse=True)

    def get_all_pitchers(self) -> List[PitcherProjection]:
        self.load()
        return sorted(self._pitcher_cache.values(), key=lambda p: p.ros_value, reverse=True)
