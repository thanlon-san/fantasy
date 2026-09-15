"""Season-long award tracking for the League HQ canvas.

Power rankings only need last week's rank (``power_rankings_history.json``).
These awards need a running tally across every week played, so they get their
own history file: ``season_awards_history.json`` (CWD-relative, like the
other history files, and -- like ``power_rankings_history.json`` -- NOT
gitignored, since it must survive across cloud-agent runs that each start
from a fresh checkout).

Each award is stored as a *list of weeks* a team earned it, not a running
counter -- that makes re-running a week idempotent for free (drop the week
from every list, then re-add it wherever it now applies) instead of needing
separate undo bookkeeping that's easy to get wrong.

Shape::

    {
      "<team_key>": {
        "owner": "...", "team_name": "...",
        "upset_win_weeks": [1, 4],
        "blowout_win_weeks": [2],
        "low_score_weeks": [1],
        "bench_hero_weeks": [3],
        "bench_points_by_week": {"1": 68.9, ...}
      }
    }
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from src.bench_stats import pick_bench_hero, summarize_all_rosters

HISTORY_FILE = "season_awards_history.json"

_LIST_FIELDS = ("upset_win_weeks", "blowout_win_weeks", "low_score_weeks", "bench_hero_weeks")


def load_history(path: str = HISTORY_FILE) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_history(history: Dict[str, Any], path: str = HISTORY_FILE) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)


def _entry(history: Dict[str, Any], team_key: str, team: Dict[str, Any]) -> Dict[str, Any]:
    e = history.setdefault(
        team_key,
        {
            "owner": team.get("owner", "Unknown"),
            "team_name": team.get("team_name", "Unknown"),
            "upset_win_weeks": [],
            "blowout_win_weeks": [],
            "low_score_weeks": [],
            "bench_hero_weeks": [],
            "bench_points_by_week": {},
        },
    )
    # Names can change mid-season (Yahoo lets managers rename); keep current.
    e["owner"] = team.get("owner", e.get("owner", "Unknown"))
    e["team_name"] = team.get("team_name", e.get("team_name", "Unknown"))
    for field in _LIST_FIELDS:
        e.setdefault(field, [])
    e.setdefault("bench_points_by_week", {})
    return e


def record_week(
    week: int,
    week_data: Dict[str, Any],
    history_path: str = HISTORY_FILE,
) -> Dict[str, Any]:
    """Fold one week's results into the season-long award history.

    Idempotent: re-running the same week first clears any award that week
    previously earned, then recomputes from this week_data, so re-runs never
    double-count.
    """
    history = load_history(history_path)
    week_str = str(week)

    # Clear this week's prior contribution everywhere before recomputing.
    for entry in history.values():
        for field in _LIST_FIELDS:
            if week in entry.get(field, []):
                entry[field].remove(week)
        entry.get("bench_points_by_week", {}).pop(week_str, None)

    teams = week_data.get("standings", {}).get("standings", [])
    team_lookup = {t["team_key"]: t for t in teams if t.get("team_key")}
    matchups = week_data.get("matchups", {}).get("matchups", [])
    stats = week_data.get("week_stats", {})
    rosters = week_data.get("rosters", {})

    def award(team_key: Optional[str], field: str) -> None:
        if not team_key or team_key not in team_lookup:
            return
        entry = _entry(history, team_key, team_lookup[team_key])
        if week not in entry[field]:
            entry[field].append(week)
            entry[field].sort()

    for matchup in matchups:
        home, away = matchup["home_team"], matchup["away_team"]
        if matchup.get("winner") == home["team_name"]:
            winner_side, loser_side = home, away
        elif matchup.get("winner") == away["team_name"]:
            winner_side, loser_side = away, home
        else:
            continue
        winner_proj = winner_side.get("projected") or 0.0
        loser_proj = loser_side.get("projected") or 0.0
        if winner_proj and loser_proj and winner_proj < loser_proj:
            award(winner_side.get("team_key"), "upset_win_weeks")

    blowout = stats.get("biggest_blowout")
    if blowout:
        winner_team = next(
            (t for t in teams if t.get("team_name") == blowout.get("winner")), None
        )
        if winner_team:
            award(winner_team.get("team_key"), "blowout_win_weeks")

    lowest = stats.get("lowest_score")
    if lowest:
        low_team = next(
            (t for t in teams if t.get("owner") == lowest.get("owner")), None
        )
        if low_team:
            award(low_team.get("team_key"), "low_score_weeks")

    if rosters:
        summaries = summarize_all_rosters(rosters)
        for team_key, summary in summaries.items():
            if team_key not in team_lookup:
                continue
            entry = _entry(history, team_key, team_lookup[team_key])
            entry["bench_points_by_week"][week_str] = summary["bench_points"]

        hero = pick_bench_hero(summaries, team_lookup)
        if hero:
            award(hero["team_key"], "bench_hero_weeks")

    _save_history(history, history_path)
    return history


def compute_leaders(history: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
    """Reduce the history to one leader per award, or None if nobody qualifies."""
    empty = {
        key: None
        for key in (
            "bench_whisperer",
            "iron_fist",
            "human_highlight_reel",
            "giant_slayer",
            "the_hammer",
            "iron_stomach",
        )
    }
    if not history:
        return empty

    def top_by_weeks(field: str) -> Optional[Dict[str, Any]]:
        candidates = [
            (key, entry) for key, entry in history.items() if entry.get(field)
        ]
        if not candidates:
            return None
        key, entry = max(candidates, key=lambda kv: len(kv[1][field]))
        return {
            "team_key": key,
            "owner": entry["owner"],
            "team_name": entry["team_name"],
            "value": len(entry[field]),
        }

    bench_averages = []
    for key, entry in history.items():
        by_week = entry.get("bench_points_by_week", {})
        if by_week:
            avg = sum(by_week.values()) / len(by_week)
            bench_averages.append((key, entry, avg, len(by_week)))

    bench_whisperer = iron_fist = None
    if bench_averages:
        key, entry, avg, weeks = max(bench_averages, key=lambda t: t[2])
        bench_whisperer = {
            "team_key": key,
            "owner": entry["owner"],
            "team_name": entry["team_name"],
            "value": round(avg, 1),
            "weeks": weeks,
        }
        key, entry, avg, weeks = min(bench_averages, key=lambda t: t[2])
        iron_fist = {
            "team_key": key,
            "owner": entry["owner"],
            "team_name": entry["team_name"],
            "value": round(avg, 1),
            "weeks": weeks,
        }

    return {
        "bench_whisperer": bench_whisperer,
        "iron_fist": iron_fist,
        "human_highlight_reel": top_by_weeks("bench_hero_weeks"),
        "giant_slayer": top_by_weeks("upset_win_weeks"),
        "the_hammer": top_by_weeks("blowout_win_weeks"),
        "iron_stomach": top_by_weeks("low_score_weeks"),
    }
