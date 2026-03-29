#!/usr/bin/env python3
"""
Waiver Wire Assistant
Comprehensive free agent scanning with breakout detection
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / 'packages'))

from src.yahoo_client import YahooFantasyClient
from src.yahoo_oauth_manual import YahooOAuth2
from src.importers import CSVImporter
from src.waiver_analyzer import WaiverAnalyzer, print_waiver_report
from src.breakout_detector import BreakoutDetector, BreakoutSignal
from src.models import Player


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
        description='Waiver Wire Assistant - Comprehensive free agent scanning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Full scan with breakout detection
  %(prog)s --position 2B      # Only second basemen
  %(prog)s --position SP      # Only starting pitchers  
  %(prog)s --top 5            # Show top 5 recommendations
  %(prog)s --count 200        # Scan top 200 free agents (default: 100)
  %(prog)s --demo             # Use sample data
  %(prog)s --export           # Export to dashboard JSON
        """
    )
    parser.add_argument('--position', type=str, help='Filter by position (e.g., 2B, SP, OF)')
    parser.add_argument('--top', type=int, default=15, help='Number of recommendations to show (default: 15)')
    parser.add_argument('--count', type=int, default=100, help='Number of free agents to scan (default: 100)')
    parser.add_argument('--demo', action='store_true', help='Force demo mode with sample data')
    parser.add_argument('--export', action='store_true', help='Export results to dashboard JSON')
    parser.add_argument('--no-breakouts', action='store_true', help='Skip breakout detection (faster)')
    args = parser.parse_args()
    
    print("\n🔍 COMPREHENSIVE WAIVER WIRE SCANNER")
    print("="*70)
    if args.position:
        print(f"📍 Filtering for position: {args.position}")
    if args.demo:
        print(f"🎮 Demo mode enabled")
    if args.no_breakouts:
        print(f"⚡ Breakout detection disabled (fast mode)")
    print(f"🎯 Scanning top {args.count} free agents")
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
        free_agents = fetch_free_agents(count=args.count)
    
    # Scan for breakouts (optional)
    breakout_signals = {}
    if not args.no_breakouts and not args.demo:
        print("🔬 Running breakout detection on free agents...")
        breakout_signals = scan_for_breakouts(free_agents)
        print(f"✅ Found {len([s for s in breakout_signals.values() if s])} players with breakout signals\n")
    
    # Analyze waiver wire (with breakout integration)
    print("🤖 Analyzing pickup opportunities...\n")
    analyzer = WaiverAnalyzer(roster, use_breakout_signals=(not args.no_breakouts))
    recommendations = analyzer.analyze_free_agents(
        free_agents, 
        max_recommendations=args.top * 3,  # Get more for filtering
        position_filter=args.position
    )
    
    # Sort by total value (ADP + breakout + position need)
    recommendations.sort(key=lambda r: r.value_gain, reverse=True)
    
    # Take top N
    top_recommendations = recommendations[:args.top]
    
    # Print report
    print_waiver_report(top_recommendations, breakout_signals=breakout_signals)
    
    # Export to dashboard
    if args.export:
        export_to_dashboard(top_recommendations, breakout_signals)
    
    if args.position and not recommendations:
        print(f"\n💡 TIP: No {args.position} upgrades found. Try without --position filter.")


def scan_for_breakouts(free_agents):
    """
    Scan free agents for breakout signals using Statcast data
    
    Args:
        free_agents: List of player dicts from Yahoo API
        
    Returns:
        Dict of player_name -> BreakoutAlert (or None)
    """
    detector = BreakoutDetector()
    breakout_signals = {}
    
    for i, player in enumerate(free_agents):
        name = player.get('name', '')
        
        # Parse name
        parts = name.split()
        if len(parts) < 2:
            continue
        
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        
        # Determine player type
        positions = player.get('eligible_positions', [])
        is_pitcher = any(p in ['SP', 'RP', 'P'] for p in positions)
        player_type = 'pitcher' if is_pitcher else 'hitter'
        
        try:
            # Check for breakout (during season only)
            alert = detector.analyze_player(
                first_name,
                last_name,
                player_type,
                recent_days=14,   # 2 weeks for waiver decisions
                baseline_days=30  # 1 month baseline
            )
            
            breakout_signals[name] = alert
            
            # Show progress for strong signals
            if alert and alert.signal in [BreakoutSignal.STRONG, BreakoutSignal.EMERGING]:
                print(f"  🔥 {name}: {alert.signal.value}")
            
        except Exception as e:
            # Player not found in Statcast or other error - just skip
            breakout_signals[name] = None
            continue
    
    return breakout_signals


def export_to_dashboard(recommendations, breakout_signals):
    """Export waiver recommendations to dashboard JSON"""
    dashboard_root = workspace_root / "apps" / "baseball-dashboard"
    output_dir = dashboard_root / "public" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n📤 Exporting to dashboard...")
    
    waiver_data = {
        "generated_at": datetime.now().isoformat(),
        "targets": []
    }
    
    for rec in recommendations:
        player_name = rec.add_player.name
        breakout = breakout_signals.get(player_name)
        
        target = {
            "player": player_name,
            "position": rec.add_player.position,
            "adp": int(rec.add_player.adp) if rec.add_player.adp else 999,
            "value_gain": int(rec.value_gain),
            "reason": rec.reason,
            "drop_player": rec.drop_player.name if rec.drop_player else None
        }
        
        # Add breakout signal if present
        if breakout:
            target["breakout_signal"] = breakout.signal.value
            target["breakout_category"] = breakout.category.value
        
        waiver_data["targets"].append(target)
    
    # Write to file
    output_file = output_dir / "waiver_wire.json"
    with open(output_file, "w") as f:
        json.dump(waiver_data, f, indent=2)
    
    print(f"✅ Exported {len(recommendations)} targets to {output_file}")


def fetch_free_agents(count=100):
    """Fetch free agents from Yahoo API or use sample data"""
    print(f"🔎 Fetching top {count} free agents from Yahoo...")
    
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
        free_agents = client.get_free_agents(league_key, count=count)
        
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
