"""
Season-long leaderboard/achievements, aggregated across recap_history.json.

Reads the same ``week_data`` shape produced by
:class:`~src.yahoo_fetcher.YahooLeagueFetcher.fetch_all_for_week` and
persisted per-week by ``RecapGenerator.finalize_recap`` (under
``history_entry["context"]["data"]``).

Design principle: this is meant to run in a casual, low-stakes league.
Categories are framed as playful achievements, not personal call-outs —
even the "negative" ones (most bench points wasted, most last-place
finishes) use a light, affectionate name rather than a shame label. Keep
new categories in that spirit.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

# Single recurring trophy surfaced in the weekly Slack digest (updated each week).
SLACK_SEASON_TROPHY_KEY = "bench_whisperer"


def _week_data_entries(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract (week, week_data) pairs from recap_history.json entries."""
    out = []
    for entry in history:
        data = (entry.get("context") or {}).get("data")
        if data:
            out.append({"week": entry.get("week"), "data": data})
    return out


def _all_matchup_teams(week_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    matchups = week_data.get("matchups", {}).get("matchups", []) or []
    teams = []
    for m in matchups:
        for side in ("home_team", "away_team"):
            t = m.get(side)
            if t:
                teams.append(t)
    return teams


def compute_season_awards(
    history: List[Dict[str, Any]],
    *,
    latest_standings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Aggregate season-long achievements from weekly history.

    Returns a dict of category -> details, safe to render directly into a
    Slack Canvas or recap. Categories with no qualifying data are omitted.
    """
    entries = _week_data_entries(history)
    if not entries:
        return {"weeks_played": 0, "awards": {}}

    awards: Dict[str, Any] = {}

    # ---- Bench Whisperer (most cumulative points left on the bench) -------
    # Framed positively: "your bench had a big week, shame you didn't know
    # it" rather than "worst manager."
    bench_totals: Dict[str, float] = defaultdict(float)
    bench_owner: Dict[str, str] = {}
    for e in entries:
        for t in _all_matchup_teams(e["data"]):
            name = t.get("team_name")
            if not name:
                continue
            bench_totals[name] += t.get("management_gap", 0.0) or 0.0
            bench_owner[name] = t.get("owner", "")
    if bench_totals:
        top_team = max(bench_totals, key=lambda k: bench_totals[k])
        awards["bench_whisperer"] = {
            "label": "🪑 The Bench Whisperer",
            "description": "Most cumulative points left on the bench this season.",
            "team": top_team,
            "owner": bench_owner.get(top_team, ""),
            "total_points_left": round(bench_totals[top_team], 2),
        }

    # ---- Iron Fist (best cumulative lineup management, i.e. smallest gap) -
    management_totals: Dict[str, List[float]] = defaultdict(list)
    for e in entries:
        for t in _all_matchup_teams(e["data"]):
            name = t.get("team_name")
            if not name:
                continue
            management_totals[name].append(t.get("management_gap", 0.0) or 0.0)
    if management_totals:
        avg_gap = {
            name: sum(gaps) / len(gaps) for name, gaps in management_totals.items()
        }
        best_team = min(avg_gap, key=lambda k: avg_gap[k])
        awards["iron_fist"] = {
            "label": "🧠 Iron Fist Award",
            "description": "Smallest average points left on the bench — a lineup savant.",
            "team": best_team,
            "owner": bench_owner.get(best_team, ""),
            "avg_points_left": round(avg_gap[best_team], 2),
        }

    # ---- Human Highlight Reel (most bench-hero superlatives earned) -------
    bench_hero_counts: Dict[str, int] = defaultdict(int)
    bench_hero_owner: Dict[str, str] = {}
    upset_counts: Dict[str, int] = defaultdict(int)
    upset_owner: Dict[str, str] = {}
    blowout_counts: Dict[str, int] = defaultdict(int)
    blowout_owner: Dict[str, str] = {}
    for e in entries:
        sup = e["data"].get("superlatives", {}) or {}
        bh = sup.get("bench_hero_of_the_week")
        if bh:
            bench_hero_counts[bh["team"]] += 1
            bench_hero_owner[bh["team"]] = bh.get("owner", "")
        up = sup.get("upset_of_the_week")
        if up:
            upset_counts[up["winner"]] += 1
            upset_owner[up["winner"]] = up.get("winner_owner", "")
        bo = sup.get("blowout_of_the_week")
        if bo:
            blowout_counts[bo["team"]] += 1
            blowout_owner[bo["team"]] = bo.get("owner", "")

    if bench_hero_counts:
        top = max(bench_hero_counts, key=lambda k: bench_hero_counts[k])
        awards["human_highlight_reel"] = {
            "label": "🎬 Human Highlight Reel",
            "description": "Most Bench Hero of the Week awards — the bench that keeps producing.",
            "team": top,
            "owner": bench_hero_owner.get(top, ""),
            "count": bench_hero_counts[top],
        }

    if upset_counts:
        top = max(upset_counts, key=lambda k: upset_counts[k])
        awards["giant_slayer"] = {
            "label": "🎲 Giant Slayer",
            "description": "Most Upset of the Week wins — nobody saw these coming.",
            "team": top,
            "owner": upset_owner.get(top, ""),
            "count": upset_counts[top],
        }

    if blowout_counts:
        top = max(blowout_counts, key=lambda k: blowout_counts[k])
        awards["hammer"] = {
            "label": "🔨 The Hammer",
            "description": "Most Blowout of the Week wins — shows no mercy.",
            "team": top,
            "owner": blowout_owner.get(top, ""),
            "count": blowout_counts[top],
        }

    # ---- Closest call of the season ---------------------------------------
    closest: Optional[Dict[str, Any]] = None
    for e in entries:
        for m in e["data"].get("matchups", {}).get("matchups", []) or []:
            home, away = m.get("home_team", {}), m.get("away_team", {})
            margin = abs(home.get("score", 0) - away.get("score", 0))
            if closest is None or margin < closest["margin"]:
                closest = {
                    "week": e["week"],
                    "team1": home.get("team_name"),
                    "team2": away.get("team_name"),
                    "margin": round(margin, 2),
                }
    if closest:
        awards["nail_biter_of_the_season"] = {
            "label": "😰 Nail-Biter of the Season",
            "description": f"Closest margin all year, Week {closest['week']}.",
            **closest,
        }

    # ---- Biggest blowout of the season ------------------------------------
    biggest: Optional[Dict[str, Any]] = None
    for e in entries:
        for m in e["data"].get("matchups", {}).get("matchups", []) or []:
            home, away = m.get("home_team", {}), m.get("away_team", {})
            margin = abs(home.get("score", 0) - away.get("score", 0))
            if biggest is None or margin > biggest["margin"]:
                winner, loser = (
                    (home, away) if home.get("score", 0) >= away.get("score", 0) else (away, home)
                )
                biggest = {
                    "week": e["week"],
                    "winner": winner.get("team_name"),
                    "loser": loser.get("team_name"),
                    "margin": round(margin, 2),
                }
    if biggest:
        awards["blowout_of_the_season"] = {
            "label": "💥 Blowout of the Season",
            "description": f"Biggest margin all year, Week {biggest['week']}.",
            **biggest,
        }

    # ---- Iron Stomach (most weeks finishing last in that week's scores) ---
    # Framed as resilience, not shame — "kept showing up."
    last_place_counts: Dict[str, int] = defaultdict(int)
    last_place_owner: Dict[str, str] = {}
    for e in entries:
        teams = _all_matchup_teams(e["data"])
        if not teams:
            continue
        lowest = min(teams, key=lambda t: t.get("score", 0))
        name = lowest.get("team_name")
        if name:
            last_place_counts[name] += 1
            last_place_owner[name] = lowest.get("owner", "")
    if last_place_counts:
        top = max(last_place_counts, key=lambda k: last_place_counts[k])
        awards["iron_stomach"] = {
            "label": "💪 Iron Stomach Award",
            "description": "Most weeks with the low score — still showing up every Sunday.",
            "team": top,
            "owner": last_place_owner.get(top, ""),
            "count": last_place_counts[top],
        }

    return {"weeks_played": len(entries), "awards": awards}
