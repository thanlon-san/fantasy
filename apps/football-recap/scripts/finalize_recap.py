#!/usr/bin/env python3
"""
Update recap_history.json after the automation agent writes a recap.

Usage:
    .venv/bin/python apps/football-recap/scripts/finalize_recap.py --week 6

Use ``--force`` when matchup scores are still 0 / unfinalized on Yahoo.
"""

from __future__ import annotations

import argparse
import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from src.constants import validate_week_number
from src.recap_generator import RecapGenerator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a finished recap in recap_history.json"
    )
    parser.add_argument("--week", type=int, required=True, help="NFL week number")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Finalize even when Yahoo matchup scores are still 0 / unfinalized",
    )
    args = parser.parse_args()

    if not validate_week_number(args.week):
        print(f"❌ Invalid week: {args.week}")
        return 1

    generator = RecapGenerator()
    if generator.finalize_recap(args.week, force=args.force):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
