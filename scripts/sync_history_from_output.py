#!/usr/bin/env python3
"""
Sync recap_history.json entries from the updated markdown files in output/.

This updates only the 'recap' field for each week, preserving existing dates.

Usage:
  python3 scripts/sync_history_from_output.py --start-week 1 --end-week 7
"""

import argparse
import json
import os
from datetime import datetime


def load_history(path: str) -> list:
    if os.path.exists(path):
        with open(path, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_history(path: str, data: list) -> None:
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def sync_weeks(start_week: int, end_week: int, output_dir: str, history_path: str) -> None:
    history = load_history(history_path)
    # map week -> index in history
    index_map = {entry.get('week'): i for i, entry in enumerate(history) if isinstance(entry, dict)}

    updated = 0
    for week in range(start_week, end_week + 1):
        md_path = os.path.join(output_dir, f"week-{week}-recap.md")
        if not os.path.exists(md_path):
            print(f"⚠️  Skipping Week {week}: {md_path} not found")
            continue
        with open(md_path, 'r') as f:
            content = f.read()

        if week in index_map:
            i = index_map[week]
            history[i]['recap'] = content
            # leave existing date as-is
        else:
            # create new entry if missing
            history.append({
                'week': week,
                'date': datetime.now().isoformat(),
                'recap': content
            })
        updated += 1

    save_history(history_path, history)
    print(f"✅ Synced {updated} week(s) into {history_path}")


def main():
    parser = argparse.ArgumentParser(description='Sync recap_history.json from output markdown files')
    parser.add_argument('--start-week', type=int, default=1)
    parser.add_argument('--end-week', type=int, default=7)
    parser.add_argument('--output-dir', default='output')
    parser.add_argument('--history-path', default='recap_history.json')
    args = parser.parse_args()

    sync_weeks(args.start_week, args.end_week, args.output_dir, args.history_path)


if __name__ == '__main__':
    main()


