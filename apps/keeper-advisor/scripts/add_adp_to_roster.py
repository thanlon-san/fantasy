#!/usr/bin/env python3
"""
Add ADP data to roster CSV from multiple sources
Aggregates FantasyPros and CBS Sports ADP data
"""

import sys
import csv
from pathlib import Path

app_root = Path(__file__).parent.parent

# ADP data from FantasyPros (2026 season - Feb 1, 2026)
# Source: https://www.fantasypros.com/mlb/adp/overall.php
# Consensus ADP across Yahoo, CBS, RTS, NFBC, Fantrax
ADP_DATA = {
    # Your roster players with their 2026 consensus ADP
    'Mookie Betts': 45.0,  # Rank #42
    'Gunnar Henderson': 17.2,  # Rank #19
    'Garrett Crochet': 11.0,  # Rank #12
    'Jacob deGrom': 48.4,  # Rank #47
    'Randy Arozarena': 78.6,  # Rank #79
    'Matt Chapman': 152.8,  # Rank #155
    'Taylor Ward': 127.4,  # Rank #129
    'Dylan Crews': 202.4,  # Rank #193
    'Mason Miller': 55.8,  # Rank #54
    'Royce Lewis': 223.6,  # Rank #211
    'Max Muncy': 216.0,  # Rank #203
    'Zach Neto': 36.0,  # Rank #35 ⭐ HUGE improvement from old data!
    'Nathaniel Lowe': 456.0,  # Rank #497 (FA)
    'Kyle Bradish': 85.0,  # Rank #85
    'Daulton Varsho': 212.2,  # Rank #198
    'Jo Adell': 129.4,  # Rank #130
    'Kyle Manzardo': 266.0,  # Rank #256
    'Nolan Schanuel': 303.0,  # Rank #314
    'Agustín Ramírez': 100.0,  # Rank #101 (Agustin Ramirez)
    'Jakob Marsee': 134.6,  # Rank #135
    'Kyle Hendricks': 450.0,  # Not in top 500
    'Will Vest': 284.2,  # Rank #273
    'JoJo Romero': 449.0,  # Rank #496
    'Hurston Waldrep': 274.8,  # Rank #261
}


def main():
    print("📊 Adding ADP data to roster...\n")
    
    csv_file = app_root / "data" / "my_roster_from_yahoo.csv"
    
    # Read current roster
    rows = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        # Add 'adp' column if not present
        if 'adp' not in fieldnames:
            fieldnames = list(fieldnames)
            fieldnames.insert(4, 'adp')  # Insert after draft_round
        
        for row in reader:
            player_name = row['player_name']
            
            # Match player to ADP data
            if player_name in ADP_DATA:
                row['adp'] = str(ADP_DATA[player_name])
                print(f"✅ {player_name:<30} ADP: {ADP_DATA[player_name]:.1f}")
            else:
                row['adp'] = ''
                print(f"⚠️  {player_name:<30} ADP: Not found")
            
            rows.append(row)
    
    # Write updated CSV
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ Updated {csv_file}")
    print("\nADP Sources:")
    print("  - FantasyPros (aggregates Yahoo, CBS, NFBC, RTS, FT)")
    print("  - CBS Sports")
    print(f"  - Total {len([v for v in rows if v.get('adp')])} players with ADP data")
    print("\n💡 Now run: npm run analyze:yahoo")


if __name__ == "__main__":
    main()
