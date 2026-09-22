#!/usr/bin/env python3
"""
Build the "League HQ" Slack Canvas markdown from recap_history.json plus the
latest week's fetched data.

No LLM call. Writes output/league-hq-canvas.md. The automation agent (or you,
manually) reads that file and calls slack_create_canvas (first time) or
slack_update_canvas (every week after) targeting #cx-retention-fantasy-football.

Usage:
    .venv/bin/python apps/football-recap/scripts/prepare_league_hq_canvas.py --week 6
    .venv/bin/python apps/football-recap/scripts/prepare_league_hq_canvas.py --week 6 --history recap_history.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from src.canvas_builder import build_league_hq_canvas_markdown
from src.constants import RECAP_HISTORY_FILE, validate_week_number
from src.fetch_league_data import get_fetcher
from src.season_leaderboard import compute_season_awards

OUTPUT_DIR = "output"


def _load_history(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def _load_weekdata_from_disk(week: int):
    path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build League HQ Canvas markdown")
    parser.add_argument("--week", type=int, required=True, help="Latest completed week")
    parser.add_argument(
        "--history", type=str, default=RECAP_HISTORY_FILE, help="Path to recap_history.json"
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Use cached output/week-N-weekdata.json instead of a live Yahoo fetch",
    )
    args = parser.parse_args()

    if not validate_week_number(args.week):
        print(f"❌ Invalid week: {args.week}")
        return 1

    print("=" * 70)
    print("🏈 Prepare League HQ Canvas")
    print(f"📊 Through Week {args.week}")
    print("=" * 70)

    week_data = None
    if args.no_fetch:
        week_data = _load_weekdata_from_disk(args.week)
        if not week_data:
            print(f"❌ No cached week_data for week {args.week}; run without --no-fetch")
            return 1
    else:
        try:
            fetcher = get_fetcher()
            week_data = fetcher.fetch_all_for_week(args.week)
        except Exception as exc:
            print(f"⚠️  Live fetch failed ({exc}); trying cached week_data")
            week_data = _load_weekdata_from_disk(args.week)
            if not week_data:
                print("❌ No cached week_data available either")
                return 1

    history = _load_history(args.history)
    season_awards = compute_season_awards(history)

    canvas_md = build_league_hq_canvas_markdown(week_data, season_awards, week=args.week)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    canvas_path = os.path.join(OUTPUT_DIR, "league-hq-canvas.md")
    with open(canvas_path, "w") as f:
        f.write(canvas_md)

    print(f"✅ Canvas markdown saved to {canvas_path}")
    print()
    print("Next: the automation agent should call slack_update_canvas (or")
    print("slack_create_canvas on the very first run) targeting")
    print("#cx-retention-fantasy-football with this file's contents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
