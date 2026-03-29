#!/usr/bin/env python3
"""
Fetch roster from Yahoo Fantasy API and prepare for keeper analysis
"""

import sys
import json
import csv
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_client import YahooFantasyClient
from shared.logger import get_logger

logger = get_logger(__name__)


def main():
    print("🏈 Yahoo Fantasy Roster Fetcher\n")
    
    # Load OAuth config
    config_file = app_root / "config" / "oauth2.json"
    if not config_file.exists():
        print("❌ OAuth config not found. Please run: npm run setup:yahoo")
        return 1
    
    try:
        # Initialize client
        print("🔐 Connecting to Yahoo Fantasy API...")
        client = YahooFantasyClient.from_config(config_file)
        print("✅ Connected!\n")
        
        # Get user's leagues
        print("🔍 Fetching your baseball leagues...")
        year = int(input("Enter season year (e.g., 2025): ").strip())
        
        leagues = client.get_user_leagues(year, sport="mlb")
        
        if not leagues:
            print(f"\n❌ No baseball leagues found for {year}")
            return 1
        
        # Display leagues
        print(f"\n📊 Found {len(leagues)} league(s):\n")
        for i, league in enumerate(leagues, 1):
            print(f"{i}. {league['name']}")
            print(f"   League ID: {league['league_id']}")
            print(f"   Season: {league['season']}")
            print(f"   Teams: {league['num_teams']}")
            print()
        
        # Select league
        selection = int(input("Select league number: ").strip())
        if selection < 1 or selection > len(leagues):
            print("❌ Invalid selection")
            return 1
        
        selected_league = leagues[selection - 1]
        print(f"\n✅ Selected: {selected_league['name']}\n")
        
        # Get teams in league
        print("🔍 Fetching teams...")
        teams = client.get_league_teams(selected_league['league_key'])
        
        if not teams:
            print("❌ No teams found")
            return 1
        
        # Display teams
        print(f"\n👥 Found {len(teams)} team(s):\n")
        for i, team in enumerate(teams, 1):
            print(f"{i}. {team['name']} (Manager: {team['manager']})")
        print()
        
        # Select team
        team_selection = int(input("Select your team number: ").strip())
        if team_selection < 1 or team_selection > len(teams):
            print("❌ Invalid selection")
            return 1
        
        selected_team = teams[team_selection - 1]
        print(f"\n✅ Selected: {selected_team['name']}\n")
        
        # Get roster
        print("🔍 Fetching roster...")
        roster = client.get_team_roster(selected_team['team_key'])
        
        if not roster:
            print("❌ No players found")
            return 1
        
        print(f"\n✅ Found {len(roster)} players!\n")
        
        # Display roster
        print("📋 Your Roster:")
        print("-" * 80)
        for player in roster:
            positions = ', '.join(player.get('eligible_positions', []))
            team = player.get('editorial_team_abbr', 'FA')
            print(f"{player['name']:25} {positions:15} {team}")
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
        print(f"\n1. Edit {output_file}")
        print("   - Add draft_round for each player (1-12, or leave blank for undrafted)")
        print("   - Update years_kept if any players were kept from previous years")
        print("   - Add any notes\n")
        print("2. Run keeper analysis:")
        print("   npm run analyze:csv\n")
        print("="*80)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error fetching roster: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
