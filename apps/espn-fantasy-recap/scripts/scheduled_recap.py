#!/usr/bin/env python3
"""
Scheduled Weekly Recap Generator and Slack Notifier

This script is designed to be run automatically (via cron or scheduler)
to generate and send weekly fantasy football recaps to Slack.

Usage:
    # Generate and send recap for current week
    python scripts/scheduled_recap.py

    # Generate and send recap for specific week
    python scripts/scheduled_recap.py --week 6

    # Dry run (generate but don't send to Slack)
    python scripts/scheduled_recap.py --dry-run

    # Send an existing recap without regenerating
    python scripts/scheduled_recap.py --week 6 --send-only

Cron Example (runs every Tuesday at 9 AM):
    0 9 * * 2 cd /path/to/fantasy && /usr/bin/python3 scripts/scheduled_recap.py >> logs/scheduler.log 2>&1
"""

import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic import Anthropic
from src.recap_generator import RecapGenerator
from shared.slack_notifier import SlackNotifier

# Load environment variables
load_dotenv()


def get_current_nfl_week() -> int:
    """
    Estimate current NFL week based on date
    NFL season typically starts first week of September
    This is a simple estimation - you may want to adjust based on your league
    """
    now = datetime.now()
    year = now.year

    # Assume NFL season starts September 5th (adjust as needed)
    season_start = datetime(year, 9, 5)

    # If we're before season start, check if we're at end of previous year
    if now < season_start:
        season_start = datetime(year - 1, 9, 5)

    # Calculate weeks since season start
    days_since_start = (now - season_start).days
    week = (days_since_start // 7) + 1

    # Cap at 18 weeks (NFL regular season + playoffs)
    return min(max(week, 1), 18)


def generate_and_send_recap(
    week: int, dry_run: bool = False, send_only: bool = False
) -> bool:
    """
    Generate a recap and send it to Slack

    Args:
        week: NFL week number
        dry_run: If True, generate recap but don't send to Slack
        send_only: If True, only send existing recap without regenerating

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 70)
    print("🏈 Fantasy Football Recap Automation")
    print(f"📅 {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
    print(f"📊 Week {week}")
    print("=" * 70)
    print()

    recap_file = f"output/week-{week}-recap.md"
    recap_content = None

    # Generate recap if needed
    if not send_only:
        print("🤖 Generating recap with Claude Sonnet 4.5...")

        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ ANTHROPIC_API_KEY not found in environment")
            print("   Please set it in your .env file")
            return False

        try:
            # Initialize generator and client
            client = Anthropic(api_key=api_key)
            generator = RecapGenerator()

            # Generate recap
            recap_content = generator.generate_recap_with_anthropic(
                week=week, client=client
            )

            if not recap_content:
                print("❌ Failed to generate recap")
                return False

            print(f"✅ Recap generated and saved to {recap_file}")

        except Exception as e:
            print(f"❌ Error generating recap: {e}")
            return False
    else:
        print(f"📄 Using existing recap from {recap_file}")

    # Read recap from file if we didn't just generate it
    if not recap_content:
        if not os.path.exists(recap_file):
            print(f"❌ Recap file not found: {recap_file}")
            print("   Generate it first by running without --send-only")
            return False

        with open(recap_file, "r") as f:
            recap_content = f.read()

    # Send to Slack (unless dry run)
    if dry_run:
        print("\n🏃 DRY RUN MODE - Skipping Slack notification")
        print(f"   Recap saved to: {recap_file}")
        print("\nTo send to Slack, run without --dry-run")
        return True

    print("\n📤 Sending to Slack...")

    try:
        # Initialize Slack notifier
        notifier = SlackNotifier()

        # Send recap
        success = notifier.send_recap(week, recap_content)

        if success:
            print("\n" + "=" * 70)
            print("✅ SUCCESS! Recap generated and sent to Slack")
            print("=" * 70)
            return True
        else:
            print("\n❌ Failed to send recap to Slack")
            return False

    except ValueError as e:
        print(f"\n❌ Slack configuration error: {e}")
        print("\nPlease configure Slack in your .env file:")
        print("  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        print("  OR")
        print("  SLACK_BOT_TOKEN=xoxb-your-bot-token")
        print("  SLACK_CHANNEL=#fantasy-football")
        return False
    except Exception as e:
        print(f"\n❌ Error sending to Slack: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate and send weekly fantasy football recaps to Slack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate and send recap for current week
  python scripts/scheduled_recap.py
  
  # Generate and send recap for specific week
  python scripts/scheduled_recap.py --week 6
  
  # Generate but don't send (dry run)
  python scripts/scheduled_recap.py --dry-run
  
  # Send existing recap without regenerating
  python scripts/scheduled_recap.py --week 6 --send-only

Cron Setup:
  # Edit crontab
  crontab -e
  
  # Add line to run every Tuesday at 9 AM
  0 9 * * 2 cd /path/to/fantasy && python3 scripts/scheduled_recap.py >> logs/scheduler.log 2>&1
        """,
    )

    parser.add_argument(
        "--week", type=int, help="NFL week number (auto-detects if not specified)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Generate recap but don't send to Slack"
    )
    parser.add_argument(
        "--send-only",
        action="store_true",
        help="Send existing recap without regenerating",
    )

    args = parser.parse_args()

    # Determine week
    if args.week:
        week = args.week
    else:
        week = get_current_nfl_week()
        print(f"ℹ️  Auto-detected week: {week}")
        print("   (Use --week to specify manually)")
        print()

    # Validate week
    if week < 1 or week > 18:
        print(f"❌ Invalid week: {week}")
        print("   Week must be between 1 and 18")
        sys.exit(1)

    # Generate and send
    success = generate_and_send_recap(week, args.dry_run, args.send_only)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
