#!/usr/bin/env python3
"""
One-shot Yahoo OAuth refresh helper for the fantasy-football recap pipeline.

RUN THIS ON YOUR OWN LAPTOP, NOT ON A CLOUD AGENT VM. It needs a web
browser and your personal Yahoo login (the account that can see league
1324751), neither of which a cloud agent has access to.

It uses Yahoo's "out-of-band" (oob) OAuth flow, so there's no localhost
callback server to run -- Yahoo just shows you a code on the page after
you approve the app, you paste it here, and this script exchanges it for
real tokens and prints the complete JSON blob ready to paste into the
YAHOO_OAUTH_JSON secret (Cursor Dashboard -> Cloud Agents -> Secrets).

Usage:
    pip install requests   # if you don't already have it
    python3 yahoo_oauth_refresh.py

You'll be prompted for your app's consumer_key / consumer_secret (find
these at https://developer.yahoo.com/apps/ under your app's "Keys" tab,
or reuse whatever is already in your current YAHOO_OAUTH_JSON secret --
those two fields have been stable all season; only the tokens kept
breaking). You can also set them as env vars first to skip the prompts:

    export YAHOO_CONSUMER_KEY="..."
    export YAHOO_CONSUMER_SECRET="..."
    python3 yahoo_oauth_refresh.py
"""
import json
import os
import sys
import webbrowser

try:
    import requests
except ImportError:
    print("This script needs the 'requests' package: pip install requests")
    sys.exit(1)

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
REDIRECT_URI = "oob"  # out-of-band: Yahoo shows the code on-page, no server needed


def main():
    consumer_key = os.environ.get("YAHOO_CONSUMER_KEY") or input("Consumer key: ").strip()
    consumer_secret = os.environ.get("YAHOO_CONSUMER_SECRET") or input("Consumer secret: ").strip()

    if not consumer_key or not consumer_secret:
        print("Both consumer_key and consumer_secret are required.")
        sys.exit(1)

    auth_url = (
        f"{AUTH_URL}?client_id={consumer_key}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&language=en-us"
    )

    print("\nOpening your browser to authorize with Yahoo...")
    print("If it doesn't open automatically, copy/paste this URL into your browser:\n")
    print(auth_url)
    print()
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print("Log in with the Yahoo account that can see league 1324751 and click Agree.")
    print("Yahoo will then show a code directly on the page (NOT a redirect --")
    print("just a string of characters to copy). Paste exactly that below.\n")

    code = input("Authorization code from Yahoo: ").strip()
    if not code:
        print("No code entered, aborting.")
        sys.exit(1)

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": consumer_key,
            "client_secret": consumer_secret,
            "redirect_uri": REDIRECT_URI,
            "code": code,
            "grant_type": "authorization_code",
        },
    )

    if resp.status_code != 200:
        print(f"\nToken exchange failed: {resp.status_code}")
        print(resp.text)
        print("\nCommon causes: the code was already used (they're single-use and")
        print("expire in minutes), or it was copied with extra whitespace/newlines.")
        print("Re-run this script to get a fresh code and try again.")
        sys.exit(1)

    token_data = resp.json()
    refresh_token = token_data.get("refresh_token")
    access_token = token_data.get("access_token")

    if not refresh_token or not access_token:
        print("\nYahoo's response didn't include both tokens -- unexpected shape:")
        print(json.dumps(token_data, indent=2))
        sys.exit(1)

    secret_blob = {
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_data.get("token_type", "bearer"),
    }

    print("\n" + "=" * 70)
    print("SUCCESS. Paste this EXACT line into the YAHOO_OAUTH_JSON secret")
    print("(Cursor Dashboard -> Cloud Agents -> Secrets -- check whether this")
    print("repo uses your personal secret or the team one, and update that one):")
    print("=" * 70 + "\n")
    print(json.dumps(secret_blob))
    print(
        f"\n(sanity check: refresh_token is {len(refresh_token)} chars -- "
        "real Yahoo refresh tokens run 40-60+ chars. If this prints a short "
        "or obviously truncated value, something went wrong in the exchange "
        "above, not in what you pasted -- re-run the script.)"
    )


if __name__ == "__main__":
    main()
