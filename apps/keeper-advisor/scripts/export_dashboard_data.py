#!/usr/bin/env python3
"""
Export Dashboard Data
Generate JSON files for the baseball dashboard from real Python analysis
"""

import json
import sys
from pathlib import Path
from datetime import datetime

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / 'packages'))

from src.importers import CSVImporter
from src.lineup_optimizer import LineupOptimizer
from src.waiver_analyzer import WaiverAnalyzer
from src.analyzer import KeeperAnalyzer
from src.breakout_detector import BreakoutDetector
from src.accuracy_tracker import AccuracyTracker

# Output directory
dashboard_root = workspace_root / "apps" / "baseball-dashboard"
output_dir = dashboard_root / "public" / "api"
output_dir.mkdir(parents=True, exist_ok=True)

print("\n🔄 Exporting dashboard data...")
print("="*70)

# Load roster
print("\n📋 Loading roster...")
roster = CSVImporter.import_roster(
    app_root / "data" / "my_roster_from_yahoo.csv",
    team_name="2balls"
)
print(f"✅ Loaded {len(roster.players)} players")

# 1. Daily Lineup
print("\n📊 Generating daily lineup recommendations...")
try:
    optimizer = LineupOptimizer(use_breakout_signals=True)
    recommendations = optimizer.get_daily_recommendations(roster, show_all_players=True)
    
    # Log predictions for accuracy tracking
    tracker = AccuracyTracker()
    today = datetime.now().strftime("%Y-%m-%d")
    for rec in recommendations:
        if rec.opponent != "No game":  # Only log games being played
            tracker.log_prediction(
                date=today,
                player_name=rec.player.name,
                player_position=rec.player.position,
                team=rec.player.team,
                opponent=rec.opponent,
                confidence_score=rec.confidence_score,
                recommendation=rec.recommendation.value,
                matchup_score=rec.matchup_score,
                park_score=rec.park_score,
                form_score=rec.form_score,
                platoon_score=rec.platoon_score,
                breakout_boost=rec.breakout_boost
            )
    print(f"✅ Logged {len([r for r in recommendations if r.opponent != 'No game'])} predictions for tracking")
    
    # Group into categories
    playing = [r for r in recommendations if r.opponent != "No game"]
    not_playing = [r for r in recommendations if r.opponent == "No game"]
    
    # Separate into tiers
    must_start = [r for r in playing if r.confidence_score >= 80]
    start = [r for r in playing if 65 <= r.confidence_score < 80]
    flex = [r for r in playing if 50 <= r.confidence_score < 65]
    bench = [r for r in playing if r.confidence_score < 50]
    
    lineup_data = {
        "generated_at": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "must_start": [
            {
                "player": r.player.name,
                "position": r.player.position,
                "team": r.player.team,
                "opponent": f"{'@' if r.home_away == 'away' else 'vs'} {r.opponent}",
                "opponent_pitcher": r.opponent_pitcher or "TBD",
                "game_time": r.game_time or "TBD",
                "confidence": int(r.confidence_score),
                "matchup": r.matchup_score,
                "parkFactor": r.park_score,
                "platoon": r.platoon_score,
                "form": r.form_score,
                "breakout": r.breakout_boost,
                "reasons": r.reasons
            }
            for r in must_start
        ],
        "start": [
            {
                "player": r.player.name,
                "position": r.player.position,
                "team": r.player.team,
                "opponent": f"{'@' if r.home_away == 'away' else 'vs'} {r.opponent}",
                "opponent_pitcher": r.opponent_pitcher or "TBD",
                "game_time": r.game_time or "TBD",
                "confidence": int(r.confidence_score),
                "matchup": r.matchup_score,
                "parkFactor": r.park_score,
                "platoon": r.platoon_score,
                "form": r.form_score,
                "breakout": r.breakout_boost,
                "reasons": r.reasons
            }
            for r in start
        ],
        "flex": [
            {
                "player": r.player.name,
                "position": r.player.position,
                "team": r.player.team,
                "opponent": f"{'@' if r.home_away == 'away' else 'vs'} {r.opponent}",
                "opponent_pitcher": r.opponent_pitcher or "TBD",
                "game_time": r.game_time or "TBD",
                "confidence": int(r.confidence_score),
                "matchup": r.matchup_score,
                "parkFactor": r.park_score,
                "platoon": r.platoon_score,
                "form": r.form_score,
                "breakout": r.breakout_boost,
                "reasons": r.reasons
            }
            for r in flex
        ],
        "bench": [
            {
                "player": r.player.name,
                "position": r.player.position,
                "team": r.player.team,
                "opponent": f"{'@' if r.home_away == 'away' else 'vs'} {r.opponent}",
                "opponent_pitcher": r.opponent_pitcher or "TBD",
                "game_time": r.game_time or "TBD",
                "confidence": int(r.confidence_score),
                "matchup": r.matchup_score,
                "parkFactor": r.park_score,
                "platoon": r.platoon_score,
                "form": r.form_score,
                "breakout": r.breakout_boost,
                "reasons": r.reasons
            }
            for r in bench
        ],
        "not_playing": [
            {
                "player": r.player.name,
                "position": r.player.position,
                "team": r.player.team,
                "adp": r.player.adp
            }
            for r in not_playing
        ],
        "summary": {
            "total_roster": len(recommendations),
            "playing_today": len(playing),
            "not_playing": len(not_playing),
            "must_start_count": len(must_start),
            "start_count": len(start),
            "flex_count": len(flex),
            "bench_count": len(bench)
        }
    }
    
    with open(output_dir / "daily_lineup.json", "w") as f:
        json.dump(lineup_data, f, indent=2)
    
    print(f"✅ Exported daily lineup: {len(playing)} playing, {len(not_playing)} not playing")
    
