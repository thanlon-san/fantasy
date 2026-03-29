#!/usr/bin/env python3
"""
Automatically update roster CSV with latest ADP data from FantasyPros
"""

import sys
import csv
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / 'packages'))

from src.adp_fetcher import ADPFetcher


def main():
    print("📊 Automatically updating roster with latest ADP data...\n")
    
    csv_file = app_root / "data" / "my_roster_from_yahoo.csv"
    
    # Read current roster
    rows = []
    fieldnames = []
    with open(csv_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    print(f"📄 Loaded {len(rows)} players from CSV\n")
    
    # Fetch latest ADP data
    fetcher = ADPFetcher()
    updated_rows = fetcher.update_roster_with_adp(rows)
    
    # Write back to CSV
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    
    print(f"\n✅ Updated {csv_file}")
    print("\n💡 ADP data fetched from FantasyPros (consensus across Yahoo, CBS, NFBC, RTS, FT)")
    print("\n🔄 Run this script anytime to refresh ADP data before your draft!")


if __name__ == "__main__":
    main()
