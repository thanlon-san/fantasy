#!/usr/bin/env python3
"""
Breakout Scanner
Scan free agents for breakout candidates using Statcast data
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

from src.breakout_detector import BreakoutDetector, BreakoutSignal
from src.yahoo_client import YahooFantasyClient
from src.yahoo_oauth_manual import YahooOAuth2


# Sample free agents for demo mode
SAMPLE_FREE_AGENTS = [
    {'name': 'Pete Alonso'},
    {'name': 'Jazz Chisholm Jr.'},
    {'name': 'Wyatt Langford'},
    {'name': 'Luis Robert Jr.'},
    {'name': 'Joe Ryan'},
    {'name': 'Hunter Greene'},
    {'name': 'Gunnar Henderson'},
]


def main():
    parser = argparse.ArgumentParser(
        description='Breakout Scanner - Find emerging breakout players',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Scan free agents for hitters
  %(prog)s --pitchers               # Scan for pitchers
  %(prog)s --player "Gunnar Henderson"  # Analyze specific player
  %(prog)s --demo                   # Use sample data
        """
    )
    parser.add_argument('--pitchers', action='store_true', help='Scan for pitchers instead of hitters')
    parser.add_argument('--player', type=str, help='Analyze a specific player by name')
    parser.add_argument('--demo', action='store_true', help='Use sample data')
    parser.add_argument('--recent-days', type=int, default=14, help='Days for recent sample (default: 14)')
    parser.add_argument('--baseline-days', type=int, default=30, help='Days for baseline (default: 30)')
    args = parser.parse_args()
    
    player_type = 'pitcher' if args.pitchers else 'hitter'
    
    print("\n🔬 BREAKOUT SCANNER")
    print("="*70)
    print(f"Mode: {player_type.title()}s")
    print(f"Recent: Last {args.recent_days} days vs Baseline: Previous {args.baseline_days} days")
    print("="*70 + "\n")
    
    detector = BreakoutDetector()
    
    # Single player analysis
    if args.player:
        analyze_single_player(detector, args.player, player_type, args.recent_days, args.baseline_days)
        return
    
    # Scan free agents
    if args.demo:
        print("📝 Using sample data for demo\n")
        free_agents = SAMPLE_FREE_AGENTS
    else:
        free_agents = fetch_free_agents()
        if not free_agents:
            print("⚠️  No free agents available. Use --demo for sample data.")
            return
    
    print(f"🔎 Scanning {len(free_agents)} free agents for breakout signals...\n")
    
    alerts = detector.scan_free_agents(free_agents, player_type)
    
    if not alerts:
        print("📊 No significant breakout signals detected.")
        print("\nNote: Statcast data is only available during the MLB season.")
        print("      Run with --demo during off-season to see how it works.")
        return
    
    # Display alerts
    display_alerts(alerts)


def analyze_single_player(detector, player_name, player_type, recent_days, baseline_days):
    """Analyze a specific player"""
    parts = player_name.split()
    if len(parts) < 2:
        print("❌ Invalid name format. Use: 'FirstName LastName'")
        return
    
    first_name = parts[0]
    last_name = ' '.join(parts[1:])
    
    print(f"🔍 Analyzing {player_name} ({player_type})...\n")
    
    alert = detector.analyze_player(first_name, last_name, player_type, recent_days, baseline_days)
    
    if alert:
        print(alert)
        
        # Export option
        save_path = app_root / "data" / f"breakout_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(save_path, 'w') as f:
            json.dump({
                'player_name': alert.player_name,
                'player_id': alert.player_id,
                'signal': alert.signal.value,
                'confidence': alert.confidence_score,
                'improving_metrics': alert.improving_metrics,
                'declining_metrics': alert.declining_metrics,
                'summary': alert.summary,
                'advice': alert.actionable_advice,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        print(f"\n💾 Alert saved to: {save_path}")
    else:
        print("📊 No significant breakout signals detected for this player.")
        print("\nNote: Statcast data is only available during the MLB season.")


def display_alerts(alerts):
    """Display breakout alerts grouped by signal strength"""
    
    # Group by signal
    strong = [a for a in alerts if a.signal == BreakoutSignal.STRONG]
    emerging = [a for a in alerts if a.signal == BreakoutSignal.EMERGING]
    watch = [a for a in alerts if a.signal == BreakoutSignal.WATCH]
    fading = [a for a in alerts if a.signal == BreakoutSignal.FADING]
    
    # Display strong alerts
    if strong:
        print("\n🔥 STRONG BREAKOUT ALERTS")
        print("="*70)
        for alert in strong:
            print(alert)
    
    # Display emerging
    if emerging:
        print("\n⚡ EMERGING BREAKOUTS")
        print("="*70)
        for alert in emerging:
            print(alert)
    
    # Display watch list
    if watch:
        print("\n👀 WATCH LIST")
        print("="*70)
        for alert in watch:
            print(alert)
    
    # Display fading (sell high)
    if fading:
        print("\n⚠️  FADING PLAYERS (Sell High)")
        print("="*70)
        for alert in fading:
            print(alert)
    
    # Summary
    print("\n📊 SCAN SUMMARY")
    print("="*70)
    print(f"Strong Breakouts: {len(strong)}")
    print(f"Emerging: {len(emerging)}")
    print(f"Watch List: {len(watch)}")
    print(f"Fading: {len(fading)}")
    print(f"Total Alerts: {len(alerts)}")
    print("="*70)
    
    # Export all alerts
    if alerts:
        save_path = app_root / "data" / f"breakout_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(save_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_scanned': len(alerts),
                'alerts': [{
                    'player_name': a.player_name,
                    'signal': a.signal.value,
                    'confidence': a.confidence_score,
                    'summary': a.summary,
                    'advice': a.actionable_advice
                } for a in alerts]
            }, f, indent=2)
        print(f"\n💾 Full scan results saved to: {save_path}")


def fetch_free_agents():
    """Fetch free agents from Yahoo API"""
    try:
        config_file = app_root / "config" / "oauth2.json"
        with open(config_file) as f:
            config = json.load(f)
        
        client_id = config.get('consumer_key')
        client_secret = config.get('consumer_secret')
        
        if not client_id or not client_secret:
            return []
        
        oauth = YahooOAuth2(client_id, client_secret)
        
        if 'access_token' in config:
            oauth.access_token = config['access_token']
            oauth.refresh_token = config.get('refresh_token')
            oauth.token_type = config.get('token_type', 'Bearer')
        
        if not oauth.access_token:
            return []
        
        client = YahooFantasyClient(oauth)
        leagues = client.get_user_leagues(year=2025, sport="mlb")
        
        if not leagues:
            return []
        
        league_key = None
        for league in leagues:
            if 'California Palm League' in league.get('name', ''):
                league_key = league['league_key']
                break
        
        if not league_key:
            return []
        
        return client.get_free_agents(league_key, count=50)
        
    except Exception:
        return []


if __name__ == "__main__":
    main()
