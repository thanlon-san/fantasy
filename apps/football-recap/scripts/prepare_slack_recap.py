#!/usr/bin/env python3
"""
Build the compact Slack weekly digest from cached or live week_data.

Writes ``output/week-N-slack.md`` (no LLM).

Usage:
    .venv/bin/python apps/football-recap/scripts/prepare_slack_recap.py --week 6
    .venv/bin/python apps/football-recap/scripts/prepare_slack_recap.py --week 6 --no-fetch
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

from dotenv import load_dotenv

from src.constants import get_current_nfl_week, validate_week_number
from src.recap_generator import OUTPUT_DIR, RecapGenerator
from src.slack_recap_builder import save_slack_recap

load_dotenv()


def _load_weekdata(week: int) -> dict | None:
    path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build output/week-N-slack.md from week_data"
    )
    parser.add_argument("--week", type=int, help="NFL week (default: current)")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Read output/week-N-weekdata.json only (no Yahoo)",
    )
    args = parser.parse_args()

    week = args.week if args.week is not None else get_current_nfl_week()
    if not validate_week_number(week):
        print(f"❌ Invalid week: {week}")
        return 1

    generator = RecapGenerator()
    if args.no_fetch:
        week_data = _load_weekdata(week)
        if not week_data:
            print(f"❌ Missing {OUTPUT_DIR}/week-{week}-weekdata.json — run prepare_recap_context or omit --no-fetch")
            return 1
    else:
        week_data = generator.fetch_week_data(week)
        if not week_data:
            print("❌ Yahoo fetch failed")
            return 1
        weekdata_path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(weekdata_path, "w", encoding="utf-8") as handle:
            json.dump(week_data, handle, indent=2, default=str)

    path = save_slack_recap(week, week_data, history=generator.recap_history)
    print(f"✅ Slack digest: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
