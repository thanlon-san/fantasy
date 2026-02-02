#!/usr/bin/env python3
"""
Breakout Scanner
Scan free agents for breakout signals using Statcast data
Finds emerging talent before ADP catches up
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
from src.breakout_detector import BreakoutDetector, BreakoutSignal
from src.adp_fetcher import ADPFetcher


def main():
    parser = argparse.ArgumentParser(
        description='Breakout Scanner - Find emerging talent in free agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Scan all free agents
  %(prog)s --count 200        # Scan top 200 free agents
  %(prog)s --hitters-only     # Only scan hitters
  %(prog)s --pitchers-only    # Only scan pitchers
  %(prog)s --export           # Export to dashboard JSON
        """
    )
    parser.add_argument('--count', type=int, default=100, help='Number of free agents to scan (default: 100)')
    parser.add_argument('--hitters-only', action='store_true', help='Only scan hitters')
    parser.add_argument('--pitchers-only', action='store_true', help='Only scan pitchers')
    parser.add_argument('--export', action='store_true', help='Export to dashboard JSON')
    parser.add_argument('--demo', action='store_true', help='Use sample data')
    args = parser.parse_args()
    
    print("\n🔬 BREAKOUT SCANNER")
    print("="*70)
    print(f"🎯 Scanning top {args.count} free agents")
    if args.hitters_only:
        print("⚾ Hitters only")
    elif args.pitchers_only:
        print("🥎 Pitchers only")
    print("="*70 + "\n")
    
    # Get free agents
    if args.demo:
        free_agents = get_sample_free_agents()
    else:
        free_agents = fetch_free_agents(args.count)
    
    print(f"📋 Loaded {len(free_agents)} free agents\n")
    
    # Initialize detectors
    detector = BreakoutDetector()
    adp_fetcher = ADPFetcher()
    
    # Scan for breakouts
    print("🔍 Analyzing Statcast data...\n")
    
    strong_signals = []
    emerging_signals = []
    watch_signals = []
    
    for i, player in enumerate(free_agents):
        name = player.get('name', '')
        positions = player.get('eligible_positions', [])
        team = player.get('editorial_team_abbr', 'UNK')
        
        # Filter by player type if requested
        is_pitcher = any(p in ['SP', 'RP', 'P'] for p in positions)
        if args.hitters_only and is_pitcher:
            continue
        if args.pitchers_only and not is_pitcher:
            continue
        
        # Parse name
        parts = name.split()
        if len(parts) < 2:
            continue
        
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        player_type = 'pitcher' if is_pitcher else 'hitter'
        
        # Show progress
        if (i + 1) % 10 == 0:
            print(f"  Scanned {i + 1}/{len(free_agents)}... Found {len(strong_signals)} strong, {len(emerging_signals)} emerging")
        
        try:
            # Check for breakout
            alert = detector.analyze_player(
                first_name,
                last_name,
                player_type,
                recent_days=14,
                baseline_days=30
            )
            
            if not alert:
                continue
            
            # Get ADP for context
            adp = adp_fetcher.get_player_adp(name)
            
            player_info = {
                'name': name,
                'positions': ','.join(positions),
                'team': team,
                'signal': alert.signal.value,
                'category': alert.category.value,
                'description': alert.description,
                'adp': int(adp) if adp else 999,
                'alert': alert
            }
            
            if alert.signal == BreakoutSignal.STRONG:
                strong_signals.append(player_info)
                print(f"  🔥 STRONG: {name} ({player_info['positions']}) - {alert.category.value}")
            elif alert.signal == BreakoutSignal.EMERGING:
                emerging_signals.append(player_info)
                print(f"  ⚡ EMERGING: {name} ({player_info['positions']}) - {alert.category.value}")
            elif alert.signal == BreakoutSignal.WATCH:
                watch_signals.append(player_info)
        
        except Exception as e:
            # Player not in Statcast or error - skip silently
            continue
    
    # Print results
    print("\n" + "="*70)
    print("🎯 BREAKOUT SCAN RESULTS")
    print("="*70)
    
    if strong_signals:
        print(f"\n🔥 STRONG BREAKOUTS ({len(strong_signals)} found)")
        print("-"*70)
        for player in sorted(strong_signals, key=lambda p: p['adp']):
            print(f"\n{player['name']} ({player['positions']}) - {player['team']}")
            print(f"  ADP: {player['adp']} | {player['category']} breakout")
            print(f"  {player['description']}")
    
    if emerging_signals:
        print(f"\n⚡ EMERGING BREAKOUTS ({len(emerging_signals)} found)")
        print("-"*70)
        for player in sorted(emerging_signals, key=lambda p: p['adp'])[:10]:
            print(f"\n{player['name']} ({player['positions']}) - {player['team']}")
            print(f"  ADP: {player['adp']} | {player['category']} breakout")
            print(f"  {player['description']}")
    
    if watch_signals:
        print(f"\n👀 WATCH LIST ({len(watch_signals)} found)")
        print("-"*70)
        print(f"  {len(watch_signals)} players showing early signals")
    
    # Summary
    print("\n" + "="*70)
    print(f"📊 SUMMARY")
    print("-"*70)
    print(f"Free agents scanned: {len(free_agents)}")
    print(f"STRONG breakouts: {len(strong_signals)}")
    print(f"EMERGING breakouts: {len(emerging_signals)}")
    print(f"Watch list: {len(watch_signals)}")
    print("="*70)
    
    if not strong_signals and not emerging_signals:
        print("\n💡 TIP: No breakouts found. Try during the season when Statcast data is fresh!")
    else:
        print("\n💡 TIP: Strong breakouts are immediate adds. Act fast!")
    
    print("="*70 + "\n")
    
    # Export to dashboard
    if args.export:
        export_to_dashboard(strong_signals + emerging_signals)


