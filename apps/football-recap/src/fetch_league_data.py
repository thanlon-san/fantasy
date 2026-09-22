#!/usr/bin/env python3
"""
Football league data facade.

This module used to wrap ``espn_api``; the app is now Yahoo-backed. Keep this
file as the single import point for callers that just want a ready-to-use
fetcher, without them caring about OAuth loading or league-key resolution.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.yahoo_fetcher import YahooLeagueFetcher

DEFAULT_CONFIG_PATHS = (
    Path("config.json"),  # legacy: some scripts run from the app dir
    Path(__file__).resolve().parent.parent / "config" / "config.json",
    Path(__file__).resolve().parent.parent / "config" / "config.example.json",
)


def load_config(explicit_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the football-recap config JSON, preferring the app-level path."""
    candidates = [explicit_path] if explicit_path else list(DEFAULT_CONFIG_PATHS)
    for p in candidates:
        if p and Path(p).exists():
            with open(p, "r") as f:
                return json.load(f)
    raise FileNotFoundError(
        "No config.json found. Copy config/config.example.json to "
        "config/config.json and set league_id/year."
    )


def get_fetcher(
    config: Optional[Dict[str, Any]] = None,
    oauth_path: Optional[Path] = None,
) -> YahooLeagueFetcher:
    """Return a ready-to-use ``YahooLeagueFetcher`` for the current league."""
    cfg = config if config is not None else load_config()
    # Allow env-var overrides for CI/automation contexts.
    if os.environ.get("YAHOO_LEAGUE_ID"):
        cfg["league_id"] = int(os.environ["YAHOO_LEAGUE_ID"])
    if os.environ.get("YAHOO_SEASON_YEAR"):
        cfg["year"] = int(os.environ["YAHOO_SEASON_YEAR"])
    return YahooLeagueFetcher.from_config(cfg, oauth_path=oauth_path)
