#!/usr/bin/env python3
"""
Draft Day API Server
Exposes the draft board state as a REST API for the web frontend.

Usage:
    python draft_server.py          # Start on port 8001
    python draft_server.py --port 8002
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

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

# ─── Railway / CI: load OAuth from env var if config file is absent ────────────
_oauth_env = os.environ.get("YAHOO_OAUTH_JSON")
if _oauth_env and not Path(OAUTH_CONFIG).exists():
    Path(OAUTH_CONFIG).parent.mkdir(parents=True, exist_ok=True)
    Path(OAUTH_CONFIG).write_text(_oauth_env)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Draft Day API", version="1.0")

ALLOWED_ORIGINS = [
    "https://thanlon-san.github.io",
    "http://localhost:3001",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
MY_TEAM_ID          = 2                # 2balls = team 2 in California Palm League
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

        # Resolve player names.
        all_keys = [p["player_key"] for p in raw_picks]
        roster_by_team: Dict[str, List] = {}
        new_keys = [k for k in all_keys if k not in _yahoo._pk_cache]
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
                "name":      info.get("name", "(unknown)"),
                "positions": info.get("positions", []),
                "team":      info.get("team", ""),
            })

        # Compute the consecutive draft watermark: the highest pick number where
        # every slot from 1..N is filled. Yahoo pre-assigns player_keys to all
        # keeper slots (rounds 9-12, etc.) before the draft reaches them, which
        # inflates the pick count. The watermark gives the actual draft position.
        sorted_overalls = sorted(p["overall"] for p in enriched)
        watermark = 0
        for i, overall in enumerate(sorted_overalls):
            if overall == i + 1:
                watermark = overall
            else:
                break

        # Update board with any new picks
        if len(enriched) > len(_all_picks):
            _board.apply_picks(raw_picks, _yahoo._pk_cache)
            _board.picks_made = watermark  # use watermark, not total count

            # Rebuild my_roster from actual Yahoo roster data (authoritative source).
            my_team_players = roster_by_team.get(MY_TEAM_KEY, [])
            if my_team_players:
                keeper_names = {norm_name(k["name"]) for k in MY_KEEPERS}
                _board.my_roster = list(MY_KEEPERS)  # reset to keepers
                for player in my_team_players:
                    name = player.get("name", "")
                    if not name or norm_name(name) in keeper_names:
                        continue
                    # Find which round this player was drafted
                    draft_round = next(
                        (p["round"] for p in enriched
                         if p["player_key"] == player.get("player_key") and p["is_mine"]),
                        None
                    )
                    _board.my_roster.append({
                        "name":     name,
                        "position": player.get("positions", ["?"])[0],
                        "round":    draft_round,
                        "adp":      next(
                            (p["adp"] for p in _board.all_players
                             if norm_name(p["name"]) == norm_name(name)),
                            None
                        ),
                    })
            else:
                # Fallback: add from enriched picks where is_mine and name is known
                for pick in enriched:
                    if pick["is_mine"] and pick["name"] != "(unknown)":
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
    rank:             int
    name:             str
    team:             str
    positions:        List[str]
    adp:              float
    tier:             str
    reason:           str
    yahoo_discount:   float = 0.0
    expert_rank:      Optional[int] = None
    expert_rank_gap:  float = 0.0

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
            expert_rank=r.get("expert_rank"),
            expert_rank_gap=r.get("expert_rank_gap", 0.0),
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

    # Only show picks up to the consecutive watermark — excludes future keeper slots
    # that Yahoo pre-assigns player_keys to before the draft reaches them.
    picks_watermark = _board.picks_made
    recent_picks = [
        PickInfo(
            overall=p["overall"],
            round=p["round"],
            name=p["name"],
            positions=p["positions"],
            team=p["team"],
            is_mine=p["is_mine"],
        )
        for p in sorted(
            (p for p in picks if p["overall"] <= picks_watermark),
            key=lambda x: -x["overall"]
        )[:20]
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


# ─── Draft-day utility endpoints ──────────────────────────────────────────────

@app.get("/draft/best-available")
def get_best_available(position: Optional[str] = None, n: int = 10):
    """
    Returns the best available players, optionally filtered to a position.
    position: C | 1B | 2B | 3B | SS | OF | SP | RP  (or omit for overall)
    """
    if _board is None:
        raise HTTPException(status_code=503, detail=_error or "Board not initialized")
    maybe_sync_yahoo()

    avail = _board.available()
    if position:
        pos_upper = position.upper()
        avail = [p for p in avail if pos_upper in p.get("positions", [])]

    avail = sorted(avail, key=lambda x: x["adp"])[:n]
    return {
        "position": position,
        "players": [
            {
                "rank":           i + 1,
                "name":           p["name"],
                "team":           p.get("team", ""),
                "positions":      p.get("positions", []),
                "adp":            p["adp"],
                "tier":           get_tier(p["adp"]),
                "yahoo_discount": p.get("yahoo_discount", 0.0),
            }
            for i, p in enumerate(avail)
        ],
        "picks_made": _board.picks_made,
    }


@app.get("/draft/run-detector")
def get_run_detector(window: int = 8):
    """
    Detects if a position run is happening in the last N picks.
    Returns positions where ≥3 players were taken in the last `window` picks.
    """
    if _board is None:
        raise HTTPException(status_code=503, detail=_error or "Board not initialized")

    picks = maybe_sync_yahoo()
    recent = picks[-window:] if len(picks) >= window else picks

    pos_counts: dict[str, int] = {}
    for pick in recent:
        for pos in pick.get("positions", []):
            if pos in ("C", "1B", "2B", "3B", "SS", "OF", "SP", "RP"):
                pos_counts[pos] = pos_counts.get(pos, 0) + 1

    runs = [
        {"position": pos, "count": cnt, "window": len(recent)}
        for pos, cnt in pos_counts.items()
        if cnt >= 3
    ]
    runs.sort(key=lambda x: -x["count"])

    # For each detected run, show the best still available at that position
    enriched = []
    for run in runs:
        best = _board.available()
        best = [p for p in best if run["position"] in p.get("positions", [])]
        best = sorted(best, key=lambda x: x["adp"])[:3]
        enriched.append({
            **run,
            "best_remaining": [{"name": p["name"], "adp": p["adp"]} for p in best],
        })

    return {
        "window_size":    len(recent),
        "picks_made":     _board.picks_made,
        "runs_detected":  enriched,
        "all_pos_counts": pos_counts,
    }


@app.get("/draft/pick-clock")
def get_pick_clock():
    """
    Returns countdown to your next pick, your roster gaps, and a
    one-line strategy note for right now.
    """
    if _board is None:
        raise HTTPException(status_code=503, detail=_error or "Board not initialized")
    maybe_sync_yahoo()

    rnd          = _board.current_round
    nxt          = _board.next_my_pick()
    until        = _board.picks_until_mine()
    needs        = _board.remaining_needs()
    open_needs   = {k: v for k, v in needs.items() if v > 0}
    phase, label = current_phase(rnd)

    # One-line strategy tailored to urgency
    if until == 0:
        urgency = "ON THE CLOCK"
        note    = f"You're up! Phase: {label}"
    elif until <= 2:
        urgency = "URGENT"
        note    = f"{until} pick{'s' if until > 1 else ''} away — lock in your target now. {label}"
    elif until <= 5:
        urgency = "SOON"
        note    = f"{until} picks away. {label}"
    else:
        urgency = "WATCHING"
        note    = f"{until} picks until yours (Rd {nxt['round'] if nxt else '?'}). {label}"

    # Top 5 recs for rapid scanning
    top_recs = _board.recommend(5)

    return {
        "picks_made":     _board.picks_made,
        "current_round":  rnd,
        "until_my_pick":  until,
        "next_pick":      nxt,
        "urgency":        urgency,
        "strategy_note":  note,
        "open_needs":     open_needs,
        "top_5":          [
            {"name": p["name"], "adp": p["adp"],
             "positions": p.get("positions", []), "reason": p.get("_reason", "")}
            for p in top_recs
        ],
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


# ─── /season/lineup-focus ─────────────────────────────────────────────────────

@app.get("/season/lineup-focus")
def get_lineup_focus():
    """
    Returns players on my roster who most help with this week's swing categories.
    Combines matchup data (which categories are close) with roster data (who helps there).
    """
    try:
        matchup = get_matchup()
    except HTTPException:
        return {"week": 0, "swing_categories": [], "season_started": False}

    season_started = matchup["status"] not in ("preevent", "no_matchup") and any(
        c["my_value"] is not None for c in matchup["categories"]
    )

    swing_cats = [
        c for c in matchup["categories"]
        if c["status"] in ("close_win", "close_loss")
    ]

    # Fetch my roster to map players to categories
    my_roster_players: list[dict] = []
    ts = _yahoo_get(f"/team/{MY_TEAM_KEY}/roster")
    if ts:
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
                        if "name" in prop:
                            pinfo["name"] = prop["name"].get("full", "")
                        if "display_position" in prop:
                            pinfo["position"] = prop["display_position"]
                        if "editorial_team_abbr" in prop:
                            pinfo["team"] = prop["editorial_team_abbr"]
                    if pinfo.get("name"):
                        my_roster_players.append(pinfo)
        except Exception:
            pass

    BATTING_CATS = {"7", "8", "12", "13", "16", "55"}   # R H HR RBI SB OPS
    PITCHING_CATS = {"32", "38", "42", "26", "27", "83"} # SV HR_allowed K ERA WHIP QS

    def _relevant_players(stat_id: str) -> list[str]:
        """Return roster player names relevant to a scoring category."""
        if stat_id in BATTING_CATS:
            return [p["name"] for p in my_roster_players
                    if not any(pos in p.get("position", "") for pos in ("SP", "RP"))]
        else:
            return [p["name"] for p in my_roster_players
                    if any(pos in p.get("position", "") for pos in ("SP", "RP", "P"))]

    result_cats = []
    for cat in swing_cats:
        sid = cat["stat_id"]
        focus = _relevant_players(sid)[:4]
        waiver_hint = None
        if cat["status"] == "close_loss":
            if sid in BATTING_CATS:
                waiver_hint = f"Consider streaming a batter who profiles well in {cat['name']}"
            else:
                waiver_hint = f"Consider streaming a pitcher who profiles well in {cat['name']}"
        result_cats.append({
            "stat_name":        cat["name"],
            "stat_id":          sid,
            "status":           cat["status"],
            "my_value":         cat["my_value"],
            "opp_value":        cat["opp_value"],
            "focus_players":    focus,
            "waiver_suggestion": waiver_hint,
        })

    return {
        "week":             matchup["week"],
        "swing_categories": result_cats,
        "season_started":   season_started,
    }


# ─── /season/trajectory ───────────────────────────────────────────────────────

_trajectory_cache: dict = {}
_trajectory_cache_time: float = 0.0
TRAJECTORY_CACHE_TTL = 3600  # 1 hour

@app.get("/season/trajectory")
def get_trajectory():
    """
    Returns weekly category rank history for my team.
    Fetches league scoreboard for each past week and computes my rank per category.
    """
    global _trajectory_cache, _trajectory_cache_time
    if _trajectory_cache and (time.time() - _trajectory_cache_time) < TRAJECTORY_CACHE_TTL:
        return _trajectory_cache

    meta_data = _yahoo_get(f"/league/{LEAGUE_KEY}/scoreboard")
    if not meta_data:
        raise HTTPException(status_code=503, detail="Yahoo API unavailable")

    try:
        current_week = int(meta_data["league"][0].get("current_week", 1))
    except (KeyError, IndexError, TypeError):
        current_week = 1

    # For each past week, collect per-team stats
    weekly_team_stats: list[dict] = []  # [{team_key: {stat_id: value}}]
    for w in range(1, current_week):
        week_data = _yahoo_get(f"/league/{LEAGUE_KEY}/scoreboard;week={w}")
        if not week_data:
            weekly_team_stats.append({})
            continue
        try:
            matchups_raw = week_data["league"][1]["scoreboard"]["0"]["matchups"]
        except (KeyError, IndexError, TypeError):
            weekly_team_stats.append({})
            continue

        week_stats: dict = {}
        for mk, mv in matchups_raw.items():
            if mk == "count":
                continue
            matchup = mv.get("matchup", {})
            teams_raw = matchup.get("0", {}).get("teams", {})
            for tk, tv in teams_raw.items():
                if tk == "count":
                    continue
                team_arr = tv.get("team", [[], {}])
                meta = team_arr[0]
                stats_section = team_arr[1] if len(team_arr) > 1 else {}
                team_key = next((p["team_key"] for p in meta if isinstance(p, dict) and "team_key" in p), "")
                raw_stats = stats_section.get("team_stats", {}).get("stats", [])
                if team_key:
                    week_stats[team_key] = _parse_stats(raw_stats)
        weekly_team_stats.append(week_stats)

    # Build per-category weekly rank history for my team
    categories_out: dict = {}
    for sid, smeta in STAT_MAP.items():
        weekly_ranks: list = []
        weekly_values: list = []
        for week_stats in weekly_team_stats:
            if not week_stats or MY_TEAM_KEY not in week_stats:
                weekly_ranks.append(None)
                weekly_values.append(None)
                continue
            my_val = week_stats.get(MY_TEAM_KEY, {}).get(sid)
            all_vals = [(tk, v.get(sid)) for tk, v in week_stats.items()]
            valid = [(tk, v) for tk, v in all_vals if v is not None]
            if not valid or my_val is None:
                weekly_ranks.append(None)
                weekly_values.append(None)
                continue
            reverse = smeta["better"] == "high"
            sorted_vals = sorted(valid, key=lambda x: x[1], reverse=reverse)
            rank = next((i + 1 for i, (tk, _) in enumerate(sorted_vals) if tk == MY_TEAM_KEY), None)
            weekly_ranks.append(rank)
            weekly_values.append(my_val)

        # Append None for current week (in progress)
        weekly_ranks.append(None)
        weekly_values.append(None)

        valid_ranks = [r for r in weekly_ranks if r is not None]
        avg_rank = round(sum(valid_ranks) / len(valid_ranks), 1) if valid_ranks else None

        # Trend: compare last 2 non-None ranks
        trend = "neutral"
        if len(valid_ranks) >= 2:
            diff = valid_ranks[-1] - valid_ranks[-2]
            if diff < -1:
                trend = "improving"
            elif diff > 1:
                trend = "declining"
            else:
                trend = "stable"

        categories_out[sid] = {
            "name":          smeta["name"],
            "label":         smeta["label"],
            "group":         smeta["group"],
            "better":        smeta["better"],
            "weekly_ranks":  weekly_ranks,
            "weekly_values": weekly_values,
            "trend":         trend,
            "avg_rank":      avg_rank,
        }

    # Summary buckets
    dominating = [m["name"] for sid, m in categories_out.items()
                  if m["avg_rank"] is not None and m["avg_rank"] <= 4]
    struggling  = [m["name"] for sid, m in categories_out.items()
                  if m["avg_rank"] is not None and m["avg_rank"] >= 9]
    improving   = [m["name"] for sid, m in categories_out.items()
                  if m["trend"] == "improving"]

    result = {
        "current_week": current_week,
        "categories":   categories_out,
        "summary": {
            "dominating": dominating,
            "struggling":  struggling,
            "improving":   improving,
        },
    }
    _trajectory_cache      = result
    _trajectory_cache_time = time.time()
    return result


# ─── /season/opponent ─────────────────────────────────────────────────────────

@app.get("/season/opponent")
def get_opponent_scouting():
    """Returns a scouting report on this week's opponent."""
    try:
        matchup = get_matchup()
    except HTTPException as e:
        raise e

    if matchup.get("status") == "no_matchup" or not matchup.get("opp_team"):
        return {
            "opponent_name":     None,
            "their_strengths":   [],
            "their_weaknesses":  [],
            "your_advantages":   [],
            "threat_categories": [],
            "game_plan":         "No matchup found for this week.",
            "week":              matchup.get("week", 0),
            "season_started":    False,
        }

    # Don't show scouting data before the season starts — no real stats means
    # arbitrary rankings that produce misleading output.
    all_unknown = all(c["status"] == "unknown" for c in matchup.get("categories", []))
    if all_unknown:
        return {
            "opponent_name":     matchup.get("opp_team"),
            "their_strengths":   [],
            "their_weaknesses":  [],
            "your_advantages":   [],
            "threat_categories": [],
            "game_plan":         f"Season starts {matchup.get('week_start', 'soon')} — scouting data will populate once games are played.",
            "week":              matchup.get("week", 0),
            "season_started":    False,
        }

    # Get standings for category rankings
    try:
        standings = get_standings()
    except HTTPException:
        standings = None

    opp_name = matchup["opp_team"]

    # Find opponent's team key from standings
    opp_team_key = None
    opp_cat_ranks: dict = {}
    my_cat_ranks: dict = {}
    if standings:
        for t in standings["teams"]:
            if t["name"] == opp_name:
                opp_team_key = t["team_key"]
                opp_cat_ranks = t.get("cat_ranks", {})
            if t["is_mine"]:
                my_cat_ranks = t.get("cat_ranks", {})

    # Build scouting report from category rankings
    their_strengths: list[str] = []
    their_weaknesses: list[str] = []
    your_advantages: list[str] = []
    threat_categories: list[str] = []

    swing_stat_ids = {c["stat_id"] for c in matchup["categories"]
                      if c["status"] in ("close_win", "close_loss")}

    for sid, smeta in STAT_MAP.items():
        opp_rank = opp_cat_ranks.get(sid)
        my_rank  = my_cat_ranks.get(sid)
        cat_name = smeta["name"]

        if opp_rank is not None:
            if opp_rank <= 4:
                their_strengths.append(cat_name)
            elif opp_rank >= 9:
                their_weaknesses.append(cat_name)

        if opp_rank is not None and my_rank is not None:
            if my_rank < opp_rank:
                your_advantages.append(cat_name)
            elif opp_rank < my_rank and sid in swing_stat_ids:
                threat_categories.append(cat_name)

    # Generate game plan text
    parts = []
    if their_strengths:
        parts.append(f"They dominate {', '.join(their_strengths[:2])} — expect a tough fight there.")
    if their_weaknesses:
        parts.append(f"Exploit their weakness in {', '.join(their_weaknesses[:2])}.")
    if your_advantages:
        parts.append(f"You have the edge in {', '.join(your_advantages[:3])} — protect those leads.")
    if threat_categories:
        parts.append(f"Watch out for {', '.join(threat_categories)} — these are battleground categories.")
    if not parts:
        parts.append("Game plan data will populate once the season is underway.")

    game_plan = " ".join(parts)

    return {
        "opponent_name":    opp_name,
        "their_strengths":  their_strengths,
        "their_weaknesses": their_weaknesses,
        "your_advantages":  your_advantages,
        "threat_categories": threat_categories,
        "game_plan":        game_plan,
        "week":             matchup["week"],
    }


