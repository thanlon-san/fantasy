#!/usr/bin/env python3
"""
Draft Day API Server
Exposes the draft board state as a REST API for the web frontend.

Usage:
    python draft_server.py          # Start on port 8001
    python draft_server.py --port 8002
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# ─── Path setup ───────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
APP_ROOT    = SCRIPTS_DIR.parent
WORKSPACE   = APP_ROOT.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))   # import draft_assistant
sys.path.insert(0, str(APP_ROOT))      # import src.*
sys.path.insert(0, str(WORKSPACE / "packages"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from draft_assistant import (
    FPScraper, YahooDraft, DraftBoard,
    MY_KEEPERS, MY_DRAFT_POSITION, TOTAL_TEAMS, TOTAL_ROUNDS,
    BATTER_ROUNDS, SP_TARGET_ROUNDS, CLOSER_ROUNDS,
    LEAGUE_KEY, OAUTH_CONFIG,
    get_tier, calc_my_picks, norm_name,
)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Draft Day API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Server state (module-level, lives for duration of process) ───────────────
_board:      Optional[DraftBoard] = None
_yahoo:      Optional[YahooDraft] = None
_all_picks:  List[dict] = []          # cached Yahoo picks
_last_poll:  float = 0.0              # epoch time of last Yahoo poll
_error:      Optional[str] = None

YAHOO_POLL_INTERVAL = 25              # seconds between Yahoo API calls
MY_TEAM_ID          = 2               # 2balls = team 2 in California Palm League
MY_TEAM_KEY         = f"{LEAGUE_KEY}.t.{MY_TEAM_ID}"


# ─── Startup ──────────────────────────────────────────────────────────────────

def init():
    global _board, _yahoo, _error

    print("  Loading FantasyPros ADP...")
    try:
        players = FPScraper().fetch()
        if not players:
            _error = "Failed to load ADP data from FantasyPros."
            print(f"  ERROR: {_error}")
            return
        _board = DraftBoard(players)
        print(f"  Board ready: {len(players)} players loaded.")
    except Exception as e:
        _error = f"ADP load failed: {e}"
        print(f"  ERROR: {_error}")
        return

    print("  Connecting to Yahoo Fantasy API...")
    try:
        _yahoo = YahooDraft()
        print(f"  Yahoo connected — league {LEAGUE_KEY}")
    except Exception as e:
        _error = f"Yahoo connection failed: {e}"
        print(f"  WARNING: {_error} — live pick tracking disabled.")
        _yahoo = None


@app.on_event("startup")
def on_startup():
    init()


# ─── Yahoo polling ────────────────────────────────────────────────────────────

def maybe_sync_yahoo() -> List[dict]:
    """Poll Yahoo at most every YAHOO_POLL_INTERVAL seconds. Returns all picks."""
    global _all_picks, _last_poll

    if _yahoo is None:
        return _all_picks

    now = time.time()
    if now - _last_poll < YAHOO_POLL_INTERVAL:
        return _all_picks

    try:
        raw_picks = _yahoo.fetch_picks()
        if not raw_picks:
            _last_poll = now
            return _all_picks

        # Resolve any new player keys to names
        all_keys    = [p["player_key"] for p in raw_picks if p.get("player_key")]
        new_keys    = [k for k in all_keys if k not in _yahoo._pk_cache]
        if new_keys:
            _yahoo.resolve_player_keys(new_keys)

        # Rebuild picks list with names
        enriched = []
        for pick in raw_picks:
            info = _yahoo._pk_cache.get(pick["player_key"], {})
            enriched.append({
                "overall":   pick["overall"],
                "round":     pick["round"],
                "team_key":  pick["team_key"],
                "is_mine":   pick["team_key"] == MY_TEAM_KEY,
                "player_key": pick["player_key"],
                "name":      info.get("name", f"(unknown)"),
                "positions": info.get("positions", []),
                "team":      info.get("team", ""),
            })

        # Update board with any new picks
        if len(enriched) > len(_all_picks):
            _board.apply_picks(raw_picks, _yahoo._pk_cache)
            _board.picks_made = len(enriched)

            # Add my picks to my_roster
            my_pick_overalls = {
                p["overall"] for p in calc_my_picks()
                if not p["is_keeper"] and p["overall"] is not None
            }
            for pick in enriched:
                if pick["is_mine"]:
                    already = any(norm_name(r.get("name","")) == norm_name(pick["name"])
                                  for r in _board.my_roster)
                    if not already:
                        _board.my_roster.append({
                            "name":     pick["name"],
                            "position": pick["positions"][0] if pick["positions"] else "?",
                            "round":    pick["round"],
                            "adp":      next(
                                (p["adp"] for p in _board.all_players
                                 if norm_name(p["name"]) == norm_name(pick["name"])),
                                None
                            ),
                        })

        _all_picks = enriched
        _last_poll = now

    except Exception as e:
        print(f"  Yahoo poll error: {e}")

    return _all_picks


# ─── Response models ──────────────────────────────────────────────────────────

class PickInfo(BaseModel):
    overall:   int
    round:     int
    name:      str
    positions: List[str]
    team:      str
    is_mine:   bool

class Recommendation(BaseModel):
    rank:           int
    name:           str
    team:           str
    positions:      List[str]
    adp:            float
    tier:           str
    reason:         str
    yahoo_discount: float = 0.0

class RosterPlayer(BaseModel):
    name:     str
    position: str
    round:    Optional[int]
    adp:      Optional[float]
    is_keeper: bool = False

class NextPick(BaseModel):
    round:      int
    overall:    int
    picks_away: int

class TurnPick(BaseModel):
    overall:   int
    name:      str
    team:      str
    positions: List[str]
    adp:       float
    reason:    str

class TurnCombo(BaseModel):
    pick1_overall: int
    pick2_overall: int
    pick1:         TurnPick
    pick2:         TurnPick
    gap:           int

class TierBreak(BaseModel):
    before_index: int
    adp_gap:      float

class DraftState(BaseModel):
    status:        str          # predraft | live | complete
    picks_made:    int
    current_round: int
    phase:         str          # BATTER_PRIORITY | SP_WINDOW | CLOSER_MODE
    phase_label:   str
    my_next_pick:  Optional[NextPick]
    recommendations: List[Recommendation]
    tier_breaks:   List[TierBreak]
    turn_combo:    Optional[TurnCombo]
    my_roster:     List[RosterPlayer]
    recent_picks:  List[PickInfo]
    open_needs:    dict
    last_synced:   str
    error:         Optional[str]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def current_phase(round_num: int) -> tuple[str, str]:
    if round_num in BATTER_ROUNDS:
        return "BATTER_PRIORITY", "Batters only — ignore pitchers"
    if round_num in SP_TARGET_ROUNDS:
        return "SP_WINDOW", "Grab 1–2 SP for K strikeouts"
    return "CLOSER_MODE", "Stack closers — HR/ERA/WHIP/SV"


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/state", response_model=DraftState)
def get_state():
    if _board is None:
        raise HTTPException(status_code=503, detail=_error or "Board not initialized")

    picks = maybe_sync_yahoo()

    # Determine status
    if len(picks) == 0:
        status = "predraft"
    elif _board.picks_made >= TOTAL_TEAMS * TOTAL_ROUNDS:
        status = "complete"
    else:
        status = "live"

    rnd           = _board.current_round
    phase, label  = current_phase(rnd)
    nxt           = _board.next_my_pick()
    needs         = _board.remaining_needs()
    recs          = _board.recommend(15)
    tier_break_idxs = _board.tier_breaks(recs, top_n=12)
    turn_raw      = _board.recommend_turn()

    next_pick_info = None
    if nxt:
        next_pick_info = NextPick(
            round=nxt["round"],
            overall=nxt["overall"],
            picks_away=_board.picks_until_mine(),
        )

    recommendations = [
        Recommendation(
            rank=i + 1,
            name=r["name"],
            team=r.get("team", ""),
            positions=r.get("positions", []),
            adp=r["adp"],
            tier=get_tier(r["adp"]),
            reason=r.get("_reason", ""),
            yahoo_discount=r.get("yahoo_discount", 0.0),
        )
        for i, r in enumerate(recs)
    ]

    my_roster = [
        RosterPlayer(
            name=p.get("name", ""),
            position=p.get("position", "?"),
            round=p.get("round"),
            adp=p.get("adp") if isinstance(p.get("adp"), (int, float)) else None,
            is_keeper=any(norm_name(k["name"]) == norm_name(p.get("name",""))
                          for k in MY_KEEPERS),
        )
        for p in _board.my_roster
    ]

    recent_picks = [
        PickInfo(
            overall=p["overall"],
            round=p["round"],
            name=p["name"],
            positions=p["positions"],
            team=p["team"],
            is_mine=p["is_mine"],
        )
        for p in sorted(picks, key=lambda x: -x["overall"])[:20]
    ]

    open_needs = {k: v for k, v in needs.items() if v > 0}

    tier_breaks_out = [
        TierBreak(
            before_index=idx,
            adp_gap=recs[idx]["adp"] - recs[idx - 1]["adp"],
        )
        for idx in tier_break_idxs
    ]

    turn_combo = None
    if turn_raw:
        def _tp(p: dict, overall: int) -> TurnPick:
            return TurnPick(overall=overall, name=p["name"], team=p.get("team",""),
                            positions=p.get("positions",[]), adp=p["adp"],
                            reason=p.get("_reason",""))
        turn_combo = TurnCombo(
            pick1_overall=turn_raw["pick1_overall"],
            pick2_overall=turn_raw["pick2_overall"],
            pick1=_tp(turn_raw["pick1"], turn_raw["pick1_overall"]),
            pick2=_tp(turn_raw["pick2"], turn_raw["pick2_overall"]),
            gap=turn_raw["gap"],
        )

    return DraftState(
        status=status,
        picks_made=_board.picks_made,
        current_round=rnd,
        phase=phase,
        phase_label=label,
        my_next_pick=next_pick_info,
        recommendations=recommendations,
        tier_breaks=tier_breaks_out,
        turn_combo=turn_combo,
        my_roster=my_roster,
        recent_picks=recent_picks,
        open_needs=open_needs,
        last_synced=datetime.now().strftime("%H:%M:%S"),
        error=_error,
    )


class ManualPickBody(BaseModel):
    player_name: str
    is_mine:     bool = False


@app.post("/mark-pick")
def mark_pick(body: ManualPickBody):
    """Manually mark a player as drafted (fallback if Yahoo tracking lags)."""
    if _board is None:
        raise HTTPException(status_code=503, detail="Board not initialized")

    player = _board.fuzzy_find(body.player_name)
    if player:
        _board.mark_drafted_by_name(player["name"])
        _board.picks_made += 1
        if body.is_mine:
            _board.my_roster.append({
                "name":     player["name"],
                "position": player["positions"][0] if player.get("positions") else "?",
                "round":    _board.current_round,
                "adp":      player["adp"],
            })
        return {"ok": True, "matched": player["name"]}
    else:
        _board.mark_drafted_by_name(body.player_name)
        _board.picks_made += 1
        return {"ok": True, "matched": body.player_name, "warning": "not in ADP list"}


@app.post("/reset")
def reset():
    """Re-initialize the board (clear all tracked picks)."""
    global _board, _all_picks, _last_poll
    _all_picks = []
    _last_poll = 0.0
    init()
    return {"ok": True}


@app.get("/health")
def health():
    return {
        "ok":           _board is not None,
        "yahoo":        _yahoo is not None,
        "adp_loaded":   _board is not None and len(_board.all_players) > 0,
        "picks_cached": len(_all_picks),
    }


# ─── Season endpoints ─────────────────────────────────────────────────────────
#
# Stat ID map (confirmed from league settings API):
#   Batting:  R=7  H=8  HR=12  RBI=13  SB=16  OPS=55
#   Pitching: SV=32  HR_allowed=38  K=42  ERA=26  WHIP=27  QS=83
#   Display:  H/AB=60  IP=50

STAT_MAP = {
    "7":  {"name": "R",    "label": "Runs",          "group": "batting",  "better": "high"},
    "8":  {"name": "H",    "label": "Hits",           "group": "batting",  "better": "high"},
    "12": {"name": "HR",   "label": "Home Runs",      "group": "batting",  "better": "high"},
    "13": {"name": "RBI",  "label": "RBI",            "group": "batting",  "better": "high"},
    "16": {"name": "SB",   "label": "Stolen Bases",   "group": "batting",  "better": "high"},
    "55": {"name": "OPS",  "label": "OPS",            "group": "batting",  "better": "high"},
    "32": {"name": "SV",   "label": "Saves",          "group": "pitching", "better": "high"},
    "38": {"name": "HR",   "label": "HR Allowed",     "group": "pitching", "better": "low"},
    "42": {"name": "K",    "label": "Strikeouts",     "group": "pitching", "better": "high"},
    "26": {"name": "ERA",  "label": "ERA",            "group": "pitching", "better": "low"},
    "27": {"name": "WHIP", "label": "WHIP",           "group": "pitching", "better": "low"},
    "83": {"name": "QS",   "label": "Quality Starts", "group": "pitching", "better": "high"},
}
SCORING_STAT_IDS = set(STAT_MAP.keys())

def _yahoo_get(path: str):
    """Make an authenticated Yahoo Fantasy API call. Refreshes token if needed."""
    if _yahoo is None:
        return None
    return _yahoo._get(f"https://fantasysports.yahooapis.com/fantasy/v2{path}")

def _parse_stats(stats_list: list) -> dict:
    """Parse a Yahoo stats list [{stat: {stat_id, value}}, ...] into {stat_id: value}."""
    result = {}
    for entry in stats_list:
        s = entry.get("stat", {})
        sid = str(s.get("stat_id", ""))
        val = s.get("value", "")
        if sid in SCORING_STAT_IDS:
            try:
                result[sid] = float(val) if val not in ("", "-", None) else None
            except (ValueError, TypeError):
                result[sid] = None
    return result

def _category_status(my_val, opp_val, better: str) -> str:
    """Return 'win' | 'loss' | 'tied' | 'close_win' | 'close_loss' | 'unknown'."""
    if my_val is None or opp_val is None:
        return "unknown"
    if my_val == opp_val:
        return "tied"
    winning = (my_val > opp_val) if better == "high" else (my_val < opp_val)
    diff    = abs(my_val - opp_val)
    base    = max(abs(opp_val if winning else my_val), 0.001)
    diff_pct = diff / base
    # "Close" = within 12% OR within a small absolute threshold for rate stats
    # ERA: <0.35 difference, WHIP: <0.05, OPS: <0.020 — tighter than 12% catches these
    is_close = diff_pct < 0.12
    if winning:
        return "close_win" if is_close else "win"
    else:
        return "close_loss" if is_close else "loss"


@app.get("/season/matchup")
def get_matchup(week: Optional[int] = None):
    """Current (or specified) week's H2H matchup with per-category breakdown."""
    data = _yahoo_get(f"/league/{LEAGUE_KEY}/scoreboard" + (f";week={week}" if week else ""))
    if not data:
        raise HTTPException(status_code=503, detail="Yahoo API unavailable")

    try:
        league_meta = data["league"][0]
        current_week = int(league_meta.get("current_week", 1))
        matchups_raw = data["league"][1]["scoreboard"]["0"]["matchups"]
    except (KeyError, IndexError, TypeError) as e:
        raise HTTPException(status_code=502, detail=f"Unexpected scoreboard format: {e}")

    # Find my matchup
    my_matchup = None
    for k, v in matchups_raw.items():
        if k == "count":
            continue
        matchup = v.get("matchup", {})
        teams_in_matchup = matchup.get("0", {}).get("teams", {})
        for tk, tv in teams_in_matchup.items():
            if tk == "count":
                continue
            team_arr = tv.get("team", [[]])[0]
            for prop in team_arr:
                if isinstance(prop, dict) and prop.get("team_key") == MY_TEAM_KEY:
                    my_matchup = matchup
                    break
        if my_matchup:
            break

    if not my_matchup:
        return {
            "week": current_week,
            "week_start": None,
            "week_end": None,
            "status": "no_matchup",
            "my_team": None,
            "opp_team": None,
            "categories": [],
        }

    week_start  = my_matchup.get("week_start")
    week_end    = my_matchup.get("week_end")
    matchup_status = my_matchup.get("status", "unknown")
    teams_raw   = my_matchup.get("0", {}).get("teams", {})

    teams = []
    for tk, tv in teams_raw.items():
        if tk == "count":
            continue
        team_arr = tv.get("team", [[], {}])
        meta     = team_arr[0]
        stats_section = team_arr[1] if len(team_arr) > 1 else {}

        name = next((p["name"] for p in meta if isinstance(p, dict) and "name" in p), "Unknown")
        team_key = next((p["team_key"] for p in meta if isinstance(p, dict) and "team_key" in p), "")

        raw_stats = stats_section.get("team_stats", {}).get("stats", [])
        parsed = _parse_stats(raw_stats) if raw_stats else {}

        teams.append({"name": name, "team_key": team_key, "stats": parsed})

    if len(teams) != 2:
        raise HTTPException(status_code=502, detail="Could not parse both teams from matchup")

    my_team  = next((t for t in teams if t["team_key"] == MY_TEAM_KEY), teams[0])
    opp_team = next((t for t in teams if t["team_key"] != MY_TEAM_KEY), teams[1])

    categories = []
    for sid, meta in STAT_MAP.items():
        my_val  = my_team["stats"].get(sid)
        opp_val = opp_team["stats"].get(sid)
        status  = _category_status(my_val, opp_val, meta["better"])
        categories.append({
            "stat_id":  sid,
            "name":     meta["name"],
            "label":    meta["label"],
            "group":    meta["group"],
            "better":   meta["better"],
            "my_value": my_val,
            "opp_value": opp_val,
            "status":   status,
        })

    # Sort: batting first, then pitching; within each group swing cats first
    order = {"close_win": 0, "close_loss": 1, "win": 2, "loss": 3, "tied": 4, "unknown": 5}
    categories.sort(key=lambda c: (0 if c["group"] == "batting" else 1, order.get(c["status"], 9)))

    return {
        "week":       current_week,
        "week_start": week_start,
        "week_end":   week_end,
        "status":     matchup_status,
        "my_team":    my_team["name"],
        "opp_team":   opp_team["name"],
        "categories": categories,
    }


