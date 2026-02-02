#!/usr/bin/env python3
"""Debug script to see the actual teams response structure"""

import sys
import json
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_client import YahooFantasyClient

config_file = app_root / "config" / "oauth2.json"
client = YahooFantasyClient.from_config(config_file)

# Get leagues
leagues = client.get_user_leagues(2025, sport="mlb")
league_key = leagues[0]['league_key']

print(f"Fetching teams for league: {league_key}\n")

# Make raw API call
url = f"{client.BASE_URL}/league/{league_key}/teams?format=json"
response = client.session.get(url)
data = response.json()

print("Full response structure:")
print(json.dumps(data, indent=2))
