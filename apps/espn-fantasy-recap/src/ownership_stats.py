"""
Ownership & Roster % Stats for Fantasy Football
Uses Sleeper API (free) to get roster/start rates across all leagues
"""

import requests
from typing import Dict, Optional
from shared.logger import get_logger

logger = get_logger(__name__)

class OwnershipStats:
    """Fetch roster % and start % from Sleeper API"""
    
    BASE_URL = "https://api.sleeper.app/v1"
    
    def __init__(self):
        self.player_cache = {}
        self.trending_cache = {}
    
    def get_player_id(self, player_name: str) -> Optional[str]:
        """
        Get Sleeper player ID from name
        Note: Sleeper API uses player IDs, not names
        """
        try:
            # Get all players (cached)
            if not self.player_cache:
                response = requests.get(f"{self.BASE_URL}/players/nfl", timeout=10)
                response.raise_for_status()
                players = response.json()
                
                # Build name -> ID mapping
                for player_id, player_data in players.items():
                    full_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                    self.player_cache[full_name.lower()] = player_id
            
            return self.player_cache.get(player_name.lower())
        
        except Exception as e:
            logger.warning(f"Failed to get player ID for {player_name}: {e}")
            return None
    
    def get_trending_players(self, trend_type: str = "add") -> Dict:
        """
        Get trending adds or drops
        trend_type: 'add' or 'drop'
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/players/nfl/trending/{trend_type}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.warning(f"Failed to get trending {trend_type}: {e}")
            return {}
    
    def is_trending_add(self, player_name: str, top_n: int = 50) -> bool:
        """Check if player is in top N trending adds"""
        if not self.trending_cache.get('add'):
            self.trending_cache['add'] = self.get_trending_players('add')
        
        player_id = self.get_player_id(player_name)
        if not player_id:
            return False
        
        trending = self.trending_cache['add']
        for idx, item in enumerate(trending[:top_n]):
            if item.get('player_id') == player_id:
                return True, idx + 1  # Return rank
        
        return False, None
    
    def is_trending_drop(self, player_name: str, top_n: int = 50) -> bool:
        """Check if player is in top N trending drops"""
        if not self.trending_cache.get('drop'):
            self.trending_cache['drop'] = self.get_trending_players('drop')
        
        player_id = self.get_player_id(player_name)
        if not player_id:
            return False
        
        trending = self.trending_cache['drop']
        for idx, item in enumerate(trending[:top_n]):
            if item.get('player_id') == player_id:
                return True, idx + 1  # Return rank
        
        return False, None
    
    def generate_ownership_roast(
        self, 
        player_name: str, 
        was_started: bool,
        points_scored: float,
        percent_started: float  # From ESPN API
    ) -> Optional[str]:
        """
        Generate roast based on ownership % and start/sit decision
        
        Args:
            player_name: Player's name
            was_started: Did the manager start this player?
            points_scored: Points the player scored
            percent_started: % started from ESPN (0-100)
        
        Returns:
            Roast string or None
        """
        # Skip if invalid data (ESPN API returns -1 for some players)
        if percent_started < 0:
            return None
            
        roasts = []
        
        # Scenario 1: STARTED a player almost nobody starts
        if was_started and percent_started < 5:
            roasts.append(
                f"{player_name} is started in {percent_started:.1f}% of leagues. "
                f"You're the {percent_started:.1f}%. There's a reason for that."
            )
        
        # Scenario 2: BENCHED a player almost everyone starts
        if not was_started and percent_started > 70 and points_scored > 15:
            roasts.append(
                f"You benched {player_name} ({percent_started:.0f}% start rate). "
                f"He scored {points_scored:.1f}. The people tried to warn you."
            )
        
        # Scenario 3: Started a trending DROP
        is_drop, drop_rank = self.is_trending_drop(player_name, top_n=25)
        if was_started and is_drop:
            roasts.append(
                f"{player_name} is the #{drop_rank} trending DROP this week. "
                f"You started him. Contrarian or clueless?"
            )
        
        # Scenario 4: Dropped/benched a trending ADD
        is_add, add_rank = self.is_trending_add(player_name, top_n=25)
        if not was_started and is_add and points_scored > 20:
            roasts.append(
                f"{player_name} is the #{add_rank} trending ADD. "
                f"You benched {points_scored:.1f} points. Everyone else saw it coming."
            )
        
        return roasts[0] if roasts else None


def get_ownership_context(
    starter_name: str,
    starter_points: float,
    starter_percent_started: float,
    bench_player_name: str = None,
    bench_points: float = None,
    bench_percent_started: float = None
) -> str:
    """
    Helper function to get ownership-based roasts
    
    Example usage in recap_generator.py:
        roast = get_ownership_context(
            starter_name="Gus Edwards",
            starter_points=4.2,
            starter_percent_started=8.3,
            bench_player_name="Jahmyr Gibbs",
            bench_points=27.4,
            bench_percent_started=92.1
        )
    """
    ownership = OwnershipStats()
    roasts = []
    
    # Check starter
    if starter_percent_started:
        roast = ownership.generate_ownership_roast(
            starter_name, 
            was_started=True,
            points_scored=starter_points,
            percent_started=starter_percent_started
        )
        if roast:
            roasts.append(roast)
    
    # Check bench (if provided)
    if bench_player_name and bench_percent_started:
        roast = ownership.generate_ownership_roast(
            bench_player_name,
            was_started=False,
            points_scored=bench_points,
            percent_started=bench_percent_started
        )
        if roast:
            roasts.append(roast)
    
    return "\n\n".join(roasts) if roasts else None


if __name__ == "__main__":
    # Test the ownership stats
    ownership = OwnershipStats()
    
    # Test 1: Low ownership start
    print("Test 1: Starting a player nobody else starts")
    roast = ownership.generate_ownership_roast(
        player_name="Gus Edwards",
        was_started=True,
        points_scored=4.2,
        percent_started=3.1
    )
    print(f"  {roast}\n")
    
    # Test 2: High ownership bench
    print("Test 2: Benching a player everyone else starts")
    roast = ownership.generate_ownership_roast(
        player_name="Christian McCaffrey",
        was_started=False,
        points_scored=28.4,
        percent_started=99.2
    )
    print(f"  {roast}\n")
    
    # Test 3: Trending checks
    print("Test 3: Checking trending adds")
    is_add, rank = ownership.is_trending_add("Tyreek Hill", top_n=50)
    if is_add:
        print(f"  Tyreek Hill is trending ADD (#{rank})\n")
    else:
        print(f"  Not in top 50 trending adds\n")

