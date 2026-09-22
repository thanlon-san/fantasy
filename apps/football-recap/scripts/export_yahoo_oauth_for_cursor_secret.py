#!/usr/bin/env python3
"""Write the working Yahoo OAuth blob for pasting into Cursor Secrets.

Use when YAHOO_OAUTH_JSON in the dashboard never matches oauth2.json on the
agent (team environment forward-fill / stale build). Does not print tokens.

Writes minified JSON to output/yahoo-oauth-secret-paste.json (gitignored via
output/) and prints the refresh_token fingerprint to verify after you paste.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import OUTPUT_DIR, YAHOO_OAUTH_OVERRIDE_ENV_VAR
from src.yahoo_nfl_client import _refresh_token_works, load_credentials


def main() -> int:
    try:
        creds = load_credentials()
    except Exception as exc:
        print(f"❌ No working credentials: {exc}")
        return 1

    mini = json.dumps(creds, separators=(",", ":"))
    rt = creds.get("refresh_token", "")
    fp = hashlib.sha256(rt.encode()).hexdigest()[:16]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "yahoo-oauth-secret-paste.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(mini)
        handle.write("\n")

    if not _refresh_token_works(creds):
        print("❌ Loaded credentials do not refresh (unexpected).")
        return 1

    print("✅ Working Yahoo OAuth blob exported (no secrets printed below).\n")
    print(f"Wrote: {out_path}")
    print(f"refresh_token fingerprint (verify after paste): sha256={fp}\n")
    print("Paste into Cursor (pick ONE path):\n")
    print(
        f"  A) Add a NEW Runtime secret named {YAHOO_OAUTH_OVERRIDE_ENV_VAR}\n"
        "     (recommended when YAHOO_OAUTH_JSON never updates). Paste the\n"
        f"     entire contents of {out_path} as the value.\n"
    )
    print(
        "  B) Team environment → Secrets → YAHOO_OAUTH_JSON\n"
        "     https://cursor.com/dashboard/cloud-agents/environments\n"
        "     Open the environment for github.com/thanlon-san/fantasy, edit\n"
        "     YAHOO_OAUTH_JSON, paste the file, save, then run **New setup run**\n"
        "     (not just a new agent on an old snapshot).\n"
    )
    print(
        "  C) Copy from the SAME machine where re-auth succeeded:\n"
        "     apps/baseball-engine/config/oauth2.json on this Cloud Agent VM,\n"
        "     not an older oauth2.json from your laptop.\n"
    )
    print(
        "\nAfter saving, run: python scripts/verify_yahoo_oauth.py\n"
        "You want env fingerprint sha256 to match the line above."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
