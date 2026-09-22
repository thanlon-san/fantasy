#!/usr/bin/env python3
"""Check which Yahoo credential source works (env vs local oauth2.json).

Does not print tokens. Exit 0 when refresh succeeds, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import YAHOO_OAUTH_ENV_VAR, YAHOO_OAUTH_FILE_CANDIDATES


def _refresh_ok(creds: dict) -> tuple[bool, str]:
    try:
        response = requests.post(
            "https://api.login.yahoo.com/oauth2/get_token",
            data={
                "client_id": creds["consumer_key"],
                "client_secret": creds["consumer_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
                "redirect_uri": "oob",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        return False, str(exc)
    if response.status_code == 200:
        return True, "ok"
    try:
        body = response.json()
        return False, f"{body.get('error')}: {body.get('error_description', '')}"
    except json.JSONDecodeError:
        return False, response.text[:120]


def _load_env() -> dict | None:
    raw = os.environ.get(YAHOO_OAUTH_ENV_VAR, "").strip()
    if not raw:
        return None
    return json.loads(raw)


def _token_fingerprint(creds: dict) -> str:
    import hashlib

    token = creds.get("refresh_token") or ""
    return f"len={len(token)} sha256={hashlib.sha256(token.encode()).hexdigest()[:12]}"


def main() -> int:
    env_creds = None
    try:
        env_creds = _load_env()
    except json.JSONDecodeError:
        print(f"❌ {YAHOO_OAUTH_ENV_VAR} is not valid JSON")
        return 1

    file_creds = None
    file_path = None
    for path in YAHOO_OAUTH_FILE_CANDIDATES:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                file_creds = json.load(handle)
            file_path = path
            break

    if env_creds and file_creds:
        if env_creds.get("refresh_token") == file_creds.get("refresh_token"):
            print("refresh_token: env and file match")
        else:
            print(
                "refresh_token: env and file DIFFER — the cloud secret was not "
                "updated to match oauth2.json (consumer keys may still match).\n"
                f"  env:  {_token_fingerprint(env_creds)}\n"
                f"  file: {_token_fingerprint(file_creds)} ({file_path})"
            )

    if env_creds:
        ok, detail = _refresh_ok(env_creds)
        if ok:
            print(f"✅ {YAHOO_OAUTH_ENV_VAR} (cloud secret / env) — refresh OK")
            return 0
        print(f"❌ {YAHOO_OAUTH_ENV_VAR} — refresh failed: {detail}")

    for path in YAHOO_OAUTH_FILE_CANDIDATES:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            creds = json.load(handle)
        ok, detail = _refresh_ok(creds)
        if ok:
            print(f"✅ {path} — refresh OK")
            print(
                f"\n→ Cloud agents use {YAHOO_OAUTH_ENV_VAR}, not this file. "
                "Copy the entire file into Cursor → Cloud Agents → Secrets → "
                f"{YAHOO_OAUTH_ENV_VAR}, save, then start a new agent run."
            )
            return 0
        print(f"❌ {path} — refresh failed: {detail}")

    if not env_creds:
        print(f"No {YAHOO_OAUTH_ENV_VAR} and no oauth2.json found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
