#!/usr/bin/env python3
"""
Example: Generate a weekly recap using Claude Sonnet 4.5

Usage:
    # Option 1: Using .env file (recommended)
    cp env.example .env
    # Edit .env and add your ANTHROPIC_API_KEY
    python3 example_generate_recap.py

    # Option 2: Using environment variable
    export ANTHROPIC_API_KEY='your-key-here'
    python3 example_generate_recap.py
"""

from anthropic import Anthropic
from src.recap_generator import RecapGenerator
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ Please set ANTHROPIC_API_KEY")
    print("\nOption 1: Create a .env file (recommended)")
    print("   cp env.example .env")
    print("   # Edit .env and add your API key")
    print("\nOption 2: Export environment variable")
    print("   export ANTHROPIC_API_KEY='sk-ant-your-key-here'")
    exit(1)

# Initialize
print("🏈 Fantasy Football Recap Generator")
print("=" * 60)

client = Anthropic(api_key=api_key)
generator = RecapGenerator()

# Choose week (or make it a command line argument)
week = 6  # Change this to the week you want

print(f"\n📊 Generating recap for Week {week}...")
print(f"🤖 Using Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)")
print(f"⏳ This may take 30-60 seconds...\n")

# Generate the recap
recap = generator.generate_recap_with_anthropic(
    week=week,
    client=client
    # No need to specify model - claude-sonnet-4-5-20250929 is the default!
)

if recap:
    print("\n" + "=" * 60)
    print("✅ RECAP GENERATED!")
    print("=" * 60)
    print(recap)
    print("\n" + "=" * 60)
    print(f"📁 Saved to: output/week-{week}-recap.md")
else:
    print("\n❌ Failed to generate recap. Check the errors above.")