def fetch_free_agents(count):
    """Fetch free agents from Yahoo API"""
    print(f"🔎 Fetching top {count} free agents from Yahoo...")
    
    try:
        config_file = app_root / "config" / "oauth2.json"
        with open(config_file) as f:
            config = json.load(f)
        
        client_id = config.get('consumer_key')
        client_secret = config.get('consumer_secret')
        
        if not client_id or not client_secret:
            print("⚠️  Missing Yahoo API credentials - using demo mode")
            return get_sample_free_agents()
        
        oauth = YahooOAuth2(client_id, client_secret)
        
        if 'access_token' in config:
            oauth.access_token = config['access_token']
            oauth.refresh_token = config.get('refresh_token')
            oauth.token_type = config.get('token_type', 'Bearer')
        
        if not oauth.access_token:
            print("⚠️  No access token - run: npm run setup:yahoo")
            return get_sample_free_agents()
        
        client = YahooFantasyClient(oauth)
        leagues = client.get_user_leagues(year=2025, sport="mlb")
        
        if not leagues:
            print("⚠️  No leagues found - using demo mode")
            return get_sample_free_agents()
        
        league_key = None
        for league in leagues:
            if 'California Palm League' in league.get('name', ''):
                league_key = league['league_key']
                break
        
        if not league_key:
            print("⚠️  League not found - using demo mode")
            return get_sample_free_agents()
        
        free_agents = client.get_free_agents(league_key, count=count)
        
        if len(free_agents) == 0:
            print("⚠️  No free agents returned (off-season?) - using demo mode")
            return get_sample_free_agents()
        
        print(f"✅ Found {len(free_agents)} free agents")
        return free_agents
        
    except Exception as e:
        print(f"⚠️  Error: {e}")
        print("📝 Using demo mode")
        return get_sample_free_agents()


def get_sample_free_agents():
    """Sample free agents for demo"""
    return [
        {'name': 'Pete Alonso', 'eligible_positions': ['1B'], 'editorial_team_abbr': 'NYM'},
        {'name': 'Jazz Chisholm Jr.', 'eligible_positions': ['2B', '3B'], 'editorial_team_abbr': 'NYY'},
        {'name': 'Wyatt Langford', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'TEX'},
        {'name': 'Corbin Carroll', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'ARI'},
        {'name': 'Hunter Greene', 'eligible_positions': ['SP'], 'editorial_team_abbr': 'CIN'},
    ]


def export_to_dashboard(breakouts):
    """Export breakout signals to dashboard JSON"""
    dashboard_root = workspace_root / "apps" / "baseball-dashboard"
    output_dir = dashboard_root / "public" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n📤 Exporting to dashboard...")
    
    data = {
        "generated_at": datetime.now().isoformat(),
        "alerts": [
            {
                "player": b['name'],
                "signal": b['signal'],
                "stat": b['description'],
                "category": b['category']
            }
            for b in breakouts
        ]
    }
    
    output_file = output_dir / "breakouts.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Exported {len(breakouts)} breakouts to {output_file}")


if __name__ == "__main__":
    main()
