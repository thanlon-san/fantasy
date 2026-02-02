#!/usr/bin/env python3
"""
Waiver Wire Assistant
Fetch free agents and generate pickup recommendations
"""

import sys
import json
import argparse
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / 'packages'))

from src.yahoo_client import YahooFantasyClient
from src.yahoo_oauth_manual import YahooOAuth2
from src.importers import CSVImporter
from src.waiver_analyzer import WaiverAnalyzer, print_waiver_report


# Sample free agents for demo mode
SAMPLE_FREE_AGENTS = [
    {'name': 'Pete Alonso', 'eligible_positions': ['1B'], 'editorial_team_abbr': 'BAL'},
    {'name': 'Jazz Chisholm Jr.', 'eligible_positions': ['2B', '3B'], 'editorial_team_abbr': 'NYY'},
    {'name': 'Brice Turang', 'eligible_positions': ['2B'], 'editorial_team_abbr': 'MIL'},
    {'name': 'Ketel Marte', 'eligible_positions': ['2B'], 'editorial_team_abbr': 'ARI'},
    {'name': 'Wyatt Langford', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'TEX'},
    {'name': 'Luis Robert Jr.', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'NYM'},
    {'name': 'Corbin Carroll', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'ARI'},
    {'name': 'Joe Ryan', 'eligible_positions': ['SP'], 'editorial_team_abbr': 'MIN'},
    {'name': 'Hunter Greene', 'eligible_positions': ['SP'], 'editorial_team_abbr': 'CIN'},
]


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Waiver Wire Assistant - Find upgrade opportunities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Full analysis
  %(prog)s --position 2B      # Only second basemen
  %(prog)s --position SP      # Only starting pitchers  
  %(prog)s --top 5            # Show top 5 recommendations
        """
    )
    parser.add_argument('--position', type=str, help='Filter by position (e.g., 2B, SP, OF)')
    parser.add_argument('--top', type=int, default=10, help='Number of recommendations to show (default: 10)')
    parser.add_argument('--demo', action='store_true', help='Force demo mode with sample data')
    args = parser.parse_args()
    
    print("\n🔍 WAIVER WIRE ASSISTANT")
    print("="*70)
    if args.position:
        print(f"📍 Filtering for position: {args.position}")
    if args.demo:
        print(f"🎮 Demo mode enabled")
    print("="*70 + "\n")
    
    # Load roster
    print("📋 Loading your current roster...")
    roster = CSVImporter.import_roster(
        app_root / "data" / "my_roster_from_yahoo.csv",
        team_name="2balls"
    )
    print(f"✅ Loaded {len(roster.players)} players\n")
    
    # Get free agents
    if args.demo:
        free_agents = SAMPLE_FREE_AGENTS
        print(f"📝 Using {len(free_agents)} sample free agents for demo\n")
    else:
        free_agents = fetch_free_agents()
    
    # Analyze waiver wire
    print("🤖 Analyzing pickup opportunities...\n")
    analyzer = WaiverAnalyzer(roster)
    recommendations = analyzer.analyze_free_agents(
        free_agents, 
        max_recommendations=args.top,
        position_filter=args.position
    )
    
    # Print report
    print_waiver_report(recommendations)
    
    if args.position and not recommendations:
        print(f"\n💡 TIP: No {args.position} upgrades found. Try without --position filter.")


def fetch_free_agents():
    """Fetch free agents from Yahoo API or use sample data"""
    print("🔎 Fetching free agents from Yahoo...")
    
    try:
        # Load config
        config_file = app_root / "config" / "oauth2.json"
        with open(config_file) as f:
            config = json.load(f)
        
        client_id = config.get('consumer_key')
        client_secret = config.get('consumer_secret')
        
        if not client_id or not client_secret:
            print("⚠️  Missing Yahoo API credentials - using demo mode")
            return SAMPLE_FREE_AGENTS
        
        oauth = YahooOAuth2(client_id, client_secret)
        
        # Load existing tokens
        if 'access_token' in config:
            oauth.access_token = config['access_token']
            oauth.refresh_token = config.get('refresh_token')
            oauth.token_type = config.get('token_type', 'Bearer')
        
        if not oauth.access_token:
            print("⚠️  No access token - run: npm run setup:yahoo")
            return SAMPLE_FREE_AGENTS
        
        client = YahooFantasyClient(oauth)
        
        # Get leagues
        leagues = client.get_user_leagues(year=2025, sport="mlb")
        
        if not leagues:
            print("⚠️  No leagues found - using demo mode")
            return SAMPLE_FREE_AGENTS
        
        # Find target league
        league_key = None
        for league in leagues:
            if 'California Palm League' in league.get('name', ''):
                league_key = league['league_key']
                break
        
        if not league_key:
            print("⚠️  League not found - using demo mode")
            return SAMPLE_FREE_AGENTS
        
        # Fetch free agents
        free_agents = client.get_free_agents(league_key, count=50)
        
        if len(free_agents) == 0:
            print("⚠️  No free agents returned (off-season?) - using demo mode")
            return SAMPLE_FREE_AGENTS
        
        print(f"✅ Found {len(free_agents)} free agents")
        return free_agents
        
    except Exception as e:
        print(f"⚠️  Error: {e}")
        print("📝 Using demo mode with sample data")
        return SAMPLE_FREE_AGENTS


if __name__ == "__main__":
    main()
