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

from shared.yahoo import YahooFantasyClient, YahooOAuth2
from shared.logger import get_logger

logger = get_logger(__name__)

FANTASY_GAMES_URL = (
    "https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games?format=json"
)


def print_leagues(leagues):
    for i, league in enumerate(leagues, 1):
        print(
            f"  {i}. {league.get('name')} "
            f"(key={league.get('league_key')}, season={league.get('season')})"
        )


def ensure_yahoo_session(oauth_file: Path) -> YahooFantasyClient:
    """Refresh tokens (or run browser OAuth) and return an API client."""
    oauth = YahooOAuth2.load_from_file(str(oauth_file))

    if oauth.refresh_token and oauth.refresh_access_token():
        oauth.save_to_file(str(oauth_file))
        print("✅ Access token refreshed")
    elif oauth.authorize():
        oauth.save_to_file(str(oauth_file))
        print("✅ Browser authorization complete")
    else:
        raise RuntimeError(
            "Could not refresh or obtain Yahoo tokens. "
            "Try: python scripts/test_yahoo_oauth.py"
        )

    return YahooFantasyClient(oauth)


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
    try:
        client = ensure_yahoo_session(oauth_file)
    except RuntimeError as exc:
        print(f"\n❌ Authentication failed: {exc}")
        return 1

    probe = client.session.get(FANTASY_GAMES_URL)
    if probe.status_code == 403:
        print("\n❌ Yahoo Fantasy API returned 403 (application not authorized).")
        print("   Your tokens refreshed, but the Yahoo developer app lacks Fantasy Sports access.")
        print("   At https://developer.yahoo.com/apps/ enable Fantasy Sports (Read), then run:")
        print("     python scripts/test_yahoo_oauth.py")
        return 1
    if probe.status_code != 200:
        print(f"\n❌ Fantasy API probe failed: HTTP {probe.status_code}")
        print(probe.text[:400])
        return 1

    print("✅ Fantasy API reachable")

    # Get leagues
    print("\n🔍 Fetching your Fantasy Baseball leagues...")
    leagues = client.get_user_leagues(year=2026, sport="mlb")

    if not leagues:
        print("\n⚠️  No leagues found for 2026")
        print("   Try a different year:")
        year_input = input("   Enter year (e.g., 2025): ").strip()
        if year_input:
            leagues = client.get_user_leagues(year=int(year_input), sport="mlb")

    if leagues:
        print_leagues(leagues)
        print(
            "\n💡 To export a roster with draft history, run from baseball-engine:"
        )
        print("     npm run fetch:roster")
    
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
