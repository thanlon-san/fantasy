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