except Exception as e:
    print(f"❌ Error generating lineup: {e}")
    # Create minimal data
    lineup_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "must_start": [],
        "start": [],
        "flex": [],
        "bench": [],
        "not_playing": []
    }
    with open(output_dir / "daily_lineup.json", "w") as f:
        json.dump(lineup_data, f, indent=2)

# 2. Waiver Wire (demo - would fetch free agents in production)
print("\n🎯 Generating waiver wire data...")
waiver_data = {
    "generated_at": datetime.now().isoformat(),
    "note": "Run waiver_wire.py with Yahoo API for live data",
    "targets": [
        {
            "player": "Example Player",
            "position": "OF",
            "adp": 150,
            "reason": "Run: python scripts/waiver_wire.py"
        }
    ]
}
with open(output_dir / "waiver_wire.json", "w") as f:
    json.dump(waiver_data, f, indent=2)
print("✅ Exported waiver wire data (placeholder)")

# 3. Breakouts (demo - would scan free agents in production)
print("\n🔬 Generating breakout data...")
breakout_data = {
    "generated_at": datetime.now().isoformat(),
    "note": "Run breakout_scanner.py for live Statcast data",
    "alerts": [
        {
            "player": "Example Player",
            "signal": "STRONG",
            "stat": "Exit velo up 2.5 mph",
            "category": "Power"
        }
    ]
}
with open(output_dir / "breakouts.json", "w") as f:
    json.dump(breakout_data, f, indent=2)
print("✅ Exported breakout data (placeholder)")

# 4. Keepers
print("\n⭐ Generating keeper analysis...")
try:
    analyzer = KeeperAnalyzer(roster)
    analyses = analyzer.analyze_all_players()
    top_keepers = analyzer.get_recommended_keepers(3)
    
    keeper_data = {
        "generated_at": datetime.now().isoformat(),
        "keepers": [
            {
                "player": k.player.name,
                "position": k.player.position,
                "round": k.adjusted_keeper_round or k.keeper_round,
                "adp": int(k.player.adp) if k.player.adp else 0,
                "surplus": f"+{int(k.surplus_value)}" if k.surplus_value else "N/A",
                "value": k.recommendation,
                "years_remaining": k.years_remaining,
                "reason": k.recommendation_reason
            }
            for k in top_keepers
        ],
        "summary": {
            "total_eligible": len([a for a in analyses if a.is_eligible]),
            "recommended": len([a for a in analyses if a.recommendation == "Keep"])
        }
    }
    
    with open(output_dir / "keepers.json", "w") as f:
        json.dump(keeper_data, f, indent=2)
    
    print(f"✅ Exported keeper data: {len(top_keepers)} recommended")
    
except Exception as e:
    print(f"❌ Error generating keepers: {e}")
    keeper_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "keepers": []
    }
    with open(output_dir / "keepers.json", "w") as f:
        json.dump(keeper_data, f, indent=2)

print("\n" + "="*70)
print("✅ Dashboard data export complete!")
print(f"📁 Output: {output_dir}")
print("\n💡 To update dashboard:")
print("   1. Run this script: python scripts/export_dashboard_data.py")
print("   2. Commit the updated JSON files")
print("   3. Push to GitHub (auto-deploys to GitHub Pages)")
print("="*70 + "\n")
