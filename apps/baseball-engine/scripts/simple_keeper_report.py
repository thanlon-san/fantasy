#!/usr/bin/env python3
"""Simple keeper report showing all eligible players without ADP"""

import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.importers import CSVImporter
from src.keeper_rules import KeeperRules

# Load roster
csv_file = app_root / "data" / "my_roster_from_yahoo.csv"
roster = CSVImporter.import_roster(str(csv_file), team_name="2balls")

print("\n⚾ KEEPER ELIGIBILITY REPORT")
print("="*100)
print(f"\nRoster: {roster.team_name}")
print(f"Total Players: {len(roster.players)}\n")

# Group players by keeper cost
by_cost = {}
ineligible = []

for player in roster.players:
    eligibility = KeeperRules.check_eligibility(
        draft_round=player.draft_round,
        years_kept=player.years_kept,
        is_undrafted_fa=player.is_undrafted_fa
    )
    
    if eligibility.is_eligible:
        cost = eligibility.keeper_round
        if cost not in by_cost:
            by_cost[cost] = []
        by_cost[cost].append((player, eligibility))
    else:
        ineligible.append((player, eligibility))

# Display by keeper cost
print("KEEPER-ELIGIBLE PLAYERS (by cost)")
print("-"*100)

for cost in sorted(by_cost.keys()):
    players = by_cost[cost]
    print(f"\n📍 ROUND {cost} KEEPERS ({len(players)} players):")
    print(f"   {'Player':<30} {'Pos':<20} {'Team':<6} {'Years Left'}")
    print(f"   {'-'*80}")
    
    for player, elig in sorted(players, key=lambda x: x[0].name):
        print(f"   {player.name:<30} {player.position:<20} {player.team:<6} {elig.years_remaining}")

# Ineligible players
if ineligible:
    print(f"\n\n❌ INELIGIBLE PLAYERS ({len(ineligible)}):")
    print("-"*100)
    for player, elig in ineligible:
        print(f"   {player.name:<30} {elig.reason}")

# Multiple round-12 keeper note
if 12 in by_cost and len(by_cost[12]) >= 2:
    print(f"\n\n⚠️  IMPORTANT: Multiple Round-12 Keepers Detected!")
    print("="*100)
    print(f"\nYou have {len(by_cost[12])} players eligible for round 12.")
    print("\n📋 LEAGUE RULE: If keeping 3 round-12 players:")
    print("   - Best player (by ADP) → Round 10")
    print("   - 2nd best player → Round 11")
    print("   - 3rd best player → Round 12")
    print("\n💡 To get personalized recommendations with this rule applied:")
    print("   1. Add ADP data to the CSV (column 'adp')")
    print("   2. Run: npm run analyze:yahoo")

print("\n" + "="*100)
print("\n💡 NEXT STEPS:")
print("   1. Review your keeper-eligible players above")
print("   2. Consider late-round picks (rounds 10-12) for best value")
print("   3. Add ADP data for detailed value analysis")
print("   4. Run 'npm run analyze:yahoo' for full recommendations\n")
