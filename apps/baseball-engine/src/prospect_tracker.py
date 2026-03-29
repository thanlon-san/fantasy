#!/usr/bin/env python3
"""
Prospect Call-Up Watchlist Tracker

Monitors top fantasy-relevant prospects by:
- Fetching recent MiLB game logs from MLB Stats API
- Detecting hot streaks (14-day OPS > 1.000)
- Tracking 40-man roster status changes
- Flagging call-up candidates based on ETA + performance
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

APP_ROOT = Path(__file__).parent.parent

try:
    from src.cache_manager import get_cache
    cache = get_cache()
except Exception:
    cache = None


@dataclass
class ProspectProfile:
    name: str
    mlb_id: int
    team: str
    position: str
    level: str
    top_100_rank: int
    eta: str

    games_14d: int = 0
    ab_14d: int = 0
    hits_14d: int = 0
    hr_14d: int = 0
    rbi_14d: int = 0
    sb_14d: int = 0
    avg_14d: float = 0.0
    ops_14d: float = 0.0
    k_14d: int = 0
    bb_14d: int = 0

    # Pitcher stats (14-day)
    ip_14d: float = 0.0
    p_k_14d: int = 0
    p_bb_14d: int = 0
    era_14d: float = 0.0
    whip_14d: float = 0.0
    p_games_14d: int = 0

    is_hot: bool = False
    hot_streak_ops: float = 0.0
    is_on_40_man: bool = False
    roster_status: str = ""
    callup_score: int = 0
    alert_reasons: List[str] = field(default_factory=list)

    @property
    def is_pitcher(self) -> bool:
        return self.position in ("SP", "RP", "P")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "mlb_id": self.mlb_id,
            "team": self.team,
            "position": self.position,
            "level": self.level,
            "top_100_rank": self.top_100_rank,
            "eta": self.eta,
            "games_14d": self.games_14d,
            "ab_14d": self.ab_14d,
            "hits_14d": self.hits_14d,
            "hr_14d": self.hr_14d,
            "rbi_14d": self.rbi_14d,
            "sb_14d": self.sb_14d,
            "avg_14d": round(self.avg_14d, 3),
            "ops_14d": round(self.ops_14d, 3),
            "k_14d": self.k_14d,
            "bb_14d": self.bb_14d,
            "ip_14d": round(self.ip_14d, 1),
            "p_k_14d": self.p_k_14d,
            "p_bb_14d": self.p_bb_14d,
            "era_14d": round(self.era_14d, 2),
            "whip_14d": round(self.whip_14d, 2),
            "p_games_14d": self.p_games_14d,
            "is_pitcher": self.is_pitcher,
            "is_hot": self.is_hot,
            "hot_streak_ops": round(self.hot_streak_ops, 3),
            "is_on_40_man": self.is_on_40_man,
            "roster_status": self.roster_status,
            "callup_score": self.callup_score,
            "alert_reasons": self.alert_reasons,
        }


class ProspectTracker:
    BASE_URL = "https://statsapi.mlb.com/api/v1"
    TIMEOUT = 20

    def __init__(self):
        self.session = requests.Session()
        self.watchlist: List[dict] = []
        self._load_watchlist()

    def _load_watchlist(self):
        path = APP_ROOT / "data" / "prospect_watchlist.json"
        try:
            with open(path) as f:
                self.watchlist = json.load(f)
            logger.info(f"Loaded {len(self.watchlist)} prospects from watchlist")
        except Exception as e:
            logger.warning(f"Could not load prospect watchlist: {e}")
            self.watchlist = []

    def _fetch_game_log(self, player_id: int, days: int = 14) -> Optional[list]:
        cache_key = f"prospect_gamelog_{player_id}_{days}"
        if cache:
            cached = cache.get(cache_key, max_age_hours=6)
            if cached is not None:
                return cached

        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        for game_type in ("A", "R"):
            try:
                url = f"{self.BASE_URL}/people/{player_id}/stats"
                params = {
                    "stats": "gameLog",
                    "group": "hitting",
                    "season": datetime.now().year,
                    "gameType": game_type,
                    "startDate": start_date,
                    "endDate": end_date,
                }
                resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                stats = data.get("stats", [])
                if stats:
                    splits = stats[0].get("splits", [])
                    if splits:
                        if cache:
                            cache.set(cache_key, splits)
                        return splits
            except Exception as e:
                logger.debug(f"Game log fetch failed for {player_id} type={game_type}: {e}")

        if cache:
            cache.set(cache_key, [])
        return []

    def _fetch_pitcher_log(self, player_id: int, days: int = 14) -> Optional[list]:
        cache_key = f"prospect_pitcher_log_{player_id}_{days}"
        if cache:
            cached = cache.get(cache_key, max_age_hours=6)
            if cached is not None:
                return cached

        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        for game_type in ("A", "R"):
            try:
                url = f"{self.BASE_URL}/people/{player_id}/stats"
                params = {
                    "stats": "gameLog",
                    "group": "pitching",
                    "season": datetime.now().year,
                    "gameType": game_type,
                    "startDate": start_date,
                    "endDate": end_date,
                }
                resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                stats = data.get("stats", [])
                if stats:
                    splits = stats[0].get("splits", [])
                    if splits:
                        if cache:
                            cache.set(cache_key, splits)
                        return splits
            except Exception as e:
                logger.debug(f"Pitcher log fetch failed for {player_id} type={game_type}: {e}")

        if cache:
            cache.set(cache_key, [])
        return []

    def _fetch_roster_status(self, player_id: int) -> Dict:
        cache_key = f"prospect_roster_{player_id}"
        if cache:
            cached = cache.get(cache_key, max_age_hours=12)
            if cached is not None:
                return cached

        result = {"is_on_40_man": False, "status": ""}
        try:
            url = f"{self.BASE_URL}/people/{player_id}"
            params = {"hydrate": "currentTeam"}
            resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            people = data.get("people", [])
            if people:
                person = people[0]
                status = person.get("status", {}).get("description", "")
                active = person.get("active", False)
                result["status"] = status
                result["is_on_40_man"] = active or "Active" in status
        except Exception as e:
            logger.debug(f"Roster status fetch failed for {player_id}: {e}")

        if cache:
            cache.set(cache_key, result)
        return result

    def _aggregate_hitter(self, splits: list) -> dict:
        ab = hits = hr = rbi = sb = k = bb = 0
        doubles = triples = sf = hbp = 0
        games = len(splits)

        for game in splits:
            s = game.get("stat", {})
            ab += s.get("atBats", 0)
            hits += s.get("hits", 0)
            hr += s.get("homeRuns", 0)
            rbi += s.get("rbi", 0)
            sb += s.get("stolenBases", 0)
            k += s.get("strikeOuts", 0)
            bb += s.get("baseOnBalls", 0)
            doubles += s.get("doubles", 0)
            triples += s.get("triples", 0)
            sf += s.get("sacFlies", 0)
            hbp += s.get("hitByPitch", 0)

        avg = hits / ab if ab > 0 else 0.0
        pa = ab + bb + hbp + sf
        obp = (hits + bb + hbp) / pa if pa > 0 else 0.0
        tb = hits + doubles + 2 * triples + 3 * hr
        slg = tb / ab if ab > 0 else 0.0
        ops = obp + slg

        return {
            "games": games, "ab": ab, "hits": hits, "hr": hr,
            "rbi": rbi, "sb": sb, "k": k, "bb": bb,
            "avg": avg, "ops": ops,
        }

    def _aggregate_pitcher(self, splits: list) -> dict:
        ip_total = 0.0
        k = bb = hits = er = 0
        games = len(splits)

        for game in splits:
            s = game.get("stat", {})
            ip_str = str(s.get("inningsPitched", "0"))
            try:
                parts = ip_str.split(".")
                full = int(parts[0])
                thirds = int(parts[1]) if len(parts) > 1 else 0
                ip_total += full + thirds / 3.0
            except (ValueError, IndexError):
                pass
            k += s.get("strikeOuts", 0)
            bb += s.get("baseOnBalls", 0)
            hits += s.get("hits", 0)
            er += s.get("earnedRuns", 0)

        era = (er / ip_total) * 9 if ip_total > 0 else 0.0
        whip = (bb + hits) / ip_total if ip_total > 0 else 0.0

        return {
            "games": games, "ip": ip_total, "k": k, "bb": bb,
            "era": era, "whip": whip,
        }

    def _calc_callup_score(self, p: ProspectProfile) -> int:
        score = 0

        rank_boost = max(0, 51 - p.top_100_rank)
        score += rank_boost

        level_map = {"MLB": 30, "AAA": 25, "AA": 10, "A+": 2, "A": 0}
        score += level_map.get(p.level, 0)

        if p.eta == str(datetime.now().year):
            score += 15
        elif p.eta == str(datetime.now().year + 1):
            score += 5

        if p.is_hot:
            score += 20

        if p.is_on_40_man:
            score += 10

        if not p.is_pitcher:
            if p.hr_14d >= 3:
                score += 10
            if p.avg_14d >= 0.300 and p.ab_14d >= 20:
                score += 10
        else:
            if p.era_14d <= 2.50 and p.ip_14d >= 10:
                score += 15
            if p.p_k_14d >= 15 and p.ip_14d >= 10:
                score += 10

        return min(score, 100)

    def _generate_alerts(self, p: ProspectProfile) -> List[str]:
        alerts = []

        if p.is_hot:
            alerts.append(f"Hot streak: {p.ops_14d:.3f} OPS over last 14 days")

        if p.is_on_40_man and p.level == "AAA":
            alerts.append("On 40-man roster at AAA — call-up eligible")

        if not p.is_pitcher:
            if p.hr_14d >= 4:
                alerts.append(f"Power surge: {p.hr_14d} HR in 14 days")
            if p.sb_14d >= 4:
                alerts.append(f"Speed burst: {p.sb_14d} SB in 14 days")
            if p.avg_14d >= 0.350 and p.ab_14d >= 20:
                alerts.append(f"On fire: {p.avg_14d:.3f} AVG ({p.hits_14d}-for-{p.ab_14d})")
        else:
            if p.era_14d <= 1.50 and p.ip_14d >= 10:
                alerts.append(f"Dominant: {p.era_14d:.2f} ERA over {p.ip_14d:.1f} IP")
            if p.p_k_14d >= 20 and p.ip_14d >= 10:
                alerts.append(f"Strikeout machine: {p.p_k_14d} K in {p.ip_14d:.1f} IP")

        if p.eta == str(datetime.now().year) and p.level in ("AAA", "MLB"):
            alerts.append(f"{p.eta} ETA — fantasy-relevant now")

        return alerts

    def scan_all(self) -> List[ProspectProfile]:
        profiles: List[ProspectProfile] = []

        for entry in self.watchlist:
            p = ProspectProfile(
                name=entry["name"],
                mlb_id=entry["mlb_id"],
                team=entry["team"],
                position=entry["position"],
                level=entry["level"],
                top_100_rank=entry["top_100_rank"],
                eta=entry["eta"],
            )

            if p.is_pitcher:
                splits = self._fetch_pitcher_log(p.mlb_id, days=14) or []
                if splits:
                    agg = self._aggregate_pitcher(splits)
                    p.p_games_14d = agg["games"]
                    p.ip_14d = agg["ip"]
                    p.p_k_14d = agg["k"]
                    p.p_bb_14d = agg["bb"]
                    p.era_14d = agg["era"]
                    p.whip_14d = agg["whip"]
                    p.is_hot = agg["era"] <= 2.50 and agg["ip"] >= 10
                    p.hot_streak_ops = 0.0
            else:
                splits = self._fetch_game_log(p.mlb_id, days=14) or []
                if splits:
                    agg = self._aggregate_hitter(splits)
                    p.games_14d = agg["games"]
                    p.ab_14d = agg["ab"]
                    p.hits_14d = agg["hits"]
                    p.hr_14d = agg["hr"]
                    p.rbi_14d = agg["rbi"]
                    p.sb_14d = agg["sb"]
                    p.avg_14d = agg["avg"]
                    p.ops_14d = agg["ops"]
                    p.k_14d = agg["k"]
                    p.bb_14d = agg["bb"]
                    p.is_hot = agg["ops"] >= 1.000 and agg["ab"] >= 15
                    p.hot_streak_ops = agg["ops"]

            roster = self._fetch_roster_status(p.mlb_id)
            p.is_on_40_man = roster.get("is_on_40_man", False)
            p.roster_status = roster.get("status", "")

            p.callup_score = self._calc_callup_score(p)
            p.alert_reasons = self._generate_alerts(p)

            profiles.append(p)

        profiles.sort(key=lambda x: x.callup_score, reverse=True)
        return profiles

    def get_hot_prospects(self) -> List[ProspectProfile]:
        all_profiles = self.scan_all()
        return [p for p in all_profiles if p.is_hot or p.alert_reasons]
