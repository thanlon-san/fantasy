"""
Shared Yahoo Fantasy Sports API client.

Sport-generic OAuth2 flow and REST client for the Yahoo Fantasy API.
Used by both baseball-engine and football-recap.
"""

from .yahoo_oauth_manual import YahooOAuth2
from .yahoo_client import YahooFantasyClient

__all__ = ["YahooOAuth2", "YahooFantasyClient"]
