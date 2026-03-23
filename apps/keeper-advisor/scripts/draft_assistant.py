#!/usr/bin/env python3
"""
Draft Day Assistant — 2balls, California Palm League 2026
Live draft tracker + ADP-based recommendation engine

Usage:
    python draft_assistant.py              # Live Yahoo API polling mode
    python draft_assistant.py --cheatsheet # Print ranked cheat sheet and exit
    python draft_assistant.py --offline    # Manual pick-entry mode (no Yahoo API)
"""

import sys
import time
import json
import re
import argparse
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Paths ────────────────────────────────────────────────────────────────────
APP_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "packages"))

OAUTH_CONFIG = APP_ROOT / "config" / "oauth2.json"
PLAYER_KEY_CACHE = Path("/tmp/yahoo_player_keys_2026.json")
ADP_CACHE = Path("/tmp/fp_adp_2026.json")

# ─── Terminal Colors ──────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

# ─── League & Strategy Configuration ─────────────────────────────────────────
MY_DRAFT_POSITION = 7
TOTAL_TEAMS       = 12
TOTAL_ROUNDS      = 24
SEASON            = 2026
MY_KEEPER_ROUNDS  = {9, 11, 12}   # Confirmed from Yahoo: Crochet R9, Miller R11, Neto R12

MY_KEEPERS = [
    # ADP values = FantasyPros 2026 consensus avg (refreshed pre-draft).
    # All three keepers are strong surplus picks at their keeper rounds:
    #   Crochet: consensus 12, keeping in R9 (~#107) → +95 picks early
    #   Miller:  consensus 43, keeping in R11 (~#131) → +88 picks early
    #   Neto:    consensus 34, keeping in R12 (~#155) → +121 picks early
    #            (Yahoo ADP 29 means Yahoo drafters actually value him even higher)
    {"name": "Garrett Crochet", "position": "SP", "round": 9,  "adp": 12},
    {"name": "Mason Miller",    "position": "RP", "round": 11, "adp": 43},
    {"name": "Zach Neto",       "position": "SS", "round": 12, "adp": 34},
]

# All 12 teams' confirmed keepers — pre-removed from the available pool at draft start.
# Knowing these shifts the effective ADP board significantly (Skenes ADP 4, Raleigh ADP 11,
# Ketel Marte ADP 13, Elly De La Cruz ADP ~29, George Kirby ADP ~22 all off the board).
LEAGUE_KEEPERS_ALL = [
    # Col. Chin Music
    "Cal Raleigh", "Elly De La Cruz", "Roman Anthony",
    # 2balls (my own)
    "Garrett Crochet", "Mason Miller", "Zach Neto",
    # Bloodrocuted
    "George Kirby", "Chris Sale", "Riley Greene",
    # Clayton Kerfax
    "Jesus Luzardo", "Tyler Soderstrom", "Hunter Goodman",
    # Eephus Knieephus
    "William Contreras", "Devin Williams", "Ben Rice",
    # Jobu
    "Pete Crow-Armstrong", "Nolan McLean",
    # Jedi Master All Stars
    "Josh Naylor", "Jarren Duran",
    # Ooh Piece Of Candy
    "Trevor Story", "Kyle Stowers", "Nico Hoerner",
    # PrepareTheLazorbeam
    "Ketel Marte", "Brent Rooker", "Maikel Garcia",
    # sallywithacrouton
    "Junior Caminero", "Cristopher Sanchez", "Brice Turang",
    # Slam Diego
    "Byron Buxton", "Aroldis Chapman", "Jacob Misiorowski",
    # Uncle Charlie
    "Paul Skenes", "Jackson Merrill", "Nick Kurtz",
]

# ─── Target Lists & Breakouts ─────────────────────────────────────────────────

# Players you absolutely want. Huge score boost.
MY_GUYS = [
    "Juan Soto",
    "Julio Rodriguez",
    "Kyle Tucker",
    "Fernando Tatis Jr.",
    "Corbin Carroll",
    "Ryan Pepiot",
    "Andres Munoz",
    "Cade Smith",
    "Matt Wallner",
]

# Elite Groundball SPs (Protects your HR Allowed category)
GROUNDBALL_SPS = [
    "Logan Webb",
    "Framber Valdez",
    "Sonny Gray",
    "Zack Wheeler",
    "Max Fried"
]

# Elite OPS/Power targets (Massive bump since your league uses OPS instead of AVG)
OPS_MONSTERS = [
    "Kyle Schwarber",
    "Max Muncy",
    "Pete Alonso",
    "Matt Olson",
    "Marcell Ozuna"
]

# Late-round prospect stashes (Draft in R23/24 to save waiver moves)
PROSPECT_STASHES = [
    "Jasson Dominguez",
    "Jordan Lawlar",
    "Christian Moore",
    "Coby Mayo",
    "Emmanuel Rodriguez"
]

# Players you want to avoid entirely. Huge score penalty.
DND = [
    "Cole Ragans",
    "Kyle Bradish",
    "Chris Sale",
    "Yoshinobu Yamamoto",
    "Ranger Suarez",
    "Ryne Nelson",
    "Sandy Alcantara",
    "George Springer",
    "James Wood",
    "Junior Caminero",
    "Byron Buxton",
    "Esteury Ruiz",   # Empty speed, kills other cats
]

# Late 2025 Statcast darlings (high barrel %, low xwOBA vs wOBA, etc.)
STATCAST_BREAKOUTS = [
    "Matt Wallner",
    "Sal Stewart",
    "Daylen Lile",
    "JJ Wetherholt",
    "Ryan Waldschmidt",
    "Ryan Pepiot",
    "Shea Langeliers",
    "Riley Greene",
    "Brent Rooker",
    "Tarik Skubal",
]

# 2026 Spring Training Risers (Velocity spikes, new pitches, winning jobs)
SPRING_RISERS = [
    "Ryan Weathers",
    "Triston McKenzie",
    "Carson Whisenhunt",
    "Chayce McDermott",
    "Matt McLain",
    "Jac Caglianone",
    "Mick Abel",
    "Konnor Griffin",
    "Samuel Basallo",
    "Angel Bastardo",
]

# Elite Speed / Stolen Base targets (SB dries up FAST, these guys carry the category)
ELITE_SPEED = [
    "Elly De La Cruz", "Corbin Carroll", "Bobby Witt Jr.", "CJ Abrams", 
    "Brice Turang", "Esteury Ruiz", "Jose Caballero", "Maikel Garcia", 
    "Lane Thomas", "Jarren Duran", "David Hamilton", "Jacob Young", 
    "Victor Scott II", "Jon Berti", "Johan Rojas"
]

