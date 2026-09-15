"""Power rankings computed locally from Yahoo week data.

The ESPN pipeline got rankings from a FastAPI endpoint that replayed box scores.
The Yahoo pipeline has no server, so this module derives rankings from the data
a single scoreboard + standings fetch already gives us: record, points for,
current-week score, and streak.

Rankings are persisted to ``power_rankings_history.json`` (CWD-relative, like
the other history files) so the next week can report movement.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from src.slack_mentions import message_mention

POWER_RANKINGS_HISTORY_FILE = "power_rankings_history.json"

# Weights by season phase. Early on, record is noise and scoring is signal.
_WEIGHTS = {
    "early": {"record": 0.30, "points": 0.45, "recent": 0.20, "streak": 0.05},
    "mid": {"record": 0.35, "points": 0.38, "recent": 0.22, "streak": 0.05},
    "late": {"record": 0.40, "points": 0.33, "recent": 0.19, "streak": 0.08},
}


def _phase(week: int) -> str:
    if week <= 3:
        return "early"
    if week <= 10:
        return "mid"
    return "late"


def _normalize(value: float, values: List[float]) -> float:
    """Min-max a value into 0..1, treating a flat field as all-average."""
    if not values:
        return 0.5
    low, high = min(values), max(values)
    if high - low < 1e-9:
        return 0.5
    return (value - low) / (high - low)


def _streak_score(streak: str) -> float:
    """Turn a streak like 'W3' / 'L2' into a signed magnitude, capped at 5."""
    if not streak or len(streak) < 2:
        return 0.0
    kind, _, digits = streak[0].upper(), None, streak[1:]
    try:
        length = min(int(digits), 5)
    except ValueError:
        return 0.0
    if kind == "W":
        return float(length)
    if kind == "L":
        return float(-length)
    return 0.0


def load_history(path: str = POWER_RANKINGS_HISTORY_FILE) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_history(
    week: int,
    rankings: List[Dict[str, Any]],
    path: str = POWER_RANKINGS_HISTORY_FILE,
) -> None:
    history = load_history(path)
    history[str(week)] = {
        str(r["team_key"]): r["rank"] for r in rankings if r.get("team_key")
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)


def compute_power_rankings(
    week_data: Dict[str, Any],
    week: int,
    history_path: str = POWER_RANKINGS_HISTORY_FILE,
) -> List[Dict[str, Any]]:
    """Rank every team, best first, with movement vs the previous week."""
    teams: List[Dict[str, Any]] = week_data.get("standings", {}).get("standings", [])
    if not teams:
        return []

    # This week's score per team, so "recent form" reflects the week we're
    # recapping rather than season-long averages.
    week_scores: Dict[str, float] = {}
    for matchup in week_data.get("matchups", {}).get("matchups", []):
        for key in ("home_team", "away_team"):
            side = matchup.get(key, {})
            if side.get("team_key"):
                week_scores[side["team_key"]] = side.get("score", 0.0)

    games_played = max(1, week)
    metrics = []
    for team in teams:
        metrics.append(
            {
                "team_key": team.get("team_key"),
                "team_id": team.get("team_id"),
                "team_name": team.get("team_name"),
                "owner": team.get("owner"),
                "wins": team.get("wins", 0),
                "losses": team.get("losses", 0),
                "ties": team.get("ties", 0),
                "pf": team.get("points_for", 0.0),
                "pa": team.get("points_against", 0.0),
                "streak": team.get("streak", "--"),
                "win_pct": team.get("win_pct", 0.0),
                "ppg": round(team.get("points_for", 0.0) / games_played, 2),
                "week_score": round(week_scores.get(team.get("team_key"), 0.0), 2),
                "streak_score": _streak_score(team.get("streak", "")),
            }
        )

    weights = _WEIGHTS[_phase(week)]
    fields = {
        "record": [m["win_pct"] for m in metrics],
        "points": [m["ppg"] for m in metrics],
        "recent": [m["week_score"] for m in metrics],
        "streak": [m["streak_score"] for m in metrics],
    }
    source_key = {
        "record": "win_pct",
        "points": "ppg",
        "recent": "week_score",
        "streak": "streak_score",
    }

    for metric in metrics:
        metric["score"] = round(
            sum(
                weight * _normalize(metric[source_key[name]], fields[name])
                for name, weight in weights.items()
            ),
            4,
        )

    metrics.sort(key=lambda m: (-m["score"], -m["pf"]))

    history = load_history(history_path)
    previous = history.get(str(week - 1), {})

    for index, metric in enumerate(metrics, 1):
        metric["rank"] = index
        prior = previous.get(str(metric["team_key"]))
        metric["previous_rank"] = prior
        if prior is None:
            metric["movement"] = "—"
            metric["movement_emoji"] = "—"
        else:
            delta = prior - index
            if delta > 0:
                metric["movement"] = f"+{delta}"
                metric["movement_emoji"] = f":triangle_upmaster: {delta}"
            elif delta < 0:
                metric["movement"] = str(delta)
                metric["movement_emoji"] = f":triangle_downred: {abs(delta)}"
            else:
                metric["movement"] = "—"
                metric["movement_emoji"] = "—"

    return metrics


def format_rankings_lines(rankings: List[Dict[str, Any]]) -> List[str]:
    """Render the exact ranking lines the recap must copy 1:1."""
    lines = []
    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        if r.get("ties"):
            record += f"-{r['ties']}"
        mention = message_mention(r["owner"], team_key=r.get("team_key"))
        lines.append(
            f"{r['rank']}. **{mention}** ({record}, PF {r['pf']:.1f}) "
            f"{r['movement_emoji']}"
        )
    return lines
