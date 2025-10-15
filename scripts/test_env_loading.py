#!/usr/bin/env python3
"""
Test that .env file loading works correctly
"""

from dotenv import load_dotenv
import os

print("🔍 Testing .env file loading...\n")

# Load .env file
load_dotenv()

# Check if key is loaded
api_key = os.getenv("ANTHROPIC_API_KEY")

if api_key:
    # Mask the key for security
    masked = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
    print(f"✅ ANTHROPIC_API_KEY loaded: {masked}")
    print(f"   Length: {len(api_key)} characters")

    if api_key == "sk-ant-your-key-here":
        print("\n⚠️  WARNING: You're still using the example key!")
        print("   Edit .env and add your real API key from:")
        print("   https://console.anthropic.com/")
    else:
        print("\n✅ Custom API key detected (not the example)")
        print("   Ready to generate recaps!")
else:
    print("❌ ANTHROPIC_API_KEY not found")
    print("\nTroubleshooting:")
    print("1. Make sure .env file exists in current directory")
    print("2. Make sure it contains: ANTHROPIC_API_KEY=sk-ant-...")
    print("3. No quotes needed around the value")

print("\n" + "=" * 60)
print("Other environment variables:")
api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
print(f"API_BASE_URL: {api_url}")

openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    masked = (
        openai_key[:10] + "..." + openai_key[-4:] if len(openai_key) > 14 else "***"
    )
    print(f"OPENAI_API_KEY: {masked} (optional)")
else:
    print("OPENAI_API_KEY: Not set (optional)")
