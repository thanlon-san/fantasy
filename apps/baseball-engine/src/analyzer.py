"""
Keeper Analysis Engine
Analyzes roster and provides keeper recommendations
"""

from typing import List, Optional
import sys
from pathlib import Path

# Add paths for imports
app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.models import Player, KeeperAnalysis, Roster, KeeperScenario
from src.keeper_rules import KeeperRules
from shared.logger import get_logger

logger = get_logger(__name__)


class KeeperAnalyzer:
    """Analyzes players and provides keeper recommendations"""
    
    def __init__(self, roster: Roster):
        self.roster = roster
        self.rules = KeeperRules()
    
    def analyze_player(self, player: Player) -> KeeperAnalysis:
        """
        Analyze a single player for keeper eligibility and value
        
        Args:
            player: Player to analyze
            
        Returns:
            KeeperAnalysis with full evaluation
        """
        # Check eligibility using rules engine
        eligibility = self.rules.check_eligibility(
            draft_round=player.draft_round,
            years_kept=player.years_kept,
            is_undrafted_fa=player.is_undrafted_fa,
            rostered_before_september=True  # Assume true if on roster
        )
        
        analysis = KeeperAnalysis(
            player=player,
            is_eligible=eligibility.is_eligible,
            keeper_round=eligibility.keeper_round,
            years_remaining=eligibility.years_remaining,
            reason=eligibility.reason
        )
        
        # If eligible, calculate value
        if eligibility.is_eligible and player.adp:
            analysis.keeper_value = self._calculate_keeper_value(player, eligibility.keeper_round)
            analysis.draft_value = self._calculate_draft_value(player)
            analysis.surplus_value = analysis.keeper_value - analysis.draft_value
            
            # Make recommendation
            analysis.recommendation, analysis.recommendation_reason = self._make_recommendation(
                player, analysis
            )
        else:
            analysis.recommendation = "Don't Keep"
            analysis.recommendation_reason = eligibility.reason
        
        return analysis
    
    def analyze_all_players(self) -> List[KeeperAnalysis]:
        """
        Analyze all players on the roster
        
        Returns:
            List of KeeperAnalysis for each player
        """
        logger.info(f"Analyzing {len(self.roster.players)} players...")
        
        analyses = []
        for player in self.roster.players:
            analysis = self.analyze_player(player)
            analyses.append(analysis)
        
        # Rank the keeper candidates
        keeper_candidates = [a for a in analyses if a.is_eligible]
        keeper_candidates.sort(key=lambda a: a.surplus_value or 0, reverse=True)
        
        for i, analysis in enumerate(keeper_candidates, 1):
            analysis.rank = i
        
        self.roster.keeper_analyses = analyses
        return analyses
    
    def get_recommended_keepers(self, max_keepers: int = 3) -> List[KeeperAnalysis]:
        """
        Get the top recommended keepers with adjusted rounds if needed
        
        Args:
            max_keepers: Maximum number of keepers to return
            
        Returns:
            List of recommended keeper analyses with adjusted_keeper_round attribute
        """
        if not self.roster.keeper_analyses:
            self.analyze_all_players()
        
        # Get all "Keep" recommendations, sorted by rank
        keepers = [a for a in self.roster.keeper_analyses if a.recommendation == "Keep"]
        keepers.sort(key=lambda a: a.rank or 999)
        
        top_keepers = keepers[:max_keepers]
        
        # Apply round adjustments for multiple round-12 keepers
        adjusted_rounds = self._adjust_keeper_rounds(top_keepers)
        for i, keeper in enumerate(top_keepers):
            keeper.adjusted_keeper_round = adjusted_rounds[i]
        
        return top_keepers
    
    def generate_keeper_scenarios(self) -> List[KeeperScenario]:
        """
        Generate different keeper combination scenarios
        
        Returns:
            List of possible keeper scenarios
        """
        if not self.roster.keeper_analyses:
            self.analyze_all_players()
        
        # Get eligible keepers sorted by value
        candidates = [a for a in self.roster.keeper_analyses 
                     if a.is_eligible and a.surplus_value and a.surplus_value > 0]
        candidates.sort(key=lambda a: a.surplus_value, reverse=True)
        
        scenarios = []
        
        # Scenario 1: Top 3 keepers
        if len(candidates) >= 3:
            top3 = candidates[:3]
            adjusted_rounds = self._adjust_keeper_rounds(top3)
            scenarios.append(KeeperScenario(
                keepers=[a.player for a in top3],
                total_value=sum(a.surplus_value for a in top3),
                rounds_used=adjusted_rounds,
                description="Top 3 value keepers" + self._get_round_adjustment_note(top3, adjusted_rounds)
            ))
        
        # Scenario 2: Top 2 keepers (save a pick)
        if len(candidates) >= 2:
            top2 = candidates[:2]
            adjusted_rounds = self._adjust_keeper_rounds(top2)
            scenarios.append(KeeperScenario(
                keepers=[a.player for a in top2],
                total_value=sum(a.surplus_value for a in top2),
                rounds_used=adjusted_rounds,
                description="Top 2 keepers (save a round)" + self._get_round_adjustment_note(top2, adjusted_rounds)
            ))
        
        # Scenario 3: Top 1 keeper only
        if len(candidates) >= 1:
            top1 = [candidates[0]]
            scenarios.append(KeeperScenario(
                keepers=[a.player for a in top1],
                total_value=top1[0].surplus_value,
                rounds_used=[top1[0].keeper_round],
                description="Single best keeper (save 2 rounds)"
            ))
        
        # Scenario 4: No keepers (fresh start)
        scenarios.append(KeeperScenario(
            keepers=[],
            total_value=0,
            rounds_used=[],
            description="No keepers (draft flexibility)"
        ))
        
        return scenarios
    
    def _adjust_keeper_rounds(self, analyses: List[KeeperAnalysis]) -> List[int]:
        """
        Adjust keeper rounds when multiple round-12 keepers are selected.
        Per league rules: If keeping multiple round-12 eligible players,
        they spread to rounds 10, 11, 12. Best player should go in round 12 (latest)
        for maximum value.
        
        Args:
            analyses: List of keeper analyses
            
        Returns:
            List of adjusted keeper rounds
        """
        rounds = [a.keeper_round for a in analyses]
        
        # Check if we have multiple round-12 keepers
        round_12_count = sum(1 for r in rounds if r >= 11)
        
        if round_12_count >= 2:
            # Need to spread them across rounds 10, 11, 12
            round_12_keepers = [(i, a) for i, a in enumerate(analyses) if a.keeper_round >= 11]
            
            # Sort by ADP (best ADP = lowest number → should get LATEST round for max value)
            # Reverse sort so best player gets round 12, worst gets round 10
            round_12_keepers.sort(key=lambda x: x[1].player.adp if x[1].player.adp else 999, reverse=True)
            
            # Assign rounds 10, 11, 12 (best player gets 12)
            assignment_rounds = [10, 11, 12]
            adjusted_rounds = rounds.copy()
            
            for idx, (original_idx, analysis) in enumerate(round_12_keepers):
                if idx < len(assignment_rounds):
                    adjusted_rounds[original_idx] = assignment_rounds[idx]
            
            return adjusted_rounds
        
        return rounds
    
    def _get_round_adjustment_note(self, analyses: List[KeeperAnalysis], adjusted_rounds: List[int]) -> str:
        """Get a note about round adjustments if any were made"""
        original_rounds = [a.keeper_round for a in analyses]
        if original_rounds != adjusted_rounds:
            return " (rounds 10-12: you choose order, best player → Rd 12 recommended)"
        return ""
    
    def _calculate_keeper_value(self, player: Player, keeper_round: int) -> float:
        """
        Calculate the value of keeping a player
        Higher is better
        
        Value = Round savings
        If player's ADP is round 3, but you can keep in round 10, you save 7 rounds
        """
        if not player.adp:
            return 0.0
        
        # Convert ADP to draft round (roughly ADP / 12)
        expected_round = max(1, min(12, player.adp / 12))
        
        # Surplus = round savings
        # If they'd go in round 3 but you keep in round 11, surplus = 8 rounds
        surplus_rounds = keeper_round - expected_round
        
        # Convert to value score (higher is better)
        # Multiply by 10 to make differences more apparent
        return surplus_rounds * 10
    
    def _calculate_draft_value(self, player: Player) -> float:
        """
        Calculate what this player would cost in the draft
        Based on their ADP
        """
        if not player.adp:
            return 0.0
        
        # Convert ADP to round
        return player.adp / 12
    
    def _make_recommendation(
        self, 
        player: Player, 
        analysis: KeeperAnalysis
    ) -> tuple[str, str]:
        """
        Make a keep/don't keep recommendation
        
        Returns:
            Tuple of (recommendation, reason)
        """
        if not analysis.surplus_value:
            return ("Don't Keep", "Insufficient data for recommendation")
        
        surplus = analysis.surplus_value
        keeper_round = analysis.keeper_round
        
        # Strong keep: surplus > 30 or keeping in round 10+
        if surplus > 30 or (keeper_round and keeper_round >= 10):
            return ("Keep", f"Excellent value: {surplus:.1f} surplus points, cost: round {keeper_round}")
        
        # Maybe: surplus 10-30
        elif surplus > 10:
            return ("Maybe", f"Good value: {surplus:.1f} surplus points, cost: round {keeper_round}")
        
        # Don't keep: low or negative surplus
        else:
            return ("Don't Keep", f"Poor value: only {surplus:.1f} surplus points")


