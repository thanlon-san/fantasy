#!/usr/bin/env python3
"""
Comprehensive Scanner
Run all intelligence tools and update dashboard
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

app_root = Path(__file__).parent.parent


def run_command(script, args=None):
    """Run a Python script and return success status"""
    cmd = [sys.executable, str(app_root / "scripts" / script)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {script}: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("🚀 COMPREHENSIVE INTELLIGENCE SCAN")
    print("="*70)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    success_count = 0
    total_count = 4
    
    # 1. Daily Lineup
    print("📊 [1/4] Running daily lineup optimizer...")
    print("-"*70)
    if run_command("daily_lineup.py"):
        success_count += 1
    print()
    
    # 2. Waiver Wire (with breakouts)
    print("🎯 [2/4] Scanning waiver wire (top 100 free agents)...")
    print("-"*70)
    if run_command("waiver_wire.py", ["--count", "100", "--export"]):
        success_count += 1
    print()
    
    # 3. Breakout Scanner
    print("🔬 [3/4] Running breakout detector...")
    print("-"*70)
    if run_command("scan_breakouts.py", ["--count", "100", "--export"]):
        success_count += 1
    print()
    
    # 4. Export Dashboard Data
    print("📤 [4/4] Exporting all data to dashboard...")
    print("-"*70)
    if run_command("export_dashboard_data.py"):
        success_count += 1
    print()
    
    # Summary
    print("="*70)
    print("✅ SCAN COMPLETE")
    print("="*70)
    print(f"Completed: {success_count}/{total_count} tasks")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success_count == total_count:
        print("\n🎉 All scans completed successfully!")
        print("\n📊 Next steps:")
        print("  1. Review the terminal output above")
        print("  2. View dashboard: cd ../baseball-dashboard && npm run dev")
        print("  3. Commit updated JSON files if using GitHub Pages")
    else:
        print(f"\n⚠️  Some scans failed. Check output above for details.")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