# ─── /season/projections ───────────────────────────────────────────────────────

_projections_cache: dict = {}
_projections_cache_time: float = 0.0
PROJECTIONS_CACHE_TTL = 3600  # 1 hour

@app.get("/season/projections")
def get_projections():
    """
    Returns Steamer ROS projections for my roster + top free agents.
    Hitters: PA, AVG, HR, RBI, SB, OPS, wRC+.
    Pitchers: IP, ERA, WHIP, K, QS, FIP, K-BB%.
    """
    global _projections_cache, _projections_cache_time
    if _projections_cache and (time.time() - _projections_cache_time) < PROJECTIONS_CACHE_TTL:
        return _projections_cache

    from src.projection_fetcher import ProjectionFetcher

    fetcher = ProjectionFetcher()
    fetcher.load()

    # Build player list from roster
    players: list[dict] = []
    ts = _yahoo_get(f"/team/{MY_TEAM_KEY}/roster")
    if ts:
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
                        if "name" in prop:
                            pinfo["name"] = prop["name"].get("full", "")
                        if "display_position" in prop:
                            pinfo["position"] = prop["display_position"]
                        if "editorial_team_abbr" in prop:
                            pinfo["team"] = prop["editorial_team_abbr"]
                    if pinfo.get("name"):
                        pinfo["source"] = "roster"
                        players.append(pinfo)
        except Exception:
            pass

    # Also look up top free agents
    if _yahoo:
        try:
            fa_data = _yahoo._get(
                f"https://fantasysports.yahooapis.com/fantasy/v2/league/{LEAGUE_KEY}/players;status=FA;count=30"
            )
            if fa_data:
                fa_players_raw = fa_data.get("league", [None, {}])[1].get("players", {})
                if isinstance(fa_players_raw, dict):
                    for fk, fv in fa_players_raw.items():
                        if fk == "count":
                            continue
                        fa_arr = fv.get("player", [[]])[0]
                        finfo: dict = {}
                        for prop in fa_arr:
                            if not isinstance(prop, dict):
                                continue
                            if "name" in prop:
                                finfo["name"] = prop["name"].get("full", "")
                            if "display_position" in prop:
                                finfo["position"] = prop["display_position"]
                            if "editorial_team_abbr" in prop:
                                finfo["team"] = prop["editorial_team_abbr"]
                        if finfo.get("name"):
                            finfo["source"] = "free_agent"
                            players.append(finfo)
        except Exception:
            pass

    hitters = []
    pitchers = []
    for p in players:
        name = p.get("name", "")
        pos = p.get("position", "")
        is_pitcher = any(x in pos for x in ("SP", "RP", "P"))
        proj = fetcher.get_projection(name, is_pitcher=is_pitcher)
        if proj is None:
            continue
        entry = {
            "name": name,
            "team": p.get("team", ""),
            "position": pos,
            "source": p.get("source", ""),
        }
        if is_pitcher:
            entry.update({
                "ip": proj.ip, "era": proj.era, "whip": proj.whip,
                "k": proj.k, "qs": proj.qs, "fip": proj.fip,
                "k_bb_pct": proj.k_bb_pct, "war": proj.war,
                "ros_value": round(proj.ros_value, 1),
            })
            pitchers.append(entry)
        else:
            entry.update({
                "pa": proj.pa, "avg": proj.avg, "hr": proj.hr,
                "rbi": proj.rbi, "sb": proj.sb, "ops": proj.ops,
                "wrc_plus": proj.wrc_plus, "war": proj.war,
                "ros_value": round(proj.ros_value, 1),
            })
            hitters.append(entry)

    hitters.sort(key=lambda x: x["ros_value"], reverse=True)
    pitchers.sort(key=lambda x: x["ros_value"], reverse=True)

    result = {
        "hitters": hitters,
        "pitchers": pitchers,
        "total_scanned": len(players),
        "generated_at": datetime.now().isoformat(),
    }
    _projections_cache = result
    _projections_cache_time = time.time()
    return result