def print_analysis_report(roster: Roster, analyses: List[KeeperAnalysis]):
    """
    Print a nicely formatted analysis report
    
    Args:
        roster: The roster being analyzed
        analyses: List of keeper analyses
    """
    print("\n" + "="*80)
    print(f"KEEPER ANALYSIS REPORT: {roster.team_name}")
    print("="*80)
    
    # Summary stats
    eligible = [a for a in analyses if a.is_eligible]
    keepers = [a for a in analyses if a.recommendation == "Keep"]
    maybes = [a for a in analyses if a.recommendation == "Maybe"]
    
    print(f"\nTotal Players: {len(analyses)}")
    print(f"Keeper Eligible: {len(eligible)}")
    print(f"Recommended Keepers: {len(keepers)}")
    print(f"Maybes: {len(maybes)}")
    
    # Top keepers
    if keepers:
        print("\n" + "-"*80)
        print("RECOMMENDED KEEPERS")
        print("-"*80)
        
        # Apply round adjustments
        from src.analyzer import KeeperAnalyzer
        analyzer = KeeperAnalyzer(roster)
        top_keepers = analyzer.get_recommended_keepers(3)
        
        # Check if adjustments were made
        round_12_count = sum(1 for k in top_keepers if k.keeper_round >= 11)
        if round_12_count >= 2:
            print("\n⚠️  Multiple round 11+ keepers detected!")
            print("    League rule: Must spread across rounds 10, 11, 12")
            print("    💡 Recommendation: Put BEST player in round 12 (latest) for max value\n")
        
        for analysis in top_keepers:
            adjusted_round = getattr(analysis, 'adjusted_keeper_round', analysis.keeper_round)
            round_text = f"Round {adjusted_round}"
            if adjusted_round != analysis.keeper_round:
                round_text += f" (adjusted from {analysis.keeper_round})"
            
            print(f"\n#{analysis.rank} - {analysis.player.name} ({analysis.player.position})")
            print(f"   Cost: {round_text}")
            print(f"   ADP: {analysis.player.adp:.1f}" if analysis.player.adp else "   ADP: Unknown")
            print(f"   Surplus Value: {analysis.surplus_value:.1f}" if analysis.surplus_value else "")
            print(f"   Years Left: {analysis.years_remaining}")
            print(f"   Reason: {analysis.recommendation_reason}")
    
    # Maybes
    if maybes:
        print("\n" + "-"*80)
        print("MAYBE KEEPERS (Consider These)")
        print("-"*80)
        
        for analysis in maybes:
            print(f"\n{analysis.player.name} ({analysis.player.position})")
            print(f"   Cost: Round {analysis.keeper_round}")
            print(f"   ADP: {analysis.player.adp:.1f}" if analysis.player.adp else "   ADP: Unknown")
            print(f"   Reason: {analysis.recommendation_reason}")
    
    # Ineligible players
    ineligible = [a for a in analyses if not a.is_eligible]
    if ineligible:
        print("\n" + "-"*80)
        print(f"INELIGIBLE PLAYERS ({len(ineligible)})")
        print("-"*80)
        for analysis in ineligible:
            print(f"   {analysis.player.name}: {analysis.reason}")
    
    print("\n" + "="*80 + "\n")
