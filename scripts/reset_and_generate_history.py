#!/usr/bin/env python3
"""
Reset recap history and regenerate a fresh set of weekly recaps via the running API.

Actions:
- Back up recap_history.json (if present) with a timestamped filename
- Clear recap_history.json to an empty list
- Remove output/week-*-recap.md files
- POST to /api/recaps/generate for weeks [start..end], using V2 format

Usage:
  python3 scripts/reset_and_generate_history.py --host http://localhost:8000 --start-week 1 --end-week 7
"""

import argparse
import glob
import json
import os
from datetime import datetime

import requests


def backup_and_clear_history(history_path: str) -> None:
    if os.path.exists(history_path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{os.path.splitext(history_path)[0]}.backup.{ts}.json"
        with open(history_path, "r") as f:
            try:
                data = json.load(f)
            except Exception:
                data = None
        with open(backup_path, "w") as bf:
            json.dump(data, bf, indent=2)
        print(f"📦 Backed up history to {backup_path}")

    with open(history_path, "w") as f:
        json.dump([], f, indent=2)
    print(f"🧹 Cleared {history_path}")


def clear_output_markdown(output_dir: str) -> None:
    pattern = os.path.join(output_dir, "week-*-recap.md")
    removed = 0
    for path in glob.glob(pattern):
        try:
            os.remove(path)
            removed += 1
        except Exception as e:
            print(f"  ⚠️ Could not remove {path}: {e}")
    print(f"🗑️ Removed {removed} files matching {pattern}")


def generate_week(host: str, week: int, use_v2: bool = True) -> bool:
    url = f"{host}/api/recaps/generate"
    try:
        resp = requests.post(url, json={"week": week, "use_v2_format": use_v2}, timeout=300)
        if resp.ok:
            print(f"✅ Generated recap for Week {week}")
            return True
        print(f"❌ Failed to generate Week {week}: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        print(f"❌ Error generating Week {week}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Reset and regenerate recap history via API")
    parser.add_argument("--host", default="http://localhost:8000", help="API host base URL")
    parser.add_argument("--start-week", type=int, default=1, help="Start week (inclusive)")
    parser.add_argument("--end-week", type=int, default=7, help="End week (inclusive)")
    parser.add_argument("--output-dir", default="output", help="Output directory for recap files")
    parser.add_argument("--history-path", default="recap_history.json", help="Path to recap history JSON")
    args = parser.parse_args()

    print("🏈 Resetting recap history and regenerating...")
    backup_and_clear_history(args.history_path)
    clear_output_markdown(args.output_dir)

    successes = 0
    for week in range(args.start_week, args.end_week + 1):
        ok = generate_week(args.host, week, use_v2=True)
        successes += 1 if ok else 0

    print(f"\n📊 Done. Generated {successes}/{args.end_week - args.start_week + 1} recaps.")
    print("Files saved in output/ and history recorded in recap_history.json")


if __name__ == "__main__":
    main()


