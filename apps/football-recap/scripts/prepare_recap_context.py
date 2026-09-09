#!/usr/bin/env python3
"""Fetch a week from Yahoo and write the prepared recap context.

This is the Python half of the weekly pipeline: no LLM, no invention. It writes
three CWD-relative files that the writing agent and the later steps read:

    output/week-<N>-context.md        the prepared context to write from
    output/week-<N>-context.meta.json metadata sidecar
    output/week-<N>-weekdata.json     raw normalized week data (canvas cache)

Exits non-zero on any Yahoo failure and writes the reason to the meta sidecar,
so the caller can post an honest status note instead of a fabricated recap.

Usage:
    python apps/football-recap/scripts/prepare_recap_context.py --week 1 --no-news
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import (  # noqa: E402
    OUTPUT_DIR,
    get_current_nfl_week,
    has_season_started,
)
from src.recap_context import build_context  # noqa: E402
from src.yahoo_nfl_client import YahooError, YahooNFLClient  # noqa: E402


def write_failure_meta(week: int, code: str, message: str) -> str:
    """Record why the run stopped so the caller can explain it accurately."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"week-{week}-context.meta.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(
            {"week": week, "ok": False, "error_code": code, "error": message},
            handle,
            indent=2,
        )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, help="NFL week (auto-detects if omitted)")
    parser.add_argument(
        "--no-news",
        action="store_true",
        help="Accepted for compatibility and unused -- news is never injected.",
    )
    args = parser.parse_args()

    week = args.week or get_current_nfl_week()
    if not 1 <= week <= 18:
        print(f"Invalid week: {week}", file=sys.stderr)
        return 2

    if not has_season_started():
        message = "The 2026 season has not kicked off yet."
        print(message, file=sys.stderr)
        write_failure_meta(week, "preseason", message)
        return 1

    print(f"Preparing context for week {week}...")

    try:
        client = YahooNFLClient()
        week_data = client.fetch_week_data(week)
    except YahooError as exc:
        print(f"Yahoo fetch failed ({exc.code}): {exc}", file=sys.stderr)
        write_failure_meta(week, exc.code, str(exc))
        return 1

    matchups = week_data.get("matchups", {}).get("matchups", [])
    teams = week_data.get("standings", {}).get("standings", [])
    if not matchups or not teams:
        message = (
            f"Yahoo returned no {'matchups' if not matchups else 'teams'} for "
            f"week {week}. Nothing to recap."
        )
        print(message, file=sys.stderr)
        write_failure_meta(week, "empty_week_data", message)
        return 1

    built = build_context(week_data, week)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    context_path = os.path.join(OUTPUT_DIR, f"week-{week}-context.md")
    meta_path = os.path.join(OUTPUT_DIR, f"week-{week}-context.meta.json")
    data_path = os.path.join(OUTPUT_DIR, f"week-{week}-weekdata.json")

    with open(context_path, "w", encoding="utf-8") as handle:
        handle.write(built["markdown"])
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump({**built["meta"], "ok": True}, handle, indent=2)
    with open(data_path, "w", encoding="utf-8") as handle:
        json.dump(week_data, handle, indent=2)

    print(f"Wrote {context_path}")
    print(f"Wrote {meta_path}")
    print(f"Wrote {data_path}")
    print(
        f"{len(matchups)} matchups, {len(teams)} teams, "
        f"{built['meta']['superlative_count']} superlatives"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
