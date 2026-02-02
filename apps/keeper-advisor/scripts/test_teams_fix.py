#!/usr/bin/env python3
"""Test teams parsing fix"""

import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_client import YahooFantasyClient

config_file = app_root / "config" / "oauth2.json"
client = YahooFantasyClient.from_config(config_file)

leagues = client.get_user_leagues(2025, sport="mlb")
if leagues:
    print(f"League: {leagues[0]['name']}")
    teams = client.get_league_teams(leagues[0]['league_key'])
    print(f"\nFound {len(teams)} teams:\n")
    for team in teams:
        print(f"  - {team['name']} (Manager: {team['manager']})")
