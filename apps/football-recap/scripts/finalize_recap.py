#!/usr/bin/env python3
"""Record a written recap into history.

Reads the recap the writing agent produced at ``output/week-<N>-recap.md`` and
appends it to ``recap_history.json`` (CWD-relative), replacing any existing
entry for that week so re-runs stay idempotent. Also persists the week's power
rankings so next week can report movement.

Usage:
    python apps/football-recap/scripts/finalize_recap.py --week 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import OUTPUT_DIR, RECAP_HISTORY_FILE  # noqa: E402
from src.power_rankings import save_history  # noqa: E402


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, required=True, help="NFL week number")
    args = parser.parse_args()
    week = args.week

    recap_path = os.path.join(OUTPUT_DIR, f"week-{week}-recap.md")
    if not os.path.exists(recap_path):
        print(f"No recap found at {recap_path}", file=sys.stderr)
        return 1

    with open(recap_path, "r", encoding="utf-8") as handle:
        recap = handle.read().strip()

    if not recap:
        print(f"{recap_path} is empty -- refusing to record it.", file=sys.stderr)
        return 1

    meta = _load_json(os.path.join(OUTPUT_DIR, f"week-{week}-context.meta.json"), {})
    week_data = _load_json(os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json"), {})

    history = _load_json(RECAP_HISTORY_FILE, [])
    if not isinstance(history, list):
        history = []

    entry = {
        "week": week,
        "date": datetime.now().isoformat(),
        "recap": recap,
        "context": {
            "format": "V3",
            "author": "cursor-agent",
            "closing_line": meta.get("closing_line"),
            "calendar_hook": meta.get("calendar_hook"),
            "gif_url": meta.get("gif_url"),
            "source": meta.get("source", "yahoo"),
        },
    }

    history = [e for e in history if e.get("week") != week]
    history.append(entry)
    history.sort(key=lambda e: e.get("week", 0))

    with open(RECAP_HISTORY_FILE, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)

    # Lock in this week's ranks so next week can compute movement.
    if week_data:
        try:
            from src.power_rankings import compute_power_rankings

            rankings = compute_power_rankings(week_data, week)
            if rankings:
                save_history(week, rankings)
                print(f"Recorded power rankings for week {week}")
        except (KeyError, TypeError, ValueError) as exc:
            print(f"Could not record power rankings: {exc}", file=sys.stderr)

    print(f"Recorded week {week} into {RECAP_HISTORY_FILE} ({len(recap)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
