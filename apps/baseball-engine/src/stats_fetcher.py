#!/usr/bin/env python3
"""
Stats Fetcher
Fetches recent performance stats from MLB Stats API with caching
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RecentStats:
    """Recent performance statistics for a player"""
    
    # Hitting stats
    avg: Optional[float] = None
    hr: Optional[int] = None
    rbi: Optional[int] = None
    sb: Optional[int] = None
    
    # Pitching stats
    era: Optional[float] = None
    whip: Optional[float] = None
    k: Optional[int] = None
    w: Optional[int] = None
    
    # Meta
    games: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'avg': self.avg,
            'hr': self.hr,
            'rbi': self.rbi,
            'sb': self.sb,
            'era': self.era,
            'whip': self.whip,
            'k': self.k,
            'w': self.w,
            'games': self.games
        }


class StatsFetcher:
    """Fetches recent player statistics from MLB Stats API"""
    
    MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
    CACHE_DIR = Path(__file__).parent.parent / "cache" / "stats"
    CACHE_DURATION = timedelta(hours=6)  # Cache for 6 hours
    
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        if use_cache:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._player_id_cache = {}
    
    def get_recent_stats(
        self, 
        player_name: str, 
        is_pitcher: bool,
        days: int = 30
    ) -> Optional[RecentStats]:
        """
        Get recent statistics for a player
        
        Args:
            player_name: Full player name (e.g., "Aaron Judge")
            is_pitcher: True if player is a pitcher
            days: Number of days to look back
            
        Returns:
            RecentStats object or None if not found
        """
        # Check cache first
        if self.use_cache:
            cached = self._load_from_cache(player_name, days)
            if cached:
                logger.debug(f"Using cached stats for {player_name}")
                return cached
        
        try:
            # Find player ID
            player_id = self._find_player_id(player_name)
            if not player_id:
                logger.warning(f"Could not find MLB player ID for {player_name}")
                return None
            
            # Get game logs
            stats = self._fetch_game_logs(player_id, is_pitcher, days)
            
            # Cache the result
            if self.use_cache and stats:
                self._save_to_cache(player_name, days, stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching stats for {player_name}: {e}")
            return None
    
    def get_multi_window_stats(
        self,
        player_name: str,
        is_pitcher: bool
    ) -> Dict[str, RecentStats]:
        """
        Get stats for multiple time windows (7, 14, 30 days)
        
        Returns:
            Dict with keys 'last_7_days', 'last_14_days', 'last_30_days'
        """
        windows = {
            'last_7_days': 7,
            'last_14_days': 14,
            'last_30_days': 30
        }
        
        results = {}
        for window_name, days in windows.items():
            stats = self.get_recent_stats(player_name, is_pitcher, days)
            if stats:
                results[window_name] = stats
        
        return results
    
    def get_trending_status(
        self,
        player_name: str,
        is_pitcher: bool
    ) -> str:
        """
        Determine if player is trending HOT, COLD, or STABLE
        
        Returns:
            "HOT", "COLD", or "STABLE"
        """
        stats = self.get_multi_window_stats(player_name, is_pitcher)
        
        if not stats.get('last_7_days') or not stats.get('last_30_days'):
            return "STABLE"
        
        recent = stats['last_7_days']
        baseline = stats['last_30_days']
        
        # Compare performance
        if is_pitcher:
            # For pitchers: lower ERA is better
            if recent.era and baseline.era:
                if recent.era < baseline.era * 0.75:  # 25% improvement
                    return "HOT"
                elif recent.era > baseline.era * 1.25:  # 25% worse
                    return "COLD"
        else:
            # For hitters: higher AVG is better
            if recent.avg and baseline.avg:
                if recent.avg > baseline.avg * 1.2:  # 20% improvement
                    return "HOT"
                elif recent.avg < baseline.avg * 0.8:  # 20% worse
                    return "COLD"
        
        return "STABLE"
    
    def _find_player_id(self, player_name: str) -> Optional[int]:
        """Find MLB player ID from player name"""
        # Check cache
        if player_name in self._player_id_cache:
            return self._player_id_cache[player_name]
        
        try:
            # Search for player
            url = f"{self.MLB_API_BASE}/people/search"
            params = {'names': player_name}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('people') and len(data['people']) > 0:
                player_id = data['people'][0]['id']
                self._player_id_cache[player_name] = player_id
                return player_id
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding player ID for {player_name}: {e}")
            return None
    
    @staticmethod
    def _is_spring_training_period() -> bool:
        """Return True if the current date falls in the MLB spring training window."""
        today = datetime.now()
        # Spring training runs roughly Feb 15 – Opening Day (early April)
        return (today.month == 3) or (today.month == 2 and today.day >= 15)

    def _fetch_game_logs(
        self,
        player_id: int,
        is_pitcher: bool,
        days: int
    ) -> Optional[RecentStats]:
        """Fetch and aggregate game logs for a player.

        During spring training the MLB Stats API defaults to regular-season
        game logs, which are empty. We explicitly request preseason (S) game
        types so spring stats are returned.
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            season = end_date.year
            
            stats_group = "pitching" if is_pitcher else "hitting"
            
            url = f"{self.MLB_API_BASE}/people/{player_id}/stats"
            params: dict = {
                'stats': 'gameLog',
                'season': season,
                'group': stats_group,
            }

            # During spring training, include preseason game type (S).
            # The regular season hasn't started yet, so without this the API
            # returns zero splits and all stats come back null.
            if self._is_spring_training_period():
                params['gameType'] = 'S'
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse game logs
            return self._parse_game_logs(data, is_pitcher, start_date, end_date)
            
        except Exception as e:
            logger.debug(f"Error fetching game logs for player {player_id}: {e}")
            return None
    
    def _parse_game_logs(
        self,
        data: Dict,
        is_pitcher: bool,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[RecentStats]:
        """Parse MLB API game log data"""
        try:
            stats_data = data.get('stats', [])
            if not stats_data:
                return None
            
            splits = stats_data[0].get('splits', [])
            if not splits:
                return None
            
            # Filter games in date range
            games_in_range = []
            for split in splits:
                game_date_str = split.get('date')
                if not game_date_str:
                    continue
                
                try:
                    game_date = datetime.strptime(game_date_str, '%Y-%m-%d')
                    if start_date <= game_date <= end_date:
                        games_in_range.append(split['stat'])
                except ValueError:
                    continue
            
            if not games_in_range:
                return None
            
            # Aggregate stats
            if is_pitcher:
                return self._aggregate_pitcher_stats(games_in_range)
            else:
                return self._aggregate_hitter_stats(games_in_range)
                
        except Exception as e:
            logger.debug(f"Error parsing game logs: {e}")
            return None
    
    def _aggregate_hitter_stats(self, games: List[Dict]) -> RecentStats:
        """Aggregate hitting statistics across games"""
        total_ab = 0
        total_hits = 0
        total_hr = 0
        total_rbi = 0
        total_sb = 0
        
        for game in games:
            ab = game.get('atBats', 0)
            hits = game.get('hits', 0)
            
            total_ab += ab
            total_hits += hits
            total_hr += game.get('homeRuns', 0)
            total_rbi += game.get('rbi', 0)
            total_sb += game.get('stolenBases', 0)
        
        # Calculate AVG
        avg = total_hits / total_ab if total_ab > 0 else 0.0
        
        return RecentStats(
            avg=avg,
            hr=total_hr,
            rbi=total_rbi,
            sb=total_sb,
            games=len(games)
        )
    
    def _aggregate_pitcher_stats(self, games: List[Dict]) -> RecentStats:
        """Aggregate pitching statistics across games"""
        total_ip = 0.0
        total_er = 0
        total_h = 0
        total_bb = 0
        total_k = 0
        total_w = 0
        
        for game in games:
            # Parse innings pitched (can be like "6.1" or "7.0")
            ip_str = game.get('inningsPitched', '0')
            try:
                ip_parts = str(ip_str).split('.')
                ip_whole = int(ip_parts[0])
                ip_frac = int(ip_parts[1]) / 3.0 if len(ip_parts) > 1 else 0.0
                ip = ip_whole + ip_frac
                total_ip += ip
            except (ValueError, IndexError):
                pass
            
            total_er += game.get('earnedRuns', 0)
            total_h += game.get('hits', 0)
            total_bb += game.get('baseOnBalls', 0)
            total_k += game.get('strikeOuts', 0)
            
            # Count wins (decision is "W")
            if game.get('decision') == 'W':
                total_w += 1
        
        # Calculate ERA and WHIP
        era = (total_er * 9.0) / total_ip if total_ip > 0 else 0.0
        whip = (total_h + total_bb) / total_ip if total_ip > 0 else 0.0
        
        return RecentStats(
            era=era,
            whip=whip,
            k=total_k,
            w=total_w,
            games=len(games)
        )
    
    def _load_from_cache(self, player_name: str, days: int) -> Optional[RecentStats]:
        """Load stats from cache if available and fresh"""
        try:
            cache_file = self.CACHE_DIR / f"{player_name.replace(' ', '_')}_{days}d.json"
            
            if not cache_file.exists():
                return None
            
            # Check if cache is fresh
            modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - modified_time > self.CACHE_DURATION:
                return None
            
            # Load cached data
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            return RecentStats(**data)
            
        except Exception as e:
            logger.debug(f"Error loading cache for {player_name}: {e}")
            return None
    
    def _save_to_cache(self, player_name: str, days: int, stats: RecentStats):
        """Save stats to cache"""
        try:
            cache_file = self.CACHE_DIR / f"{player_name.replace(' ', '_')}_{days}d.json"
            
            with open(cache_file, 'w') as f:
                json.dump(stats.to_dict(), f)
                
        except Exception as e:
            logger.debug(f"Error saving cache for {player_name}: {e}")


if __name__ == "__main__":
    # Test the stats fetcher
    logging.basicConfig(level=logging.INFO)
    
    fetcher = StatsFetcher()
    
    # Test with a known player
    print("Testing with Aaron Judge...")
    stats = fetcher.get_multi_window_stats("Aaron Judge", is_pitcher=False)
    
    for window, data in stats.items():
        if data:
            print(f"\n{window}:")
            print(f"  AVG: {data.avg:.3f}" if data.avg else "  AVG: N/A")
            print(f"  HR: {data.hr}")
            print(f"  RBI: {data.rbi}")
            print(f"  Games: {data.games}")
    
    trending = fetcher.get_trending_status("Aaron Judge", is_pitcher=False)
    print(f"\nTrending: {trending}")
