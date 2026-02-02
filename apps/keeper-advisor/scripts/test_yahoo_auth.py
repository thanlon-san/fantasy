#!/usr/bin/env python3
"""Quick test of Yahoo API authentication"""

import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_client import YahooFantasyClient, print_leagues

def main():
    print("\n🔐 Testing Yahoo Fantasy API authentication...")
    
    client = YahooFantasyClient("config/oauth2.json")
    
    if client.authenticate():
        print("\n✅ Authentication successful!")
        print("\n🔍 Fetching your Fantasy Baseball leagues...")
        
        # Try 2026 first
        leagues = client.get_leagues(year=2026, sport="mlb")
        
        if not leagues:
            print("   No leagues found for 2026, trying 2025...")
            leagues = client.get_leagues(year=2025, sport="mlb")
        
        if leagues:
            print_leagues(leagues)
            return 0
        else:
            print("\n⚠️  No Fantasy Baseball leagues found")
            print("   Make sure you have a Yahoo Fantasy Baseball league")
            return 1
    else:
        print("\n❌ Authentication failed")
        print("   Check your Consumer Key and Secret in config/oauth2.json")
        return 1

if __name__ == "__main__":
    sys.exit(main())
