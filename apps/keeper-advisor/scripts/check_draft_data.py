#!/usr/bin/env python3
"""Check if Yahoo API provides draft data"""

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

# Get league
leagues = client.get_user_leagues(2025, sport="mlb")
league_key = leagues[0]['league_key']

print("Checking for draft data...\n")

# Try to get draft results
urls = [
    f"{client.BASE_URL}/league/{league_key}/draftresults?format=json",
    f"{client.BASE_URL}/league/{league_key}/transactions?format=json",
    f"{client.BASE_URL}/league/{league_key}/settings?format=json",
]

for url in urls:
    print(f"Trying: {url}")
    response = client.session.get(url)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Sample response:")
        print(json.dumps(data, indent=2)[:1000])
        print("\n" + "="*80 + "\n")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"{response.text[:200]}\n")
