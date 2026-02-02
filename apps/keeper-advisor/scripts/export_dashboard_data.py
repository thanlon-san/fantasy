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

# 2. Waiver Wire Analysis
print("\n🎯 Generating waiver wire data...")
try:
    # Initialize waiver analyzer with breakout detection
    waiver_analyzer = WaiverAnalyzer(roster, use_breakout_signals=True)
    
    # Sample free agents (in production, would fetch from Yahoo API)
    # Format matches what Yahoo API returns
    sample_free_agents = [
        {'name': 'Yoshinobu Yamamoto', 'eligible_positions': ['SP'], 'editorial_team_abbr': 'LAD'},
        {'name': 'Royce Lewis', 'eligible_positions': ['3B', 'OF'], 'editorial_team_abbr': 'MIN'},
        {'name': 'Wyatt Langford', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'TEX'},
        {'name': 'Luis Robert Jr.', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'CWS'},
        {'name': 'Hunter Greene', 'eligible_positions': ['SP'], 'editorial_team_abbr': 'CIN'},
        {'name': 'Bobby Miller', 'eligible_positions': ['SP'], 'editorial_team_abbr': 'LAD'},
        {'name': 'Ezequiel Tovar', 'eligible_positions': ['SS'], 'editorial_team_abbr': 'COL'},
        {'name': 'Colton Cowser', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'BAL'},
        {'name': 'Michael Busch', 'eligible_positions': ['1B', '2B'], 'editorial_team_abbr': 'CHC'},
        {'name': 'Spencer Steer', 'eligible_positions': ['2B', '3B', 'OF'], 'editorial_team_abbr': 'CIN'},
    ]
    
    # Analyze free agents against roster
    recommendations = waiver_analyzer.analyze_free_agents(sample_free_agents, top_n=5)
    
    waiver_data = {
        "generated_at": datetime.now().isoformat(),
        "targets": [
            {
                "player": rec.add_player.name,
                "position": rec.add_player.position,
                "team": rec.add_player.team,
                "adp": int(rec.add_player.adp) if rec.add_player.adp else 0,
                "value_gain": f"+{int(rec.value_gain)}",
                "drop_player": rec.drop_player.name,
                "confidence": rec.confidence,
                "reason": rec.reason
            }
            for rec in recommendations
        ],
        "summary": {
            "scanned": len(sample_free_agents),
            "recommended": len(recommendations)
        }
    }
    
    with open(output_dir / "waiver_wire.json", "w") as f:
        json.dump(waiver_data, f, indent=2)
    
    print(f"✅ Exported waiver wire: {len(recommendations)} recommendations from {len(sample_free_agents)} players")
    
except Exception as e:
    print(f"⚠️  Error generating waiver wire: {e}")
    import traceback
    traceback.print_exc()
    # Fallback to placeholder
    waiver_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "targets": []
    }
    with open(output_dir / "waiver_wire.json", "w") as f:
        json.dump(waiver_data, f, indent=2)

# 3. Breakout Detection
print("\n🔬 Generating breakout data...")
try:
    # Use the breakout detector already initialized in lineup optimizer
    if optimizer.breakout_detector:
        detector = optimizer.breakout_detector
        
        # Scan roster players for breakout signals
        breakout_alerts = []
        for player in roster.players:
            signals = detector.detect_breakout(player.name)
            if signals and signals.overall_signal != "NONE":
                breakout_alerts.append({
                    "player": player.name,
                    "position": player.position,
                    "team": player.team,
                    "signal": signals.overall_signal,
                    "stats": [
                        f"{metric}: {value}" 
                        for metric, value in [
                            ("Exit velo", signals.exit_velocity_trend),
                            ("Hard hit %", signals.hard_hit_rate_trend),
                            ("Barrel %", signals.barrel_rate_trend)
                        ]
                        if value and value != "stable"
                    ],
                    "category": signals.breakout_type or "General",
                    "confidence": signals.confidence
                })
        
        # Sort by signal strength
        signal_order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2}
        breakout_alerts.sort(key=lambda x: signal_order.get(x["signal"], 3))
        
        breakout_data = {
            "generated_at": datetime.now().isoformat(),
            "alerts": breakout_alerts[:10],  # Top 10 signals
            "summary": {
                "total_scanned": len(roster.players),
                "signals_found": len(breakout_alerts),
                "strong_signals": len([a for a in breakout_alerts if a["signal"] == "STRONG"])
            }
        }
        
        with open(output_dir / "breakouts.json", "w") as f:
            json.dump(breakout_data, f, indent=2)
        
        print(f"✅ Exported breakout data: {len(breakout_alerts)} signals found")
    else:
        raise Exception("Breakout detector not available")
    
except Exception as e:
    print(f"⚠️  Error generating breakout data: {e}")
    # Fallback to placeholder
    breakout_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "alerts": []
    }
    with open(output_dir / "breakouts.json", "w") as f:
        json.dump(breakout_data, f, indent=2)

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
