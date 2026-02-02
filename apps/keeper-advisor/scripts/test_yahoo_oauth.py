#!/usr/bin/env python3
"""
Test Yahoo OAuth 2.0 manual implementation
"""

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
import json


def main():
    print("🔐 Yahoo OAuth 2.0 Manual Test\n")
    
    # Load credentials
    config_file = app_root / "config" / "oauth2.json"
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Initialize OAuth
    oauth = YahooOAuth2(
        consumer_key=config['consumer_key'],
        consumer_secret=config['consumer_secret']
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