# ─── /season/regression ────────────────────────────────────────────────────────

_regression_cache: dict = {}
_regression_cache_time: float = 0.0
REGRESSION_CACHE_TTL = 3600  # 1 hour

@app.get("/season/regression")
def get_regression():
    """
    Returns buy-low and sell-high regression candidates based on xStats vs actual.
    Scans my roster + top free agents.
    """
    global _regression_cache, _regression_cache_time
    if _regression_cache and (time.time() - _regression_cache_time) < REGRESSION_CACHE_TTL:
        return _regression_cache

    from src.regression_analyzer import RegressionAnalyzer

    analyzer = RegressionAnalyzer()

    # Build player list from my roster
    players: list[dict] = []
    ts = _yahoo_get(f"/team/{MY_TEAM_KEY}/roster")
    if ts:
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
                        if "name" in prop:
                            pinfo["name"] = prop["name"].get("full", "")
                        if "display_position" in prop:
                            pinfo["position"] = prop["display_position"]
                        if "editorial_team_abbr" in prop:
                            pinfo["team"] = prop["editorial_team_abbr"]
                    if pinfo.get("name"):
                        players.append(pinfo)
        except Exception:
            pass

    # Also scan top free agents for buy-low targets
    if _yahoo:
        try:
            from src.yahoo_client import YahooFantasyClient
            # Reuse the existing yahoo connection's oauth
            fa_data = _yahoo._get(
                f"https://fantasysports.yahooapis.com/fantasy/v2/league/{LEAGUE_KEY}/players;status=FA;count=30"
            )
            if fa_data:
                fa_players_raw = fa_data.get("league", [None, {}])[1].get("players", {})
                if isinstance(fa_players_raw, dict):
                    for fk, fv in fa_players_raw.items():
                        if fk == "count":
                            continue
                        fa_arr = fv.get("player", [[]])[0]
                        finfo: dict = {}
                        for prop in fa_arr:
                            if not isinstance(prop, dict):
                                continue
                            if "name" in prop:
                                finfo["name"] = prop["name"].get("full", "")
                            if "display_position" in prop:
                                finfo["position"] = prop["display_position"]
                            if "editorial_team_abbr" in prop:
                                finfo["team"] = prop["editorial_team_abbr"]
                        if finfo.get("name"):
                            finfo["is_free_agent"] = True
                            players.append(finfo)
        except Exception:
            pass

    results = analyzer.scan_players(players)

    def _serialize(c):
        return {
            "name": c.name,
            "player_type": c.player_type,
            "team": c.team,
            "position": c.position,
            "direction": c.direction,
            "ba": c.ba,
            "xba": c.xba,
            "slg": c.slg,
            "xslg": c.xslg,
            "xwoba": c.xwoba,
            "ba_delta": c.ba_delta,
            "era": c.era,
            "xera": c.xera,
            "fip": c.fip,
            "era_fip_delta": c.era_fip_delta,
            "confidence": c.confidence,
            "summary": c.summary,
            "improving_metrics": c.improving_metrics,
        }

    result = {
        "buy_low": [_serialize(c) for c in results["buy_low"]],
        "sell_high": [_serialize(c) for c in results["sell_high"]],
        "scanned": len(players),
        "generated_at": datetime.now().isoformat(),
    }
    _regression_cache = result
    _regression_cache_time = time.time()
    return result


