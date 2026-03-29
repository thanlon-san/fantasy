"""
Data models for keeper advisor
Represents players, roster, and keeper analysis
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Player:
    """Represents a player on your roster"""
    
    name: str
    position: str  # 1B, 2B, SS, 3B, OF, C, SP, RP, DH
    team: str  # MLB team
    
    # Draft information
    draft_round: int  # Round drafted (use 13+ for undrafted FA)
    draft_year: int
    is_undrafted_fa: bool = False
    
    # Keeper history
    years_kept: int = 0  # How many years already kept
    
    # Performance data
    adp: Optional[float] = None  # Average Draft Position (lower is better)
    projected_stats: Optional[dict] = None
    last_season_stats: Optional[dict] = None
    
    # Recent performance (for waiver analysis)
    recent_stats: Optional[dict] = None  # Dict of {window: RecentStats}
    trending: Optional[str] = None  # "HOT", "COLD", "STABLE"
    rostered_pct: Optional[int] = None  # Percentage rostered in leagues
    
    # Additional metadata
    rostered_date: Optional[datetime] = None  # When added to roster
    notes: str = ""
    
    def __post_init__(self):
        """Validate data after initialization"""
        if self.draft_round < 1:
            raise ValueError("Draft round must be >= 1")
        if self.years_kept < 0:
            raise ValueError("Years kept cannot be negative")


@dataclass
class KeeperAnalysis:
    """Analysis results for a keeper candidate"""
    
    player: Player
    
    # Eligibility
    is_eligible: bool
    keeper_round: Optional[int]  # Cost to keep
    years_remaining: int
    reason: str
    
    # Value analysis
    keeper_value: Optional[float] = None  # Value score (higher is better)
    draft_value: Optional[float] = None  # What they'd go for in draft
    surplus_value: Optional[float] = None  # keeper_value - draft_value
    
    # Recommendation
    recommendation: str = ""  # Keep, Don't Keep, or Maybe
    recommendation_reason: str = ""
    
    # Rankings
    rank: Optional[int] = None  # Rank among all keeper candidates
    
    # Adjusted round (for multiple round-12 keepers)
    adjusted_keeper_round: Optional[int] = None
    
    def is_keeper(self) -> bool:
        """Quick check if this should be kept"""
        return self.recommendation == "Keep"


@dataclass
class Roster:
    """Represents your full roster"""
    
    team_name: str
    league_name: str
    year: int
    
    players: List[Player] = field(default_factory=list)
    
    # Analysis results
    keeper_analyses: List[KeeperAnalysis] = field(default_factory=list)
    recommended_keepers: List[Player] = field(default_factory=list)
    
    def add_player(self, player: Player):
        """Add a player to the roster"""
        self.players.append(player)
    
    def get_keeper_candidates(self) -> List[Player]:
        """Get all players who might be keeper candidates"""
        return [p for p in self.players]
    
    def get_top_keepers(self, n: int = 3) -> List[KeeperAnalysis]:
        """Get top N recommended keepers"""
        keepers = [a for a in self.keeper_analyses if a.is_keeper()]
        return sorted(keepers, key=lambda k: k.rank or 999)[:n]
    
    def summary(self) -> str:
        """Get a text summary of the roster"""
        total = len(self.players)
        eligible = len([a for a in self.keeper_analyses if a.is_eligible])
        recommended = len([a for a in self.keeper_analyses if a.is_keeper()])
        
        return f"""
Roster Summary for {self.team_name}
{'='*50}
Total Players: {total}
Keeper Eligible: {eligible}
Recommended Keepers: {recommended}
"""


@dataclass
class KeeperScenario:
    """Represents a possible keeper combination"""
    
    keepers: List[Player]
    total_value: float
    rounds_used: List[int]
    description: str
    
    def __str__(self):
        keeper_names = [k.name for k in self.keepers]
        return f"{len(self.keepers)} Keepers: {', '.join(keeper_names)} (Value: {self.total_value:.1f})"