_standings_cache: dict = {}
_standings_cache_time: float = 0.0
STANDINGS_CACHE_TTL = 300  # 5 minutes — standings don't change by the second

@app.get("/season/standings")
def get_standings():
    """League-wide standings with per-team win totals and category ranking."""
    global _standings_cache, _standings_cache_time
    if _standings_cache and (time.time() - _standings_cache_time) < STANDINGS_CACHE_TTL:
        return _standings_cache

    # Get overall standings
    st_data = _yahoo_get(f"/league/{LEAGUE_KEY}/standings")
    if not st_data:
        raise HTTPException(status_code=503, detail="Yahoo API unavailable")

    try:
        teams_raw = st_data["league"][1]["standings"][0]["teams"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail="Unexpected standings format")

    teams = []
    for k, v in teams_raw.items():
        if k == "count":
            continue
        team_arr = v.get("team", [[], {}])
        meta     = team_arr[0]
        standing = team_arr[1].get("team_standings", {}) if len(team_arr) > 1 else {}

        name     = next((p["name"] for p in meta if isinstance(p, dict) and "name" in p), "?")
        team_key = next((p.get("team_key","") for p in meta if isinstance(p, dict) and "team_key" in p), "")
        rank     = int(standing.get("rank", 99))
        totals   = standing.get("outcome_totals", {})
        wins     = int(totals.get("wins", 0))
        losses   = int(totals.get("losses", 0))
        ties     = int(totals.get("ties", 0))

        teams.append({
            "team_key": team_key,
            "name":     name,
            "is_mine":  team_key == MY_TEAM_KEY,
            "rank":     rank,
            "wins":     wins,
            "losses":   losses,
            "ties":     ties,
            "record":   f"{wins}-{losses}-{ties}",
        })

    # Fetch per-category stats for each team (batch where possible)
    team_keys = [t["team_key"] for t in teams if t["team_key"]]
    cat_stats: dict = {}
    for tk in team_keys:
        ts = _yahoo_get(f"/team/{tk}/stats")
        if ts:
            try:
                raw = ts["team"][1]["team_stats"]["stats"]
                cat_stats[tk] = _parse_stats(raw)
            except Exception:
                cat_stats[tk] = {}

    # For each scoring category, rank all teams
    category_rankings: dict = {}
    for sid, meta in STAT_MAP.items():
        values = []
        for t in teams:
            val = cat_stats.get(t["team_key"], {}).get(sid)
            values.append((t["team_key"], val))

        # Sort by value (handle None)
        reverse = meta["better"] == "high"
        values.sort(key=lambda x: (x[1] is None, (-x[1] if x[1] is not None else 0) if reverse else (x[1] if x[1] is not None else 999)))
        for rank_idx, (tk, _) in enumerate(values):
            if tk not in category_rankings:
                category_rankings[tk] = {}
            category_rankings[tk][sid] = rank_idx + 1

    # Assemble final output
    for t in teams:
        t["cat_ranks"]  = category_rankings.get(t["team_key"], {})
        t["cat_values"] = cat_stats.get(t["team_key"], {})

    teams.sort(key=lambda t: t["rank"])

    result = {
        "teams":       teams,
        "stat_map":    STAT_MAP,
        "season_started": any(
            v is not None
            for t in teams
            for v in cat_stats.get(t["team_key"], {}).values()
        ),
    }
    _standings_cache      = result
    _standings_cache_time = time.time()
    return result


