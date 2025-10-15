#!/usr/bin/env python3
"""
Quick test to verify Claude Sonnet 4.5 model name and test it

Usage:
    # Create .env file with your key (recommended)
    cp env.example .env
    # Edit .env and add your ANTHROPIC_API_KEY
    python3 test_claude_model.py
"""

from anthropic import Anthropic
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

client = Anthropic(api_key=api_key)

# Test possible model names for Claude Sonnet 4.5
test_models = [
    "claude-sonnet-4-5-20250929",  # Known to work
    "claude-sonnet-4.5-20250101",
    "claude-4.5-sonnet-20250101",
    "claude-sonnet-4-5",
    "claude-4-5-sonnet",
    "claude-sonnet-4.5",
    "claude-4.5-sonnet",
]

print("🔍 Testing Claude Sonnet 4.5 model names...\n")

for model in test_models:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": "Write a one-sentence roast about benching your best player.",
                }
            ],
        )

        print(f"✅ FOUND: {model}")
        print(f"   Response: {response.content[0].text}")
        print(f"   This is the correct model name!\n")
        break

    except Exception as e:
        error_msg = str(e)
        if "model" in error_msg.lower() or "not found" in error_msg.lower():
            print(f"❌ {model} - Not found")
        else:
            print(f"⚠️  {model} - Error: {error_msg}")

print("\n💡 Once you find the correct name, update recap_generator.py with it!")
