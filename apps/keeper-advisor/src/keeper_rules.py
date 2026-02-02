"""
Keeper League Rules Engine
Encodes the specific keeper rules for your league
"""

from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class KeeperEligibility:
    """Represents a player's keeper eligibility status"""
    
    is_eligible: bool
    keeper_round: Optional[int]  # What round they would cost to keep
    years_remaining: int  # How many more years of control
    reason: str  # Explanation of eligibility/ineligibility


class KeeperRules:
    """
    Keeper league rules engine based on your league configuration:
    
    - Keep up to 3 players from previous year
    - Undrafted FA keepers must be rostered before Sept call-ups
    - 3-year control (draft year + 2 following years)
    - Keepers move up one round each year
    - Round 12+ players default to 12th round
    - Cannot keep 1st round picks
    - 2nd round picks only have 2 years of control
    """
    
    MAX_KEEPERS = 3
    CONTROL_YEARS = 3
    CONTROL_YEARS_ROUND_2 = 2  # Special case for 2nd rounders
    DEFAULT_LATE_ROUND = 12  # Players drafted after this become 12th rounders
    
    @staticmethod
    def calculate_keeper_cost(
        draft_round: int,
        years_kept: int = 0,
        is_undrafted_fa: bool = False
    ) -> Optional[int]:
        """
        Calculate what round a player would cost to keep
        
        Args:
            draft_round: Original draft round (1-indexed, or 12 for undrafted FA)
            years_kept: How many years they've already been kept
            is_undrafted_fa: True if player was never drafted (FA pickup)
            
        Returns:
            The round they would cost next year, or None if ineligible
        """
        # Can't keep 1st rounders (no round to move up to)
        if draft_round == 1:
            return None
        
        # Undrafted FAs: Start at round 12, then move up each year
        if is_undrafted_fa:
            keeper_cost = KeeperRules.DEFAULT_LATE_ROUND - years_kept
            if keeper_cost < 1:
                return None
            return keeper_cost
            
        # Players drafted after round 12 become 12th rounders
        effective_round = min(draft_round, KeeperRules.DEFAULT_LATE_ROUND)
        
        # Move up one round per year kept
        keeper_cost = effective_round - years_kept - 1
        
        # Can't keep if they'd cost 0 or negative rounds
        if keeper_cost < 1:
            return None
            
        return keeper_cost
    
    @staticmethod
    def calculate_years_remaining(
        draft_round: int,
        years_kept: int = 0
    ) -> int:
        """
        Calculate how many years of control remain
        
        Args:
            draft_round: Original draft round
            years_kept: How many years already kept
            
        Returns:
            Years of control remaining
        """
        # 2nd rounders only get 2 total years of control
        if draft_round == 2:
            return max(0, KeeperRules.CONTROL_YEARS_ROUND_2 - years_kept)
        
        # Everyone else gets 3 years
        return max(0, KeeperRules.CONTROL_YEARS - years_kept)
    
    @staticmethod
    def check_eligibility(
        draft_round: int,
        years_kept: int = 0,
        is_undrafted_fa: bool = False,
        rostered_before_september: bool = True
    ) -> KeeperEligibility:
        """
        Check if a player is eligible to be kept
        
        Args:
            draft_round: Original draft round (use 13+ for undrafted)
            years_kept: Years already kept
            is_undrafted_fa: Whether player was undrafted FA
            rostered_before_september: For FA, whether rostered before Sept
            
        Returns:
            KeeperEligibility with full status
        """
        # Undrafted FA must be rostered before September
        if is_undrafted_fa and not rostered_before_september:
            return KeeperEligibility(
                is_eligible=False,
                keeper_round=None,
                years_remaining=0,
                reason="Undrafted FA must be rostered before September call-ups"
            )
        
        # Calculate keeper cost
        keeper_cost = KeeperRules.calculate_keeper_cost(draft_round, years_kept, is_undrafted_fa)
        years_remaining = KeeperRules.calculate_years_remaining(draft_round, years_kept)
        
        # Check if eligible
        if keeper_cost is None:
            if draft_round == 1:
                reason = "Cannot keep 1st round picks"
            else:
                reason = "No control years remaining"
            
            return KeeperEligibility(
                is_eligible=False,
                keeper_round=None,
                years_remaining=0,
                reason=reason
            )
        
        return KeeperEligibility(
            is_eligible=True,
            keeper_round=keeper_cost,
            years_remaining=years_remaining,
            reason=f"Eligible to keep in round {keeper_cost} ({years_remaining} years remaining)"
        )
    
    @staticmethod
    def rank_keepers_by_cost(keepers: list) -> list:
        """
        Rank multiple keeper candidates when keeping late-round picks
        
        Per rules: If keeping multiple round 11+ players, they must occupy 
        rounds 10, 11, 12. Strategy: Assign best player to round 12 (latest)
        for maximum value since better players would normally go earlier.
        
        Args:
            keepers: List of keeper candidates with 'adp' field
            
        Returns:
            Sorted list with assigned rounds
        """
        if len(keepers) > 3:
            raise ValueError(f"Cannot keep more than {KeeperRules.MAX_KEEPERS} players")
        
        # Sort by ADP (lower ADP = better player)
        sorted_keepers = sorted(keepers, key=lambda k: k.get('adp', 999))
        
        # Assign rounds: Best player → 12, worst → 10
        # This maximizes value since you're keeping the best player cheapest
        rounds = [12, 11, 10]  # Reversed from before
        for i, keeper in enumerate(sorted_keepers):
            keeper['assigned_round'] = rounds[i] if i < len(rounds) else 10
        
        return sorted_keepers
