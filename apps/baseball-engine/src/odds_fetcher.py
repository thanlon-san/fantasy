#!/usr/bin/env python3
"""
Vegas Odds Fetcher

Fetches implied run totals from The Odds API (free tier: 500 requests/month).
The game total (over/under) is the single most predictive number for
"how many runs will be scored in this game."

Usage:
    Set the ODDS_API_KEY environment variable, then:
        fetcher = OddsFetcher()
        fetcher.load()
        total = fetcher.get_game_total("NYY", "BOS")  # e.g. 9.5
        implied = fetcher.get_team_implied_runs("NYY")  # e.g. 5.2
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache_manager import get_cache

logger = logging.getLogger(__name__)

ODDS_API_URL = (
    "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
    "?markets=totals,h2h&regions=us&oddsFormat=american"
)
CACHE_TTL_HOURS = 2
TIMEOUT = 15

# The Odds API uses full team names; map to standard abbreviations
TEAM_ABBR_MAP: Dict[str, str] = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL", "Detroit Tigers": "DET",
    "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA", "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK",
    "Philadelphia Phillies": "PHI", "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB", "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

# Reverse map: abbreviation → full name
ABBR_TO_FULL: Dict[str, str] = {v: k for k, v in TEAM_ABBR_MAP.items()}


@dataclass
class GameOdds:
    """Odds for a single MLB game."""
    away_team: str
    home_team: str
    total: Optional[float] = None
    away_ml: Optional[int] = None
    home_ml: Optional[int] = None

    @property
    def away_implied_runs(self) -> Optional[float]:
        """Estimate each team's implied runs from the total + moneyline."""
        if self.total is None:
            return None
        if self.away_ml is not None and self.home_ml is not None:
            away_prob = _ml_to_prob(self.away_ml)
            home_prob = _ml_to_prob(self.home_ml)
            total_prob = away_prob + home_prob
            if total_prob > 0:
                return round(self.total * (away_prob / total_prob), 1)
        return round(self.total / 2, 1)

    @property
    def home_implied_runs(self) -> Optional[float]:
        if self.total is None:
            return None
        if self.away_ml is not None and self.home_ml is not None:
            away_prob = _ml_to_prob(self.away_ml)
            home_prob = _ml_to_prob(self.home_ml)
            total_prob = away_prob + home_prob
            if total_prob > 0:
                return round(self.total * (home_prob / total_prob), 1)
        return round(self.total / 2, 1)

    @property
    def environment(self) -> str:
        """Classify the game environment for lineup decisions."""
        if self.total is None:
            return "unknown"
        if self.total >= 10.0:
            return "high_scoring"
        if self.total <= 7.0:
            return "low_scoring"
        return "neutral"


def _ml_to_prob(ml: int) -> float:
    """Convert American moneyline to implied probability."""
    if ml > 0:
        return 100.0 / (ml + 100.0)
    return abs(ml) / (abs(ml) + 100.0)


def _abbr(full_name: str) -> str:
    """Convert full team name to 2-3 letter abbreviation."""
    return TEAM_ABBR_MAP.get(full_name, full_name[:3].upper())


class OddsFetcher:
    """Fetches and caches today's MLB game odds."""

    def __init__(self):
        self.cache = get_cache()
        self.session = self._create_session()
        self._games: Dict[str, GameOdds] = {}
        self._team_map: Dict[str, GameOdds] = {}
        self._loaded = False
        self._api_key = os.environ.get("ODDS_API_KEY", "")

    @staticmethod
    def _create_session() -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "FantasyBaseball/1.0",
            "Accept": "application/json",
        })
        retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def load(self, force: bool = False) -> None:
        """Load odds from cache or The Odds API."""
        if self._loaded and not force:
            return

        cached = self.cache.get("odds_data", max_age_hours=CACHE_TTL_HOURS)
        if cached and not force:
            self._games = cached.get("games", {})
            self._build_team_map()
            self._loaded = True
            logger.info(f"Loaded {len(self._games)} game odds from cache")
            return

        if not self._api_key:
            logger.warning("ODDS_API_KEY not set — Vegas lines unavailable")
            self._loaded = True
            return

        self._fetch_odds()
        self._loaded = True

    def _fetch_odds(self) -> None:
        """Fetch from The Odds API."""
        try:
            url = f"{ODDS_API_URL}&apiKey={self._api_key}"
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            events = resp.json()

            remaining = resp.headers.get("x-requests-remaining", "?")
            logger.info(f"Odds API: {len(events)} events, {remaining} requests remaining this month")
        except Exception as e:
            logger.warning(f"Odds API fetch failed: {e}")
            return

        games: Dict[str, GameOdds] = {}
        for event in events:
            away_full = event.get("away_team", "")
            home_full = event.get("home_team", "")
            away = _abbr(away_full)
            home = _abbr(home_full)
            game_key = f"{away}@{home}"

            total = None
            away_ml = None
            home_ml = None

            for book in event.get("bookmakers", []):
                for market in book.get("markets", []):
                    if market["key"] == "totals":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == "Over" and outcome.get("point"):
                                total = float(outcome["point"])
                                break
                    elif market["key"] == "h2h":
                        for outcome in market.get("outcomes", []):
                            price = outcome.get("price")
                            if price is None:
                                continue
                            if outcome.get("name") == away_full:
                                away_ml = int(price)
                            elif outcome.get("name") == home_full:
                                home_ml = int(price)
                if total is not None:
                    break

            odds = GameOdds(
                away_team=away, home_team=home,
                total=total, away_ml=away_ml, home_ml=home_ml,
            )
            games[game_key] = odds

        self._games = games
        self._build_team_map()

        self.cache.set("odds_data", {"games": self._games})
        logger.info(f"Loaded {len(games)} game odds from The Odds API")

    def _build_team_map(self) -> None:
        """Build team → GameOdds lookup."""
        self._team_map = {}
        for game in self._games.values():
            self._team_map[game.away_team] = game
            self._team_map[game.home_team] = game

    def get_game_odds(self, team: str) -> Optional[GameOdds]:
        """Get odds for the game a team is playing in."""
        self.load()
        return self._team_map.get(team.upper())

    def get_game_total(self, away_team: str, home_team: str) -> Optional[float]:
        """Get the over/under total for a specific game."""
        self.load()
        key = f"{away_team.upper()}@{home_team.upper()}"
        game = self._games.get(key)
        return game.total if game else None

    def get_team_implied_runs(self, team: str) -> Optional[float]:
        """Get a team's implied run total for today's game."""
        self.load()
        game = self._team_map.get(team.upper())
        if not game:
            return None
        if team.upper() == game.away_team:
            return game.away_implied_runs
        return game.home_implied_runs

    def get_all_odds(self) -> List[GameOdds]:
        """Return all game odds for today."""
        self.load()
        return list(self._games.values())
