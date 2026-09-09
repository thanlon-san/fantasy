#!/usr/bin/env python3
"""Render the League HQ canvas markdown for an in-season week.

League HQ is the living reference doc: standings, power rankings, and season
awards. The weekly recap is the story; this is the scoreboard.

Writes ``output/league-hq-canvas.md`` (CWD-relative, like the rest of the
pipeline). The caller then pushes that file to the existing Slack canvas.

Usage:
    # Reuse the weekdata prepare_recap_context.py already cached (no Yahoo hit)
    python apps/football-recap/scripts/prepare_league_hq_canvas.py --week 1 --no-fetch

    # Fetch live, falling back to cache if Yahoo is unavailable
    python apps/football-recap/scripts/prepare_league_hq_canvas.py --week 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import OUTPUT_DIR  # noqa: E402
from src.power_rankings import compute_power_rankings  # noqa: E402
from src.yahoo_nfl_client import YahooError, YahooNFLClient  # noqa: E402

CANVAS_FILENAME = "league-hq-canvas.md"


def load_cached_weekdata(week: int) -> Optional[Dict[str, Any]]:
    path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def _standings_table(teams: List[Dict[str, Any]]) -> List[str]:
    lines = [
        "| # | Manager | Team | Record | PF | PA | Streak |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, team in enumerate(teams, 1):
        record = f"{team.get('wins', 0)}-{team.get('losses', 0)}"
        if team.get("ties"):
            record += f"-{team['ties']}"
        lines.append(
            f"| {index} | {team.get('owner', '?')} | {team.get('team_name', '?')} "
            f"| {record} | {team.get('points_for', 0):.1f} "
            f"| {team.get('points_against', 0):.1f} | {team.get('streak', '--')} |"
        )
    return lines


def _rankings_table(rankings: List[Dict[str, Any]]) -> List[str]:
    lines = ["| # | Manager | Record | PF | Move |", "| --- | --- | --- | --- | --- |"]
    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        if r.get("ties"):
            record += f"-{r['ties']}"
        lines.append(
            f"| {r['rank']} | {r['owner']} | {record} | {r['pf']:.1f} "
            f"| {r['movement']} |"
        )
    return lines


def _season_awards(teams: List[Dict[str, Any]], week: int) -> List[str]:
    if not teams:
        return []
    games = max(1, week)
    most_points = max(teams, key=lambda t: t.get("points_for", 0))
    fewest_points = min(teams, key=lambda t: t.get("points_for", 0))
    most_against = max(teams, key=lambda t: t.get("points_against", 0))
    best_diff = max(
        teams, key=lambda t: t.get("points_for", 0) - t.get("points_against", 0)
    )
    return [
        f"- **Most Points For** — {most_points.get('owner')} "
        f"({most_points.get('points_for', 0):.1f}, "
        f"{most_points.get('points_for', 0) / games:.1f}/wk)",
        f"- **Fewest Points For** — {fewest_points.get('owner')} "
        f"({fewest_points.get('points_for', 0):.1f})",
        f"- **Most Points Against** — {most_against.get('owner')} "
        f"({most_against.get('points_against', 0):.1f})",
        f"- **Best Differential** — {best_diff.get('owner')} "
        f"({best_diff.get('points_for', 0) - best_diff.get('points_against', 0):+.1f})",
    ]


def build_canvas(week_data: Dict[str, Any], week: int) -> str:
    league = week_data.get("league", {})
    teams = week_data.get("standings", {}).get("standings", [])
    rankings = compute_power_rankings(week_data, week)
    stats = week_data.get("week_stats", {})

    parts: List[str] = []
    parts.append(f"# 🏈 {league.get('league_name', 'League HQ')}")
    parts.append(
        f"_Through Week {week} · updated "
        f"{datetime.now().strftime('%b %d, %Y')}_"
    )

    parts.append("\n## Standings")
    parts.extend(_standings_table(teams) if teams else ["_No standings available._"])

    parts.append("\n## Power Rankings")
    parts.extend(_rankings_table(rankings) if rankings else ["_Not enough data yet._"])

    parts.append(f"\n## Week {week} Highlights")
    high, low = stats.get("highest_score"), stats.get("lowest_score")
    if high:
        parts.append(
            f"- **High score** — {high['owner']} ({high['points']:.1f})"
        )
    if low:
        parts.append(f"- **Low score** — {low['owner']} ({low['points']:.1f})")
    if stats.get("closest_game"):
        game = stats["closest_game"]
        parts.append(
            f"- **Closest game** — {game['team1']} vs {game['team2']} "
            f"({game['margin']:.1f})"
        )
    if stats.get("biggest_blowout"):
        game = stats["biggest_blowout"]
        parts.append(
            f"- **Biggest blowout** — {game['winner']} over {game['loser']} "
            f"({game['margin']:.1f})"
        )
    if not any([high, low, stats.get("closest_game")]):
        parts.append("_No scoring data for this week._")

    awards = _season_awards(teams, week)
    if awards:
        parts.append("\n## Season Awards (running)")
        parts.extend(awards)

    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, required=True, help="NFL week number")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Read output/week-<N>-weekdata.json instead of hitting Yahoo.",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(OUTPUT_DIR, CANVAS_FILENAME),
        help="Where to write the canvas markdown.",
    )
    args = parser.parse_args()
    week = args.week

    week_data: Optional[Dict[str, Any]] = None

    if args.no_fetch:
        week_data = load_cached_weekdata(week)
        if week_data is None:
            print(
                f"--no-fetch was set but no cache exists at "
                f"{OUTPUT_DIR}/week-{week}-weekdata.json",
                file=sys.stderr,
            )
            return 1
        print(f"Using cached week {week} data")
    else:
        try:
            week_data = YahooNFLClient().fetch_week_data(week)
            print(f"Fetched week {week} from Yahoo")
        except YahooError as exc:
            print(f"Yahoo fetch failed ({exc.code}): {exc}", file=sys.stderr)
            week_data = load_cached_weekdata(week)
            if week_data is None:
                print("No cached fallback available.", file=sys.stderr)
                return 1
            print("Falling back to cached week data")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(build_canvas(week_data, week))

    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
