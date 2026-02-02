#!/usr/bin/env python3
"""
Daily Matchups Fetcher
Get today's games, starting pitchers, and matchup data
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Game:
    """A single MLB game"""
    game_id: str
    game_date: str
    game_time: str
    away_team: str
    home_team: str
    away_pitcher: Optional[str] = None
    home_pitcher: Optional[str] = None
    venue: Optional[str] = None
    weather: Optional[Dict] = None
    
    def __str__(self) -> str:
        return (
            f"{self.away_team} @ {self.home_team} - {self.game_time}\n"
            f"Pitchers: {self.away_pitcher or 'TBD'} vs {self.home_pitcher or 'TBD'}"
        )


@dataclass
class PlayerMatchup:
    """Matchup data for a specific player"""
    player_name: str
    player_team: str
    opponent: str
    opponent_pitcher: Optional[str] = None
    home_away: str = "away"  # "home" or "away"
    game_time: Optional[str] = None
    park_factor: float = 1.0  # > 1.0 = hitter friendly
    platoon_advantage: bool = False  # True if favorable L/R matchup
    
    # Historical vs pitcher
    career_avg: Optional[float] = None
    career_abs: int = 0
    
    # Recent form
    last_7_days_avg: Optional[float] = None
    last_7_days_ops: Optional[float] = None
    is_hot: bool = False  # 3+ game hitting streak
    
    def __str__(self) -> str:
        return f"{self.player_name} vs {self.opponent_pitcher or 'TBD'} @ {self.opponent}"


class MLBStatsAPI:
    """Client for MLB Stats API"""
    
    BASE_URL = "https://statsapi.mlb.com/api/v1"
    TIMEOUT = 30  # seconds
    
    def __init__(self):
        self.session = self._create_session_with_retries()
    
    def _create_session_with_retries(self) -> requests.Session:
        """Create session with automatic retries on failures"""
        session = requests.Session()
        
        # Retry strategy: 3 attempts with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_todays_games(self, date: Optional[str] = None) -> List[Game]:
        """
        Get today's MLB games
        
        Args:
            date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            List of Game objects
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            url = f"{self.BASE_URL}/schedule"
            params = {
                'sportId': 1,  # MLB
                'date': date,
                'hydrate': 'probablePitcher,venue,weather'
            }
            
            logger.info(f"Fetching games for {date}...")
            response = self.session.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            games = []
            
            for game_date in data.get('dates', []):
                for game_data in game_date.get('games', []):
                    # Extract game info
                    game_id = str(game_data.get('gamePk'))
                    game_datetime = game_data.get('gameDate', '')
                    
                    # Parse time
                    if game_datetime:
                        dt = datetime.fromisoformat(game_datetime.replace('Z', '+00:00'))
                        game_time = dt.strftime('%I:%M %p ET')
                    else:
                        game_time = 'TBD'
                    
                    # Teams
                    teams = game_data.get('teams', {})
                    away_team = teams.get('away', {}).get('team', {}).get('name', 'Unknown')
                    home_team = teams.get('home', {}).get('team', {}).get('name', 'Unknown')
                    
                    # Probable pitchers
                    away_pitcher = None
                    home_pitcher = None
                    
                    away_pitcher_data = teams.get('away', {}).get('probablePitcher')
                    if away_pitcher_data:
                        away_pitcher = away_pitcher_data.get('fullName')
                    
                    home_pitcher_data = teams.get('home', {}).get('probablePitcher')
                    if home_pitcher_data:
                        home_pitcher = home_pitcher_data.get('fullName')
                    
                    # Venue
                    venue_data = game_data.get('venue', {})
                    venue = venue_data.get('name')
                    
                    # Weather
                    weather = game_data.get('weather')
                    
                    game = Game(
                        game_id=game_id,
                        game_date=date,
                        game_time=game_time,
                        away_team=away_team,
                        home_team=home_team,
                        away_pitcher=away_pitcher,
                        home_pitcher=home_pitcher,
                        venue=venue,
                        weather=weather
                    )
                    
                    games.append(game)
            
            logger.info(f"Found {len(games)} games for {date}")
            return games
            
        except Exception as e:
            logger.error(f"Error fetching games: {e}")
            return []
    
    def get_player_recent_stats(
        self,
        player_id: int,
        days: int = 7
    ) -> Optional[Dict]:
        """
        Get player's recent stats (last N days)
        
        Args:
            player_id: MLB player ID
            days: Number of days to look back
            
        Returns:
            Dictionary with recent stats
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            url = f"{self.BASE_URL}/people/{player_id}/stats"
            params = {
                'stats': 'gameLog',
                'season': datetime.now().year,
                'startDate': start_date,
                'endDate': end_date
            }
            
            response = self.session.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            stats = data.get('stats', [])
            
            if not stats:
                return None
            
            # Aggregate game logs
            game_logs = stats[0].get('splits', [])
            
            if not game_logs:
                return None
            
            # Calculate rolling stats
            total_abs = 0
            total_hits = 0
            total_hrs = 0
            total_walks = 0
            total_ks = 0
            
            for game in game_logs:
                stat = game.get('stat', {})
                total_abs += stat.get('atBats', 0)
                total_hits += stat.get('hits', 0)
                total_hrs += stat.get('homeRuns', 0)
                total_walks += stat.get('baseOnBalls', 0)
                total_ks += stat.get('strikeOuts', 0)
            
            if total_abs == 0:
                return None
            
            avg = total_hits / total_abs
            obp = (total_hits + total_walks) / (total_abs + total_walks) if (total_abs + total_walks) > 0 else 0
            
            # Simple OPS estimate (no slugging available from game log easily)
            slg = avg + (total_hrs * 0.15)  # Rough estimate
            ops = obp + slg
            
            return {
                'avg': avg,
                'abs': total_abs,
                'hits': total_hits,
                'hrs': total_hrs,
                'walks': total_walks,
                'strikeouts': total_ks,
                'ops': ops,
                'games': len(game_logs)
            }
            
        except Exception as e:
            logger.error(f"Error fetching recent stats for player {player_id}: {e}")
            return None


# Park factors (hardcoded for now, based on multi-year data)
PARK_FACTORS = {
    # > 1.0 = hitter friendly, < 1.0 = pitcher friendly
    'Coors Field': 1.25,  # Denver - highest elevation
    'Great American Ball Park': 1.15,  # Cincinnati
    'Fenway Park': 1.10,  # Boston - Green Monster
    'Yankee Stadium': 1.08,  # Short right porch
    'Citizens Bank Park': 1.06,  # Philadelphia
    'Globe Life Field': 1.05,  # Texas - retractable roof
    'Target Field': 1.02,  # Minnesota
    'Wrigley Field': 1.02,  # Chicago Cubs - wind dependent
    'American Family Field': 1.00,  # Milwaukee - neutral
    'Guaranteed Rate Field': 1.00,  # Chicago White Sox
    'Busch Stadium': 0.98,  # St. Louis
    'Dodger Stadium': 0.96,  # LA - pitcher friendly
    'Petco Park': 0.94,  # San Diego - marine layer
    'Oracle Park': 0.92,  # San Francisco - cold, marine layer
    'T-Mobile Park': 0.93,  # Seattle
    'Kauffman Stadium': 0.95,  # Kansas City
    'Truist Park': 1.01,  # Atlanta
    'Minute Maid Park': 1.03,  # Houston
    'Tropicana Field': 0.97,  # Tampa Bay - dome
    'Rogers Centre': 1.04,  # Toronto
    'Oriole Park at Camden Yards': 1.07,  # Baltimore
    'Nationals Park': 0.99,  # Washington
    'Comerica Park': 0.94,  # Detroit - pitcher friendly
    'Progressive Field': 0.98,  # Cleveland
    'Citi Field': 0.96,  # NY Mets
    'Oakland Coliseum': 0.93,  # Oakland - huge foul territory
    'Angel Stadium': 0.97,  # Anaheim
    'Chase Field': 1.06,  # Arizona
    'Marlins Park': 0.95,  # Miami
    'PNC Park': 0.96,  # Pittsburgh
}


def get_park_factor(venue_name: str) -> float:
    """Get park factor for a venue"""
    return PARK_FACTORS.get(venue_name, 1.0)


if __name__ == "__main__":
    # Test the API
    logging.basicConfig(level=logging.INFO)
    
    api = MLBStatsAPI()
    
    print("\n⚾ MLB DAILY MATCHUPS")
    print("="*70)
    
    games = api.get_todays_games()
    
    if games:
        print(f"\n📅 {len(games)} games scheduled today:\n")
        for i, game in enumerate(games, 1):
            print(f"{i}. {game}")
            if game.venue:
                pf = get_park_factor(game.venue)
                park_type = "⬆️ Hitter friendly" if pf > 1.05 else "⬇️ Pitcher friendly" if pf < 0.95 else "➡️ Neutral"
                print(f"   Park: {game.venue} ({pf:.2f}) {park_type}")
            print()
    else:
        print("\n❌ No games scheduled (likely off-season)")
        print("ℹ️  Try during MLB season (April-October)")
