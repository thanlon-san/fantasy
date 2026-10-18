"""
Weekly superlatives / awards computed from a ``week_data`` dict.

Each function is pure and takes the same shape produced by
:class:`~src.yahoo_fetcher.YahooLeagueFetcher.fetch_all_for_week`. The
top-level :func:`compute_superlatives` returns a flat dict keyed by award
label; callers (context builder, LLM prompt) can iterate in insertion order.

Design principle: only surface an award when the underlying data is
actually interesting. A boring "closest game: 8-point margin" isn't a
nail-biter and shouldn't get top billing. Thresholds intentionally err
toward *fewer, punchier* awards over "one award for every team."
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.constants import EXCELLENT_MANAGEMENT_GAP, MANAGEMENT_DISASTER_GAP
from src.ownership_stats import is_management_gap_roastable


# ---------------------------------------------------------------------------
# Thresholds — tuned to keep the awards feed sparse and punchy.
# ---------------------------------------------------------------------------

NAILBITER_MARGIN = 5.0          # < points = a genuine nail-biter
BLOWOUT_MARGIN = 30.0            # >= points = blowout
SHOOTOUT_COMBINED = 250.0        # combined score threshold
LOW_SCORING_COMBINED = 170.0     # combined score threshold for "cold war"
COACH_OF_WEEK_GAP = EXCELLENT_MANAGEMENT_GAP  # <= management gap for perfect(ish) lineup
BENCH_HERO_POINTS = 20.0         # bench player who out-scored their slot
UPSET_PROJECTION_DIFF = 15.0     # winner started with projection this far behind


def _iter_matchups(week_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    return week_data.get("matchups", {}).get("matchups", []) or []


def _teams(matchup: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [matchup["home_team"], matchup["away_team"]]


def _projected_score(team: Dict[str, Any]) -> float:
    return sum(p.get("projected_points", 0.0) for p in team.get("starters", []))


def compute_superlatives(week_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Return an ordered dict of award-label -> details.

    Consumers should treat missing keys as "no award earned this week" — the
    context builder prints only entries that are populated.
    """
    awards: Dict[str, Dict[str, Any]] = {}

    matchups = list(_iter_matchups(week_data))
    if not matchups:
        return awards

    # ---- Blowout / nail-biter / shootout / cold war -----------------------
    biggest = max(
        matchups,
        key=lambda m: abs(m["home_team"]["score"] - m["away_team"]["score"]),
    )
    biggest_margin = abs(
        biggest["home_team"]["score"] - biggest["away_team"]["score"]
    )
    if biggest_margin >= BLOWOUT_MARGIN:
        winner = _pick_winner(biggest)
        loser = _pick_loser(biggest)
        awards["blowout_of_the_week"] = {
            "label": "💥 Blowout of the Week",
            "team": winner["team_name"],
            "owner": winner.get("owner", ""),
            "opponent": loser["team_name"],
            "opponent_owner": loser.get("owner", ""),
            "margin": round(biggest_margin, 2),
        }

    closest = min(
        matchups,
        key=lambda m: abs(m["home_team"]["score"] - m["away_team"]["score"]),
    )
    closest_margin = abs(
        closest["home_team"]["score"] - closest["away_team"]["score"]
    )
    if closest_margin < NAILBITER_MARGIN:
        home = closest["home_team"]
        away = closest["away_team"]
        awards["nailbiter_of_the_week"] = {
            "label": "😰 Nail Biter of the Week",
            "team1": home["team_name"],
            "team2": away["team_name"],
            "margin": round(closest_margin, 2),
        }

    combined_scores = [
        (m, m["home_team"]["score"] + m["away_team"]["score"])
        for m in matchups
    ]
    biggest_combined = max(combined_scores, key=lambda kv: kv[1])
    if biggest_combined[1] >= SHOOTOUT_COMBINED:
        awards["shootout_of_the_week"] = {
            "label": "🎯 Shootout of the Week",
            "team1": biggest_combined[0]["home_team"]["team_name"],
            "team2": biggest_combined[0]["away_team"]["team_name"],
            "combined": round(biggest_combined[1], 2),
        }
    smallest_combined = min(combined_scores, key=lambda kv: kv[1])
    if smallest_combined[1] <= LOW_SCORING_COMBINED:
        awards["cold_war_of_the_week"] = {
            "label": "🥶 Cold War of the Week",
            "team1": smallest_combined[0]["home_team"]["team_name"],
            "team2": smallest_combined[0]["away_team"]["team_name"],
            "combined": round(smallest_combined[1], 2),
        }

    # ---- Coach-of-the-week / cooked ---------------------------------------
    all_teams = [t for m in matchups for t in _teams(m)]

    good_coaches = [
        t for t in all_teams
        if t.get("management_gap", 0) <= COACH_OF_WEEK_GAP
        and t.get("score", 0) > 0
    ]
    if good_coaches:
        best = min(good_coaches, key=lambda t: t.get("management_gap", 0))
        awards["coach_of_the_week"] = {
            "label": "🧠 Coach of the Week",
            "team": best["team_name"],
            "owner": best.get("owner", ""),
            "management_gap": round(best.get("management_gap", 0), 2),
            "score": best.get("score", 0),
        }

    cooked = [
        t
        for t in all_teams
        if t.get("management_gap", 0) >= MANAGEMENT_DISASTER_GAP
        and is_management_gap_roastable(t)
    ]
    if cooked:
        worst = max(cooked, key=lambda t: t.get("management_gap", 0))
        awards["cooked_of_the_week"] = {
            "label": "🍳 Cooked of the Week",
            "team": worst["team_name"],
            "owner": worst.get("owner", ""),
            "management_gap": round(worst.get("management_gap", 0), 2),
            "score": worst.get("score", 0),
        }

    # ---- Bench hero -------------------------------------------------------
    bench_stars = []
    for t in all_teams:
        for p in t.get("bench", []) or []:
            pts = p.get("actual_points", 0)
            if pts >= BENCH_HERO_POINTS:
                bench_stars.append((t, p))
    if bench_stars:
        top_team, top_player = max(
            bench_stars, key=lambda kv: kv[1].get("actual_points", 0)
        )
        awards["bench_hero_of_the_week"] = {
            "label": "🪑 Bench Hero of the Week",
            "player": top_player["name"],
            "position": top_player.get("position", ""),
            "points": round(top_player.get("actual_points", 0), 2),
            "team": top_team["team_name"],
            "owner": top_team.get("owner", ""),
        }

    # ---- Upset (winner was projected way lower) ---------------------------
    for m in matchups:
        winner = _pick_winner(m)
        loser = _pick_loser(m)
        winner_proj = _projected_score(winner)
        loser_proj = _projected_score(loser)
        if loser_proj - winner_proj >= UPSET_PROJECTION_DIFF:
            # First qualifying upset wins the award; loop stops.
            awards["upset_of_the_week"] = {
                "label": "🎲 Upset of the Week",
                "winner": winner["team_name"],
                "winner_owner": winner.get("owner", ""),
                "loser": loser["team_name"],
                "loser_owner": loser.get("owner", ""),
                "projection_gap": round(loser_proj - winner_proj, 2),
            }
            break

    return awards


def _pick_winner(matchup: Dict[str, Any]) -> Dict[str, Any]:
    home = matchup["home_team"]
    away = matchup["away_team"]
    return home if home["score"] >= away["score"] else away


def _pick_loser(matchup: Dict[str, Any]) -> Dict[str, Any]:
    home = matchup["home_team"]
    away = matchup["away_team"]
    return away if home["score"] >= away["score"] else home
