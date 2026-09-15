"""Maps Yahoo teams to real Slack user IDs for @mentions.

Without this, every "@Owner" the pipeline writes is plain text that looks like
a mention but pings nobody -- someone has to retag every name by hand. This
module is the single place that resolves a Yahoo team to a Slack user ID,
falling back to plain text only when a team truly has no mapping (e.g. a
mid-season roster change nobody has recorded yet, or -- deliberately -- any
non-production/synthetic team_key such as a test fixture's).

Keyed by the *full* ``team_key`` (e.g. "470.l.1324751.t.1"), not the bare
team_id: team_id alone is just a small integer (1..14 for this league) that
would collide with any other 14-team league or synthetic test fixture using
the same numbering. The full key ties a mapping to this exact league+season.

Two output formats, because Slack uses different syntax in messages vs.
Canvases:
    message_mention()  -> "<@U0123>"     (Slack message markdown)
    canvas_mention()    -> "![](@U0123)"  (Canvas-flavored markdown)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

CONFIG_FILE = "config/slack_owners.json"

_cache: Optional[Dict[str, Any]] = None


def load_owner_map(config_path: str = CONFIG_FILE) -> Dict[str, Any]:
    """Load and cache the team_key -> {owner, slack_user_id} mapping."""
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.exists(config_path):
        _cache = {}
        return _cache
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        _cache = data.get("teams", {}) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        _cache = {}
    return _cache


def reset_cache() -> None:
    """Test hook / call after editing the config file mid-process."""
    global _cache
    _cache = None


def _lookup_slack_id(team_key: Optional[str], config_path: str = CONFIG_FILE) -> Optional[str]:
    if not team_key:
        return None
    owners = load_owner_map(config_path)
    entry = owners.get(team_key)
    return entry.get("slack_user_id") if entry else None


def message_mention(owner: str, team_key: Optional[str] = None, config_path: str = CONFIG_FILE) -> str:
    """Return a Slack message mention, or '@Owner' text if unmapped."""
    slack_id = _lookup_slack_id(team_key, config_path)
    return f"<@{slack_id}>" if slack_id else f"@{owner}"


def canvas_mention(owner: str, team_key: Optional[str] = None, config_path: str = CONFIG_FILE) -> str:
    """Return a Canvas-flavored mention, or the plain owner name if unmapped."""
    slack_id = _lookup_slack_id(team_key, config_path)
    return f"![](@{slack_id})" if slack_id else owner


def has_mapping(team_key: Optional[str], config_path: str = CONFIG_FILE) -> bool:
    return _lookup_slack_id(team_key, config_path) is not None
