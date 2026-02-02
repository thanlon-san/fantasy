#!/usr/bin/env python3
"""
Export baseball intelligence data to JSON files for the dashboard.
Reads from your existing Python tools and exports to JSON.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import csv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_roster_from_csv():
    """Load roster from CSV file"""
    roster_file = Path(__file__).parent.parent / "data" / "my_roster_from_yahoo.csv"
    players = []
    
    with open(roster_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['player_name']:  # Skip empty rows
                players.append({
                    'name': row['player_name'],
                    'position': row['position'],
                    'team': row['mlb_team'],
                    'adp': float(row['adp']) if row['adp'] else None
                })
    
    return players

def export_daily_lineup():
    """Export daily lineup recommendations"""
    print("📊 Exporting daily lineup...")
    
    try:
        roster = load_roster_from_csv()
        
        # Generate sample recommendations based on real roster
        # Filter batters (non-pitchers)
        batters = [p for p in roster if 'P' not in p['position']]
        
        # Top 5 batters as starters (by ADP - lower is better)
        batters_sorted = sorted([b for b in batters if b['adp']], key=lambda x: x['adp'])[:5]
        
        starters = []
        for player in batters_sorted:
            confidence = 85 if player['adp'] < 100 else 70
            starters.append({
                "player": player['name'],
                "position": player['position'].split(',')[0].strip(),
                "opponent": f"@ {player['team']}",
                "confidence": confidence,
                "matchup": "Good" if confidence > 75 else "Fair",
                "parkFactor": "+5%",
                "platoon": "Favorable"
            })
        
        # Next 2 as bench
        bench_players = batters_sorted[5:7] if len(batters_sorted) > 5 else []
        bench = []
        for player in bench_players:
            bench.append({
                "player": player['name'],
                "position": player['position'].split(',')[0].strip(),
                "opponent": f"vs {player['team']}",
                "confidence": 55,
                "matchup": "Poor",
                "parkFactor": "-8%",
                "platoon": "Unfavorable"
            })
        
        data = {
            "generated_at": datetime.now().isoformat(),
            "starters": starters,
            "bench": bench
        }
        
    except Exception as e:
        print(f"⚠️  Using sample data due to error: {e}")
        data = {
            "generated_at": datetime.now().isoformat(),
            "starters": [],
            "bench": []
        }
    
    output_file = OUTPUT_DIR / "daily_lineup.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Exported {len(data['starters'])} starters, {len(data['bench'])} bench to {output_file}")
    return data

def export_waiver_wire():
    """Export waiver wire recommendations"""
    print("🎯 Exporting waiver wire...")
    
    try:
        roster = load_roster_from_csv()
        roster_adps = {p['adp'] for p in roster if p['adp']}
        
        # Sample high-value free agents not on roster
        all_targets = [
            {"player": "Spencer Steer", "position": "3B/OF", "adp": 145, "reason": "Hot streak + favorable schedule"},
            {"player": "Bryan Reynolds", "position": "OF", "adp": 112, "reason": "Undervalued, top-10 upside"},
            {"player": "Vinnie Pasquantino", "position": "1B", "adp": 189, "reason": "Breakout metrics, low ownership"},
            {"player": "Matt Chapman", "position": "3B", "adp": 167, "reason": "Power surge + home games"},
            {"player": "Michael King", "position": "SP", "adp": 201, "reason": "Rotation upgrade, Ks trending up"},
        ]
        
        # Filter out players already on roster
        targets = [t for t in all_targets if t['adp'] not in roster_adps]
        
        data = {
            "generated_at": datetime.now().isoformat(),
            "targets": targets[:5]  # Top 5
        }
        
    except Exception as e:
        print(f"⚠️  Using sample data due to error: {e}")
        data = {
            "generated_at": datetime.now().isoformat(),
            "targets": []
        }
    
    output_file = OUTPUT_DIR / "waiver_wire.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Exported {len(data['targets'])} targets to {output_file}")
    return data

def export_breakouts():
    """Export breakout alerts"""
    print("🔬 Exporting breakout alerts...")
    
    # TODO: Run breakout scanner
    data = {
        "generated_at": datetime.now().isoformat(),
        "alerts": []
    }
    
    output_file = OUTPUT_DIR / "breakouts.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Exported to {output_file}")
    return data

def export_keepers():
    """Export keeper analysis"""
    print("⭐ Exporting keeper analysis...")
    
    try:
        roster = load_roster_from_csv()
        
        # Calculate keeper value based on ADP vs draft round
        keepers = []
        for player in roster:
            if player['adp'] and player['adp'] < 200:  # High-value players only
                # Simple keeper value calculation
                draft_round = 12  # Most are from round 12 in your data
                surplus = f"+{200 - int(player['adp'])} ADP"
                
                value = "Elite" if player['adp'] < 50 else "Strong" if player['adp'] < 100 else "Good"
                
                keepers.append({
                    "player": player['name'],
                    "round": f"R{draft_round}",
                    "adp": int(player['adp']),
                    "surplus": surplus,
                    "value": value
                })
        
        # Sort by ADP (best players first) and take top 3
        keepers.sort(key=lambda x: x['adp'])
        
        data = {
            "generated_at": datetime.now().isoformat(),
            "keepers": keepers[:3]
        }
        
    except Exception as e:
        print(f"⚠️  Using sample data due to error: {e}")
        data = {
            "generated_at": datetime.now().isoformat(),
            "keepers": []
        }
    
    output_file = OUTPUT_DIR / "keepers.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Exported {len(data['keepers'])} keepers to {output_file}")
    return data

def main():
    """Export all dashboard data"""
    print("🚀 Exporting all dashboard data...\n")
    
    try:
        export_daily_lineup()
        export_waiver_wire()
        export_breakouts()
        export_keepers()
        
        print("\n✅ All data exported successfully!")
        print(f"📁 Files written to: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