@app.get("/season/closers")
def get_closers():
    """Your RP roster with save situation and recent stats."""
    ts = _yahoo_get(f"/team/{MY_TEAM_KEY}/roster")
    if not ts:
        raise HTTPException(status_code=503, detail="Yahoo API unavailable")

    closers = []
    try:
        roster_data = ts["team"][1]["roster"]
        players_raw = roster_data.get("0", {}).get("players", {})
        if isinstance(players_raw, dict):
            for pk, pv in players_raw.items():
                if pk == "count":
                    continue
                player_arr = pv.get("player", [[]])[0]
                pinfo: dict = {}
                for prop in player_arr:
                    if not isinstance(prop, dict):
                        continue
                    if "player_key" in prop:     pinfo["player_key"] = prop["player_key"]
                    if "name" in prop:           pinfo["name"] = prop["name"].get("full", "")
                    if "display_position" in prop: pinfo["position"] = prop["display_position"]
                    if "editorial_team_abbr" in prop: pinfo["team"] = prop["editorial_team_abbr"]
                if "RP" in pinfo.get("position", "") and pinfo.get("name"):
                    closers.append(pinfo)
    except Exception:
        pass

    # Add keeper RPs if roster is empty pre-draft
    if not closers:
        closers = [
            {"name": "Mason Miller", "position": "RP", "team": "SD",
             "player_key": "", "is_keeper": True},
        ]

    # Fetch season stats for each closer from Yahoo
    enriched = []
    for c in closers:
        stats = {}
        if c.get("player_key"):
            ps = _yahoo_get(f"/player/{c['player_key']}/stats")
            if ps:
                try:
                    raw = ps["player"][1]["player_stats"]["stats"]
                    stats = _parse_stats(raw)
                except Exception:
                    pass

        enriched.append({
            "name":       c.get("name", ""),
            "team":       c.get("team", ""),
            "position":   c.get("position", "RP"),
            "is_keeper":  c.get("is_keeper", False),
            "saves":      stats.get("32"),
            "era":        stats.get("26"),
            "whip":       stats.get("27"),
            "k":          stats.get("42"),
            "hr_allowed": stats.get("38"),
        })

    return {"closers": enriched}


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"\n  Draft Day API Server")
    print(f"  http://{args.host}:{args.port}\n")

    uvicorn.run("draft_server:app", host=args.host, port=args.port, reload=False)
