#!/usr/bin/env python3
"""
Test Yahoo OAuth 2.0 manual implementation.

Requires apps/baseball-engine/config/oauth2.json with at least consumer_key and
consumer_secret. If the file is missing but YAHOO_OAUTH_JSON is set in the
environment (Cursor cloud secret, or export locally), this script creates
oauth2.json from that blob automatically — then runs the browser re-auth flow.
"""

import json
import os
import sys
from pathlib import Path

import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_oauth_manual import YahooOAuth2


def _oauth_blob_from_env() -> dict:
    raw = os.environ.get("YAHOO_OAUTH_JSON", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"❌ YAHOO_OAUTH_JSON is not valid JSON: {exc}")
        sys.exit(1)
    if not isinstance(data, dict):
        print("❌ YAHOO_OAUTH_JSON must be a JSON object.")
        sys.exit(1)
    return data


def load_or_bootstrap_config(config_file: Path) -> dict:
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as handle:
            return json.load(handle)

    env_blob = _oauth_blob_from_env()
    if env_blob:
        missing = [
            key
            for key in ("consumer_key", "consumer_secret")
            if not env_blob.get(key)
        ]
        if missing:
            print(
                f"❌ YAHOO_OAUTH_JSON is missing: {', '.join(missing)}"
            )
            sys.exit(1)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as handle:
            json.dump(env_blob, handle, indent=2)
        print(
            f"✅ Created {config_file} from YAHOO_OAUTH_JSON.\n"
            "   (Stale tokens are OK — re-auth below will replace them.)\n"
        )
        return env_blob

    print(
        "❌ No OAuth config found.\n\n"
        f"   Expected file: {config_file}\n\n"
        "   Option A — Cursor / cloud (this VM):\n"
        "     Ensure YAHOO_OAUTH_JSON is set, then re-run this script.\n"
        "     It will bootstrap oauth2.json from that secret.\n\n"
        "   Option B — your laptop:\n"
        "     1. Cursor → Cloud Agents → Secrets → YAHOO_OAUTH_JSON\n"
        "     2. Copy consumer_key and consumer_secret into a new file:\n"
        f"        {config_file}\n"
        "        { \"consumer_key\": \"...\", \"consumer_secret\": \"...\" }\n"
        "     3. Re-run: python3 scripts/test_yahoo_oauth.py\n"
    )
    sys.exit(1)


def main():
    print("🔐 Yahoo OAuth 2.0 Manual Test\n")

    config_file = app_root / "config" / "oauth2.json"
    config = load_or_bootstrap_config(config_file)
    
    if not config.get("consumer_key") or not config.get("consumer_secret"):
        print(
            "❌ oauth2.json must include consumer_key and consumer_secret "
            "(from the Yahoo Developer app, or the YAHOO_OAUTH_JSON secret)."
        )
        return 1

    oauth = YahooOAuth2(
        consumer_key=config["consumer_key"],
        consumer_secret=config["consumer_secret"],
    )
    
    # Authorize
    print("Starting authorization flow...")
    if oauth.authorize():
        print("\n✅ Authorization successful!")
        
        # Save tokens
        oauth.save_to_file(str(config_file))
        
        # Test API call
        print("\n🔍 Testing API access...")
        session = oauth.get_session()
        
        # Try to fetch user's games
        response = session.get('https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games?format=json')
        
        if response.status_code == 200:
            print("✅ API call successful!")
            data = response.json()
            print(f"\nResponse data: {json.dumps(data, indent=2)[:500]}...")
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"Response: {response.text}")
    else:
        print("\n❌ Authorization failed")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
