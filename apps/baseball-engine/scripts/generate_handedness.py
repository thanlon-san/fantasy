#!/usr/bin/env python3
"""
Generate player_handedness.json from the MLB Stats API.

Fetches all active 40-man roster players and writes a JSON file mapping
player names to their bat/pitch handedness.

Run monthly to keep the file up to date:
    python scripts/generate_handedness.py
"""

import json
import sys
from pathlib import Path
import requests

APP_ROOT = Path(__file__).parent.parent
OUTPUT = APP_ROOT / "data" / "player_handedness.json"

MLB_API = "https://statsapi.mlb.com/api/v1"


def fetch_all_players() -> dict:
    """Fetch every active MLB player and return a handedness lookup dict.

    Uses hydrate=person on the roster endpoint so each team request returns
    full person details (including batSide/pitchHand) in a single call.
    ~30 requests total instead of ~1200.
    """
    print("Fetching active MLB rosters...")

    resp = requests.get(f"{MLB_API}/teams", params={"sportId": 1}, timeout=15)
    resp.raise_for_status()
    teams = resp.json().get("teams", [])
    team_ids = [t["id"] for t in teams if t.get("active")]
    print(f"  Found {len(team_ids)} active teams")

    lookup: dict = {}
    for i, tid in enumerate(team_ids, 1):
        try:
            r = requests.get(
                f"{MLB_API}/teams/{tid}/roster",
                params={"rosterType": "40Man", "hydrate": "person"},
                timeout=20,
            )
            r.raise_for_status()
            roster = r.json().get("roster", [])
            count = 0
            for entry in roster:
                person = entry.get("person", {})
                name = person.get("fullName")
                if not name:
                    continue

                bat = (person.get("batSide") or {}).get("code")
                pitch = (person.get("pitchHand") or {}).get("code")

                if bat or pitch:
                    lookup[name] = {"bat": bat, "pitch": pitch}
                    count += 1
            print(f"  [{i}/{len(team_ids)}] Team {tid}: {count} players")
        except Exception as e:
            print(f"  [{i}/{len(team_ids)}] Warning: team {tid} failed — {e}")

    return lookup


def main():
    lookup = fetch_all_players()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w") as f:
        json.dump(lookup, f, indent=2, sort_keys=True)

    print(f"\n✅ Wrote {len(lookup)} players to {OUTPUT}")


if __name__ == "__main__":
    main()
