#!/usr/bin/env python3
"""
Interactive Waiver Wire Assistant
Arrow key navigation and interactive selection
"""

import sys
import json
from pathlib import Path
from typing import List, Optional

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import radiolist_dialog, button_dialog, message_dialog

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / 'packages'))

from src.yahoo_client import YahooFantasyClient
from src.yahoo_oauth_manual import YahooOAuth2
from src.importers import CSVImporter
from src.waiver_analyzer import WaiverAnalyzer, WaiverRecommendation


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
    print("\n🔍 INTERACTIVE WAIVER WIRE ASSISTANT")
    print("="*70)
    print("Navigate with arrow keys, Enter to select\n")
    
    # Load roster
    print("📋 Loading your current roster...")
    roster = CSVImporter.import_roster(
        app_root / "data" / "my_roster_from_yahoo.csv",
        team_name="2balls"
    )
    print(f"✅ Loaded {len(roster.players)} players\n")
    
    # Interactive mode selection
    mode = button_dialog(
        title='Waiver Wire Mode',
        text='How would you like to proceed?',
        buttons=[
            ('Live', 'live'),
            ('Demo', 'demo'),
            ('Exit', 'exit'),
        ],
    ).run()
    
    if mode == 'exit':
        print("\n👋 Goodbye!")
        return
    
    # Get free agents
    if mode == 'demo':
        free_agents = SAMPLE_FREE_AGENTS
        print(f"\n📝 Using {len(free_agents)} sample free agents for demo")
    else:
        free_agents = fetch_free_agents()
        if not free_agents:
            print("\n⚠️  No free agents available. Using demo mode.")
            free_agents = SAMPLE_FREE_AGENTS
    
    # Position filter selection
    positions = radiolist_dialog(
        title='Position Filter',
        text='Filter by position? (optional)',
        values=[
            ('all', 'All Positions'),
            ('C', 'Catcher'),
            ('1B', 'First Base'),
            ('2B', 'Second Base'),
            ('3B', 'Third Base'),
            ('SS', 'Shortstop'),
            ('OF', 'Outfield'),
            ('Util', 'Utility'),
            ('SP', 'Starting Pitcher'),
            ('RP', 'Relief Pitcher'),
            ('P', 'Pitcher'),
        ],
    ).run()
    
    if positions is None:
        print("\n❌ Cancelled")
        return
    
    position_filter = None if positions == 'all' else positions
    
    # Number of recommendations
    top_n_values = [(str(i), str(i)) for i in [3, 5, 10, 15, 20]]
    top_n = radiolist_dialog(
        title='Number of Recommendations',
        text='How many recommendations would you like?',
        values=top_n_values,
        default='10'
    ).run()
    
    if top_n is None:
        print("\n❌ Cancelled")
        return
    
    max_recommendations = int(top_n)
    
    # Analyze waiver wire
    print(f"\n🤖 Analyzing pickup opportunities...")
    if position_filter:
        print(f"📍 Filtering for position: {position_filter}")
    
    analyzer = WaiverAnalyzer(roster)
    recommendations = analyzer.analyze_free_agents(
        free_agents,
        max_recommendations=max_recommendations,
        position_filter=position_filter
    )
    
    if not recommendations:
        message_dialog(
            title='No Recommendations',
            text='No suitable waiver wire upgrades found.\n\n'
                 'Try adjusting your filters or wait for better options.'
        ).run()
        return
    
    # Display recommendations interactively
    display_recommendations_interactive(recommendations)


