#!/usr/bin/env python3
"""
Daily Lineup Recommendations
Get start/sit advice based on matchups, park factors, and recent performance
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / 'packages'))

from src.lineup_optimizer import LineupOptimizer, print_lineup_recommendations
from src.daily_matchups import MLBStatsAPI
from src.importers import CSVImporter
from src.models import Player, Roster


def main():
    parser = argparse.ArgumentParser(
        description='Daily Lineup Optimizer - Start/Sit Recommendations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                       # Today's recommendations
  %(prog)s --date 2026-05-15     # Specific date
  %(prog)s --schedule            # Show today's games only
  %(prog)s --demo                # Demo mode with sample roster
        """
    )
    parser.add_argument('--date', type=str, help='Date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--schedule', action='store_true', help='Show today\'s schedule only')
    parser.add_argument('--demo', action='store_true', help='Demo mode')
    args = parser.parse_args()
    
    date = args.date or datetime.now().strftime('%Y-%m-%d')
    
    print("\n⚾ DAILY LINEUP OPTIMIZER")
    print("="*70)
    print(f"Date: {date}")
    print("="*70 + "\n")
    
    api = MLBStatsAPI()
    
    # Show schedule
    if args.schedule:
        show_schedule(api, date)
        return
    
    # Load roster
    roster_file = app_root / "data" / "my_roster_from_yahoo.csv"
    
    if not roster_file.exists() or args.demo:
        print("📝 Using demo roster\n")
        roster = create_demo_roster()
    else:
        print("📋 Loading your roster...")
        roster = CSVImporter.import_roster(roster_file, team_name="2balls")
        print(f"✅ Loaded {len(roster.players)} players\n")
    
    # Check for games
    games = api.get_todays_games(date)
    
    if not games:
        print(f"❌ No MLB games scheduled for {date}")
        print("\nℹ️  The MLB season typically runs from early April to late September.")
        print("   Playoffs run through October.")
        print("\n💡 Try with --demo to see how it works")
        return
    
    print(f"📅 {len(games)} games scheduled:\n")
    for game in games[:5]:  # Show first 5
        print(f"  • {game.away_team} @ {game.home_team} - {game.game_time}")
    if len(games) > 5:
        print(f"  ... and {len(games) - 5} more")
    print()
    
    # Get recommendations
    print("🤖 Analyzing matchups...")
    optimizer = LineupOptimizer()
    recommendations = optimizer.get_daily_recommendations(roster, date)
    
    if not recommendations:
        print("\n⚠️  No players from your roster are playing today.")
        return
    
    # Display recommendations
    print_lineup_recommendations(recommendations)
    
    # Export option
    export_path = app_root / "data" / f"lineup_recommendations_{date}.txt"
    with open(export_path, 'w') as f:
        f.write(f"DAILY LINEUP RECOMMENDATIONS - {date}\n")
        f.write("="*70 + "\n\n")
        for rec in recommendations:
            f.write(str(rec) + "\n")
    
    print(f"\n💾 Recommendations saved to: {export_path}")


def show_schedule(api: MLBStatsAPI, date: str):
    """Show today's MLB schedule"""
    games = api.get_todays_games(date)
    
    if not games:
        print(f"❌ No games scheduled for {date}")
        print("\nℹ️  Try during MLB season (April-October)")
        return
    
    print(f"\n📅 MLB SCHEDULE - {date}")
    print("="*70)
    print(f"{len(games)} games\n")
    
    for i, game in enumerate(games, 1):
        print(f"\n{i}. {game.away_team} @ {game.home_team}")
        print(f"   Time: {game.game_time}")
        
        if game.away_pitcher and game.home_pitcher:
            print(f"   Pitchers: {game.away_pitcher} vs {game.home_pitcher}")
        
        if game.venue:
            from src.daily_matchups import get_park_factor
            pf = get_park_factor(game.venue)
            park_type = "⬆️ Hitter friendly" if pf > 1.05 else "⬇️ Pitcher friendly" if pf < 0.95 else "➡️ Neutral"
            print(f"   Park: {game.venue} ({pf:.2f}) {park_type}")
        
        if game.weather:
            temp = game.weather.get('temp')
            condition = game.weather.get('condition')
            wind = game.weather.get('wind')
            if temp:
                print(f"   Weather: {temp}°F", end="")
                if condition:
                    print(f", {condition}", end="")
                if wind:
                    print(f", Wind: {wind}", end="")
                print()


def create_demo_roster() -> Roster:
    """Create a demo roster for testing"""
    players = [
        Player(name="Mookie Betts", position="2B,OF", team="LAD", draft_round=1, draft_year=2026, adp=45.0),
        Player(name="Gunnar Henderson", position="SS", team="BAL", draft_round=2, draft_year=2026, adp=17.2),
        Player(name="Aaron Judge", position="OF", team="NYY", draft_round=1, draft_year=2026, adp=8.0),
        Player(name="Ronald Acuña Jr.", position="OF", team="ATL", draft_round=1, draft_year=2026, adp=8.6),
        Player(name="Shohei Ohtani", position="DH", team="LAD", draft_round=1, draft_year=2026, adp=1.0),
        Player(name="Bobby Witt Jr.", position="SS", team="KC", draft_round=1, draft_year=2026, adp=12.5),
        Player(name="Zack Wheeler", position="SP", team="PHI", draft_round=3, draft_year=2026, adp=29.0),
        Player(name="Corbin Burnes", position="SP", team="BAL", draft_round=2, draft_year=2026, adp=18.0),
    ]
    
    return Roster(team_name="Demo Team", players=players)


if __name__ == "__main__":
    main()
