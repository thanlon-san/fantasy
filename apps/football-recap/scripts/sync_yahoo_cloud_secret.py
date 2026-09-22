#!/usr/bin/env python3
"""
Validate local Yahoo oauth2.json, smoke-test token refresh, and compare to
YAHOO_OAUTH_JSON (Cursor Cloud Agents secret). Does not call Cursor APIs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OAUTH_PATH = WORKSPACE_ROOT / "apps" / "baseball-engine" / "config" / "oauth2.json"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
FANTASY_GAMES_URL = (
    "https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games?format=json"
)
CLOUD_DASHBOARD = "https://cursor.com/dashboard?tab=cloud-agents"
REQUIRED_KEYS = ("consumer_key", "consumer_secret", "access_token", "refresh_token")


def _bootstrap_paths() -> None:
    sys.path.insert(0, str(WORKSPACE_ROOT / "packages"))
    sys.path.insert(0, str(APP_ROOT))


def load_oauth_json(path: Path) -> dict:
    if not path.exists():
        print(f"❌ OAuth file not found: {path}")
        print("   Run: python apps/baseball-engine/scripts/setup_yahoo.py")
        sys.exit(1)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"❌ Invalid JSON in {path}: {exc}")
        sys.exit(1)
    if not isinstance(data, dict):
        print(f"❌ Expected JSON object in {path}")
        sys.exit(1)
    missing = [k for k in REQUIRED_KEYS if not data.get(k)]
    if missing:
        print(f"❌ Missing or empty keys in {path}: {', '.join(missing)}")
        sys.exit(1)
    return data


def canonical_oauth_blob(data: dict) -> str:
    subset = {k: data[k] for k in REQUIRED_KEYS if k in data}
    if data.get("token_type"):
        subset["token_type"] = data["token_type"]
    return json.dumps(subset, sort_keys=True, separators=(",", ":"))


def fingerprint(data: dict, path: Path) -> str:
    rt = str(data.get("refresh_token", ""))
    tail = rt[-4:] if len(rt) >= 4 else "????"
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    return f"refresh_token …{tail}, file mtime {mtime}"


def refresh_tokens(data: dict) -> tuple[bool, dict, str | None]:
    """Refresh access token; return (ok, updated_data, error_code)."""
    payload = {
        "client_id": data["consumer_key"],
        "client_secret": data["consumer_secret"],
        "refresh_token": data["refresh_token"],
        "grant_type": "refresh_token",
    }
    try:
        response = requests.post(TOKEN_URL, data=payload, timeout=30)
    except requests.RequestException as exc:
        print(f"❌ Token refresh request failed: {exc}")
        return False, data, "network_error"

    if response.status_code == 200:
        token_data = response.json()
        updated = dict(data)
        updated["access_token"] = token_data.get("access_token", updated["access_token"])
        if token_data.get("refresh_token"):
            updated["refresh_token"] = token_data["refresh_token"]
        if token_data.get("token_type"):
            updated["token_type"] = token_data["token_type"]
        return True, updated, None

    error_code = None
    try:
        body = response.json()
        error_code = body.get("error")
    except Exception:
        body = response.text[:200]

    print(f"❌ Token refresh failed: HTTP {response.status_code}")
    if error_code:
        print(f"   Yahoo error: {error_code}")
    elif body:
        print(f"   Response: {body}")

    return False, data, error_code


def fantasy_smoke_test(access_token: str) -> bool:
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    )
    resp = session.get(FANTASY_GAMES_URL, timeout=30)
    if resp.status_code == 200:
        print("✅ Fantasy API smoke test OK (users/games)")
        return True
    if resp.status_code == 403:
        print("⚠️  OAuth refresh succeeded but Fantasy API returned 403.")
        print("   Enable Fantasy Sports (Read) on your Yahoo developer app.")
        return False
    print(f"⚠️  Fantasy API returned HTTP {resp.status_code}")
    return False


def compare_env_var(file_data: dict, path: Path) -> None:
    env_blob = os.environ.get("YAHOO_OAUTH_JSON")
    if not env_blob:
        print("\nℹ️  YAHOO_OAUTH_JSON not set in this shell — skipping env compare.")
        print(f"   File fingerprint: {fingerprint(file_data, path)}")
        return

    try:
        env_data = json.loads(env_blob)
    except json.JSONDecodeError as exc:
        print(f"\n❌ YAHOO_OAUTH_JSON is not valid JSON: {exc}")
        sys.exit(1)

    file_canon = canonical_oauth_blob(file_data)
    env_canon = canonical_oauth_blob(env_data)
    fp = fingerprint(file_data, path)
    if file_canon == env_canon:
        print(f"\n✅ YAHOO_OAUTH_JSON MATCH (file: {fp})")
    else:
        print(f"\n⚠️  YAHOO_OAUTH_JSON MISMATCH (file: {fp})")
        print("   Update the cloud secret after saving a fresh oauth2.json locally.")


def print_cloud_instructions() -> None:
    print("\n--- Cursor Cloud Agents ---")
    print(f"Dashboard: {CLOUD_DASHBOARD}")
    print("Set secret YAHOO_OAUTH_JSON to the full minified JSON body")
    print("(consumer_key, consumer_secret, access_token, refresh_token).")
    print("Re-run this script after re-auth to refresh tokens and compare.")


def copy_to_clipboard(text: str) -> None:
    if sys.platform != "darwin":
        print("⚠️  --copy is only supported on macOS (pbcopy).")
        return
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    print("✅ Minified JSON copied to clipboard (paste into YAHOO_OAUTH_JSON).")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate oauth2.json, refresh tokens, compare YAHOO_OAUTH_JSON."
    )
    parser.add_argument(
        "--oauth-file",
        type=Path,
        default=DEFAULT_OAUTH_PATH,
        help=f"Path to oauth2.json (default: {DEFAULT_OAUTH_PATH})",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy minified JSON to clipboard (macOS pbcopy)",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print full JSON to stdout (sensitive — for piping)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write refreshed tokens back to the oauth file",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip Fantasy API GET after refresh",
    )
    args = parser.parse_args()

    _bootstrap_paths()
    oauth_path = args.oauth_file.expanduser().resolve()
    data = load_oauth_json(oauth_path)
    print(f"✅ OAuth file valid: {oauth_path}")
    print(f"   {fingerprint(data, oauth_path)}")

    ok, updated, error_code = refresh_tokens(data)
    if not ok:
        if error_code == "invalid_grant":
            print("\n❌ Refresh token expired or revoked (invalid_grant).")
            print("   Re-authorize: python apps/baseball-engine/scripts/test_yahoo_oauth.py")
            print("   Then re-run this script and update YAHOO_OAUTH_JSON in cloud.")
            return 1
        print("\n   Try: python apps/baseball-engine/scripts/test_yahoo_oauth.py")
        return 1

    print("✅ Access token refreshed")
    if not args.no_save:
        oauth_path.parent.mkdir(parents=True, exist_ok=True)
        with open(oauth_path, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2)
            f.write("\n")
        print(f"   Saved to {oauth_path}")

    if not args.skip_smoke:
        fantasy_smoke_test(updated["access_token"])

    compare_env_var(updated, oauth_path)
    print_cloud_instructions()

    minified = canonical_oauth_blob(updated)
    if args.copy:
        copy_to_clipboard(minified)
    if args.print_json:
        print("\n--- oauth JSON (sensitive) ---")
        print(minified)

    return 0


if __name__ == "__main__":
    sys.exit(main())
