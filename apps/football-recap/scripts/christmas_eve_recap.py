#!/usr/bin/env python3
"""
Generate a Christmas-week recap in the house voice.

Same Ghost as every other week. The calendar hook (if week 16/17 lands on
Christmas) is the only seasonal nod — not a Mall Santa costume.
"""

import os
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_APP_ROOT))
sys.path.insert(0, str(_APP_ROOT.parent.parent / "packages"))

from anthropic import Anthropic
from src.recap_generator import RecapGenerator
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ Please set ANTHROPIC_API_KEY in .env file")
    exit(1)

print("🏈 Christmas-week Fantasy Football Recap")
print("=" * 60)
print("Guest Author: The Commissioner's Ghost")
print("=" * 60)

client = Anthropic(api_key=api_key)
generator = RecapGenerator()

# Week 16 is typically Christmas week; calendar_hook may add a holiday note.
week = 16

print(f"\n📊 Generating recap for Week {week}...")
print("🤖 Using Claude Sonnet 4.5")
print("⏳ This may take 30-60 seconds...\n")

recap = generator.generate_recap_with_anthropic(week=week, client=client)

if recap:
    print("\n" + "=" * 60)
    print("✅ CHRISTMAS-WEEK RECAP GENERATED!")
    print("=" * 60)
    print(recap)
    print("\n" + "=" * 60)
    print(f"📁 Saved to: output/week-{week}-recap.md")
else:
    print("\n❌ Failed to generate recap.")
