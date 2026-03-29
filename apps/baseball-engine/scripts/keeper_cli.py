#!/usr/bin/env python3
"""
Keeper Advisor CLI
Interactive command-line interface for keeper analysis
"""

import sys
import os
import argparse
from pathlib import Path

# Add app and shared to Python path
app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.models import Roster
from src.analyzer import KeeperAnalyzer, print_analysis_report
from src.importers import CSVImporter, JSONImporter, create_sample_roster
from src.ai_advisor import AIKeeperAdvisor, format_ai_advice
from shared.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Baseball Keeper League Advisor - Make smarter keeper decisions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze sample roster
  python scripts/keeper_cli.py --sample
  
  # Analyze your roster from CSV
  python scripts/keeper_cli.py --csv data/my_roster.csv --team "My Team"
  
  # Get AI recommendations
  python scripts/keeper_cli.py --sample --ai
  
  # Export analysis to file
  python scripts/keeper_cli.py --sample --output report.txt
  
  # Create a template CSV to fill out
  python scripts/keeper_cli.py --create-template data/my_roster.csv
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--csv', type=str, help='Path to CSV file with roster data')
    input_group.add_argument('--json', type=str, help='Path to JSON file with roster data')
    input_group.add_argument('--sample', action='store_true', help='Use sample roster for testing')
    input_group.add_argument('--create-template', type=str, metavar='PATH', 
                           help='Create a template CSV file')
    
    # Team info
    parser.add_argument('--team', type=str, default='My Team', help='Your team name')
    parser.add_argument('--league', type=str, default='My League', help='League name')
    parser.add_argument('--year', type=int, default=2026, help='Current year')
    
    # Analysis options
    parser.add_argument('--max-keepers', type=int, default=3, 
                       help='Maximum number of keepers to recommend')
    parser.add_argument('--ai', action='store_true', 
                       help='Get AI-powered keeper recommendations')
    parser.add_argument('--use-gpt', action='store_true',
                       help='Use GPT-4o instead of Claude for AI recommendations')
    
    # Output options
    parser.add_argument('--output', type=str, help='Save report to file')
    parser.add_argument('--export-csv', type=str, help='Export roster to CSV')
    parser.add_argument('--export-json', type=str, help='Export roster to JSON')
    parser.add_argument('--scenarios', action='store_true', 
                       help='Show different keeper scenarios')
    
    args = parser.parse_args()
    
    # Handle template creation
    if args.create_template:
        print(f"📝 Creating template CSV: {args.create_template}")
        CSVImporter.create_template(args.create_template)
        print(f"✅ Template created! Edit the file and run:")
        print(f"   python scripts/keeper_cli.py --csv {args.create_template}")
        return 0
    
    # Load roster
    print("\n⚾ Baseball Keeper League Advisor")
    print("=" * 80)
    
    try:
        if args.sample:
            print("\n📦 Loading sample roster...")
            roster = create_sample_roster()
        elif args.csv:
            print(f"\n📄 Loading roster from CSV: {args.csv}")
            roster = CSVImporter.import_roster(
                args.csv,
                team_name=args.team,
                league_name=args.league,
                year=args.year
            )
        else:  # JSON
            print(f"\n📄 Loading roster from JSON: {args.json}")
            roster = JSONImporter.import_roster(args.json)
        
        print(f"✅ Loaded {len(roster.players)} players")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found - {e}")
        print("\n💡 Tip: Create a template with:")
        print(f"   python scripts/keeper_cli.py --create-template data/my_roster.csv")
        return 1
    except Exception as e:
        print(f"\n❌ Error loading roster: {e}")
        return 1
    
    # Analyze roster
    print(f"\n🔍 Analyzing keepers...")
    analyzer = KeeperAnalyzer(roster)
    analyses = analyzer.analyze_all_players()
    
    # Print report to terminal
    print_analysis_report(roster, analyses)
    
    # Show scenarios if requested
    if args.scenarios:
        print("\n" + "="*80)
        print("KEEPER SCENARIOS")
        print("="*80)
        
        scenarios = analyzer.generate_keeper_scenarios()
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{i}. {scenario.description}")
            if scenario.keepers:
                print(f"   Total Value: {scenario.total_value:.1f}")
                print(f"   Players:")
                for keeper in scenario.keepers:
                    # Find the analysis for this keeper
                    analysis = next((a for a in analyses if a.player == keeper), None)
                    if analysis:
                        print(f"     - {keeper.name} ({keeper.position}): Round {analysis.keeper_round}")
                print(f"   Draft Picks Available: {[r for r in range(1, 13) if r not in scenario.rounds_used]}")
            else:
                print(f"   Keep no players - all draft picks available")
    
    # Get AI recommendations if requested
    if args.ai:
        print("\n🤖 Generating AI recommendations...")
        scenarios = analyzer.generate_keeper_scenarios()
        advisor = AIKeeperAdvisor()
        
        advice = advisor.get_keeper_advice(
            roster,
            analyses,
            scenarios,
            use_anthropic=not args.use_gpt
        )
        
        if advice:
            print(format_ai_advice(advice))
        else:
            print("⚠️  AI recommendations unavailable (API key not configured)")
    
    # Save report to file if requested
    if args.output:
        print(f"\n💾 Saving report to: {args.output}")
        with open(args.output, 'w') as f:
            # Redirect stdout to file
            original_stdout = sys.stdout
            sys.stdout = f
            print_analysis_report(roster, analyses)
            if args.scenarios:
                scenarios = analyzer.generate_keeper_scenarios()
                print("\nKEEPER SCENARIOS")
                print("="*80)
                for i, scenario in enumerate(scenarios, 1):
                    print(f"\n{i}. {scenario}")
            sys.stdout = original_stdout
        print("✅ Report saved")
    
    # Export roster if requested
    if args.export_csv:
        print(f"\n💾 Exporting to CSV: {args.export_csv}")
        CSVImporter.export_roster(roster, args.export_csv)
        print("✅ CSV exported")
    
    if args.export_json:
        print(f"\n💾 Exporting to JSON: {args.export_json}")
        JSONImporter.export_roster(roster, args.export_json)
        print("✅ JSON exported")
    
    print("\n" + "="*80)
    print("✨ Analysis complete!")
    print("\n💡 Tips:")
    print("   - Add --ai flag for AI-powered recommendations")
    print("   - Add --scenarios to see different keeper combinations")
    print("   - Add --output report.txt to save full analysis")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
