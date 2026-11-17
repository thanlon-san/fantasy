#!/usr/bin/env python3
"""
One-time (or re-runnable) backfill of recap_history.json for past weeks whose
real recap text was only ever sent to Slack, never recorded in this branch's
own history (this pipeline didn't exist yet when those weeks were played).

Safe-by-construction: only fetches ``week_matchups(week)`` (per-week
box scores + rosters, correctly scoped to that week by Yahoo regardless of
when it's fetched) and derives ``superlatives`` from it. Deliberately never
touches ``standings`` or ``power_rankings`` for a past week — those Yahoo
endpoints are always live/current, not point-in-time, and feeding them into
history would corrupt season-long aggregates (see docs/AUTOMATION_SPEC.md /
the automation's own memory notes for why).

Usage:
    .venv/bin/python apps/football-recap/scripts/backfill_season_history.py
"""

from __future__ import annotations

import json
import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from datetime import datetime, timedelta

from src.constants import RECAP_HISTORY_FILE
from src.fetch_league_data import get_fetcher
from src.superlatives import compute_superlatives

# Real recap text as actually sent to #cx-retention-fantasy-football,
# scraped via slack_read_channel on 2026-11-17. Only needed so
# RecapGenerator._get_unique_closing_line()'s last-5-week lookback and
# get_previous_recaps_context() have something real to read — season
# awards themselves only need the ``context.data`` block below.
REAL_RECAP_TEXT = {
    1: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week1.txt")).read(),
    2: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week2.txt")).read(),
    3: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week3.txt")).read(),
    4: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week4.txt")).read(),
    5: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week5.txt")).read(),
    6: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week6.txt")).read(),
    7: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week7.txt")).read(),
    8: open(os.path.join(_APP_ROOT, "scripts", "_backfill_text", "week8.txt")).read(),
}

# Approximate real send dates (Tuesday mornings), just for history ordering.
REAL_SEND_DATES = {
    1: datetime(2026, 9, 15, 10, 0),
    2: datetime(2026, 9, 22, 10, 0),
    3: datetime(2026, 9, 29, 10, 0),
    4: datetime(2026, 10, 6, 10, 0),
    5: datetime(2026, 10, 13, 10, 0),
    6: datetime(2026, 10, 20, 10, 0),
    7: datetime(2026, 10, 27, 10, 0),
    8: datetime(2026, 11, 3, 10, 0),
}


def load_history():
    if os.path.exists(RECAP_HISTORY_FILE):
        with open(RECAP_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_history(history):
    history_sorted = sorted(history, key=lambda e: e.get("week", 0))
    with open(RECAP_HISTORY_FILE, "w") as f:
        json.dump(history_sorted, f, indent=2)


def main() -> int:
    history = load_history()
    existing_weeks = {e.get("week") for e in history}

    fetcher = get_fetcher()

    for week in sorted(REAL_RECAP_TEXT.keys()):
        if week in existing_weeks:
            print(f"Week {week} already in recap_history.json — skipping")
            continue

        print(f"Fetching Week {week} matchups (point-in-time, safe)...")
        matchups = fetcher.week_matchups(week)
        if not matchups.get("matchups"):
            print(f"⚠️  Week {week}: no matchups returned, skipping")
            continue

        week_data = {"week": week, "matchups": matchups}
        week_data["superlatives"] = compute_superlatives(week_data)

        entry = {
            "week": week,
            "date": REAL_SEND_DATES.get(week, datetime.now()).isoformat(),
            "recap": REAL_RECAP_TEXT[week],
            "context": {
                "source": "backfill-from-slack-channel-history-2026-11-17",
                "format": "V3",
                "data": week_data,
            },
        }
        history.append(entry)
        print(f"✅ Week {week} backfilled ({len(matchups['matchups'])} matchups)")

    save_history(history)
    weeks_now = sorted(e.get("week") for e in history)
    print(f"\nrecap_history.json now has weeks: {weeks_now}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
