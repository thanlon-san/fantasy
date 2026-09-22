#!/usr/bin/env python3
"""
Local-only demo: generates a 4-team, 4-week synthetic season and renders
the season leaderboard + League HQ Canvas markdown, so you can preview what
these features look like before real Yahoo data (or a real Slack post)
is involved.

Writes:
  output/demo-recap-history.json
  output/demo-league-hq-canvas.md

Does NOT touch the real recap_history.json, Yahoo, or Slack.

Usage:
    .venv/bin/python apps/football-recap/scripts/demo_season_preview.py
"""

from __future__ import annotations

import json
import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from src.canvas_builder import build_league_hq_canvas_markdown
from src.gif_bank import pick_gif
from src.season_leaderboard import compute_season_awards
from src.superlatives import compute_superlatives

OUTPUT_DIR = "output"

TEAMS = [
    {"id": 1, "name": "Beacon", "owner": "Han Jang"},
    {"id": 2, "name": "Purdy Boys", "owner": "tyler.hanlon"},
    {"id": 3, "name": "Laser Focused", "owner": "Tiffany Wong"},
    {"id": 4, "name": "Team Wise", "owner": "Christopher Wise"},
]

# (week, [(home_score, away_score, home_bench_pts, away_bench_pts, home_mgmt_gap, away_mgmt_gap)])
# Team pairing: (0,1) and (2,3) each week, scores hand-picked to trigger a
# spread of superlatives/awards across the demo season.
WEEKS = [
    # Week 1: a blowout + a nail-biter
    (1, [(142.0, 98.0, 8.0, 30.0, 3.0, 26.0), (110.2, 108.9, 15.0, 5.0, 5.0, 4.0)]),
    # Week 2: cold war + upset (away team wins despite lower projection)
    (2, [(80.0, 85.0, 4.0, 6.0, 2.0, 8.0), (95.0, 130.0, 22.0, 3.0, 10.0, 2.0)]),
    # Week 3: shootout + another blowout for the same team (Beacon again)
    (3, [(150.0, 128.0, 10.0, 12.0, 4.0, 6.0), (139.0, 91.0, 5.0, 28.0, 3.0, 22.0)]),
    # Week 4: bench hero explosion + close game
    (4, [(105.0, 101.0, 32.0, 8.0, 6.0, 3.0), (112.0, 118.0, 10.0, 9.0, 5.0, 4.0)]),
]


def _team_payload(name, owner, score, bench_pts, mgmt_gap, is_home):
    starters = [
        {"name": f"{name} QB1", "position": "QB", "actual_points": round(score * 0.25, 1),
         "projected_points": round(score * 0.22, 1)},
        {"name": f"{name} RB1", "position": "RB", "actual_points": round(score * 0.25, 1),
         "projected_points": round(score * 0.25, 1)},
    ]
    bench = [
        {"name": f"{name} Bench Star", "position": "WR", "actual_points": bench_pts},
    ]
    return {
        "team_name": name,
        "owner": owner,
        "score": score,
        "management_gap": mgmt_gap,
        "starters": starters,
        "bench": bench,
    }


def build_demo_history():
    history = []
    for week, pairs in WEEKS:
        matchups = []
        for i, (hs, aws, hb, ab, hg, ag) in enumerate(pairs):
            home_team = TEAMS[i * 2]
            away_team = TEAMS[i * 2 + 1]
            matchups.append({
                "matchup_id": i + 1,
                "home_team": _team_payload(home_team["name"], home_team["owner"], hs, hb, hg, True),
                "away_team": _team_payload(away_team["name"], away_team["owner"], aws, ab, ag, False),
            })
        week_data = {
            "league": {"league_name": "Demo League (synthetic preview)"},
            "matchups": {"matchups": matchups},
        }
        week_data["superlatives"] = compute_superlatives(week_data)
        week_data["gif_of_the_week"] = pick_gif(
            week_data, week, superlatives=week_data["superlatives"]
        )
        history.append({
            "week": week,
            "date": f"2026-09-{week:02d}",
            "recap": f"[demo recap text for week {week}]",
            "context": {"source": "demo", "format": "V3", "data": week_data},
        })
    return history


def build_demo_latest_week_data():
    """A standings/power_rankings-shaped bundle for the Canvas preview."""
    standings = []
    for i, t in enumerate(TEAMS, 1):
        standings.append({
            "rank": i,
            "team_name": t["name"],
            "owner": t["owner"],
            "wins": 4 - (i - 1),
            "losses": i - 1,
            "ties": 0,
            "points_for": 450.0 - (i * 12),
            "points_against": 400.0 + (i * 8),
        })
    rankings = [
        {**s, "pf": s["points_for"], "movement": "—"} for s in standings
    ]
    return {
        "league": {"league_name": "Demo League (synthetic preview)"},
        "standings": {"standings": standings},
        "power_rankings": {"rankings": rankings},
    }


def main():
    print("=" * 70)
    print("🏈 Season Preview Demo (synthetic data — no Yahoo, no Slack)")
    print("=" * 70)
    print()

    history = build_demo_history()
    season_awards = compute_season_awards(history)

    print(f"Weeks in demo season: {season_awards['weeks_played']}")
    print()
    print("Season awards computed:")
    for key, entry in season_awards["awards"].items():
        who = entry.get("team") or entry.get("winner") or entry.get("team1")
        print(f"  {entry['label']}: {who} ({entry.get('description', '')})")
    print()

    week_data = build_demo_latest_week_data()
    canvas_md = build_league_hq_canvas_markdown(week_data, season_awards, week=4)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    history_path = os.path.join(OUTPUT_DIR, "demo-recap-history.json")
    canvas_path = os.path.join(OUTPUT_DIR, "demo-league-hq-canvas.md")

    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    with open(canvas_path, "w") as f:
        f.write(canvas_md)

    print(f"✅ Demo history saved to {history_path}")
    print(f"✅ Demo Canvas markdown saved to {canvas_path}")
    print()
    print("=" * 70)
    print("CANVAS PREVIEW")
    print("=" * 70)
    print(canvas_md)


if __name__ == "__main__":
    main()
