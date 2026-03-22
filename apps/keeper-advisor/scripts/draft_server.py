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
    rank:      int
    name:      str
    team:      str
    positions: List[str]
    adp:       float
    tier:      str
    reason:    str

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

class DraftState(BaseModel):
    status:        str          # predraft | live | complete
    picks_made:    int
    current_round: int
    phase:         str          # BATTER_PRIORITY | SP_WINDOW | CLOSER_MODE
    phase_label:   str
    my_next_pick:  Optional[NextPick]
    recommendations: List[Recommendation]
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

    return DraftState(
        status=status,
        picks_made=_board.picks_made,
        current_round=rnd,
        phase=phase,
        phase_label=label,
        my_next_pick=next_pick_info,
        recommendations=recommendations,
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
