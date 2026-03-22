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
MY_DRAFT_POSITION = 11
TOTAL_TEAMS       = 12
TOTAL_ROUNDS      = 24
SEASON            = 2026
MY_KEEPER_ROUNDS  = {9, 10, 11}

MY_KEEPERS = [
    {"name": "Garrett Crochet", "position": "SP", "round": 9,  "adp": 11},
    {"name": "Mason Miller",    "position": "RP", "round": 10, "adp": 55},
    {"name": "Zach Neto",       "position": "SS", "round": 11, "adp": 36},
]

# Remaining roster slots to fill via the draft (keepers subtract from these)
ROSTER_NEEDS = {
    "C":    1,
    "1B":   1,
    "2B":   1,
    "3B":   1,
    "SS":   0,   # Neto
    "OF":   3,
    "Util": 2,
    "SP":   5,   # 6 slots − Crochet
    "RP":   2,   # 3 slots − Miller
    "P":    1,   # Pitcher flex slot
    "BN":   4,
}

# Strategy windows
# Pitching cats: HR allowed, K, ERA, WHIP, SV, QS
# Relievers dominate HR, ERA, WHIP, SV — 4 of 6 very winnable
# Only need 1–2 SPs for K counting stats (punting QS entirely)
BATTER_ROUNDS    = set(range(1, 9))    # Rounds 1–8: batters only
SP_TARGET_ROUNDS = {12, 13}            # 1–2 K-upside SPs (no W category to chase)
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

        # Table columns: rank | player | yahoo_adp | cbs | rts | nfbc | ft | avg_adp
        # We capture both yahoo_adp and avg_adp to compute the value discount.
        # A positive yahoo_discount means Yahoo drafters are sleeping on this player
        # relative to the broader expert consensus — a real value signal.

        # Parse all rows, then deduplicate (keep best ADP per player)
        seen: Dict[str, Dict] = {}  # normalized_name -> player dict

        for row in soup.select("table tbody tr"):
            cells = row.find_all("td")
            for i in range(0, len(cells), 8):
                if i + 7 >= len(cells):
                    break
                player_text = cells[i + 1].get_text(strip=True)
                yahoo_text  = cells[i + 2].get_text(strip=True)
                avg_text    = cells[i + 7].get_text(strip=True)

                m = re.match(r"^(.+?)\s*\(([A-Z]{2,3}(?:/[A-Z]{2,3})?)\s*-\s*([^)]+)\)", player_text)
                if not m:
                    continue
                name      = m.group(1).strip()
                team      = m.group(2).strip()
                raw_positions = [p.strip() for p in m.group(3).split(",")]

                # Normalize positions to fantasy slots
                positions = self._normalize_positions(raw_positions)

                try:
                    adp = float(avg_text)
                except ValueError:
                    continue

                # Yahoo-specific ADP — if Yahoo drafters sleep on this player
                # relative to expert consensus, it's a value opportunity.
                # Positive yahoo_discount = Yahoo drafts LATER than consensus = undervalued on Yahoo
                _yahoo_adp = adp  # default: no platform difference
                _yahoo_discount = 0.0
                try:
                    _yahoo_adp = float(yahoo_text)
                    # yahoo_adp > adp means Yahoo drafts later → undervalued here
                    _yahoo_discount = round(_yahoo_adp - adp, 1)
                except ValueError:
                    pass

                key = norm_name(name)
                if key not in seen or adp < seen[key]["adp"]:
                    seen[key] = {
                        "name":           name,
                        "team":           team,
                        "positions":      positions,
                        "adp":            adp,
                        "yahoo_adp":      _yahoo_adp,
                        "yahoo_discount": _yahoo_discount,
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
        """Return all picks made so far, sorted by overall pick number."""
        if not self.league_key:
            return []
        data = self._get(f"{YAHOO_BASE}/league/{self.league_key}/draftresults?")
        if not data:
            return []
        try:
            dr = data["league"][1]["draft_results"]
            picks = []
            for k, v in dr.items():
                if k == "count":
                    continue
                d = v.get("draft_result", {})
                picks.append({
                    "overall":    int(d.get("pick", 0)),
                    "round":      int(d.get("round", 0)),
                    "team_key":   d.get("team_key", ""),
                    "player_key": d.get("player_key", ""),
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

    def resolve_player_keys(self, keys: List[str]) -> Dict[str, Dict]:
        """Resolve player_keys to {name, positions, team}. Uses local cache first."""
        unknown = [k for k in keys if k not in self._pk_cache]
        if not unknown:
            return {k: self._pk_cache[k] for k in keys}

        for i in range(0, len(unknown), 25):
            batch = unknown[i : i + 25]
            data  = self._get(f"{YAHOO_BASE}/players;player_keys={','.join(batch)};out=metadata?")
            if not data:
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
            except Exception:
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

        # Pre-mark my own keepers
        for k in MY_KEEPERS:
            self.drafted_norm.add(norm_name(k["name"]))

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

    # ── Recommendations ───────────────────────────────────────────────────────

    def recommend(self, n: int = 15) -> List[Dict]:
        avail = self.available()
        rnd   = self.current_round
        needs = self.remaining_needs()

        scored = []
        for p in avail:
            positions = p.get("positions", [])
            adp       = p["adp"]

            is_bat = any(pos in positions for pos in ("C", "1B", "2B", "3B", "SS", "OF", "DH"))
            is_sp  = "SP" in positions
            is_rp  = "RP" in positions

            # ADP value score — lower ADP = better value
            score  = max(0, 350 - adp)
            reason = ""

            # Yahoo value bonus: positive discount means Yahoo drafters are sleeping
            # on this player relative to expert consensus — genuine value for us.
            # Thresholds are intentionally conservative to avoid noise.
            yahoo_discount = p.get("yahoo_discount", 0.0)
            if yahoo_discount >= 40:
                score += 35
                value_tag = f" · Yahoo sleeper +{yahoo_discount:.0f}"
            elif yahoo_discount >= 20:
                score += 15
                value_tag = f" · Yahoo +{yahoo_discount:.0f}"
            else:
                value_tag = ""

            if rnd in BATTER_ROUNDS:
                if not is_bat:
                    score -= 300  # strongly deprioritize pitchers
                    reason = "pitcher — wait"
                else:
                    for pos in BAT_SCARCITY:
                        if pos in positions and needs.get(pos, 0) > 0:
                            score += (len(BAT_SCARCITY) - BAT_SCARCITY.index(pos)) * 20
                            reason = f"fills {pos} need (scarce)"
                            break
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

            scored.append({**p, "_score": score, "_reason": (reason or "value") + value_tag})

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
        elif "closer" in reason or "ERA" in reason:
            reason_c = C.MAGENTA
        elif "SP window" in reason or "K/W" in reason:
            reason_c = C.YELLOW
        elif "fills" in reason or "need" in reason:
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
    print(f"  DRAFT CHEAT SHEET — 2balls  |  Pick 11/12  |  2026 Season")
    print(f"  Hitting: R H HR RBI SB OPS  |  Pitching: HR K ERA WHIP SV QS")
    print(f"  Strategy: Batters R1–8 → 1–2 K-SP R12–13 → Closers R14–24")
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
    print(f"  Draft position: 11 of 12  |  Snake  |  24 rounds")
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
    from datetime import datetime
    main()
