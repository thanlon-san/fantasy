#!/usr/bin/env python3
"""Get complete draft data for all players and transactions"""

import sys
import json
from pathlib import Path
from collections import defaultdict

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

print("Fetching complete draft data for ALL players in the league...\n")

# Get ALL draft results (not just mine)
url = f"{client.BASE_URL}/league/{league_key}/draftresults?format=json"
response = client.session.get(url)
data = response.json()

draft_results = data.get('fantasy_content', {}).get('league', [{}])[1].get('draft_results', {})

# Build a map of ALL players to their draft rounds
all_players_draft = {}
for key, value in draft_results.items():
    if key == 'count':
        continue
    
    pick_data = value.get('draft_result', {})
    player_key = pick_data.get('player_key')
    round_num = int(pick_data.get('round', 0))
    team_key = pick_data.get('team_key')
    
    all_players_draft[player_key] = {
        'round': round_num,
        'team_key': team_key,
        'drafted_by_me': team_key == my_team['team_key']
    }

print(f"Total players drafted in league: {len(all_players_draft)}\n")

# Now get my current roster and match
roster = client.get_team_roster(my_team['team_key'])

print("Matching your current roster to draft data:\n")
print("-" * 120)
print(f"{'Player':<30} {'Current Team':<6} {'Draft Rd':<10} {'Drafted By':<20} {'Status'}")
print("-" * 120)

for player in roster:
    player_key = player.get('player_key')
    draft_info = all_players_draft.get(player_key)
    
    name = player['name']
    mlb_team = player.get('editorial_team_abbr', 'FA')
    
    if draft_info:
        draft_round = draft_info['round']
        if draft_round > 12:
            draft_round_display = f"{draft_round} (→12)"
        else:
            draft_round_display = str(draft_round)
        
        if draft_info['drafted_by_me']:
            drafted_by = "YOU"
            status = "Your pick"
        else:
            # Find which team drafted them
            drafting_team = [t for t in teams if t['team_key'] == draft_info['team_key']][0]
            drafted_by = drafting_team['name'][:18]
            status = "Acquired from FA"
        
    else:
        draft_round_display = "N/A"
        drafted_by = "Undrafted"
        status = "FA pickup"
    
    print(f"{name:<30} {mlb_team:<6} {draft_round_display:<10} {drafted_by:<20} {status}")

print("-" * 120)

# Now check transactions to see when players were acquired
print("\n\nFetching transaction history...\n")
url = f"{client.BASE_URL}/team/{my_team['team_key']}/transactions?format=json"
response = client.session.get(url)
trans_data = response.json()

# Save for inspection
with open('/tmp/transactions.json', 'w') as f:
    json.dump(trans_data, f, indent=2)

print("Transaction data saved to /tmp/transactions.json for inspection")
print("\nTransaction structure sample:")
print(json.dumps(trans_data, indent=2)[:1500])
