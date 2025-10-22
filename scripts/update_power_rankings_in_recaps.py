#!/usr/bin/env python3
"""
Update only the Power Rankings records (X–Y, PF NNN) in existing recap markdown files
by fetching correct through-week records from the running API, without regenerating recaps.

Usage:
  python3 scripts/update_power_rankings_in_recaps.py --host http://localhost:8000 --start-week 1 --end-week 7
"""

import argparse
import os
import re
import requests


def _normalize_key(s: str) -> str:
    # Normalize for matching: lowercase, normalize apostrophes/spaces
    return (
        s.strip()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .lower()
    )


def extract_team_name(display_name: str) -> str:
    """Extract the team name from a display like "@Owner's Team Name" or with bold ** ** wrappers."""
    name = display_name.strip()
    if name.startswith("**") and name.endswith("**"):
        name = name[2:-2].strip()
    if name.startswith("*@") and name.endswith("*"):
        name = name[1:-1].strip()
    # Remove leading @
    if name.startswith("@"):
        name = name[1:]
    # Split on the first occurrence of "'s " to separate owner from team
    if "'s " in name:
        owner_part, team_part = name.split("'s ", 1)
        return team_part.strip()
    return name


def update_power_rankings_block(content: str, rankings: list) -> str:
    # Build map of team_name to (wins, losses, pf)
    team_map = {
        _normalize_key(r.get("team_name", "")): (
            r.get("wins", 0),
            r.get("losses", 0),
            r.get("pf", 0.0),
        )
        for r in rankings
    }

    # Locate Power Rankings section
    header_pattern = re.compile(r"^##\s*🏆\s*Power Rankings", re.MULTILINE)
    m = header_pattern.search(content)
    if not m:
        return content  # nothing to do

    start_idx = m.end()
    # Find next section header or end of content
    next_header = re.search(r"^##\s+", content[start_idx:], re.MULTILINE)
    end_idx = start_idx + next_header.start() if next_header else len(content)

    block = content[start_idx:end_idx]

    # Regex to find ranking lines and replace the (X–Y, PF NNN)
    # Example line:
    # 1. **@[Owner]'s Team Name** (3–4, PF 689.92) [↕ —] — tag
    line_regex = re.compile(r"^(\s*\d+\.[\s]+)(\*?\*?@[^\n]*?\*?\*?)(\s*)\(([^)]*)\)(.*)$", re.MULTILINE)

    def repl(match):
        prefix = match.group(1)
        display = match.group(2)
        space = match.group(3)
        # current_paren = match.group(4)
        suffix = match.group(5)
        team = extract_team_name(display)
        wins, losses, pf = team_map.get(_normalize_key(team), (None, None, None))
        if wins is None:
            return match.group(0)  # no change if team not found
        new_paren = f"({wins}–{losses}, PF {pf})"
        return f"{prefix}{display}{space}{new_paren}{suffix}"

    new_block = line_regex.sub(repl, block)

    return content[:start_idx] + new_block + content[end_idx:]


def main():
    parser = argparse.ArgumentParser(description="Update Power Rankings records in recaps without regeneration")
    parser.add_argument("--host", default="http://localhost:8000", help="API host base URL")
    parser.add_argument("--start-week", type=int, default=1, help="Start week (inclusive)")
    parser.add_argument("--end-week", type=int, default=7, help="End week (inclusive)")
    parser.add_argument("--output-dir", default="output", help="Directory containing recap markdown files")
    args = parser.parse_args()

    for week in range(args.start_week, args.end_week + 1):
        path = os.path.join(args.output_dir, f"week-{week}-recap.md")
        if not os.path.exists(path):
            print(f"⚠️  Skipping Week {week}: {path} not found")
            continue
        try:
            resp = requests.get(f"{args.host}/api/power_rankings/{week}", timeout=60)
            resp.raise_for_status()
            rankings = resp.json().get("rankings", [])
        except Exception as e:
            print(f"❌ Failed to fetch rankings for Week {week}: {e}")
            continue

        with open(path, "r") as f:
            content = f.read()

        updated = update_power_rankings_block(content, rankings)

        if updated != content:
            with open(path, "w") as f:
                f.write(updated)
            print(f"✅ Updated Power Rankings records in {path}")
        else:
            print(f"ℹ️  No changes needed in {path}")


if __name__ == "__main__":
    main()