def display_recommendations_interactive(recommendations: List[WaiverRecommendation]):
    """Display recommendations with interactive selection"""
    
    while True:
        # Group by confidence
        strong = [r for r in recommendations if r.confidence == "STRONG"]
        good = [r for r in recommendations if r.confidence == "GOOD"]
        consider = [r for r in recommendations if r.confidence == "CONSIDER"]
        
        # Build menu
        values = []
        
        if strong:
            values.append(('divider_strong', f'⭐ STRONG PICKUPS ({len(strong)} found)'))
            for i, rec in enumerate(strong[:10], 1):
                label = f"{i}. Add {rec.add_player.name} ({rec.add_player.position}) - Drop {rec.drop_player.name} (+{rec.value_gain:.0f})"
                values.append((rec, label))
        
        if good:
            values.append(('divider_good', f'✨ GOOD PICKUPS ({len(good)} found)'))
            for i, rec in enumerate(good[:5], 1):
                label = f"{i}. Add {rec.add_player.name} ({rec.add_player.position}) - Drop {rec.drop_player.name} (+{rec.value_gain:.0f})"
                values.append((rec, label))
        
        if consider:
            values.append(('divider_consider', f'💭 CONSIDER ({len(consider)} found)'))
            for i, rec in enumerate(consider[:5], 1):
                label = f"{i}. Add {rec.add_player.name} ({rec.add_player.position}) - Drop {rec.drop_player.name} (+{rec.value_gain:.0f})"
                values.append((rec, label))
        
        # Show selection dialog
        selected = radiolist_dialog(
            title='🎯 Waiver Wire Recommendations',
            text='Use arrow keys to navigate, Enter to see details, ESC to exit',
            values=values,
        ).run()
        
        if selected is None or isinstance(selected, str):
            # User pressed ESC or selected a divider
            break
        
        # Show recommendation details
        show_recommendation_details(selected)


def show_recommendation_details(rec: WaiverRecommendation):
    """Show detailed view of a single recommendation"""
    
    details = f"""
╔═══════════════════════════════════════════════════════════════╗
║                    WAIVER WIRE RECOMMENDATION                 ║
╚═══════════════════════════════════════════════════════════════╝

🆕 ADD:  {rec.add_player.name}
   Position: {rec.add_player.position}
   Team: {rec.add_player.team}
   ADP: {rec.add_player.adp}
   Keeper Cost: Round {rec.add_keeper_cost}

🗑️  DROP: {rec.drop_player.name}
   Position: {rec.drop_player.position}
   Team: {rec.drop_player.team}
   ADP: {rec.drop_player.adp or 'N/A'}
   {f'Keeper Cost: Round {rec.drop_keeper_cost}' if rec.drop_keeper_cost else 'Not keeper-eligible'}

📊 ANALYSIS:
   Value Gain: +{rec.value_gain:.1f} ADP points
   Confidence: {rec.confidence}
   Reason: {rec.reason}

═══════════════════════════════════════════════════════════════
"""
    
    action = button_dialog(
        title=f'💡 {rec.confidence} Recommendation',
        text=details,
        buttons=[
            ('Back', 'back'),
            ('Next', 'next'),
            ('Done', 'done'),
        ],
    ).run()
    
    # Could add more actions here (e.g., export to clipboard, add to watchlist)


def fetch_free_agents():
    """Fetch free agents from Yahoo API or use sample data"""
    try:
        # Load config
        config_file = app_root / "config" / "oauth2.json"
        with open(config_file) as f:
            config = json.load(f)
        
        client_id = config.get('consumer_key')
        client_secret = config.get('consumer_secret')
        
        if not client_id or not client_secret:
            return []
        
        oauth = YahooOAuth2(client_id, client_secret)
        
        # Load existing tokens
        if 'access_token' in config:
            oauth.access_token = config['access_token']
            oauth.refresh_token = config.get('refresh_token')
            oauth.token_type = config.get('token_type', 'Bearer')
        
        if not oauth.access_token:
            return []
        
        client = YahooFantasyClient(oauth)
        
        # Get leagues
        leagues = client.get_user_leagues(year=2025, sport="mlb")
        
        if not leagues:
            return []
        
        # Find target league
        league_key = None
        for league in leagues:
            if 'California Palm League' in league.get('name', ''):
                league_key = league['league_key']
                break
        
        if not league_key:
            return []
        
        # Fetch free agents
        free_agents = client.get_free_agents(league_key, count=50)
        return free_agents
        
    except Exception:
        return []


if __name__ == "__main__":
    main()
