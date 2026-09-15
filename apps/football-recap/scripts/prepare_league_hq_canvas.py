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
from src.season_awards import compute_leaders, load_history  # noqa: E402
from src.slack_mentions import canvas_mention  # noqa: E402
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


def _mention(team: Dict[str, Any]) -> str:
    return canvas_mention(team.get("owner", "?"), team_key=team.get("team_key"))


def _standings_table(teams: List[Dict[str, Any]]) -> List[str]:
    lines = [
        "| # | Team | Owner | Record | PF | PA | Streak |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, team in enumerate(teams, 1):
        record = f"{team.get('wins', 0)}-{team.get('losses', 0)}"
        if team.get("ties"):
            record += f"-{team['ties']}"
        lines.append(
            f"| {index} | {team.get('team_name', '?')} | {_mention(team)} "
            f"| {record} | {team.get('points_for', 0):.1f} "
            f"| {team.get('points_against', 0):.1f} | {team.get('streak', '--')} |"
        )
    return lines


def _rankings_table(rankings: List[Dict[str, Any]]) -> List[str]:
    lines = [
        "| # | Team | Owner | Record | PF | Move |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        if r.get("ties"):
            record += f"-{r['ties']}"
        lines.append(
            f"| {r['rank']} | {r.get('team_name', '?')} | {_mention(r)} "
            f"| {record} | {r['pf']:.1f} | {r['movement']} |"
        )
    return lines


def _points_awards(teams: List[Dict[str, Any]], week: int) -> List[str]:
    """Awards computable straight from standings -- no history needed."""
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
        f"* 📈 Most Points For: {_mention(most_points)} "
        f"({most_points.get('points_for', 0):.1f}, "
        f"{most_points.get('points_for', 0) / games:.1f}/wk)",
        f"* 📉 Fewest Points For: {_mention(fewest_points)} "
        f"({fewest_points.get('points_for', 0):.1f})",
        f"* 🎯 Most Points Against: {_mention(most_against)} "
        f"({most_against.get('points_against', 0):.1f})",
        f"* 🥇 Best Differential: {_mention(best_diff)} "
        f"({best_diff.get('points_for', 0) - best_diff.get('points_against', 0):+.1f})",
    ]


def _trophy_line(
    label: str,
    emoji: str,
    leader: Optional[Dict[str, Any]],
    unit: str,
    need_hint: str,
) -> str:
    """One 'trophy' row: the real leader if history has data, else a vacant

    placeholder that says exactly what data is missing -- never a fabricated
    winner.
    """
    if not leader:
        return f"* {emoji} {label}: *vacant* — needs {need_hint}"
    weeks = leader.get("weeks")
    weeks_note = f", {weeks} wk avg" if weeks else ""
    return (
        f"* {emoji} {label}: {canvas_mention(leader['owner'], team_key=leader['team_key'])} "
        f"— {leader['value']}{unit}{weeks_note}"
    )


def _trophy_awards() -> List[str]:
    """Season-long trophies backed by ``season_awards_history.json``.

    Read-only: recording a week's contribution to that history is
    ``finalize_recap.py``'s job (via ``season_awards.record_week``), which
    always runs before this canvas step in the pipeline. Rendering must never
    also write, or calling this on a fixture (tests) or a re-fetch would
    silently mutate the real season-long history.
    """
    leaders = compute_leaders(load_history())
    return [
        _trophy_line(
            "The Bench Whisperer", "🪑", leaders["bench_whisperer"], " avg bench pts",
            "roster/lineup data (fetched automatically once rosters are available)",
        ),
        _trophy_line(
            "Iron Fist Award", "🧠", leaders["iron_fist"], " avg bench pts",
            "roster/lineup data",
        ),
        _trophy_line(
            "Human Highlight Reel", "🎬", leaders["human_highlight_reel"], " Bench Hero nod(s)",
            "roster/lineup data",
        ),
        _trophy_line(
            "Giant Slayer", "🎲", leaders["giant_slayer"], " upset win(s)",
            "Yahoo projected-points data (should already be available)",
        ),
        _trophy_line(
            "The Hammer", "🔨", leaders["the_hammer"], " Blowout-of-the-Week win(s)",
            "at least one completed week",
        ),
        _trophy_line(
            "Iron Stomach Award", "💪", leaders["iron_stomach"], " week(s) with the low score",
            "at least one completed week",
        ),
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
        mention = canvas_mention(high["owner"], team_key=high.get("team_key"))
        parts.append(f"- **High score** — {mention} ({high['points']:.1f})")
    if low:
        mention = canvas_mention(low["owner"], team_key=low.get("team_key"))
        parts.append(f"- **Low score** — {mention} ({low['points']:.1f})")
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
    if stats.get("biggest_upset"):
        upset = stats["biggest_upset"]
        mention = canvas_mention(upset["winner_owner"], team_key=upset.get("winner_team_key"))
        parts.append(
            f"- **Biggest upset** — {mention}'s {upset['winner']} "
            f"(projected {upset['winner_projected']:.1f}) beat {upset['loser']} "
            f"(projected {upset['loser_projected']:.1f})"
        )
    if not any([high, low, stats.get("closest_game")]):
        parts.append("_No scoring data for this week._")

    parts.append(f"\n## 🏆 Season Awards (through week {week})")
    parts.extend(_points_awards(teams, week))
    parts.extend(_trophy_awards())

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
