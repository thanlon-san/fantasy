#!/usr/bin/env python3
"""
Generate Christmas Eve recap with Mall Santa After His Shift persona
"""

from anthropic import Anthropic
from src.recap_generator import RecapGenerator
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ Please set ANTHROPIC_API_KEY in .env file")
    exit(1)

# Initialize
print("🎅 Christmas Eve Fantasy Football Recap Generator")
print("=" * 60)
print("Guest Author: Mall Santa After His Shift")
print("=" * 60)

client = Anthropic(api_key=api_key)
generator = RecapGenerator()

# Week 16 (Christmas week)
week = 16

print(f"\n📊 Generating recap for Week {week}...")
print(f"🎄 Special Christmas Eve Edition")
print(f"🤖 Using Claude Sonnet 4.5")
print(f"⏳ This may take 30-60 seconds...\n")

# Set environment variable for explicit playoff context
os.environ["PLAYOFF_CONTEXT"] = """
PLAYOFF STRUCTURE REMINDER:
- Week 15 (Round 1): Tyler eliminated Joe Barry. Pete eliminated Greg Davis.
- Week 16 (Semifinals): 
  * CHAMPIONSHIP BRACKET: Kevin vs Pete, Marissa vs Tyler
  * CONSOLATION BRACKET: Joe Barry vs Greg Davis (playing for 5th place - both were eliminated in Week 15)
"""

# Generate with Mall Santa persona
recap = generator.generate_recap_with_anthropic(
    week=week, client=client, persona="Mall Santa After His Shift Ghost"
)

if recap:
    print("\n" + "=" * 60)
    print("✅ CHRISTMAS EVE RECAP GENERATED!")
    print("=" * 60)
    print(recap)
    print("\n" + "=" * 60)
    print(f"📁 Saved to: output/week-{week}-recap.md")
    print("\n🎅 Ho ho ho... and good luck in the playoffs!")
else:
    print("\n❌ Failed to generate recap. Even Santa can't fix this.")
