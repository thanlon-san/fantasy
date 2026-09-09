#!/usr/bin/env python3
"""Render the League HQ canvas for the preseason / Yahoo-unavailable case.

Used when there is no week data to show: before kickoff, or when Yahoo refuses
the fetch. Emits the roster and an empty standings shell so League HQ stays
useful without pretending games have been played.

The roster comes from ``apps/football-recap/config/preseason_2026.json`` when
that file exists, else from ``PRESEASON_MANAGERS_2026``. If neither is
populated, the canvas says so plainly rather than inventing managers -- a
canvas full of made-up names is worse than one that admits it is waiting on
Yahoo.

Usage:
    python apps/football-recap/scripts/prepare_preseason_canvas.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import (  # noqa: E402
    LEAGUE_SIZE_2026,
    NFL_SEASON_START_DATE,
    OUTPUT_DIR,
    PRESEASON_CONFIG_FILE,
    PRESEASON_MANAGERS_2026,
    YAHOO_LEAGUE_ID,
)

CANVAS_FILENAME = "league-hq-canvas.md"


def load_managers() -> List[Dict[str, Any]]:
    """Load the roster from config if present, else the constant."""
    if os.path.exists(PRESEASON_CONFIG_FILE):
        try:
            with open(PRESEASON_CONFIG_FILE, "r", encoding="utf-8") as handle:
                managers = json.load(handle).get("managers", [])
            if isinstance(managers, list) and managers:
                return managers
        except (json.JSONDecodeError, OSError, AttributeError):
            pass
    return list(PRESEASON_MANAGERS_2026)


def build_canvas(managers: List[Dict[str, Any]], status_note: str) -> str:
    parts: List[str] = []
    parts.append("# 🏈 League HQ")
    parts.append(
        f"_Preseason · updated {datetime.now().strftime('%b %d, %Y')} · "
        f"Yahoo league {YAHOO_LEAGUE_ID}_"
    )

    parts.append("\n## Status")
    parts.append(status_note)

    parts.append(f"\n## Managers ({LEAGUE_SIZE_2026}-team league)")
    if managers:
        has_slots = any(m.get("draft_slot") for m in managers)
        has_names = any(m.get("manager") for m in managers)

        header = (["Pick"] if has_slots else []) + ["Team"]
        if has_names:
            header.append("Manager")
        parts.append("| " + " | ".join(header) + " |")
        parts.append("| " + " | ".join("---" for _ in header) + " |")

        ordered = (
            sorted(managers, key=lambda m: m.get("draft_slot") or 99)
            if has_slots
            else managers
        )
        for manager in ordered:
            row = ([str(manager.get("draft_slot", "—"))] if has_slots else []) + [
                str(manager.get("team_name", "—"))
            ]
            if has_names:
                row.append(str(manager.get("manager", "—")))
            parts.append("| " + " | ".join(row) + " |")
    else:
        parts.append(
            "_The 2026 roster has not been read from Yahoo yet, so there is "
            "nothing verified to list here. It will populate automatically on "
            "the first successful fetch._"
        )

    parts.append("\n## Standings")
    parts.append("_No games played yet._")

    parts.append("\n## Power Rankings")
    parts.append("_Available after Week 1._")

    parts.append("\n## Season Awards")
    parts.append("_Available after Week 1._")

    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status",
        default="",
        help="Override the status line (defaults to a kickoff/Yahoo message).",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(OUTPUT_DIR, CANVAS_FILENAME),
        help="Where to write the canvas markdown.",
    )
    args = parser.parse_args()

    kickoff = NFL_SEASON_START_DATE.strftime("%b %d, %Y")
    status = args.status or (
        f"Waiting on Yahoo. The league is not readable through the Fantasy API "
        f"yet, so standings and rankings are empty. Season kickoff was "
        f"{kickoff}; this page fills in automatically once the first fetch "
        f"succeeds."
    )

    managers = load_managers()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(build_canvas(managers, status))

    print(f"Wrote {args.out} ({len(managers)} managers)")
    if not managers:
        print(
            "No manager roster configured -- canvas notes that it is pending. "
            f"Populate {PRESEASON_CONFIG_FILE} to list them.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