# Top 30 Closers/High-Leverage RPs. Non-SP Relievers not on this list are penalized.
ELITE_CLOSERS = [
    "Mason Miller", "Edwin Diaz", "Andres Munoz", "Aroldis Chapman", 
    "Josh Hader", "Cade Smith", "Jhoan Duran", "Emmanuel Clase", 
    "Ryan Helsley", "Devin Williams", "Kirby Yates", "Robert Suarez", 
    "Raisel Iglesias", "Camilo Doval", "Kenley Jansen", "Pete Fairbanks", 
    "Evan Phillips", "Kyle Finnegan", "Clay Holmes", "Carlos Estevez", 
    "Tanner Scott", "Alexis Diaz", "Ryan Walker", "Justin Martinez", 
    "Lucas Erceg", "Chad Green", "David Bednar", "Jordan Romano", 
    "Paul Sewald", "Jason Foley", "Luke Weaver"
]

# Elite Setup Men (Insane K-rates and sub-2.50 ERAs). Perfect for your ratio-heavy strategy!
ELITE_SETUP_MEN = [
    "Bryan Abreu", "Orion Kerkering", "Jeremiah Estrada", "Matt Strahm", 
    "Jeff Hoffman", "Griffin Jax", "Jason Adam", "Hunter Harvey", 
    "Kevin Ginkel", "Yennier Cano", "A.J. Minter", "Colin Holderman",
    "Garrett Whitlock"
]

# Remaining roster slots to fill via the draft (keepers subtract from these).
# Updated after confirming keeper rounds from Yahoo:
#   Crochet R9 (SP kept), Miller R11 (RP kept), Neto R12 (SS kept)
#   Round 10 is now a REAL pick (was previously Miller's keeper slot).
ROSTER_NEEDS = {
    "C":    1,
    "1B":   1,
    "2B":   1,
    "3B":   1,
    "SS":   0,   # Neto (R12)
    "OF":   3,
    "Util": 2,
    "SP":   5,   # 6 slots − Crochet (R9)
    "RP":   2,   # 3 slots − Miller (R11)
    "P":    1,   # Pitcher flex slot
    "BN":   4,
}

# Strategy windows
# Pitching cats: HR allowed, K, ERA, WHIP, SV, QS
# Relievers dominate HR, ERA, WHIP, SV — 4 of 6 very winnable
# Only need 1–2 SPs for K counting stats (punting QS entirely)
BATTER_ROUNDS    = set(range(1, 9))    # Rounds 1–8: batters only
# R9 = Crochet keeper, R11 = Miller keeper, R12 = Neto keeper — no picks those rounds.
# R10 (overall ~119) and R13 (overall ~155) are the two real SP windows.
SP_TARGET_ROUNDS = {10, 13}            # 1–2 K-upside SPs (no W category to chase)
CLOSER_ROUNDS    = set(range(14, 25))  # Closers for HR/ERA/WHIP/SV dominance

# Scarcity priority for batters (most scarce first)
BAT_SCARCITY = ["C", "SS", "2B", "3B", "1B", "OF"]

YAHOO_BASE   = "https://fantasysports.yahooapis.com/fantasy/v2"
FP_URL       = "https://www.fantasypros.com/mlb/adp/overall.php"
LEAGUE_KEY   = "469.l.25136"  # California Palm League 2026 — confirmed

TIER_BREAKS = [12, 36, 72, 120, 180, 250]


# ─── Utilities ────────────────────────────────────────────────────────────────

