#!/usr/bin/env python3
"""
Prepare recap context for the Cursor Automation flow.

Fetches Yahoo league data, builds the enriched prompt context (house voice,
closing line, superlatives, GIF, calendar hook, bit of the week, trend
history), and writes:

  output/week-N-context.md       — agent reads this + COLUMNIST_PROMPT_V3.md
  output/week-N-context.meta.json

No LLM call. No Slack. The automation agent writes the recap.

Usage:
    .venv/bin/python apps/football-recap/scripts/prepare_recap_context.py
    .venv/bin/python apps/football-recap/scripts/prepare_recap_context.py --week 6
"""

from __future__ import annotations

import argparse
import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from dotenv import load_dotenv

from src.constants import get_current_nfl_week, validate_week_number
from src.recap_generator import RecapGenerator

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Yahoo data and prepare recap context for Cursor Automation"
    )
    parser.add_argument(
        "--week",
        type=int,
        help="NFL week (auto-detected from season calendar if omitted)",
    )
    parser.add_argument(
        "--no-news",
        action="store_true",
        help="Ignored. NewsAPI is never injected (calendar + week_data only).",
    )
    args = parser.parse_args()

    week = args.week if args.week is not None else get_current_nfl_week()
    if not validate_week_number(week):
        print(f"❌ Invalid week: {week} (must be 1–18)")
        return 1

    print("=" * 70)
    print("🏈 Prepare Recap Context (Cursor Automation)")
    print(f"📊 Week {week}")
    print("👻 Voice: The Commissioner's Ghost")
    print("=" * 70)
    print()

    generator = RecapGenerator()
    bundle = generator.prepare_recap_context(week, include_news=False)
    if not bundle:
        print("❌ Failed to prepare context (Yahoo fetch or shaping error)")
        return 1

    context_path = generator.save_prepared_context(bundle)
    print()
    print("Next: the Cursor Automation agent should:")
    print("  1. Read docs/COLUMNIST_PROMPT_V3.md (house voice + section requirements)")
    print(f"  2. Read {context_path}")
    print(f"  3. Write apps/football-recap/output/week-{week}-recap.md")
    print(f"  4. Run finalize_recap.py --week {week} (refreshes output/week-{week}-slack.md from the recap)")
    print(f"  5. Post output/week-{week}-slack.md OR the full recap as a Slack draft (see AUTOMATION_SPEC)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
