#!/usr/bin/env python3
"""Fetch draft results from Yahoo"""

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

leagues = client.get_user_leagues(2025, sport="mlb")
league_key = leagues[0]['league_key']
teams = client.get_league_teams(league_key)
my_team = [t for t in teams if t['manager'] == 'Tyler'][0]

print(f"Fetching draft results for {my_team['name']}...\n")

url = f"{client.BASE_URL}/league/{league_key}/draftresults?format=json"
response = client.session.get(url)
data = response.json()

# Save full response for inspection
with open('/tmp/draft_results.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Full draft results saved to /tmp/draft_results.json")

# Parse draft results
draft_results = data.get('fantasy_content', {}).get('league', [{}])[1].get('draft_results', {})

my_picks = []
for key, value in draft_results.items():
    if key == 'count':
        continue
    
    pick_data = value.get('draft_result', {})
    if pick_data.get('team_key') == my_team['team_key']:
        my_picks.append({
            'round': pick_data.get('round'),
            'pick': pick_data.get('pick'),
            'player_key': pick_data.get('player_key'),
        })

print(f"\nYour draft picks ({len(my_picks)} total):\n")
for pick in sorted(my_picks, key=lambda x: int(x['round'])):
    print(f"Round {pick['round']}, Pick {pick['pick']}: Player Key {pick['player_key']}")

print(f"\nFound {len(my_picks)} draft picks!")
