#!/usr/bin/env python3
"""
Yahoo Fantasy API Setup Script
Interactive setup for Yahoo Fantasy Sports API authentication
"""

import sys
import os
import json
from pathlib import Path

# Add app and shared to Python path
app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_client import YahooFantasyClient, print_leagues
from src.importers import CSVImporter
from shared.logger import get_logger

logger = get_logger(__name__)


def setup_oauth():
    """Guide user through OAuth setup"""
    print("\n" + "="*80)
    print("YAHOO FANTASY API SETUP")
    print("="*80)
    print("\nTo use the Yahoo Fantasy API, you need to:")
    print("1. Create a Yahoo Developer App")
    print("2. Get your Consumer Key and Consumer Secret")
    print("3. Save them to config/oauth2.json")
    
    print("\n" + "-"*80)
    print("STEP 1: Create a Yahoo Developer App")
    print("-"*80)
    print("\n1. Go to: https://developer.yahoo.com/apps/create/")
    print("2. Sign in with your Yahoo account")
    print("3. Fill out the form:")
    print("   - Application Name: 'Fantasy Keeper Advisor' (or any name)")
    print("   - OAuth Client Type: 'Confidential Client' ✅")
    print("   - Description: 'Keeper decision tool for fantasy baseball'")
    print("   - Redirect URI: 'https://localhost:8000' (IMPORTANT!)")
    print("   - API Permissions:")
    print("     ✅ Check 'Fantasy Sports'")
    print("     ✅ Select 'Read' permission")
    print("\n4. Click 'Create App'")
    print("5. Copy your Client ID (Consumer Key) and Client Secret")
    print("\n⚠️  CRITICAL: Make sure you selected 'Confidential Client'")
    print("   and that Fantasy Sports permission is checked!")
    
    input("\nPress Enter when you have your Consumer Key and Secret...")
    
    print("\n" + "-"*80)
    print("STEP 2: Enter Your Credentials")
    print("-"*80)
    
    consumer_key = input("\nEnter your Consumer Key: ").strip()
    consumer_secret = input("Enter your Consumer Secret: ").strip()
    
    if not consumer_key or not consumer_secret:
        print("\n❌ Invalid credentials. Please try again.")
        return False
    
    # Create config directory if it doesn't exist
    config_dir = app_root / "config"
    config_dir.mkdir(exist_ok=True)
    
    # Save to oauth2.json
    oauth_file = config_dir / "oauth2.json"
    oauth_data = {
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret
    }
    
    with open(oauth_file, 'w') as f:
        json.dump(oauth_data, f, indent=2)
    
    print(f"\n✅ Credentials saved to: {oauth_file}")
    
    print("\n" + "-"*80)
    print("STEP 3: Test Authentication")
    print("-"*80)
    print("\nYou will now be prompted to authorize the app in your browser.")
    print("This only needs to be done once.")
    
    input("\nPress Enter to continue...")
    
    return True


def main():
    """Main setup function"""
    
    # Check if oauth2.json already exists
    oauth_file = app_root / "config" / "oauth2.json"
    
    if not oauth_file.exists():
        print("\n📝 OAuth credentials not found. Let's set them up!")
        if not setup_oauth():
            return 1
    else:
        print("\n✅ Found existing OAuth credentials")
        print(f"   Location: {oauth_file}")
        
        choice = input("\nDo you want to reconfigure? (y/N): ").strip().lower()
        if choice == 'y':
            if not setup_oauth():
                return 1
    
    # Test authentication
    print("\n🔐 Testing authentication...")
    client = YahooFantasyClient(str(oauth_file))
    
    if not client.authenticate():
        print("\n❌ Authentication failed!")
        print("   - Check your Consumer Key and Consumer Secret")
        print("   - Make sure you authorized the app in your browser")
        print("   - Try running this script again")
        return 1
    
    # Get leagues
    print("\n🔍 Fetching your Fantasy Baseball leagues...")
    leagues = client.get_leagues(year=2026, sport="mlb")
    
    if not leagues:
        print("\n⚠️  No leagues found for 2026")
        print("   Try a different year:")
        year_input = input("   Enter year (e.g., 2025): ").strip()
        if year_input:
            leagues = client.get_leagues(year=int(year_input), sport="mlb")
    
    if leagues:
        print_leagues(leagues)
        
        # Ask which league to import
        print("\nWhich league would you like to import?")
        choice = input("Enter number (or press Enter to skip): ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(leagues):
            selected_league = leagues[int(choice) - 1]
            league_id = selected_league['league_id']
            
            print(f"\n📥 Fetching roster from: {selected_league['name']}")
            
            roster = client.fetch_roster_with_draft_info(
                league_id=league_id,
                team_name="My Team"
            )
            
            if roster:
                # Export to CSV for manual editing
                csv_path = "data/my_roster_from_yahoo.csv"
                CSVImporter.export_roster(roster, csv_path)
                
                print(f"\n✅ Roster exported to: {csv_path}")
                print(f"   Players: {len(roster.players)}")
                print("\n⚠️  IMPORTANT: Yahoo API doesn't provide draft history")
                print("   You need to manually add draft information:")
                print(f"   1. Open: {csv_path}")
                print("   2. For each player, fill in:")
                print("      - draft_round (what round you drafted them)")
                print("      - draft_year (what year you drafted them)")
                print("      - years_kept (how many times you've kept them)")
                print("      - adp (optional: their current ADP for value analysis)")
                print("   3. Save the file")
                print("   4. Run: npm run analyze:csv")
                
                print("\n💡 Tip: Look up player ADPs at:")
                print("   - https://www.fantasypros.com/mlb/adp/overall.php")
                print("   - https://nfc.shgn.com/adp/baseball")
    
    print("\n" + "="*80)
    print("✨ Setup complete!")
    print("\nNext steps:")
    print("1. Edit data/my_roster_from_yahoo.csv with draft information")
    print("2. Run: npm run analyze:csv")
    print("3. Get keeper recommendations!")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
