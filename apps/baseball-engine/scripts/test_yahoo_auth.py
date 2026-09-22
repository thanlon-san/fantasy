#!/usr/bin/env python3
"""Non-interactive Yahoo OAuth + Fantasy API smoke test."""

import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from shared.yahoo import YahooFantasyClient, YahooOAuth2

FANTASY_GAMES_URL = (
    "https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games?format=json"
)


def print_leagues(leagues):
    for i, league in enumerate(leagues, 1):
        print(
            f"  {i}. {league.get('name')} "
            f"(key={league.get('league_key')}, season={league.get('season')})"
        )


def main() -> int:
    print("\n🔐 Yahoo Fantasy API smoke test (non-interactive)\n")

    oauth_file = app_root / "config" / "oauth2.json"
    if not oauth_file.exists():
        print(f"❌ Missing OAuth file: {oauth_file}")
        print("   Run: python scripts/setup_yahoo.py")
        return 1

    oauth = YahooOAuth2.load_from_file(str(oauth_file))
    if not oauth.refresh_access_token():
        print("❌ Token refresh failed.")
        print("   Re-authorize with: python scripts/test_yahoo_oauth.py")
        print("   Or: python scripts/setup_yahoo.py")
        return 1

    oauth.save_to_file(str(oauth_file))
    print(f"✅ Access token refreshed (saved to {oauth_file})")

    client = YahooFantasyClient(oauth)
    resp = client.session.get(FANTASY_GAMES_URL)
    if resp.status_code == 403:
        print("\n❌ Fantasy API returned 403 — application not authorized.")
        print(
            "   OAuth tokens are valid, but this Yahoo developer app cannot call "
            "Fantasy Sports endpoints."
        )
        print("   Fix at https://developer.yahoo.com/apps/ :")
        print("     • Enable API permission: Fantasy Sports (Read)")
        print("     • Redirect URI: https://localhost:8000")
        print("   Then re-run: python scripts/test_yahoo_oauth.py")
        try:
            detail = resp.json().get("error", {}).get("description")
            if detail:
                print(f"   Yahoo says: {detail}")
        except Exception:
            pass
        return 1

    if resp.status_code != 200:
        print(f"\n❌ Fantasy API error: HTTP {resp.status_code}")
        print(resp.text[:400])
        return 1

    print("✅ Fantasy API reachable (users/games)")

    print("\n🔍 Fetching Fantasy Baseball leagues...")
    for year in (2026, 2025):
        leagues = client.get_user_leagues(year=year, sport="mlb")
        if leagues:
            print(f"\n   Leagues for {year}:")
            print_leagues(leagues)
            return 0

    print("\n⚠️  No Fantasy Baseball leagues found for 2026 or 2025.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
