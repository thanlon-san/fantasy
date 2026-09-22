#!/usr/bin/env python3
"""
Build the preseason "League HQ" Slack Canvas markdown.

No Yahoo fetch. No LLM. Uses the 2026 managers we actually know
(PRESEASON_MANAGERS_2026) plus empty standings/awards. Once Yahoo is
back, prepare_league_hq_canvas.py reads live team_name from week_data
instead — this list is only the fallback.

Writes apps/football-recap/output/league-hq-canvas.md. The agent (or you)
then calls slack_create_canvas / slack_update_canvas targeting
#cx-retention-fantasy-football.

Usage:
    .venv/bin/python apps/football-recap/scripts/prepare_preseason_canvas.py
    .venv/bin/python apps/football-recap/scripts/prepare_preseason_canvas.py --plain
"""

from __future__ import annotations

import argparse
import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE = os.path.dirname(os.path.dirname(_APP_ROOT))
sys.path.insert(0, _APP_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE, "packages"))

from src.canvas_builder import build_preseason_league_hq_canvas_markdown
from src.constants import PRESEASON_MANAGERS_2026

OUTPUT_DIR = os.path.join(_APP_ROOT, "output")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build preseason League HQ Canvas markdown")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Skip Slack user mentions (better for the local markdown file)",
    )
    args = parser.parse_args()

    locked = sum(1 for m in PRESEASON_MANAGERS_2026 if m.get("status") == "locked")
    print("=" * 70)
    print("🏈 Prepare Preseason League HQ Canvas")
    print(f"👥 {locked} of {len(PRESEASON_MANAGERS_2026)} managers locked — no Yahoo fetch")
    print("=" * 70)

    canvas_md = build_preseason_league_hq_canvas_markdown(slack_mentions=not args.plain)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    canvas_path = os.path.join(OUTPUT_DIR, "league-hq-canvas.md")
    with open(canvas_path, "w") as f:
        f.write(canvas_md)

    print(f"✅ Canvas markdown saved to {canvas_path}")
    print()
    print("Next: slack_create_canvas (first run) or slack_update_canvas")
    print("targeting #cx-retention-fantasy-football with this file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