def norm_name(name: str) -> str:
    """Normalize a player name for fuzzy matching."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Strip Yahoo two-way player role qualifiers
    for role in (" (Batter)", " (Pitcher)", " (IL)"):
        if s.endswith(role):
            s = s[: -len(role)]
    for sfx in (" Jr.", " Jr", " Sr.", " Sr", " II", " III", " IV", " V"):
        if s.endswith(sfx):
            s = s[: -len(sfx)]
    return s.lower().strip().replace(".", "").replace("  ", " ")


def get_tier(adp: float) -> str:
    labels = ["Elite", "Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5", "Deep"]
    for i, cutoff in enumerate(TIER_BREAKS):
        if adp <= cutoff:
            return labels[i]
    return labels[-1]


def calc_my_picks() -> List[Dict]:
    """Build the full list of my pick slots across all 24 rounds."""
    picks = []
    for rnd in range(1, TOTAL_ROUNDS + 1):
        if rnd in MY_KEEPER_ROUNDS:
            keeper = next(k for k in MY_KEEPERS if k["round"] == rnd)
            picks.append({"round": rnd, "overall": None, "is_keeper": True, "keeper": keeper})
        else:
            pick_in_round = MY_DRAFT_POSITION if rnd % 2 == 1 else (TOTAL_TEAMS - MY_DRAFT_POSITION + 1)
            overall = (rnd - 1) * TOTAL_TEAMS + pick_in_round
            picks.append({"round": rnd, "overall": overall, "is_keeper": False})
    return picks


def header(text: str, width: int = 80) -> str:
    return f"\n{C.BOLD}{C.CYAN}{'─' * width}\n  {text}\n{'─' * width}{C.RESET}"


def pos_color(pos: str) -> str:
    if pos in ("SP",):    return C.RED
    if pos in ("RP",):    return C.MAGENTA
    if pos in ("C",):     return C.YELLOW
    if pos in ("SS", "2B", "3B"): return C.CYAN
    if pos in ("1B",):    return C.GREEN
    if pos in ("OF",):    return C.BLUE
    return C.WHITE


# ─── FantasyPros Scraper ───────────────────────────────────────────────────────

class FPScraper:
    """Fetches ADP + position data from FantasyPros with local caching."""

    CACHE_MAX_HOURS = 12

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _load_cache(self) -> Optional[List[Dict]]:
        if not ADP_CACHE.exists():
            return None
        age = (time.time() - ADP_CACHE.stat().st_mtime) / 3600
        if age > self.CACHE_MAX_HOURS:
            return None
        with open(ADP_CACHE) as f:
            data = json.load(f)
        print(f"{C.DIM}  Using cached ADP data ({len(data)} players, {age:.1f}h old){C.RESET}")
        return data

    def fetch(self) -> List[Dict]:
        cached = self._load_cache()
        if cached:
            return cached

        print(f"{C.CYAN}  Fetching 2026 ADP from FantasyPros...{C.RESET}", end="", flush=True)
        try:
            resp = self.session.get(FP_URL, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f" {C.RED}FAILED: {e}{C.RESET}")
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.content, "html.parser")

        # Detect column layout from thead — FantasyPros occasionally adds/removes
        # platform columns (e.g. ESPN was added between FT and AVG).
        # Always trust the header, never hardcode column offsets.
        table = soup.select_one("table")
        if not table:
            print(f" {C.YELLOW}no table found{C.RESET}")
            return []

        headers = [th.get_text(strip=True).lower() for th in table.select("thead th")]
        num_cols = len(headers)

        # Locate the columns we care about
        player_col = next((i for i, h in enumerate(headers) if "player" in h), 1)
        yahoo_col  = next((i for i, h in enumerate(headers) if h == "yahoo"), 2)
        avg_col    = next((i for i, h in enumerate(headers) if h in ("avg", "average")), num_cols - 1)
        rank_col   = next((i for i, h in enumerate(headers) if h == "rank"), 0)

        # Parse all rows, then deduplicate (keep lowest avg ADP per player)
        seen: Dict[str, Dict] = {}  # normalized_name -> player dict

        for row in table.select("tbody tr"):
            cells = row.find_all("td")
            # Step through grouped-player blocks within each table row.
            # FantasyPros uses one big <tr> with all players packed in.
            for i in range(0, len(cells), num_cols):
                if i + avg_col >= len(cells):
                    break
                player_text = cells[i + player_col].get_text(strip=True)
                yahoo_text  = cells[i + yahoo_col].get_text(strip=True)  if i + yahoo_col < len(cells) else ""
                avg_text    = cells[i + avg_col].get_text(strip=True)
                rank_text   = cells[i + rank_col].get_text(strip=True)   if i + rank_col < len(cells) else ""

                m = re.match(r"^(.+?)\s*\(([A-Z]{2,3}(?:/[A-Z]{2,3})?)\s*-\s*([^)]+)\)", player_text)
                if not m:
                    continue
                name          = m.group(1).strip()
                team          = m.group(2).strip()
                raw_positions = [p.strip() for p in m.group(3).split(",")]

                positions = self._normalize_positions(raw_positions)

                try:
                    adp = float(avg_text)
                except ValueError:
                    continue

                # expert_rank: where FP consensus experts rank this player.
                # expert_rank_gap = adp - expert_rank:
                #   positive → drafted later than experts say (market sleeping = value)
                #   negative → drafted earlier than experts say (market overrating = risky)
                _expert_rank     = None
                _expert_rank_gap = 0.0
                try:
                    _expert_rank     = int(rank_text)
                    _expert_rank_gap = round(adp - _expert_rank, 1)
                except (ValueError, TypeError):
                    pass

                # Positive yahoo_discount = Yahoo drafts LATER than consensus = undervalued on Yahoo
                _yahoo_adp      = adp
                _yahoo_discount = 0.0
                try:
                    _yahoo_adp      = float(yahoo_text)
                    _yahoo_discount = round(_yahoo_adp - adp, 1)
                except ValueError:
                    pass

                key = norm_name(name)
                if key not in seen or adp < seen[key]["adp"]:
                    seen[key] = {
                        "name":            name,
                        "team":            team,
                        "positions":       positions,
                        "adp":             adp,
                        "yahoo_adp":       _yahoo_adp,
                        "yahoo_discount":  _yahoo_discount,
                        "expert_rank":     _expert_rank,
                        "expert_rank_gap": _expert_rank_gap,
                    }

        players = sorted(seen.values(), key=lambda x: x["adp"])

        if players:
            print(f" {C.GREEN}OK ({len(players)} players){C.RESET}")
            with open(ADP_CACHE, "w") as f:
                json.dump(players, f, indent=2)
        else:
            print(f" {C.YELLOW}0 players parsed — site layout may have changed{C.RESET}")

        return players

    @staticmethod
    def _normalize_positions(raw: List[str]) -> List[str]:
        """Map FantasyPros position labels to Yahoo fantasy roster positions."""
        mapping = {
            "LF": "OF", "CF": "OF", "RF": "OF",
            "DH": "Util",
        }
        out = []
        for pos in raw:
            mapped = mapping.get(pos.upper(), pos.upper())
            if mapped not in out:
                out.append(mapped)
        return out


# ─── Yahoo Live Draft Client ──────────────────────────────────────────────────

class YahooDraft:
    """Minimal Yahoo Fantasy API client for live draft monitoring."""

    def __init__(self):
        from src.yahoo_oauth_manual import YahooOAuth2
        self.oauth      = YahooOAuth2.load_from_file(str(OAUTH_CONFIG))
        self.league_key = LEAGUE_KEY  # known, skip discovery
        self._pk_cache: Dict[str, Dict] = self._load_pk_cache()

    # ── Token / session ───────────────────────────────────────────────────────

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers["Authorization"] = f"Bearer {self.oauth.access_token}"
        return s

    def _get(self, url: str) -> Optional[Dict]:
        sep = "&" if "?" in url else "?"
        url = url + sep + "format=json"
        for attempt in range(2):
            resp = self._session().get(url, timeout=15)
            if resp.status_code == 401 and attempt == 0:
                if self.oauth.refresh_access_token():
                    # Persist refreshed token to disk
                    self.oauth.save_to_file(str(OAUTH_CONFIG))
                continue
            try:
                resp.raise_for_status()
                data = resp.json()
                return data.get("fantasy_content", data)
            except Exception as e:
                print(f"{C.RED}  Yahoo error: {e}{C.RESET}")
                return None
        return None

    # ── League key ────────────────────────────────────────────────────────────

    def find_league_key(self) -> Optional[str]:
        """Returns the known league key (hardcoded from config)."""
        print(f"{C.GREEN}  League: California Palm League ({self.league_key}){C.RESET}")
        return self.league_key

    # ── Draft results ─────────────────────────────────────────────────────────

    def fetch_picks(self) -> List[Dict]:
        """Return all picks made so far, sorted by overall pick number.

        Yahoo's /draftresults endpoint returns ALL draft slots (including future
        unfilled ones). We filter to only entries that have a player_key, which
        indicates the pick has actually been made.
        """
        if not self.league_key:
            return []
        data = self._get(f"{YAHOO_BASE}/league/{self.league_key}/draftresults?")
        if not data:
            return []
        try:
            dr = data["league"][1]["draft_results"]
            # Pre-draft: Yahoo returns an empty list instead of a numbered dict
            if not isinstance(dr, dict):
                return []
            picks = []
            for k, v in dr.items():
                if k == "count":
                    continue
                d = v.get("draft_result", {})
                pk = d.get("player_key", "")
                if not pk:
                    continue  # skip unfilled future slots
                picks.append({
                    "overall":    int(d.get("pick", 0)),
                    "round":      int(d.get("round", 0)),
                    "team_key":   d.get("team_key", ""),
                    "player_key": pk,
                })
            return sorted(picks, key=lambda x: x["overall"])
        except Exception as e:
            print(f"{C.RED}  Error parsing draft results: {e}{C.RESET}")
            return []

    # ── Player name resolution ────────────────────────────────────────────────

    def _load_pk_cache(self) -> Dict[str, Dict]:
        if PLAYER_KEY_CACHE.exists():
            with open(PLAYER_KEY_CACHE) as f:
                return json.load(f)
        return {}

    def _save_pk_cache(self):
        with open(PLAYER_KEY_CACHE, "w") as f:
            json.dump(self._pk_cache, f, indent=2)

    def seed_cache_from_rosters(self) -> Dict[str, List[Dict]]:
        """
        Fetch all 12 team rosters and populate _pk_cache with every drafted player.
        This is the reliable fallback when /draftresults stops returning player_keys
        after the first ~45 picks (a Yahoo API truncation quirk).
        Returns {team_key: [player_info, ...]} for all teams.
        """
        data = self._get(f"{YAHOO_BASE}/league/{self.league_key}/teams;out=roster?")
        if not data:
            return {}
        result: Dict[str, List[Dict]] = {}
        added = 0
        try:
            teams_raw = {}
            if "league" in data:
                league_data = data["league"]
                if isinstance(league_data, list) and len(league_data) > 1:
                    teams_raw = league_data[1].get("teams", {})
            if not isinstance(teams_raw, dict):
                return {}
            for tk, tv in teams_raw.items():
                if tk == "count":
                    continue
                team_arr = tv.get("team", [[], {}])
                team_meta = team_arr[0]
                team_key = next((p["team_key"] for p in team_meta if isinstance(p, dict) and "team_key" in p), "")
                roster_section = team_arr[1] if len(team_arr) > 1 else {}
                players_raw = roster_section.get("roster", {}).get("0", {}).get("players", {})
                if not isinstance(players_raw, dict):
                    continue
                team_players: List[Dict] = []
                for pk, pv in players_raw.items():
                    if pk == "count":
                        continue
                    player_arr = pv.get("player", [[]])[0]
                    info: Dict = {}
                    for prop in player_arr:
                        if not isinstance(prop, dict):
                            continue
                        if "player_key" in prop:
                            info["player_key"] = prop["player_key"]
                        if "name" in prop:
                            info["name"] = prop["name"].get("full", "")
                        if "display_position" in prop:
                            info["positions"] = [p.strip() for p in prop["display_position"].split(",")]
                        if "editorial_team_abbr" in prop:
                            info["team"] = prop["editorial_team_abbr"]
                    if info.get("player_key") and info.get("name"):
                        if info["player_key"] not in self._pk_cache:
                            self._pk_cache[info["player_key"]] = info
                            added += 1
                        team_players.append(info)
                if team_key and team_players:
                    result[team_key] = team_players
        except Exception as e:
            print(f"{C.RED}  seed_cache_from_rosters error: {e}{C.RESET}")
        if added:
            self._save_pk_cache()
            print(f"  seed_cache_from_rosters: added {added} new player names.")
        return result

    def resolve_player_keys(self, keys: List[str]) -> Dict[str, Dict]:
        """Resolve player_keys to {name, positions, team}. Uses local cache first."""
        unknown = [k for k in keys if k not in self._pk_cache]
        if not unknown:
            return {k: self._pk_cache[k] for k in keys}

        for i in range(0, len(unknown), 25):
            batch = unknown[i : i + 25]
            if i > 0:
                time.sleep(0.4)  # brief pause between batches to avoid rate limiting
            data  = self._get(f"{YAHOO_BASE}/players;player_keys={','.join(batch)};out=metadata?")
            if not data:
                print(f"{C.YELLOW}  resolve_player_keys: no data for batch {i//25 + 1}{C.RESET}")
                continue
            try:
                players_raw = data.get("players", {})
                for pk, pv in players_raw.items():
                    if pk == "count":
                        continue
                    player_arr = pv.get("player", [[]])[0]
                    info: Dict = {}
                    for prop in player_arr:
                        if not isinstance(prop, dict):
                            continue
                        if "player_key" in prop:
                            info["player_key"] = prop["player_key"]
                        if "name" in prop:
                            info["name"] = prop["name"].get("full", "")
                        if "display_position" in prop:
                            info["positions"] = [p.strip() for p in prop["display_position"].split(",")]
                        if "editorial_team_abbr" in prop:
                            info["team"] = prop["editorial_team_abbr"]
                    if "player_key" in info:
                        self._pk_cache[info["player_key"]] = info
            except Exception as e:
                print(f"{C.RED}  resolve_player_keys parse error batch {i//25 + 1}: {e}{C.RESET}")
                continue

        self._save_pk_cache()
        return {k: self._pk_cache.get(k, {"name": f"(unknown {k})", "positions": []}) for k in keys}


# ─── Draft Board ──────────────────────────────────────────────────────────────

class DraftBoard:
    """Tracks available players and makes pick recommendations."""

    def __init__(self, all_players: List[Dict]):
        self.all_players  = sorted(all_players, key=lambda x: x["adp"])
        self.drafted_norm: Set[str] = set()  # normalized names of drafted players
        self.picks_made   = 0                # total picks across all teams
        self.my_picks     = calc_my_picks()
        self.my_roster    = list(MY_KEEPERS) # start with keepers

        # Initialize normalized lists for fast lookup
        self.my_guys_norm = {norm_name(n) for n in MY_GUYS}
        self.dnd_norm = {norm_name(n) for n in DND}
        self.breakouts_norm = {norm_name(n) for n in STATCAST_BREAKOUTS}
        self.spring_risers_norm = {norm_name(n) for n in SPRING_RISERS}
        self.speed_norm = {norm_name(n) for n in ELITE_SPEED}
        self.closers_norm = {norm_name(n) for n in ELITE_CLOSERS}
        self.setup_norm = {norm_name(n) for n in ELITE_SETUP_MEN}
        self.gb_sps_norm = {norm_name(n) for n in GROUNDBALL_SPS}
        self.prospects_norm = {norm_name(n) for n in PROSPECT_STASHES}
        self.ops_norm = {norm_name(n) for n in OPS_MONSTERS}

        # Pre-mark ALL league keepers (including other teams') as off the board.
        # This shifts the effective available pool — Skenes, Raleigh, Ketel Marte,
        # Elly De La Cruz, George Kirby etc. are all gone before pick 1.
        for name in LEAGUE_KEEPERS_ALL:
            self.drafted_norm.add(norm_name(name))

    # ── Drafting ──────────────────────────────────────────────────────────────

    def mark_drafted_by_name(self, name: str):
        self.drafted_norm.add(norm_name(name))

    def fuzzy_find(self, name: str) -> Optional[Dict]:
        """Find the closest ADP player entry for a given name."""
        norm = norm_name(name)
        # Exact
        for p in self.all_players:
            if norm_name(p["name"]) == norm:
                return p
        # Fuzzy
        from fuzzywuzzy import process
        names = [p["name"] for p in self.all_players]
        match = process.extractOne(name, names, score_cutoff=80)
        if match:
            matched_name = match[0]
            return next((p for p in self.all_players if p["name"] == matched_name), None)
        return None

    def apply_picks(self, picks: List[Dict], resolved: Dict[str, Dict]):
        """Update board from a list of Yahoo pick dicts with resolved names."""
        self.picks_made = len(picks)
        for pick in picks:
            info = resolved.get(pick["player_key"], {})
            name = info.get("name", "")
            if name:
                self.mark_drafted_by_name(name)

    # ── Available / needs ─────────────────────────────────────────────────────

    def available(self) -> List[Dict]:
        return [p for p in self.all_players if norm_name(p["name"]) not in self.drafted_norm]

    def remaining_needs(self) -> Dict[str, int]:
        # ROSTER_NEEDS already accounts for the 3 keepers (Crochet/Miller/Neto
        # are pre-subtracted from SP/RP/SS). Only subtract picks added during
        # the draft (non-keeper entries in my_roster).
        needs = dict(ROSTER_NEEDS)
        keeper_names = {norm_name(k["name"]) for k in MY_KEEPERS}
        for player in self.my_roster:
            if norm_name(player.get("name", "")) in keeper_names:
                continue  # already accounted for in ROSTER_NEEDS
            pos = player.get("position", "")
            for slot in self._slot_priority(pos):
                if needs.get(slot, 0) > 0:
                    needs[slot] -= 1
                    break
        return needs

    @staticmethod
    def _slot_priority(position: str) -> List[str]:
        p = position.upper()
        if p == "C":    return ["C",    "Util", "BN"]
        if p == "1B":   return ["1B",   "Util", "BN"]
        if p == "2B":   return ["2B",   "Util", "BN"]
        if p == "3B":   return ["3B",   "Util", "BN"]
        if p == "SS":   return ["SS",   "Util", "BN"]
        if p == "OF":   return ["OF",   "Util", "BN"]
        if p == "DH":   return ["Util", "BN"]
        if p == "SP":   return ["SP",   "P",    "BN"]
        if p == "RP":   return ["RP",   "P",    "BN"]
        return ["BN"]

    # ── Pick metadata ─────────────────────────────────────────────────────────

    @property
    def current_round(self) -> int:
        return (self.picks_made // TOTAL_TEAMS) + 1

    def next_my_pick(self) -> Optional[Dict]:
        for p in self.my_picks:
            if p["is_keeper"]:
                continue
            if p["overall"] and p["overall"] > self.picks_made:
                return p
        return None

    def picks_until_mine(self) -> int:
        nxt = self.next_my_pick()
        if not nxt:
            return 0
        return nxt["overall"] - self.picks_made

    def next_two_picks(self) -> List[Optional[Dict]]:
        """Return the next two draft pick slots for my team (for turn optimization)."""
        picks = []
        for p in self.my_picks:
            if p["is_keeper"]:
                continue
            if p["overall"] and p["overall"] > self.picks_made:
                picks.append(p)
            if len(picks) == 2:
                break
        return picks

    # ── Dynamic scarcity ─────────────────────────────────────────────────────

    # Expected number of draftable players per position in a 12-team league
    # Based on typical ADP depth charts (players with meaningful draft value)
    _POSITION_POOL = {"C": 16, "SS": 22, "2B": 24, "3B": 24, "1B": 28, "OF": 80,
                      "SP": 90, "RP": 40}

    def _scarcity_bonus(self, position: str) -> float:
        """
        Dynamic positional scarcity bonus. Increases as the available pool
        depletes — so if 10 of 16 viable catchers are gone, C urgency spikes.
        Returns a bonus score (0–120) to add to the player's base score.
        """
        avail        = self.available()
        pool_size    = self._POSITION_POOL.get(position, 30)
        remaining    = sum(1 for p in avail if position in p.get("positions", []))
        depletion    = max(0.0, 1.0 - (remaining / pool_size))
        # Scale 0→120 with a curve that accelerates past 50% depletion
        raw          = depletion ** 1.4 * 120
        return round(raw, 1)

    # ── Recommendations ───────────────────────────────────────────────────────

    def tier_breaks(self, players: List[Dict], top_n: int = 12) -> List[int]:
        """Return indices in the top_n list where a significant ADP gap begins."""
        subset = players[:top_n]
        breaks = []
        for i in range(1, len(subset)):
            gap = subset[i]["adp"] - subset[i - 1]["adp"]
            if gap >= 18:   # ~1.5 rounds worth of gap = meaningful tier cliff
                breaks.append(i)
        return breaks

    def recommend_turn(self) -> Optional[Dict]:
        """
        When you're 1–4 picks from the turn (picks 11+14), project what will
        still be available at your second pick and suggest the optimal pair.
        Returns a dict with pick1 and pick2 suggestions, or None if not near turn.
        """
        slots = self.next_two_picks()
        if len(slots) < 2:
            return None
        picks_away = slots[0]["overall"] - self.picks_made
        if picks_away > 4:
            return None

        # How many picks happen between slot 1 and slot 2?
        gap = slots[1]["overall"] - slots[0]["overall"] - 1  # picks between yours

        top = self.recommend(40)   # broad pool to work from
        batters = [p for p in top if any(pos in p.get("positions", [])
                                         for pos in ("C","1B","2B","3B","SS","OF","DH"))
                   and "pitcher" not in p.get("_reason", "")]

        if len(batters) < gap + 2:
            return None

        pick1 = batters[0]
        # Simulate gap picks taking the next best players, then pick the best remaining
        simulated_gone = {self._norm(p["name"]) for p in batters[1 : gap + 1]}
        pick2_candidates = [p for p in batters[1:] if self._norm(p["name"]) not in simulated_gone]
        if not pick2_candidates:
            return None
        pick2 = pick2_candidates[0]

        return {
            "pick1_overall": slots[0]["overall"],
            "pick2_overall": slots[1]["overall"],
            "pick1": pick1,
            "pick2": pick2,
            "gap": gap,
        }

    @staticmethod
    def _norm(name: str) -> str:
        return norm_name(name)

    def recommend(self, n: int = 15) -> List[Dict]:
        avail = self.available()
        rnd   = self.current_round
        needs = self.remaining_needs()

        # Calculate next pick for "Will He Be There?" indicator
        slots = self.next_two_picks()
        next_pick_overall = slots[1]["overall"] if len(slots) > 1 else None

        scored = []
        for p in avail:
            positions = p.get("positions", [])
            adp       = p["adp"]
            norm      = self._norm(p["name"])

            is_bat = any(pos in positions for pos in ("C", "1B", "2B", "3B", "SS", "OF", "DH"))
            is_sp  = "SP" in positions
            is_rp  = "RP" in positions

            # ADP value score — lower ADP = better value
            score  = max(0, 350 - adp)
            reason = ""
            tags   = []

            # 1. My Guys & DND
            if norm in self.dnd_norm:
                score -= 500
                tags.append("❌ DND")
            elif norm in self.my_guys_norm:
                score += 50
                tags.append("🎯 MY GUY")

            # 2. Statcast Breakouts & Spring Risers
            if norm in self.breakouts_norm:
                score += 20
                tags.append("🔥 Statcast Breakout")
            if norm in self.spring_risers_norm:
                score += 25
                tags.append("📈 Spring Riser")

            # 3. Elite Speed & Multi-Position (Swiss Army Knife)
            if norm in self.speed_norm:
                score += 15
                tags.append("🏃‍♂️ Elite Speed")
            
            # Count distinct fielding positions (ignore Util/DH/P)
            fielding_pos = [pos for pos in positions if pos not in ("Util", "DH", "P")]
            if len(fielding_pos) >= 3:
                score += 25  # Boosted for 4-move limit
                tags.append("🪖 Swiss Army Knife")

            # 4. Pitching Strategy (Groundball SPs & Closers)
            if is_sp and norm in self.gb_sps_norm:
                score += 30
                tags.append("🎳 Groundball SP (HR Allowed Buffer)")

            if is_rp and not is_sp:
                if norm in self.closers_norm:
                    pass  # Elite closer, handled below
                elif norm in self.setup_norm:
                    score += 10
                    tags.append("🛡️ Elite Ratio Reliever")
                else:
                    score -= 150
                    tags.append("⚠️ Middle Reliever")

            # 5. Prospect Stashes (Only boost in late rounds)
            if norm in self.prospects_norm:
                if rnd >= 20:
                    score += 60
                    tags.append("🌱 Prospect Stash")
                else:
                    # Don't draft them too early
                    score -= 50
                    tags.append("🌱 Prospect (Wait for late rounds)")

            # 6. OPS Monsters (Format Boost)
            if norm in self.ops_norm:
                score += 20
                tags.append("💪 Elite OPS (Format Boost)")

            # 7. "Will He Be There?" Indicator
            if next_pick_overall and adp < next_pick_overall - 2:
                tags.append("🚨 Draft Now or Lose Him")

            # Yahoo value bonus: positive discount means Yahoo drafters are sleeping
            # on this player relative to expert consensus — genuine value for us.
            # Thresholds are intentionally conservative to avoid noise.
            yahoo_discount = p.get("yahoo_discount", 0.0)
            if yahoo_discount >= 40:
                score += 35
                tags.append(f"Yahoo sleeper +{yahoo_discount:.0f}")
            elif yahoo_discount >= 20:
                score += 15
                tags.append(f"Yahoo +{yahoo_discount:.0f}")

            # Expert rank vs ADP divergence.
            # expert_rank_gap = adp - expert_rank
            #   Large negative → market drafting way ahead of experts (overrated/risky)
            #   Large positive → market sleeping vs expert opinion (undervalued)
            expert_rank_gap = p.get("expert_rank_gap", 0.0)
            expert_rank     = p.get("expert_rank")
            if expert_rank is not None:
                if expert_rank_gap <= -60:
                    score -= 40
                    tags.append(f"⚠️ Experts rank #{expert_rank} (overdrafted -{abs(expert_rank_gap):.0f})")
                elif expert_rank_gap <= -30:
                    score -= 15
                    tags.append(f"⚠️ Experts rank #{expert_rank} (-{abs(expert_rank_gap):.0f})")
                elif expert_rank_gap >= 60:
                    score += 30
                    tags.append(f"📊 Expert sleeper #{expert_rank} (+{expert_rank_gap:.0f})")
                elif expert_rank_gap >= 30:
                    score += 12
                    tags.append(f"📊 Expert value #{expert_rank} (+{expert_rank_gap:.0f})")

            if rnd in BATTER_ROUNDS:
                if not is_bat:
                    score -= 300  # strongly deprioritize pitchers
                    reason = "pitcher — wait"
                else:
                    # Dynamic scarcity: replaces fixed BAT_SCARCITY order
                    best_pos_bonus = -1.0   # -1 so any non-negative bonus wins
                    best_pos       = ""
                    for pos in positions:
                        if pos in BAT_SCARCITY and needs.get(pos, 0) > 0:
                            bonus = self._scarcity_bonus(pos)
                            if bonus > best_pos_bonus:
                                best_pos_bonus = bonus
                                best_pos       = pos
                    if best_pos:
                        score += best_pos_bonus
                        reason = f"fills {best_pos} need (scarce)"
                    if not reason:
                        if needs.get("Util", 0) > 0:
                            score += 10; reason = "Util slot"
                        elif needs.get("BN", 0) > 0:
                            score += 5;  reason = "bench depth"
                        else:
                            reason = "ADP value"

            elif rnd in SP_TARGET_ROUNDS:
                sp_needed = needs.get("SP", 0)
                if is_sp and sp_needed > 0:
                    score += 90; reason = "target SP — K strikeout upside"
                elif is_bat and sum(needs.get(p2, 0) for p2 in ("C", "1B", "2B", "3B", "OF", "Util")) > 0:
                    score += 40; reason = "bat depth"
                elif is_sp and sp_needed == 0:
                    score += 20; reason = "SP bench"

            else:  # Closer/late rounds
                if is_rp and needs.get("RP", 0) > 0:
                    score += 120; reason = "closer — HR/ERA/WHIP/SV"
                elif is_rp and needs.get("P", 0) > 0:
                    score += 100; reason = "RP flex — HR/ERA/WHIP/SV"
                elif is_rp and needs.get("BN", 0) > 0:
                    score += 70;  reason = "RP bench — HR/ERA/WHIP depth"
                elif is_sp and needs.get("SP", 0) > 0:
                    score += 50;  reason = "SP depth — K upside"
                elif is_bat:
                    score += 20;  reason = "bat depth"

            # Combine reason and tags
            final_reason = reason or "value"
            if tags:
                final_reason += " · " + " · ".join(tags)

            scored.append({**p, "_score": score, "_reason": final_reason})

        scored.sort(key=lambda x: (-x["_score"], x["adp"]))
        return scored[:n]


# ─── Display ──────────────────────────────────────────────────────────────────

def display_keepers():
    print(f"\n{C.BOLD}  Your Keepers:{C.RESET}")
    for k in MY_KEEPERS:
        pc = pos_color(k["position"])
        surplus = 288 - k["adp"] - (k["round"] * 12)  # rough surplus
        print(f"    {pc}{k['position']:3}{C.RESET}  {C.BOLD}{k['name']:<24}{C.RESET}  "
              f"ADP {k['adp']:>3}  →  Round {k['round']}  "
              f"{C.GREEN}(kept {k['round']*12 - k['adp']:+} picks early){C.RESET}")


def display_my_picks(board: DraftBoard):
    nxt   = board.next_my_pick()
    until = board.picks_until_mine()
    rnd   = board.current_round

    if nxt is None:
        print(f"\n{C.DIM}  All picks complete.{C.RESET}")
        return

    color = C.GREEN if until <= 2 else (C.YELLOW if until <= 6 else C.WHITE)
    print(f"\n{C.BOLD}  Draft Status:{C.RESET}  "
          f"Round {C.BOLD}{rnd}{C.RESET}  |  "
          f"Pick {C.BOLD}{board.picks_made}{C.RESET}/{TOTAL_TEAMS * TOTAL_ROUNDS} made  |  "
          f"Your next: {color}Round {nxt['round']}, overall #{nxt['overall']}{C.RESET}  "
          f"({color}{until} picks away{C.RESET})")


def display_recommendations(board: DraftBoard, n: int = 15):
    recs  = board.recommend(n)
    rnd   = board.current_round
    needs = board.remaining_needs()

    # Label the round strategy
    if rnd in BATTER_ROUNDS:
        strategy_label = f"{C.GREEN}BATTER PRIORITY — load up, ignore pitchers{C.RESET}"
    elif rnd in SP_TARGET_ROUNDS:
        strategy_label = f"{C.YELLOW}SP WINDOW — grab 1–2 starters for K strikeouts only{C.RESET}"
    else:
        strategy_label = f"{C.MAGENTA}CLOSER MODE — stack HR/ERA/WHIP/SV dominance{C.RESET}"

    print(f"\n  Strategy this round: {strategy_label}")

    open_needs = {k: v for k, v in needs.items() if v > 0}
    needs_str  = "  ".join(f"{C.CYAN}{slot}×{cnt}{C.RESET}" for slot, cnt in open_needs.items())
    print(f"  Open slots: {needs_str}\n")

    print(f"  {'#':<3}  {'ADP':>4}  {'Tier':<8}  {'Pos':<12}  {'Player':<24}  {'Team':<5}  Strategy Note")
    print(f"  {'─'*3}  {'─'*4}  {'─'*8}  {'─'*12}  {'─'*24}  {'─'*5}  {'─'*30}")

    for i, p in enumerate(recs, 1):
        positions = ", ".join(p.get("positions", []))
        tier      = get_tier(p["adp"])
        pos_str   = positions[:12]
        pc        = pos_color(p.get("positions", [""])[0] if p.get("positions") else "")

        # Highlight if it's very close to your pick
        until = board.picks_until_mine()
        if i <= 3 and until <= 3:
            row_c = C.BOLD + C.GREEN
        elif p["_score"] < 0:
            row_c = C.DIM
        else:
            row_c = C.RESET

        reason = p.get("_reason", "")
        if "pitcher — wait" in reason:
            reason_c = C.DIM + C.RED
        elif "closer" in reason or "ERA" in reason or "Ratio" in reason:
            reason_c = C.MAGENTA
        elif "SP window" in reason or "K/W" in reason or "Riser" in reason or "Groundball" in reason:
            reason_c = C.YELLOW
        elif "fills" in reason or "need" in reason or "Speed" in reason or "Swiss" in reason or "Prospect" in reason or "OPS" in reason:
            reason_c = C.GREEN
        else:
            reason_c = C.DIM

        print(f"  {row_c}{i:<3}{C.RESET}  {p['adp']:>4.0f}  {tier:<8}  "
              f"{pc}{pos_str:<12}{C.RESET}  {row_c}{p['name']:<24}{C.RESET}  "
              f"{p.get('team', ''):>5}  {reason_c}{reason}{C.RESET}")


def display_my_roster(board: DraftBoard):
    if not board.my_roster:
        return
    print(f"\n{C.BOLD}  Your Roster So Far:{C.RESET}")
    for p in board.my_roster:
        pc  = pos_color(p.get("position", ""))
        rnd = p.get("round", "K")
        adp = p.get("adp", "?")
        print(f"    {pc}{p.get('position','??'):3}{C.RESET}  "
              f"{C.BOLD}{p['name']:<24}{C.RESET}  ADP {adp!s:>4}  Round {rnd}")


def display_cheatsheet(board: DraftBoard):
    """Print a full pre-draft ranked cheat sheet by position."""
    avail = board.available()

    groups = {
        "CATCHERS (C)":      [p for p in avail if "C"  in p.get("positions", [])],
        "SHORTSTOPS (SS)":   [p for p in avail if "SS" in p.get("positions", [])],
        "SECOND BASE (2B)":  [p for p in avail if "2B" in p.get("positions", [])],
        "THIRD BASE (3B)":   [p for p in avail if "3B" in p.get("positions", [])],
        "FIRST BASE (1B)":   [p for p in avail if "1B" in p.get("positions", [])],
        "OUTFIELDERS (OF)":  [p for p in avail if "OF" in p.get("positions", [])],
        "STARTING PITCHERS": [p for p in avail if "SP" in p.get("positions", [])],
        "RELIEF PITCHERS":   [p for p in avail if "RP" in p.get("positions", []) and "SP" not in p.get("positions", [])],
    }

    print(f"\n{C.BOLD}{C.CYAN}{'═' * 80}")
    print(f"  DRAFT CHEAT SHEET — 2balls  |  Pick 7/12  |  2026 Season")
    print(f"  Hitting: R H HR RBI SB OPS  |  Pitching: HR K ERA WHIP SV QS")
    print(f"  Strategy: Batters R1–8 → SP window R10,13 → Closers R14–24")
    print(f"  Target: dominate HR/ERA/WHIP/SV (4 of 6 pitching cats) every week")
    print(f"{'═' * 80}{C.RESET}")
    display_keepers()
    print()

    my_picks = calc_my_picks()
    non_keeper = [p for p in my_picks if not p["is_keeper"]]
    print(f"  {C.BOLD}Your pick slots:{C.RESET}")
    for p in non_keeper[:12]:
        print(f"    Round {p['round']:>2}  →  Overall #{p['overall']}")

    for group_name, players in groups.items():
        players = sorted(players, key=lambda x: x["adp"])[:20]
        if not players:
            continue
        print(f"\n{C.BOLD}{C.YELLOW}  {group_name}{C.RESET}")
        print(f"  {'ADP':>4}  {'Tier':<8}  {'Pos':<14}  {'Player':<26}  Team")
        print(f"  {'─'*4}  {'─'*8}  {'─'*14}  {'─'*26}  {'─'*4}")
        for p in players:
            pos_str = ", ".join(p.get("positions", []))[:14]
            pc      = pos_color(p.get("positions", [""])[0] if p.get("positions") else "")
            tier    = get_tier(p["adp"])
            print(f"  {p['adp']:>4.0f}  {tier:<8}  {pc}{pos_str:<14}{C.RESET}  "
                  f"{p['name']:<26}  {p.get('team', ''):>4}")


# ─── Modes ────────────────────────────────────────────────────────────────────

def run_offline_mode(board: DraftBoard):
    """Manual pick-entry loop. Type a name to mark as drafted."""
    print(header("OFFLINE MODE — Type player names as they're drafted, or 'rec' for recs"))
    print(f"  Commands: {C.BOLD}rec{C.RESET} = recommendations  |  "
          f"{C.BOLD}board{C.RESET} = show remaining  |  "
          f"{C.BOLD}mine <name>{C.RESET} = add to my roster  |  "
          f"{C.BOLD}q{C.RESET} = quit\n")

    display_keepers()

    while True:
        try:
            picks_left = board.picks_until_mine()
            prompt_color = C.GREEN if picks_left <= 2 else C.WHITE
            inp = input(f"\n{prompt_color}Pick #{board.picks_made + 1}> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting draft assistant. Good luck!")
            break

        if not inp:
            continue

        cmd = inp.lower()

        if cmd in ("q", "quit", "exit"):
            print("\n  Exiting draft assistant. Good luck!")
            break

        if cmd in ("rec", "r", "recs", "recommend"):
            display_my_picks(board)
            display_recommendations(board)
            continue

        if cmd in ("board", "b", "available"):
            display_recommendations(board, n=25)
            continue

        if cmd in ("roster", "mine"):
            display_my_roster(board)
            continue

        if cmd.startswith("mine "):
            player_name = inp[5:].strip()
            player      = board.fuzzy_find(player_name)
            if player:
                board.my_roster.append({
                    "name":     player["name"],
                    "position": player["positions"][0] if player.get("positions") else "?",
                    "round":    board.current_round,
                    "adp":      player["adp"],
                })
                board.mark_drafted_by_name(player["name"])
                board.picks_made += 1
                print(f"  {C.GREEN}Added to your roster: {player['name']} "
                      f"({', '.join(player.get('positions', []))}){C.RESET}")
            else:
                print(f"  {C.RED}Player not found: {player_name}{C.RESET}")
            continue

        # Treat as a drafted player name
        player = board.fuzzy_find(inp)
        if player:
            board.mark_drafted_by_name(player["name"])
            board.picks_made += 1
            print(f"  {C.DIM}Drafted: {player['name']} "
                  f"({', '.join(player.get('positions', []))}  ADP {player['adp']:.0f}){C.RESET}")
        else:
            print(f"  {C.YELLOW}Not found in ADP data: '{inp}' — marked as drafted anyway{C.RESET}")
            board.mark_drafted_by_name(inp)
            board.picks_made += 1

        # Show recs automatically when your pick is close
        if board.picks_until_mine() <= 4:
            print(f"\n  {C.BOLD}{C.GREEN}>>> YOUR PICK COMING UP — {board.picks_until_mine()} picks away! <<<{C.RESET}")
            display_my_picks(board)
            display_recommendations(board, n=8)


def run_live_mode(board: DraftBoard, yahoo: YahooDraft):
    """Poll Yahoo every 30s and auto-update the board."""
    print(header("LIVE MODE — Polling Yahoo every 30 seconds"))
    display_keepers()

    league_key = yahoo.find_league_key()
    if not league_key:
        print(f"{C.RED}  Could not find league key. Falling back to offline mode.{C.RESET}")
        run_offline_mode(board)
        return

    last_pick_count = -1
    print(f"\n  {C.DIM}Waiting for draft to start...  (Ctrl+C to exit){C.RESET}\n")

    try:
        while True:
            picks = yahoo.fetch_picks()
            if not picks and last_pick_count == -1:
                print(f"  {C.DIM}Draft not started yet. Retrying in 30s...{C.RESET}")
                time.sleep(30)
                continue

            if len(picks) == last_pick_count:
                # Nothing new — quiet wait
                until = board.picks_until_mine()
                if until <= 3:
                    print(f"  {C.YELLOW}Your pick in {until}... waiting...{C.RESET}", end="\r")
                time.sleep(30)
                continue

            # Resolve any new player keys
            all_keys = [p["player_key"] for p in picks if p.get("player_key")]
            resolved = yahoo.resolve_player_keys(all_keys)

            # Find new picks since last refresh
            new_picks = picks[last_pick_count:] if last_pick_count >= 0 else picks
            board.apply_picks(picks, resolved)
            last_pick_count = len(picks)

            # Print new picks
            print(f"\n  {C.DIM}──── {datetime.now().strftime('%H:%M:%S')} ────{C.RESET}")
            for pick in new_picks:
                info     = resolved.get(pick["player_key"], {})
                name     = info.get("name", pick["player_key"])
                pos      = ", ".join(info.get("positions", []))
                pc       = pos_color(info.get("positions", [""])[0] if info.get("positions") else "")
                is_mine  = pick["overall"] in {
                    p["overall"] for p in board.my_picks
                    if not p["is_keeper"] and p["overall"] is not None
                }
                marker = f" {C.GREEN}← YOU{C.RESET}" if is_mine else ""
                print(f"  Pick {pick['overall']:>3}  Rd {pick['round']:>2}  "
                      f"{pc}{pos:<8}{C.RESET}  {name:<28}{marker}")

                if is_mine:
                    board.my_roster.append({
                        "name":     name,
                        "position": info.get("positions", ["?"])[0],
                        "round":    pick["round"],
                        "adp":      next(
                            (p["adp"] for p in board.all_players
                             if norm_name(p["name"]) == norm_name(name)), "?"
                        ),
                    })

            display_my_picks(board)
            until = board.picks_until_mine()
            if until <= 5:
                print(f"\n  {C.BOLD}{C.GREEN}>>> {until} PICKS UNTIL YOURS — RECOMMENDATIONS:{C.RESET}")
                display_recommendations(board, n=10)

            time.sleep(30)

    except KeyboardInterrupt:
        print(f"\n\n  {C.CYAN}Draft monitor stopped. Good luck!{C.RESET}")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Draft Day Assistant — 2balls 2026")
    parser.add_argument("--cheatsheet", action="store_true", help="Print cheat sheet and exit")
    parser.add_argument("--offline",    action="store_true", help="Manual pick entry (no Yahoo API)")
    parser.add_argument("--refresh",    action="store_true", help="Force refresh ADP cache")
    args = parser.parse_args()

    print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}")
    print(f"  2balls Draft Assistant — California Palm League 2026")
    print(f"  Draft position: 7 of 12  |  Snake  |  24 rounds")
    print(f"{'═' * 60}{C.RESET}")

    if args.refresh and ADP_CACHE.exists():
        ADP_CACHE.unlink()
        print(f"  {C.YELLOW}ADP cache cleared.{C.RESET}")

    print(f"\n  Loading player rankings...")
    scraper = FPScraper()
    players = scraper.fetch()

    if not players:
        print(f"  {C.RED}No ADP data available. Check your connection.{C.RESET}")
        sys.exit(1)

    board = DraftBoard(players)

    if args.cheatsheet:
        display_cheatsheet(board)
        return

    if args.offline:
        run_offline_mode(board)
        return

    # Live mode — try Yahoo, fall back to offline
    print(f"\n  Connecting to Yahoo Fantasy API...")
    try:
        yahoo = YahooDraft()
        run_live_mode(board, yahoo)
    except FileNotFoundError:
        print(f"  {C.RED}Yahoo OAuth config not found at {OAUTH_CONFIG}{C.RESET}")
        print(f"  {C.YELLOW}Falling back to offline mode.{C.RESET}")
        run_offline_mode(board)
    except Exception as e:
        print(f"  {C.RED}Yahoo connection failed: {e}{C.RESET}")
        print(f"  {C.YELLOW}Falling back to offline mode.{C.RESET}")
        run_offline_mode(board)


if __name__ == "__main__":
    main()
