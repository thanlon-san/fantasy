#!/usr/bin/env python3
"""Fetch Tyler's roster from Yahoo (non-interactive)"""

import sys
import csv
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_client import YahooFantasyClient
from shared.logger import get_logger

logger = get_logger(__name__)

config_file = app_root / "config" / "oauth2.json"
client = YahooFantasyClient.from_config(config_file)

print("🏈 Fetching your 2025 roster from Yahoo...\n")

# Get leagues
leagues = client.get_user_leagues(2025, sport="mlb")
league = leagues[0]  # California Palm League
print(f"📊 League: {league['name']}")

# Get teams
teams = client.get_league_teams(league['league_key'])
my_team = [t for t in teams if t['manager'] == 'Tyler'][0]
print(f"⚾ Team: {my_team['name']}\n")

# Get roster
print("🔍 Fetching roster...")
roster = client.get_team_roster(my_team['team_key'])

print(f"✅ Found {len(roster)} players!\n")
print("📋 Your Roster:")
print("-" * 80)
for player in roster:
    positions = ', '.join(player.get('eligible_positions', []))
    team = player.get('editorial_team_abbr', 'FA')
    print(f"{player['name']:30} {positions:15} {team}")
print("-" * 80)

# Save to CSV
output_file = app_root / "data" / "my_roster_from_yahoo.csv"
output_file.parent.mkdir(exist_ok=True)

with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['player_name', 'position', 'mlb_team', 'draft_round', 'years_kept', 'notes'])
    
    for player in roster:
        positions = ', '.join(player.get('eligible_positions', []))
        team = player.get('editorial_team_abbr', 'FA')
        writer.writerow([
            player['name'],
            positions,
            team,
            '',  # draft_round - needs manual entry
            '0',  # years_kept - default to 0
            ''   # notes
        ])

print(f"\n✅ Roster saved to: {output_file}")
print("\n" + "="*80)
print("📝 NEXT STEPS:")
print("="*80)
print(f"\n1. Edit {output_file.name} in the data/ folder")
print("   - Add draft_round for each player (1-12, or leave blank for undrafted)")
print("   - Update years_kept if any were kept from previous years\n")
print("2. Run keeper analysis:")
print("   npm run analyze:csv\n")
print("="*80)
