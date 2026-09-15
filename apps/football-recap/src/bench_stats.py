"""Derives bench/lineup-efficiency numbers from fetched roster data.

Requires ``week_data["rosters"]`` (team_key -> list of player dicts), which
``YahooNFLClient.fetch_week_data`` populates when it can. A team missing from
``rosters`` (a failed fetch, or --no-fetch on cached data from before rosters
were added) is simply absent from these summaries rather than reported as a
zero -- a real zero and "we don't know" must never look the same.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def summarize_roster(players: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reduce one team's player list to starter/bench point totals."""
    starters_points = sum(p["points"] for p in players if not p["is_bench"])
    bench_players = sorted(
        (p for p in players if p["is_bench"]), key=lambda p: -p["points"]
    )
    bench_points = sum(p["points"] for p in bench_players)
    return {
        "starters_points": round(starters_points, 2),
        "bench_points": round(bench_points, 2),
        "bench_players": bench_players,
        "top_bench_player": bench_players[0] if bench_players else None,
    }


def summarize_all_rosters(
    rosters: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    """summarize_roster() for every team_key with roster data."""
    return {team_key: summarize_roster(players) for team_key, players in rosters.items()}


def pick_bench_hero(
    roster_summaries: Dict[str, Dict[str, Any]],
    team_lookup: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """League-wide: whose bench player outscored everyone else's bench this week.

    ``team_lookup`` maps team_key -> {"team_name": ..., "owner": ...} so the
    result can name the team, not just the player.
    """
    best_key: Optional[str] = None
    best_player: Optional[Dict[str, Any]] = None
    for team_key, summary in roster_summaries.items():
        top = summary.get("top_bench_player")
        if top and (best_player is None or top["points"] > best_player["points"]):
            best_key, best_player = team_key, top
    if not best_key or not best_player:
        return None
    team = team_lookup.get(best_key, {})
    return {
        "team_key": best_key,
        "team_name": team.get("team_name", "Unknown"),
        "owner": team.get("owner", "Unknown"),
        "player_name": best_player["name"],
        "points": best_player["points"],
    }
