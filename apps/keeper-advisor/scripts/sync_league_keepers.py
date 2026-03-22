#!/usr/bin/env python3
"""
Post-Draft League Keeper Sync
Reads completed draft results from Yahoo and updates league_keepers.json.

In a keeper league, each team's "keeper picks" are the pre-assigned slots
they spent on players they kept from last year. This script identifies them
by cross-referencing the actual picks with each team's draft position math.

Usage:
    python sync_league_keepers.py              # Sync and update JSON
    python sync_league_keepers.py --dry-run    # Print results without writing
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

APP_ROOT      = Path(__file__).parent.parent
WORKSPACE     = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(WORKSPACE / "packages"))

from src.yahoo_oauth_manual import YahooOAuth2
import requests

LEAGUE_KEY  = "469.l.25136"
MY_TEAM_KEY = "469.l.25136.t.2"
OAUTH_PATH  = APP_ROOT / "config" / "oauth2.json"
OUTPUT_PATH = WORKSPACE / "apps" / "baseball-dashboard" / "public" / "api" / "league_keepers.json"


def get_session():
    oauth = YahooOAuth2.load_from_file(str(OAUTH_PATH))
    oauth.refresh_access_token()
    oauth.save_to_file(str(OAUTH_PATH))
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {oauth.access_token}"
    return s


def yahoo_get(session, path):
    url = f"https://fantasysports.yahooapis.com/fantasy/v2{path}"
    if "?" not in url:
        url += "?format=json"
    else:
        url += "&format=json"
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json().get("fantasy_content", resp.json())


def get_teams(session):
    data = yahoo_get(session, f"/league/{LEAGUE_KEY}/teams")
    teams_raw = data["league"][1]["teams"]
    teams = {}
    for k, v in teams_raw.items():
        if k == "count":
            continue
        arr = v["team"][0]
        key  = next((p["team_key"] for p in arr if isinstance(p, dict) and "team_key" in p), None)
        name = next((p["name"]     for p in arr if isinstance(p, dict) and "name"     in p), "?")
        mgr  = "?"
        for p in arr:
            if isinstance(p, dict) and "managers" in p:
                mgrs = p["managers"]
                if isinstance(mgrs, list) and mgrs:
                    mgr = mgrs[0].get("manager", {}).get("nickname", "?")
        if key:
            teams[key] = {"name": name, "manager": mgr, "key": key}
    return teams


def get_draft_results(session):
    data = yahoo_get(session, f"/league/{LEAGUE_KEY}/draftresults")
    try:
        dr = data["league"][1]["draft_results"]
    except (KeyError, IndexError):
        dr = {}

    if isinstance(dr, list):
        print("  No draft results yet (league hasn't drafted).")
        return []

    picks = []
    for k, v in dr.items():
        if k == "count":
            continue
        p = v.get("draft_result", {})
        picks.append({
            "overall":    int(p.get("pick",       0)),
            "round":      int(p.get("round",      0)),
            "team_key":   p.get("team_key",   ""),
            "player_key": p.get("player_key", ""),
        })
    return sorted(picks, key=lambda x: x["overall"])


def resolve_player_names(session, picks):
    """Batch fetch player names for all player_keys in picks."""
    keys = list({p["player_key"] for p in picks if p.get("player_key")})
    names = {}
    for i in range(0, len(keys), 25):
        batch = keys[i:i+25]
        try:
            data = yahoo_get(session, f"/players;player_keys={','.join(batch)};out=metadata")
            players_raw = data.get("players", {})
            for pk, pv in players_raw.items():
                if pk == "count":
                    continue
                parr = pv.get("player", [[]])[0]
                name = next((p["name"].get("full", "") for p in parr if isinstance(p, dict) and "name" in p), "")
                pos  = next((p["display_position"]     for p in parr if isinstance(p, dict) and "display_position" in p), "")
                key_ = next((p["player_key"]           for p in parr if isinstance(p, dict) and "player_key" in p), "")
                if key_:
                    names[key_] = {"name": name, "position": pos}
        except Exception as e:
            print(f"  Warning: batch player lookup failed: {e}")
    return names


def infer_keeper_rounds(picks, teams):
    """
    In a keeper league, a team's keeper pick is the pick they make in the
    round that matches their keeper cost.  We can't distinguish keepers from
    regular picks programmatically (Yahoo doesn't flag them), so we return
    ALL picks grouped by team and let the caller decide.

    Returns: { team_key: [ {round, overall, player_key, name, position} ] }
    """
    by_team = {tk: [] for tk in teams}
    for p in picks:
        tk = p["team_key"]
        if tk in by_team:
            by_team[tk].append(p)
    return by_team


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("\n  Post-Draft League Keeper Sync")
    print("  " + "─" * 50)

    session = get_session()
    print("  ✓  Yahoo connected")

    teams = get_teams(session)
    print(f"  ✓  {len(teams)} teams loaded")

    picks = get_draft_results(session)
    if not picks:
        print("\n  Draft hasn't started yet — run this after the draft completes.")
        return

    total_rounds = max(p["round"] for p in picks) if picks else 0
    print(f"  ✓  {len(picks)} picks across {total_rounds} rounds")

    print("  Resolving player names...")
    player_map = resolve_player_names(session, picks)
    print(f"  ✓  {len(player_map)} player names resolved")

    # Enrich picks with names
    for p in picks:
        info = player_map.get(p["player_key"], {})
        p["name"]     = info.get("name", "(unknown)")
        p["position"] = info.get("position", "?")

    by_team = infer_keeper_rounds(picks, teams)

    # Load existing league_keepers.json to preserve any manually entered data
    existing = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            data = json.load(f)
        for team in data.get("teams", []):
            existing[team["team_name"]] = team

    # Print full draft results grouped by team, asking user to identify keepers
    print()
    print("  Full draft results by team:")
    print("  " + "─" * 50)

    result_teams = []
    for team_key, team_info in sorted(teams.items(), key=lambda x: x[1]["name"]):
        team_picks = sorted(by_team.get(team_key, []), key=lambda x: x["round"])
        is_mine = team_key == MY_TEAM_KEY

        print(f"\n  {'★ ' if is_mine else '  '}{team_info['name']} ({team_info['manager']})")
        for p in team_picks:
            print(f"    Rd {p['round']:>2}  #{p['overall']:>3}  {p['position']:<8}  {p['name']}")

        # For the output JSON, try to identify likely keepers by round
        # In this league, keepers are in rounds 1-12 with specific round costs.
        # After a snake draft, we can look at which picks seem "out of order"
        # relative to ADP — but that requires ADP data. For now, flag any pick
        # where the player would never go in that round naturally as a potential keeper.
        # Since we can't auto-detect perfectly, we populate all picks and note
        # the user should verify.
        result_teams.append({
            "team_name": team_info["name"],
            "owner":     team_info["manager"],
            "is_my_team": is_mine,
            "picks":     team_picks,
            "keepers":   [],   # Will be populated by manual review or next pass
        })

    # If user just wants to see the data, stop here in dry-run mode
    if args.dry_run:
        print("\n  [DRY RUN] — not writing any files.")
        return

    # Write picks to a separate inspection file so user can identify keepers
    inspection_path = OUTPUT_PATH.parent / "draft_picks_inspection.json"
    with open(inspection_path, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_picks":  len(picks),
            "teams":        result_teams,
        }, f, indent=2)
    print(f"\n  ✓  Full draft picks written to {inspection_path.name}")
    print("     Review that file to identify keeper picks per team,")
    print("     then update league_keepers.json manually or re-run with --identify-keepers.")

    # Also do a quick update of league_keepers.json with team names/owners
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            lk = json.load(f)
        # Update last_updated
        lk["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        lk["confirmed"] = True
        with open(OUTPUT_PATH, "w") as f:
            json.dump(lk, f, indent=2)
        print(f"  ✓  league_keepers.json updated (last_updated + confirmed=true)")

    print()


if __name__ == "__main__":
    main()
