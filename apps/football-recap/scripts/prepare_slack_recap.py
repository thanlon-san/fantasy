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
import re
import sys
from pathlib import Path

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from dotenv import load_dotenv

from src.constants import default_recap_week, validate_week_number
from src.recap_generator import OUTPUT_DIR, RecapGenerator
from src.slack_recap_builder import save_slack_recap

load_dotenv()


def _load_weekdata(week: int) -> dict | None:
    path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _yahoo_current_week_from_cache() -> int | None:
    """``current_week`` from the newest cached weekdata file, if any."""
    best_file_week = -1
    yahoo_week: int | None = None
    for path in Path(OUTPUT_DIR).glob("week-*-weekdata.json"):
        match = re.fullmatch(r"week-(\d+)-weekdata\.json", path.name)
        if not match:
            continue
        file_week = int(match.group(1))
        if file_week < best_file_week:
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            continue
        best_file_week = file_week
        raw = (data.get("league") or {}).get("current_week")
        if raw is not None:
            yahoo_week = int(raw)
    return yahoo_week


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

    generator = RecapGenerator()
    yahoo_current_week: int | None = None
    if args.week is None:
        if args.no_fetch:
            yahoo_current_week = _yahoo_current_week_from_cache()
        else:
            try:
                yahoo_current_week = int(generator.fetcher.league_info()["current_week"])
            except (KeyError, TypeError, ValueError):
                yahoo_current_week = None

    week = default_recap_week(args.week, yahoo_current_week=yahoo_current_week)
    if not validate_week_number(week):
        print(f"❌ Invalid week: {week}")
        return 1

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
