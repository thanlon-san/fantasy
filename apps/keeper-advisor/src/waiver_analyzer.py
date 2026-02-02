#!/usr/bin/env python3
"""
Waiver Wire Analyzer
Identifies pickup/drop opportunities by comparing free agents to roster
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .models import Player, Roster
from .keeper_rules import KeeperRules
from .adp_fetcher import ADPFetcher
from .breakout_detector import BreakoutDetector, BreakoutSignal
from .league_settings import load_league_settings

logger = logging.getLogger(__name__)


@dataclass
class WaiverRecommendation:
    """A pickup/drop recommendation"""
    
    add_player: Player
    drop_player: Player
    value_gain: float
    add_keeper_cost: int
    drop_keeper_cost: Optional[int]
    confidence: str  # "Strong", "Good", "Consider"
    reason: str
    
    def __str__(self) -> str:
        return (
            f"\nAdd:  {self.add_player.name} ({self.add_player.position}) - ADP {self.add_player.adp}\n"
            f"Drop: {self.drop_player.name} ({self.drop_player.position}) - ADP {self.drop_player.adp or 'N/A'}\n"
            f"Value: +{self.value_gain:.1f} points\n"
            f"Keeper Cost: Round {self.add_keeper_cost}\n"
            f"Reason: {self.reason}"
        )


class WaiverAnalyzer:
    """Analyzes waiver wire opportunities"""
    
    # Thresholds for recommendation confidence
    STRONG_THRESHOLD = 100  # ADP difference for "Strong" recommendation
    GOOD_THRESHOLD = 50     # ADP difference for "Good" recommendation
    
    # Breakout signal value boosts
    BREAKOUT_BOOST = {
        BreakoutSignal.STRONG: 150,    # Huge boost - elite breakout
        BreakoutSignal.EMERGING: 75,   # Significant boost
        BreakoutSignal.WATCH: 30,      # Moderate boost
        BreakoutSignal.FADING: -50,    # Penalty - sell high signal
    }
    
    def __init__(self, roster: Roster, settings=None, use_breakout_signals: bool = True):
        self.roster = roster
        self.adp_fetcher = ADPFetcher()
        
        # Optional: integrate breakout detector
        self.use_breakout_signals = use_breakout_signals
        if use_breakout_signals:
            self.breakout_detector = BreakoutDetector()
            logger.info("Breakout signal integration enabled")
        else:
            self.breakout_detector = None
        
        # Load settings (use provided or load from file)
        if settings is None:
            try:
                settings = load_league_settings()
            except FileNotFoundError:
                # Use defaults if no config file
                settings = None
        
        self.settings = settings
        
        # Calculate position needs
        self.position_needs = self._calculate_position_needs()
    
    def analyze_free_agents(
        self,
        free_agents: List[Dict],
        max_recommendations: int = 10,
        position_filter: Optional[str] = None
    ) -> List[WaiverRecommendation]:
        """
        Analyze free agents and generate pickup recommendations
        
        Args:
            free_agents: List of free agent player data from Yahoo API
            max_recommendations: Maximum number of recommendations to return
            position_filter: Optional position to filter by (e.g., "2B", "SP", "OF")
            
        Returns:
            List of WaiverRecommendation objects, sorted by value
        """
        logger.info(f"Analyzing {len(free_agents)} free agents...")
        
        # Convert free agents to Player objects with ADP
        fa_players = []
        for fa_data in free_agents:
            player = self._convert_to_player(fa_data)
            if player and player.adp and player.adp < 400:  # Only consider rostered-worthy players
                # Apply position filter if specified
                if position_filter:
                    if position_filter not in player.position:
                        continue
                fa_players.append(player)
        
        logger.info(f"Found {len(fa_players)} viable free agents with ADP < 400")
        
        # Get droppable players from roster (bench, end of roster)
        droppable = self._get_droppable_players()
        logger.info(f"Identified {len(droppable)} droppable players on roster")
        
        # Generate recommendations
        recommendations = []
        for fa in fa_players:
            for drop in droppable:
                rec = self._evaluate_pickup(fa, drop)
                if rec:
                    recommendations.append(rec)
        
        # Sort by value gain and return top N
        recommendations.sort(key=lambda x: x.value_gain, reverse=True)
        return recommendations[:max_recommendations]
    
    def _convert_to_player(self, fa_data: Dict) -> Optional[Player]:
        """Convert free agent data to Player object"""
        try:
            name = fa_data.get('name', '')
            position = ', '.join(fa_data.get('eligible_positions', []))
            team = fa_data.get('editorial_team_abbr', 'FA')
            
            # Get ADP for this player
            adp = self.adp_fetcher.get_player_adp(name)
            
            return Player(
                name=name,
                position=position,
                team=team,
                draft_round=12,  # FAs count as 12th round for keeper purposes
                draft_year=2026,  # Current year for FAs
                years_kept=0,
                adp=adp,
                is_undrafted_fa=True
            )
        except Exception as e:
            logger.warning(f"Error converting FA {fa_data.get('name', 'Unknown')}: {e}")
            return None
    
    def _get_droppable_players(self) -> List[Player]:
        """
        Identify droppable players on roster
        
        Criteria:
        - Low ADP (or no ADP)
        - Poor keeper value
        - Bench/depth players
        """
        droppable = []
        
        for player in self.roster.players:
            # Don't consider dropping keepers or core players
            if player.adp and player.adp < 100:
                continue
            
            # Don't drop players with good keeper value
            keeper_cost = KeeperRules.calculate_keeper_cost(
                player.draft_round,
                player.years_kept,
                player.is_undrafted_fa
            )
            if keeper_cost and player.adp:
                keeper_value = (13 - keeper_cost) * 12 - player.adp
                if keeper_value > 50:  # Good keeper value
                    continue
            
            droppable.append(player)
        
        # Sort by ADP (worst first)
        droppable.sort(key=lambda p: p.adp if p.adp else 999, reverse=True)
        
        return droppable
    
    def _evaluate_pickup(
        self,
        add_player: Player,
        drop_player: Player
    ) -> Optional[WaiverRecommendation]:
        """
        Evaluate a specific pickup/drop combination
        
        Returns None if not a good move
        """
        # Calculate ADP value gain
        add_adp = add_player.adp or 400
        drop_adp = drop_player.adp or 400
        
        value_gain = drop_adp - add_adp
        
        # NEW: Apply breakout signal boost
        if self.use_breakout_signals and self.breakout_detector:
            breakout_boost = self._get_breakout_boost(add_player)
            if breakout_boost != 0:
                logger.debug(f"{add_player.name}: Breakout boost = {breakout_boost:+.0f}")
                value_gain += breakout_boost
        
        # NEW: Apply position need boost
        position_boost = self._get_position_need_boost(add_player)
        if position_boost > 0:
            logger.debug(f"{add_player.name}: Position need boost = {position_boost:+.0f}")
            value_gain += position_boost
        
        # Only recommend if positive value
        if value_gain <= 0:
            return None
        
        # Calculate keeper costs
        add_keeper_cost = 12  # FAs cost round 12
        drop_keeper_cost = KeeperRules.calculate_keeper_cost(
            drop_player.draft_round,
            drop_player.years_kept,
            drop_player.is_undrafted_fa
        )
        
        # Determine confidence level
        if value_gain >= self.STRONG_THRESHOLD:
            confidence = "STRONG"
            emoji = "⭐"
        elif value_gain >= self.GOOD_THRESHOLD:
            confidence = "GOOD"
            emoji = "📈"
        else:
            confidence = "CONSIDER"
            emoji = "🤔"
        
        # Generate reason
        reason = self._generate_reason(add_player, drop_player, value_gain)
        
        return WaiverRecommendation(
            add_player=add_player,
            drop_player=drop_player,
            value_gain=value_gain,
            add_keeper_cost=add_keeper_cost,
            drop_keeper_cost=drop_keeper_cost,
            confidence=confidence,
            reason=reason
        )
    
    def _generate_reason(
        self,
        add_player: Player,
        drop_player: Player,
        value_gain: float
    ) -> str:
        """Generate a human-readable reason for the recommendation"""
        reasons = []
        
        if value_gain >= 200:
            reasons.append("Massive ADP advantage")
        elif value_gain >= 100:
            reasons.append("Significant upgrade")
        else:
            reasons.append("Solid value gain")
        
        # Check for breakout signals
        if self.use_breakout_signals and self.breakout_detector:
            alert = self._check_breakout(add_player)
            if alert and alert.signal == BreakoutSignal.STRONG:
                reasons.append("🔥 STRONG BREAKOUT")
            elif alert and alert.signal == BreakoutSignal.EMERGING:
                reasons.append("⚡ Emerging breakout")
        
        # Check for position needs
        position_boost = self._get_position_need_boost(add_player)
        if position_boost >= 40:
            reasons.append("🎯 Critical position need")
        elif position_boost >= 20:
            reasons.append("Position need")
        
        # Position-specific notes
        if "SP" in add_player.position or "RP" in add_player.position:
            reasons.append("pitcher upgrade")
        elif "C" in add_player.position:
            reasons.append("catcher position")
        
        # Keeper value note
        reasons.append("Round 12 keeper cost")
        
        return ", ".join(reasons)
    
    def _get_breakout_boost(self, player: Player) -> float:
        """
        Calculate breakout signal boost for a player
        
        Returns:
            Boost value to add to value_gain (can be negative for fading signals)
        """
        alert = self._check_breakout(player)
        if alert:
            boost = self.BREAKOUT_BOOST.get(alert.signal, 0)
            return boost
        return 0
    
    def _calculate_position_needs(self) -> Dict[str, float]:
        """
        Calculate how badly each position is needed
        
        Returns:
            Dict of position -> need score (0-100, higher = more needed)
        """
        if not self.settings:
            return {}
        
        # Get roster requirements from settings
        roster_positions = self.settings.roster_config.get('positions', {})
        
        # Count players by position
        position_counts = {}
        for position in roster_positions.keys():
            if position == 'Bench':
                continue
            position_counts[position] = 0
        
        # Count current roster
        for player in self.roster.players:
            player_positions = player.position.split(',')
            for pos in player_positions:
                pos = pos.strip()
                if pos in position_counts:
                    position_counts[pos] += 1
        
        # Calculate need scores
        needs = {}
        for position, required in roster_positions.items():
            if position == 'Bench':
                continue
            
            current = position_counts.get(position, 0)
            
            # Score based on shortage
            if current < required:
                # Critical shortage
                needs[position] = 100
            elif current == required:
                # At minimum, but no depth
                needs[position] = 60
            elif current < required * 1.5:
                # Some depth, but could use more
                needs[position] = 30
            else:
                # Good depth
                needs[position] = 0
        
        return needs
    
    def _get_position_need_boost(self, player: Player) -> float:
        """
        Calculate boost based on position need
        
        Returns:
            Boost value (0-50 points)
        """
        if not self.position_needs:
            return 0
        
        max_boost = 0
        player_positions = player.position.split(',')
        
        for pos in player_positions:
            pos = pos.strip()
            need = self.position_needs.get(pos, 0)
            
            # Convert need score (0-100) to boost (0-50)
            boost = need * 0.5
            max_boost = max(max_boost, boost)
        
        return max_boost
    
    def _check_breakout(self, player: Player):
        """Check for breakout signal (with caching to avoid redundant API calls)"""
        if not self.breakout_detector:
            return None
        
        # Parse player name
        parts = player.name.split()
        if len(parts) < 2:
            return None
        
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        
        # Determine player type from position
        player_type = 'pitcher' if any(p in player.position for p in ['SP', 'RP', 'P']) else 'hitter'
        
        try:
            # Analyze for breakout (shorter windows for waiver decisions)
            alert = self.breakout_detector.analyze_player(
                first_name,
                last_name,
                player_type,
                recent_days=10,   # Recent hot streak
                baseline_days=30  # 1 month baseline
            )
            return alert
        except Exception as e:
            logger.debug(f"Could not check breakout for {player.name}: {e}")
            return None


def print_waiver_report(recommendations: List[WaiverRecommendation], breakout_signals: Optional[Dict] = None):
    """Print a formatted waiver wire report with breakout signals"""
    
    if not recommendations:
        print("\n🤷 No waiver wire upgrades found")
        print("Your roster is solid! No obvious pickups available.")
        return
    
    breakout_signals = breakout_signals or {}
    
    print("\n" + "="*70)
    print("🎯 TOP WAIVER WIRE OPPORTUNITIES")
    print("="*70)
    
    # Separate breakout candidates
    breakout_picks = []
    regular_picks = []
    
    for rec in recommendations:
        alert = breakout_signals.get(rec.add_player.name)
        if alert and alert.signal in [BreakoutSignal.STRONG, BreakoutSignal.EMERGING]:
            breakout_picks.append((rec, alert))
        else:
            regular_picks.append(rec)
    
    # Show breakout candidates first (HOT PICKS!)
    if breakout_picks:
        print(f"\n🔥 BREAKOUT CANDIDATES ({len(breakout_picks)} found)\n")
        for i, (rec, alert) in enumerate(breakout_picks[:5], 1):
            signal_emoji = "🔥" if alert.signal == BreakoutSignal.STRONG else "⚡"
            print(f"{i}. {signal_emoji} {rec.add_player.name} ({rec.add_player.position}) - ADP {int(rec.add_player.adp) if rec.add_player.adp else '?'}")
            print(f"   {alert.signal.value} {alert.category.value} breakout")
            print(f"   Value gain: +{int(rec.value_gain)} | {rec.reason}")
            if rec.drop_player:
                print(f"   Drop: {rec.drop_player.name}")
            print()
    
    # Group regular picks by confidence
    strong = [r for r in regular_picks if r.confidence == "STRONG"]
    good = [r for r in regular_picks if r.confidence == "GOOD"]
    consider = [r for r in regular_picks if r.confidence == "CONSIDER"]
    
    if strong:
        print(f"\n⭐ STRONG VALUE PICKUPS ({len(strong)} found)\n")
        for i, rec in enumerate(strong[:5], 1):
            print(f"{i}. {rec}")
    
    if good:
        print(f"\n📈 GOOD PICKUPS ({len(good)} found)\n")
        for i, rec in enumerate(good[:5], 1):
            print(f"{i}. {rec}")
    
    if consider:
        print(f"\n🤔 WORTH CONSIDERING ({len(consider)} found)\n")
        for i, rec in enumerate(consider[:3], 1):
            print(f"{i}. {rec}")
    
    # Summary
    print("\n" + "="*70)
    print(f"📊 SCAN SUMMARY")
    print("-"*70)
    print(f"Total opportunities: {len(recommendations)}")
    print(f"Breakout candidates: {len(breakout_picks)}")
    print(f"High-value pickups: {len(strong)}")
    print("="*70)
    print("💡 TIP: Breakout candidates are your highest-upside targets!")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Test with sample data
    import sys
    from pathlib import Path
    
    app_root = Path(__file__).parent.parent
    sys.path.insert(0, str(app_root))
    
    from src.importers import CSVImporter
    
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 Testing Waiver Analyzer...\n")
    
    # Load roster
    roster = CSVImporter.import_roster(
        app_root / "data" / "my_roster_from_yahoo.csv",
        team_name="Test Team"
    )
    
    # Sample free agents (would come from Yahoo API)
    sample_fas = [
        {'name': 'Pete Alonso', 'eligible_positions': ['1B'], 'editorial_team_abbr': 'BAL'},
        {'name': 'Jazz Chisholm Jr.', 'eligible_positions': ['2B', '3B'], 'editorial_team_abbr': 'NYY'},
        {'name': 'Wyatt Langford', 'eligible_positions': ['OF'], 'editorial_team_abbr': 'TEX'},
    ]
    
    analyzer = WaiverAnalyzer(roster)
    recommendations = analyzer.analyze_free_agents(sample_fas)
    
    print_waiver_report(recommendations)