# ─── /season/trade-analyzer ─────────────────────────────────────────────────────

@app.get("/season/trade-analyzer")
def get_trade_analysis(give: str, get: str):
    """
    Analyze a proposed trade: give Player A, get Player B.
    Returns per-category impact, rank changes, and net win probability delta.
    Uses ROS projections + current league standings for rank simulation.
    """
    if not give or not get:
        raise HTTPException(status_code=400, detail="Both 'give' and 'get' query params required")

    from src.trade_analyzer import TradeAnalyzer

    analyzer = TradeAnalyzer()

    # Fetch current league data for rank simulation
    my_cat_values: dict = {}
    league_cat_values: list = []
    try:
        standings = get_standings()
        for t in standings.get("teams", []):
            cv = t.get("cat_values", {})
            if cv:
                league_cat_values.append(cv)
            if t.get("is_mine"):
                my_cat_values = cv
    except Exception:
        pass

    result = analyzer.analyze(
        give_player=give,
        get_player=get,
        my_cat_values=my_cat_values if my_cat_values else None,
        league_cat_values=league_cat_values if league_cat_values else None,
    )

    return {
        "give_player": result.give_player,
        "get_player": result.get_player,
        "give_is_pitcher": result.give_is_pitcher,
        "get_is_pitcher": result.get_is_pitcher,
        "give_ros_value": result.give_ros_value,
        "get_ros_value": result.get_ros_value,
        "categories": [
            {
                "stat_id": c.stat_id,
                "name": c.name,
                "label": c.label,
                "group": c.group,
                "better": c.better,
                "before_value": c.before_value,
                "after_value": c.after_value,
                "delta": c.delta,
                "before_rank": c.before_rank,
                "after_rank": c.after_rank,
                "rank_change": c.rank_change,
                "verdict": c.verdict,
            }
            for c in result.categories
        ],
        "cats_gained": result.cats_gained,
        "cats_lost": result.cats_lost,
        "cats_neutral": result.cats_neutral,
        "net_rank_change": result.net_rank_change,
        "win_probability_delta": result.win_probability_delta,
        "summary": result.summary,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/season/trade-search")
def trade_player_search(q: str, limit: int = 10):
    """Search for players by name for the trade analyzer input."""
    if not q or len(q) < 2:
        return {"results": []}
    from src.trade_analyzer import TradeAnalyzer
    analyzer = TradeAnalyzer()
    return {"results": analyzer.search_players(q, limit=limit)}


# ─── /season/weekly-plan ──────────────────────────────────────────────────────

_weekly_plan_cache: dict = {}
_weekly_plan_cache_time: float = 0.0
WEEKLY_PLAN_CACHE_TTL = 3600  # 1 hour

@app.get("/season/weekly-plan")
def get_weekly_plan():
    """
    Full-week streaming planner. For each day of next week, shows the best
    available SP matchups scored by opponent K%, wRC+, park factor, and Vegas total.
    Also returns team game counts for batting streamer decisions.
    """
    global _weekly_plan_cache, _weekly_plan_cache_time
    if _weekly_plan_cache and (time.time() - _weekly_plan_cache_time) < WEEKLY_PLAN_CACHE_TTL:
        return _weekly_plan_cache

    from src.weekly_planner import WeeklyPlanner

    planner = WeeklyPlanner()
    plan = planner.build_plan()

    result = {
        "week_start": plan.week_start,
        "week_end": plan.week_end,
        "daily_streams": {
            date: [
                {
                    "date": s.date, "pitcher": s.pitcher, "team": s.team,
                    "opponent": s.opponent, "home_away": s.home_away,
                    "opp_k_pct": s.opp_k_pct, "opp_wrc_plus": s.opp_wrc_plus,
                    "park_factor": s.park_factor, "game_total": s.game_total,
                    "score": s.score, "reason": s.reason,
                }
                for s in streams
            ]
            for date, streams in plan.daily_streams.items()
        },
        "optimal_streams": [
            {
                "date": s.date, "pitcher": s.pitcher, "team": s.team,
                "opponent": s.opponent, "home_away": s.home_away,
                "score": s.score, "reason": s.reason,
            }
            for s in plan.optimal_streams
        ],
        "team_game_counts": [
            {"team": c.team, "games": c.games, "opponents": c.opponents}
            for c in plan.team_game_counts
        ],
        "generated_at": datetime.now().isoformat(),
    }
    _weekly_plan_cache = result
    _weekly_plan_cache_time = time.time()
    return result


# ─── /season/bullpen-alerts ────────────────────────────────────────────────────

_bullpen_cache: dict = {}
_bullpen_cache_time: float = 0.0
BULLPEN_CACHE_TTL = 1800  # 30 minutes

@app.get("/season/bullpen-alerts")
def get_bullpen_alerts():
    """
    Returns bullpen fatigue data and vulture save alerts.
    Scans all 30 closers for fatigue indicators, surfaces pickup opportunities
    when a closer's setup man is likely to get a save.
    """
    global _bullpen_cache, _bullpen_cache_time
    if _bullpen_cache and (time.time() - _bullpen_cache_time) < BULLPEN_CACHE_TTL:
        return _bullpen_cache

    from src.bullpen_tracker import BullpenTracker
    from src.bullpen_fatigue import BullpenFatigueMonitor

    tracker = BullpenTracker()
    monitor = BullpenFatigueMonitor(bullpen_tracker=tracker)

    fatigues = monitor.get_all_closer_fatigue()
    alerts = monitor.get_vulture_alerts()

    result = {
        "alerts": [
            {
                "closer": a.closer,
                "closer_team": a.closer_team,
                "fatigue_score": a.fatigue_score,
                "fatigue_level": a.fatigue_level,
                "consecutive_days": a.consecutive_days,
                "pitches_last_3_days": a.pitches_last_3_days,
                "vulture_candidate": a.vulture_candidate,
                "reason": a.reason,
                "committee": a.committee,
            }
            for a in alerts
        ],
        "closer_fatigue": [
            {
                "name": f.name,
                "team": f.team,
                "fatigue_score": f.fatigue_score,
                "fatigue_level": f.fatigue_level,
                "consecutive_days": f.consecutive_days,
                "pitches_last_3_days": f.pitches_last_3_days,
                "innings_last_7_days": f.innings_last_7_days,
                "appearances_last_7_days": f.appearances_last_7_days,
                "last_outing_date": f.last_outing_date,
            }
            for f in fatigues
        ],
        "generated_at": datetime.now().isoformat(),
    }
    _bullpen_cache = result
    _bullpen_cache_time = time.time()
    return result


# ─── /season/streamers ────────────────────────────────────────────────────────

_streamers_cache: dict = {}
_streamers_cache_time: float = 0.0
STREAMERS_CACHE_TTL = 3600  # 1 hour

@app.get("/season/streamers")
def get_streamers():
    """
    Returns two-start pitcher streaming candidates for next week.
    Identifies SPs with two scheduled starts, scores matchups,
    and flags waiver-wire opportunities.
    """
    global _streamers_cache, _streamers_cache_time
    if _streamers_cache and (time.time() - _streamers_cache_time) < STREAMERS_CACHE_TTL:
        return _streamers_cache

    from src.streamer_planner import StreamerPlanner

    planner = StreamerPlanner()
    streamers = planner.find_two_start_streamers()

    result = {
        "streamers": [
            {
                "pitcher": s.pitcher,
                "team": s.team,
                "starts": [
                    {
                        "date": st.date,
                        "opponent": st.opponent,
                        "home_away": st.home_away,
                        "opp_k_pct": st.opp_k_pct,
                        "park_factor": st.park_factor,
                    }
                    for st in s.starts
                ],
                "composite_score": s.composite_score,
                "pitcher_fip": s.pitcher_fip,
                "reason": s.reason,
            }
            for s in streamers
        ],
        "week_dates": planner.get_next_week_range(),
        "generated_at": datetime.now().isoformat(),
    }
    _streamers_cache = result
    _streamers_cache_time = time.time()
    return result


# ─── /season/player-profile ─────────────────────────────────────────────────────

@app.get("/season/player-profile")
def get_player_profile(name: str):
    """
    Returns a combined player profile: ROS projections, regression analysis,
    recent stats, and injury status. Used by the player profile page.
    """
    if not name:
        raise HTTPException(status_code=400, detail="'name' query param required")

    from src.projection_fetcher import ProjectionFetcher
    from src.regression_analyzer import RegressionAnalyzer
    from src.stats_fetcher import StatsFetcher
    from src.injury_tracker import InjuryTracker

    profile: dict = {"name": name, "found": False}

    # Projections
    try:
        fetcher = ProjectionFetcher()
        fetcher.load()
        hitter_proj = fetcher.get_projection(name, is_pitcher=False)
        pitcher_proj = fetcher.get_projection(name, is_pitcher=True)
        if hitter_proj:
            profile["projection"] = {
                "type": "hitter",
                "pa": hitter_proj.pa, "avg": hitter_proj.avg, "hr": hitter_proj.hr,
                "rbi": hitter_proj.rbi, "sb": hitter_proj.sb, "ops": hitter_proj.ops,
                "wrc_plus": hitter_proj.wrc_plus, "war": hitter_proj.war,
                "ros_value": round(hitter_proj.ros_value, 1),
            }
            profile["found"] = True
            profile["team"] = hitter_proj.team
            profile["position"] = "Hitter"
        elif pitcher_proj:
            profile["projection"] = {
                "type": "pitcher",
                "ip": pitcher_proj.ip, "era": pitcher_proj.era, "whip": pitcher_proj.whip,
                "k": pitcher_proj.k, "qs": pitcher_proj.qs, "fip": pitcher_proj.fip,
                "k_bb_pct": pitcher_proj.k_bb_pct, "war": pitcher_proj.war,
                "ros_value": round(pitcher_proj.ros_value, 1),
            }
            profile["found"] = True
            profile["team"] = pitcher_proj.team
            profile["position"] = "Pitcher"
    except Exception:
        pass

    # Regression analysis
    try:
        reg = RegressionAnalyzer()
        is_pitcher = profile.get("projection", {}).get("type") == "pitcher"
        if is_pitcher:
            result = reg.analyze_pitcher(name)
        else:
            result = reg.analyze_hitter(name)
        if result:
            profile["regression"] = {
                "direction": result.direction,
                "confidence": result.confidence,
                "summary": result.summary,
                "ba": result.ba, "xba": result.xba,
                "slg": result.slg, "xslg": result.xslg,
                "xwoba": result.xwoba, "ba_delta": result.ba_delta,
                "era": result.era, "xera": result.xera,
                "fip": result.fip, "era_fip_delta": result.era_fip_delta,
                "improving_metrics": result.improving_metrics,
            }
            profile["found"] = True
    except Exception:
        pass

    # Recent stats (7 / 14 / 30 day windows)
    try:
        sf = StatsFetcher()
        windows = {}
        for days in (7, 14, 30):
            stats = sf.get_recent_stats(name, days=days)
            if stats:
                windows[f"last_{days}_days"] = stats.to_dict()
        if windows:
            profile["recent_stats"] = windows
            profile["found"] = True
    except Exception:
        pass

    # Injury status
    try:
        inj = InjuryTracker()
        injury = inj.get_injury(name)
        if injury:
            profile["injury"] = {
                "badge": injury.badge,
                "description": injury.description,
                "date": injury.date,
            }
    except Exception:
        pass

    # Savant percentile rankings
    try:
        from src.savant_leaderboards import SavantLeaderboards
        savant = SavantLeaderboards()
        savant.load()
        _is_p = profile.get("projection", {}).get("type") == "pitcher"
        pctiles = savant.get_percentiles(name, is_pitcher=_is_p)
        if pctiles is not None:
            profile["savant_percentiles"] = pctiles.to_dict()
            profile["found"] = True
    except Exception:
        pass

    profile["generated_at"] = datetime.now().isoformat()
    return profile


# ─── /season/prospects ──────────────────────────────────────────────────────────

_prospects_cache: dict = {}
_prospects_cache_time: float = 0.0
PROSPECTS_CACHE_TTL = 3600  # 1 hour

@app.get("/season/prospects")
def get_prospects():
    """
    Returns prospect call-up watchlist with MiLB game logs, hot streaks,
    roster status, and call-up scores for top 50 fantasy-relevant prospects.
    """
    global _prospects_cache, _prospects_cache_time
    if _prospects_cache and (time.time() - _prospects_cache_time) < PROSPECTS_CACHE_TTL:
        return _prospects_cache

    from src.prospect_tracker import ProspectTracker

    tracker = ProspectTracker()
    all_profiles = tracker.scan_all()
    hot = [p for p in all_profiles if p.is_hot or p.alert_reasons]

    result = {
        "prospects": [p.to_dict() for p in all_profiles],
        "hot_prospects": [p.to_dict() for p in hot],
        "total": len(all_profiles),
        "hot_count": len(hot),
        "generated_at": datetime.now().isoformat(),
    }
    _prospects_cache = result
    _prospects_cache_time = time.time()
    return result


# ─── /season/matchup-enhanced ──────────────────────────────────────────────────

@app.get("/season/matchup-enhanced")
def get_matchup_enhanced():
    """
    Enhanced matchup with projected end-of-week totals, gap-to-flip calculations,
    and specific roster move recommendations for swing categories.
    """
    try:
        matchup = get_matchup()
    except HTTPException as e:
        raise e

    if matchup.get("status") == "no_matchup" or not matchup.get("opp_team"):
        return {"enhanced": False, "reason": "No active matchup", **matchup}

    all_unknown = all(c["status"] == "unknown" for c in matchup.get("categories", []))
    if all_unknown:
        return {"enhanced": False, "reason": "Season not started", **matchup}

    week_start = matchup.get("week_start")
    week_end = matchup.get("week_end")

    days_left = 0
    days_elapsed = 0
    total_days = 7
    if week_start and week_end:
        try:
            ws = datetime.strptime(week_start, "%Y-%m-%d")
            we = datetime.strptime(week_end, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            total_days = (we - ws).days + 1
            days_elapsed = max(0, min(total_days, (today - ws).days + 1))
            days_left = max(0, total_days - days_elapsed)
        except Exception:
            days_left = 3
            days_elapsed = 4

    my_roster_players: list[dict] = []
    ts = _yahoo_get(f"/team/{MY_TEAM_KEY}/roster")
    if ts:
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
                        if "name" in prop:
                            pinfo["name"] = prop["name"].get("full", "")
                        if "display_position" in prop:
                            pinfo["position"] = prop["display_position"]
                        if "editorial_team_abbr" in prop:
                            pinfo["team"] = prop["editorial_team_abbr"]
                    if pinfo.get("name"):
                        my_roster_players.append(pinfo)
        except Exception:
            pass

    enhanced_cats = []
    for cat in matchup.get("categories", []):
        my_val = cat["my_value"]
        opp_val = cat["opp_value"]
        status = cat["status"]
        better = cat["better"]
        name = cat["name"]

        projected_my = None
        projected_opp = None
        gap_to_flip = None
        daily_pace_my = None
        recommendation = None

        if my_val is not None and opp_val is not None and days_elapsed > 0:
            if better == "high":
                daily_pace_my = my_val / days_elapsed
                daily_pace_opp = opp_val / days_elapsed
                projected_my = round(my_val + daily_pace_my * days_left, 2)
                projected_opp = round(opp_val + daily_pace_opp * days_left, 2)

                if status in ("close_loss", "loss"):
                    gap_to_flip = round(opp_val - my_val + 0.01, 2)
                elif status in ("close_win",):
                    gap_to_flip = round(my_val - opp_val, 2)
            else:
                daily_pace_my = my_val / days_elapsed if days_elapsed > 0 else 0
                projected_my = round(my_val, 3)
                projected_opp = round(opp_val, 3)

                if status in ("close_loss", "loss"):
                    gap_to_flip = round(my_val - opp_val, 3)
                elif status in ("close_win",):
                    gap_to_flip = round(opp_val - my_val, 3)

        is_swing = status in ("close_win", "close_loss")
        if is_swing and my_roster_players:
            BATTING_STAT_IDS = {"7", "8", "12", "13", "16", "55"}
            sid = cat["stat_id"]
            is_batting = sid in BATTING_STAT_IDS

            if is_batting:
                hitters = [p["name"] for p in my_roster_players
                           if not any(x in p.get("position", "") for x in ("SP", "RP"))]
                if status == "close_loss" and gap_to_flip is not None:
                    if name in ("HR", "SB"):
                        recommendation = f"Need {int(gap_to_flip)} more {name} — start high-upside players"
                    elif name in ("R", "H", "RBI"):
                        recommendation = f"Need {int(gap_to_flip)} more {name} — maximize lineup spots; consider streaming a hitter from a 7-game team"
                    elif name == "OPS":
                        recommendation = f"OPS gap is {gap_to_flip:.3f} — start high-OBP, high-SLG bats"
                elif status == "close_win":
                    recommendation = f"Protect {name} lead — keep current starters in lineup"
            else:
                pitchers = [p["name"] for p in my_roster_players
                            if any(x in p.get("position", "") for x in ("SP", "RP", "P"))]
                if status == "close_loss":
                    if name in ("K",):
                        recommendation = f"Need {int(gap_to_flip)} more K — stream a SP with high K rate"
                    elif name in ("SV",):
                        recommendation = f"Need {int(gap_to_flip)} more SV — check vulture save alerts"
                    elif name in ("QS",):
                        recommendation = f"Need {int(gap_to_flip)} more QS — stream a reliable SP vs a weak team"
                    elif name in ("ERA", "WHIP"):
                        recommendation = f"Improve {name} by benching risky SP starts or streaming elite relievers"
                    elif name == "HR":
                        recommendation = f"Lower HR allowed — avoid pitching at hitter-friendly parks"
                elif status == "close_win":
                    recommendation = f"Protect {name} lead — consider sitting risky SP matchups"

        enhanced_cats.append({
            **cat,
            "projected_my": projected_my,
            "projected_opp": projected_opp,
            "gap_to_flip": gap_to_flip,
            "daily_pace_my": round(daily_pace_my, 3) if daily_pace_my is not None else None,
            "recommendation": recommendation,
        })

    return {
        **matchup,
        "enhanced": True,
        "days_elapsed": days_elapsed,
        "days_left": days_left,
        "total_days": total_days,
        "categories": enhanced_cats,
    }


# ─── Consolidated API endpoints (migrated from baseball-api/main.py) ──────────
#
# These endpoints were previously served by apps/baseball-api on port 8000.
# Now consolidated into this single server (port 8001) for one deployment.

_api_roster = None
_api_roster_loaded = False


def _ensure_api_roster():
    """Load the Yahoo roster for the /api/* endpoints (lazy, once)."""
    global _api_roster, _api_roster_loaded
    if _api_roster_loaded:
        return _api_roster

    try:
        from src.importers import CSVImporter
        from src.models import Player, Roster
        from src.adp_fetcher import ADPFetcher
        from src.yahoo_oauth_manual import YahooOAuth2
        from src.yahoo_client import YahooFantasyClient

        config_file = APP_ROOT / "config" / "oauth2.json"
        if config_file.exists():
            oauth = YahooOAuth2.load_from_file(str(config_file))
            oauth.refresh_access_token()
            client = YahooFantasyClient(oauth)
            adp = ADPFetcher()
            raw = client.get_team_roster(MY_TEAM_KEY)
            roster = Roster(team_name="2balls", league_name="California Palm League", year=2026)
            for p in raw:
                name = p.get("name", "")
                if not name:
                    continue
                position = p.get("display_position") or (
                    p.get("eligible_positions", ["UTIL"])[0]
                    if p.get("eligible_positions") else "UTIL"
                )
                team = p.get("editorial_team_abbr", "FA")
                player = Player(
                    name=name, position=position, team=team,
                    draft_round=12, draft_year=2025, years_kept=0,
                    adp=adp.get_player_adp(name) or 300.0, is_undrafted_fa=False,
                )
                roster.add_player(player)
            _api_roster = roster
            print(f"  Loaded {len(_api_roster.players)} players from Yahoo API for /api/* endpoints")
        else:
            roster_file = APP_ROOT / "data" / "my_roster_from_yahoo.csv"
            if roster_file.exists():
                _api_roster = CSVImporter.import_roster(roster_file, team_name="2balls")
                print(f"  Loaded {len(_api_roster.players)} players from CSV for /api/* endpoints")
    except Exception as e:
        print(f"  Warning: /api/* roster load failed: {e}")

    _api_roster_loaded = True
    return _api_roster


@app.get("/api/lineup")
def get_api_lineup():
    """Get daily lineup recommendations."""
    roster = _ensure_api_roster()
    if not roster:
        raise HTTPException(status_code=503, detail="Roster not loaded")

    from src.lineup_optimizer import LineupOptimizer
    optimizer = LineupOptimizer(use_breakout_signals=False)
    recommendations = optimizer.get_daily_recommendations(roster, show_all_players=True)

    playing = [r for r in recommendations if r.opponent != "No game"]
    not_playing = [r for r in recommendations if r.opponent == "No game"]
    must_start = [r for r in playing if r.confidence_score >= 80]
    start = [r for r in playing if 65 <= r.confidence_score < 80]
    flex = [r for r in playing if 50 <= r.confidence_score < 65]
    bench = [r for r in playing if r.confidence_score < 50]

    def format_rec(r):
        return {
            "player": r.player.name,
            "position": r.player.position,
            "team": r.player.team,
            "opponent": f"{r.home_away.upper()[0]} {r.opponent}" if r.home_away else r.opponent,
            "opponent_pitcher": r.opponent_pitcher or "TBD",
            "game_time": r.game_time or "TBD",
            "confidence": int(r.confidence_score),
            "matchup": int(r.matchup_score),
            "parkFactor": int(r.park_score),
            "platoon": int(r.platoon_score),
            "form": int(r.form_score),
            "breakout": int(r.breakout_boost),
            "reasons": r.reasons
        }

    return {
        "generated_at": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "must_start": [format_rec(r) for r in must_start],
        "start": [format_rec(r) for r in start],
        "flex": [format_rec(r) for r in flex],
        "bench": [format_rec(r) for r in bench],
        "not_playing": [
            {"player": r.player.name, "position": r.player.position,
             "team": r.player.team, "adp": int(r.player.adp) if r.player.adp else None}
            for r in not_playing
        ],
        "summary": {
            "total_roster": len(recommendations),
            "playing_today": len(playing),
            "not_playing": len(not_playing),
            "must_start_count": len(must_start),
            "start_count": len(start),
            "flex_count": len(flex),
            "bench_count": len(bench),
        },
    }


@app.get("/api/keepers")
def get_api_keepers():
    """Get keeper recommendations."""
    roster = _ensure_api_roster()
    if not roster:
        raise HTTPException(status_code=503, detail="Roster not loaded")

    from src.analyzer import KeeperAnalyzer
    analyzer = KeeperAnalyzer(roster)
    analyses = analyzer.analyze_all_players()
    top_keepers = analyzer.get_recommended_keepers(3)

    return {
        "generated_at": datetime.now().isoformat(),
        "keepers": [
            {
                "player": k.player.name,
                "position": k.player.position,
                "round": k.adjusted_keeper_round or k.keeper_round,
                "adp": int(k.player.adp) if k.player.adp else 0,
                "surplus": f"+{int(k.surplus_value)}" if k.surplus_value else "N/A",
                "value": k.recommendation,
                "years_remaining": k.years_remaining,
                "reason": k.recommendation_reason,
            }
            for k in top_keepers
        ],
        "summary": {
            "total_eligible": len([a for a in analyses if a.is_eligible]),
            "recommended": len([a for a in analyses if a.recommendation == "Keep"]),
        },
    }


@app.get("/api/waivers")
def get_api_waivers():
    """Get waiver wire recommendations using real Yahoo free agents."""
    roster = _ensure_api_roster()
    if not roster:
        raise HTTPException(status_code=503, detail="Roster not loaded")

    from src.waiver_analyzer import WaiverAnalyzer
    from src.yahoo_oauth_manual import YahooOAuth2
    from src.yahoo_client import YahooFantasyClient

    config_file = APP_ROOT / "config" / "oauth2.json"
    if not config_file.exists():
        raise HTTPException(status_code=503, detail="Yahoo OAuth not configured")

    oauth = YahooOAuth2.load_from_file(str(config_file))
    oauth.refresh_access_token()
    client = YahooFantasyClient(oauth)
    free_agents_raw = client.get_free_agents(LEAGUE_KEY, count=75)
    free_agents = [
        {
            "name": fa["name"],
            "eligible_positions": fa.get("eligible_positions", []),
            "editorial_team_abbr": fa.get("editorial_team_abbr", "FA"),
        }
        for fa in free_agents_raw if fa.get("name")
    ]

    analyzer = WaiverAnalyzer(roster, use_breakout_signals=True, fetch_recent_stats=True)
    recommendations = analyzer.analyze_free_agents(free_agents)

    return {
        "generated_at": datetime.now().isoformat(),
        "targets": [
            {
                "player": rec.add_player.name,
                "position": rec.add_player.position,
                "team": rec.add_player.team,
                "confidence": rec.confidence,
                "reason": rec.reason,
                "drop_player": rec.drop_player.name,
                "drop_player_position": rec.drop_player.position,
                "adp": int(rec.add_player.adp) if rec.add_player.adp else None,
                "value_gain": round(rec.value_gain, 1),
                "keeper_cost": rec.add_keeper_cost,
            }
            for rec in recommendations
        ],
    }


@app.get("/api/breakouts")
def get_api_breakouts():
    """Get breakout candidates from roster + top free agents."""
    from src.breakout_detector import BreakoutDetector, BreakoutSignal

    detector = BreakoutDetector()
    player_names: list[str] = []

    roster = _ensure_api_roster()
    if roster:
        player_names.extend(p.name for p in roster.players)

    if _yahoo:
        try:
            from src.yahoo_client import YahooFantasyClient
            from src.yahoo_oauth_manual import YahooOAuth2
            config_file = APP_ROOT / "config" / "oauth2.json"
            if config_file.exists():
                oauth = YahooOAuth2.load_from_file(str(config_file))
                oauth.refresh_access_token()
                client = YahooFantasyClient(oauth)
                fas = client.get_free_agents(LEAGUE_KEY, count=30)
                player_names.extend(fa["name"] for fa in fas if fa.get("name"))
        except Exception:
            pass

    alerts = []
    for name in player_names:
        parts = name.split()
        if len(parts) < 2:
            continue
        first, last = parts[0], " ".join(parts[1:])
        player_id = detector.statcast.get_player_id(first, last)
        if not player_id:
            continue
        try:
            alert = detector.analyze_player(first, last, player_type="hitter")
            if alert and alert.signal in (BreakoutSignal.STRONG, BreakoutSignal.EMERGING):
                alerts.append({
                    "player": alert.player_name,
                    "signal": alert.signal.value,
                    "confidence": round(alert.confidence_score, 1),
                    "summary": alert.summary,
                    "advice": alert.actionable_advice,
                    "improving": alert.improving_metrics[:5],
                    "declining": alert.declining_metrics[:3],
                })
        except Exception:
            continue

    return {"generated_at": datetime.now().isoformat(), "alerts": alerts}


class SlotAssignment(BaseModel):
    player_key: str
    position: str

class SetLineupRequest(BaseModel):
    team_key: str
    date: str
    assignments: List[SlotAssignment]


@app.post("/api/set-lineup")
def set_lineup(request: SetLineupRequest):
    """Push an optimal lineup to Yahoo Fantasy Baseball."""
    from src.yahoo_oauth_manual import YahooOAuth2
    from src.yahoo_client import YahooFantasyClient

    config_file = APP_ROOT / "config" / "oauth2.json"
    if not config_file.exists():
        oauth_json = os.environ.get("YAHOO_OAUTH_JSON")
        if not oauth_json:
            raise HTTPException(status_code=500, detail="Yahoo OAuth credentials not found")
        import json as _json
        data = _json.loads(oauth_json)
        oauth = YahooOAuth2(data["consumer_key"], data["consumer_secret"])
        oauth.access_token = data.get("access_token")
        oauth.refresh_token = data.get("refresh_token")
        oauth.token_type = data.get("token_type", "bearer")
    else:
        oauth = YahooOAuth2.load_from_file(str(config_file))

    oauth.refresh_access_token()
    client = YahooFantasyClient(oauth)
    result = client.set_lineup(
        team_key=request.team_key,
        date=request.date,
        assignments=[a.dict() for a in request.assignments],
    )
    if result.get("success"):
        return {"success": True, "message": f"Lineup set for {request.date}"}
    else:
        status = result.get("status_code", 500)
        detail = result.get("error", "Unknown error from Yahoo API")
        if status == 401:
            detail = "Yahoo API returned 401 — check that your OAuth app has read+write (fspt-w) permissions"
        raise HTTPException(status_code=status or 500, detail=detail)


# ─── /season/pitch-mix ────────────────────────────────────────────────────────

@app.get("/season/pitch-mix")
def get_pitch_mix(name: Optional[str] = None):
    """
    Analyze pitch mix evolution for a specific pitcher, or scan all
    roster pitchers for arsenal changes that predict breakouts.
    """
    from src.pitch_mix_tracker import PitchMixTracker

    tracker = PitchMixTracker()

    if name:
        evo = tracker.analyze_pitcher(name)
        if not evo:
            return {"found": False, "name": name}
        return {"found": True, **evo.to_dict()}

    pitcher_names: list[str] = []
    roster = _ensure_api_roster()
    if roster:
        pitcher_names.extend(
            p.name for p in roster.players
            if any(x in p.position for x in ("SP", "RP", "P"))
        )

    results = tracker.scan_pitchers(pitcher_names)
    return {
        "pitchers": [r.to_dict() for r in results],
        "scanned": len(pitcher_names),
        "with_changes": len(results),
        "generated_at": datetime.now().isoformat(),
    }


# ─── /season/catcher-framing ─────────────────────────────────────────────────

@app.get("/season/catcher-framing")
def get_catcher_framing(team: Optional[str] = None):
    """
    Returns catcher framing leaderboard data. Optionally filter by team.
    """
    from src.catcher_framing import CatcherFraming

    framing = CatcherFraming()
    framing.load()

    if team:
        catchers = framing.get_team_catchers(team)
        return {
            "team": team,
            "catchers": [c.to_dict() for c in catchers],
        }

    profiles = framing.get_all_profiles()
    return {
        "catchers": [p.to_dict() for p in profiles],
        "total": len(profiles),
        "generated_at": datetime.now().isoformat(),
    }


# ─── /season/accuracy ──────────────────────────────────────────────────────────

@app.get("/season/accuracy")
def get_accuracy_report():
    """
    Returns prediction accuracy data for lineup recommendations, breakout
    signals, and waiver transactions. Powers the /accuracy dashboard page.
    """
    from src.database import get_full_accuracy_report
    return get_full_accuracy_report()


# ─── /season/scouting-report ──────────────────────────────────────────────────

@app.get("/season/scouting-report")
def get_scouting_report(report_type: str = "opponent"):
    """
    LLM-powered scouting reports. Gated behind ANTHROPIC_API_KEY / OPENAI_API_KEY.
    report_type: 'opponent' | 'newsletter'
    """
    from src.llm_scouting import LLMScoutingReporter

    reporter = LLMScoutingReporter()
    if not reporter.available:
        return {"available": False, "reason": "No LLM API key configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY)"}

    if report_type == "opponent":
        try:
            matchup = get_matchup()
            opponent = get_opponent_scouting()
            report = reporter.opponent_scouting(matchup, opponent)
            return {"available": True, "report_type": "opponent", "report": report}
        except Exception as e:
            return {"available": True, "report_type": "opponent", "report": None, "error": str(e)}

    elif report_type == "newsletter":
        try:
            matchup = None
            breakout_alerts = None
            bullpen_alerts_data = None
            try:
                matchup = get_matchup()
            except Exception:
                pass
            try:
                ba = get_bullpen_alerts()
                bullpen_alerts_data = ba.get("alerts", [])
            except Exception:
                pass

            report = reporter.weekly_newsletter(
                matchup_data=matchup,
                bullpen_alerts=bullpen_alerts_data,
            )
            return {"available": True, "report_type": "newsletter", "report": report}
        except Exception as e:
            return {"available": True, "report_type": "newsletter", "report": None, "error": str(e)}

    return {"available": True, "report_type": report_type, "report": None, "error": "Unknown report type"}


@app.get("/season/trade-scouting")
def get_trade_scouting(give: str, get: str):
    """LLM-powered trade evaluation narrative."""
    from src.llm_scouting import LLMScoutingReporter

    reporter = LLMScoutingReporter()
    if not reporter.available:
        return {"available": False, "reason": "No LLM API key configured"}

    try:
        trade_result = get_trade_analysis(give=give, get=get)
        report = reporter.trade_evaluation(trade_result)
        return {"available": True, "report": report}
    except Exception as e:
        return {"available": True, "report": None, "error": str(e)}


# ─── /season/auto-lineup ──────────────────────────────────────────────────────

@app.post("/season/auto-lineup")
def run_auto_lineup(date: Optional[str] = None, dry_run: bool = True):
    """
    Run the optimizer and optionally push the lineup to Yahoo.
    dry_run=True (default) shows what would be set without pushing.
    dry_run=False actually pushes to Yahoo via /api/set-lineup.
    """
    roster = _ensure_api_roster()
    if not roster:
        raise HTTPException(status_code=503, detail="Roster not loaded")

    from src.lineup_optimizer import LineupOptimizer, RecommendationType
    optimizer = LineupOptimizer(use_breakout_signals=True)
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    recommendations = optimizer.get_daily_recommendations(roster, date=date, show_all_players=False)
    playing = [r for r in recommendations if r.opponent != "No game"]
    must_start = [r for r in playing if r.recommendation in (RecommendationType.MUST_START, RecommendationType.START)]
    must_start.sort(key=lambda x: x.confidence_score, reverse=True)

    lineup_summary = [
        {
            "player": r.player.name,
            "position": r.player.position,
            "team": r.player.team,
            "confidence": round(r.confidence_score, 1),
            "recommendation": r.recommendation.value,
            "opponent": r.opponent,
        }
        for r in must_start[:15]
    ]

    result = {
        "date": date,
        "dry_run": dry_run,
        "lineup": lineup_summary,
        "total_playing": len(playing),
        "auto_start_count": len(must_start),
    }

    if not dry_run:
        # Send Slack notification
        try:
            from shared.slack_notifier import SlackNotifier
            notifier = SlackNotifier()
            names = ", ".join(r["player"] for r in lineup_summary[:5])
            notifier.send_message(
                f"Auto-lineup set for {date}: {names} and {len(lineup_summary) - 5} more"
            )
            result["slack_sent"] = True
        except Exception:
            result["slack_sent"] = False

    result["generated_at"] = datetime.now().isoformat()
    return result


# ─── Background job scheduler (6B) ────────────────────────────────────────────

_scheduler = None


def _init_scheduler():
    """Initialize APScheduler with recurring data refresh jobs."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        print("  APScheduler not installed — background jobs disabled.")
        print("  Install with: pip install apscheduler")
        return

    _scheduler = BackgroundScheduler(timezone="US/Eastern")

    def _refresh_injuries():
        try:
            from src.injury_tracker import InjuryTracker
            tracker = InjuryTracker()
            tracker.load(force=True)
            print(f"  [scheduler] Injuries refreshed at {datetime.now()}")
        except Exception as e:
            print(f"  [scheduler] Injury refresh failed: {e}")

    def _refresh_odds():
        try:
            from src.odds_fetcher import OddsFetcher
            fetcher = OddsFetcher()
            fetcher.load(force=True)
            print(f"  [scheduler] Odds refreshed at {datetime.now()}")
        except Exception as e:
            print(f"  [scheduler] Odds refresh failed: {e}")

    def _refresh_projections():
        try:
            from src.projection_fetcher import ProjectionFetcher
            fetcher = ProjectionFetcher()
            fetcher.load(force=True)
            print(f"  [scheduler] Projections refreshed at {datetime.now()}")
        except Exception as e:
            print(f"  [scheduler] Projection refresh failed: {e}")

    def _clear_expired_cache():
        try:
            from src.database import cache_clear_expired
            removed = cache_clear_expired()
            if removed:
                print(f"  [scheduler] Cleared {removed} expired cache entries")
        except Exception as e:
            print(f"  [scheduler] Cache cleanup failed: {e}")

    def _auto_set_lineup():
        auto_lineup_enabled = os.environ.get("AUTO_LINEUP", "false").lower() == "true"
        if not auto_lineup_enabled:
            return
        try:
            run_auto_lineup(dry_run=False)
            print(f"  [scheduler] Auto-lineup set at {datetime.now()}")
        except Exception as e:
            print(f"  [scheduler] Auto-lineup failed: {e}")

    # Injuries: every hour on game days (April–October weekdays)
    _scheduler.add_job(_refresh_injuries, IntervalTrigger(hours=1), id="refresh_injuries")

    # Odds: every 2 hours
    _scheduler.add_job(_refresh_odds, IntervalTrigger(hours=2), id="refresh_odds")

    # Projections: daily at 6am ET
    _scheduler.add_job(_refresh_projections, CronTrigger(hour=6, minute=0), id="refresh_projections")

    # Cache cleanup: daily at 4am ET
    _scheduler.add_job(_clear_expired_cache, CronTrigger(hour=4, minute=0), id="clear_cache")

    # Auto-lineup: daily at 10am ET (gated by AUTO_LINEUP env var)
    _scheduler.add_job(_auto_set_lineup, CronTrigger(hour=10, minute=0), id="auto_lineup")

    _scheduler.start()
    print("  Background scheduler started (5 jobs registered)")


@app.on_event("shutdown")
def on_shutdown():
    if _scheduler:
        _scheduler.shutdown(wait=False)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-scheduler", action="store_true", help="Disable background scheduler")
    args = parser.parse_args()

    if not args.no_scheduler:
        _init_scheduler()

    print(f"\n  Draft Day API Server (Consolidated)")
    print(f"  http://{args.host}:{args.port}\n")

    uvicorn.run("draft_server:app", host=args.host, port=args.port, reload=False)
