#!/usr/bin/env python3
"""
Fetch Yahoo draft results and prepare context for a one-off "Draft Grades"
recap. This is NOT part of the weekly automation — run it once, shortly
after your league's draft.

Requires live Yahoo Fantasy API access (403 = app not authorized or stale
tokens — see docs/AUTOMATION_SPEC.md). Fails cleanly with a clear error.

Usage:
    .venv/bin/python apps/football-recap/scripts/prepare_draft_grades_context.py
"""

from __future__ import annotations

import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from dotenv import load_dotenv

from src.draft_grades import build_draft_grades_context
from src.fetch_league_data import get_fetcher

load_dotenv()

OUTPUT_DIR = "output"


def main() -> int:
    print("=" * 70)
    print("🏈 Prepare Draft Grades Context")
    print("=" * 70)
    print()

    try:
        fetcher = get_fetcher()
        league = fetcher.league_info()
        draft_results = fetcher.draft_results()
    except Exception as exc:
        print(f"❌ Error fetching draft data: {exc}")
        print("   If this mentions 'not authorized', Yahoo API access is")
        print("   still pending — see docs/AUTOMATION_SPEC.md.")
        return 1

    if not draft_results.get("picks"):
        print("❌ No draft picks found — has the draft happened yet?")
        return 1

    context = build_draft_grades_context(
        draft_results, league_name=league.get("league_name", "")
    )

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    context_path = os.path.join(OUTPUT_DIR, "draft-grades-context.md")
    with open(context_path, "w") as f:
        f.write(context)

    print(f"✅ Draft grades context saved to {context_path}")
    print(f"   {draft_results['total_picks']} picks across "
          f"{len(set(p.get('team_name') for p in draft_results['picks']))} teams")
    print()
    print("Next: the agent should read docs/COLUMNIST_PROMPT_V3.md +")
    print("this context file and write output/draft-grades-recap.md,")
    print("then post as a Slack draft (one-off, not scheduled).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
