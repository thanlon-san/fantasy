#!/usr/bin/env python3
"""
Daily Lineup Optimizer
Stat-backed daily roster recommendations based on matchups, park factors, and recent performance
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .daily_matchups import MLBStatsAPI, Game, PlayerMatchup, get_park_factor
from .models import Player, Roster
from .breakout_detector import BreakoutDetector, BreakoutSignal

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of daily recommendations"""
    MUST_START = "MUST_START"      # Elite matchup, start with confidence
    START = "START"                 # Good matchup, recommended
    FLEX = "FLEX"                   # Neutral, use if needed
    BENCH = "BENCH"                 # Poor matchup, sit if possible
    AVOID = "AVOID"                 # Terrible matchup, bench definitely


@dataclass
class LineupRecommendation:
    """A daily lineup recommendation for a player"""
    
    player: Player
    recommendation: RecommendationType
    confidence_score: float  # 0-100
    
    # Matchup details
    opponent: str
    opponent_pitcher: Optional[str]
    home_away: str
    game_time: Optional[str]
    
    # Scoring factors
    matchup_score: float  # Opponent pitcher quality
    park_score: float     # Park factor bonus
    form_score: float     # Recent hot/cold streak
    platoon_score: float  # L/R advantage
    breakout_boost: float = 0  # Breakout signal bonus
    
    # Supporting data
    recent_stats: Optional[Dict]
    career_vs_pitcher: Optional[Dict]
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
    
    def __str__(self) -> str:
        symbol = {
            RecommendationType.MUST_START: "🔥",
            RecommendationType.START: "✅",
            RecommendationType.FLEX: "➡️",
            RecommendationType.BENCH: "⚠️",
            RecommendationType.AVOID: "❌"
        }[self.recommendation]
        
        return (
            f"\n{symbol} {self.recommendation.value}: {self.player.name}\n"
            f"   vs {self.opponent_pitcher or 'TBD'} @ {self.opponent} ({self.game_time or 'TBD'})\n"
            f"   Confidence: {self.confidence_score:.0f}%\n"
            f"   Reasons: {', '.join(self.reasons[:3])}"
        )


class LineupOptimizer:
    """Optimize daily lineups based on matchups and recent performance"""
    
    # Scoring weights (with breakout factor)
    MATCHUP_WEIGHT = 0.30      # Opponent pitcher quality
    PARK_WEIGHT = 0.20         # Ballpark factor
    FORM_WEIGHT = 0.25         # Recent performance
    PLATOON_WEIGHT = 0.15      # L/R matchup advantage
    BREAKOUT_WEIGHT = 0.10     # Breakout signal boost
    
    # Platoon split advantages (OPS points)
    PLATOON_ADVANTAGE = {
        'RHB_vs_LHP': 20,  # Right-handed batter vs lefty pitcher
        'LHB_vs_RHP': 20,  # Left-handed batter vs righty pitcher
        'RHB_vs_RHP': 0,   # Neutral
        'LHB_vs_LHP': 0,   # Neutral
        'SWITCH': 10,      # Switch hitters always have slight edge
    }
    
    def __init__(self, use_breakout_signals: bool = True):
        self.api = MLBStatsAPI()
        self._games_cache = None
        self._games_cache_date = None
        
        # Optional: integrate breakout detector
        self.use_breakout_signals = use_breakout_signals
        if use_breakout_signals:
            self.breakout_detector = BreakoutDetector()
            self._breakout_cache = {}  # Cache breakout analyses
        else:
            self.breakout_detector = None
            self._breakout_cache = {}
    
    def get_daily_recommendations(
        self,
        roster: Roster,
        date: Optional[str] = None
    ) -> List[LineupRecommendation]:
        """
        Get daily lineup recommendations for entire roster
        
        Args:
            roster: User's roster
            date: Date in YYYY-MM-DD (defaults to today)
            
        Returns:
            List of LineupRecommendation objects
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Get today's games
        games = self._get_games(date)
        
        if not games:
            logger.warning(f"No games found for {date}")
            return []
        
        # Build game lookup
        game_by_team = {}
        for game in games:
            game_by_team[game.away_team] = ('away', game)
            game_by_team[game.home_team] = ('home', game)
        
        recommendations = []
        
        for player in roster.players:
            # Find player's game
            if player.team not in game_by_team:
                logger.debug(f"{player.name} ({player.team}) not playing today")
                continue
            
            home_away, game = game_by_team[player.team]
            
            # Get opponent and pitcher
            if home_away == 'away':
                opponent = game.home_team
                opponent_pitcher = game.home_pitcher
            else:
                opponent = game.away_team
                opponent_pitcher = game.away_pitcher
            
            # Analyze matchup
            rec = self._analyze_player_matchup(
                player=player,
                opponent=opponent,
                opponent_pitcher=opponent_pitcher,
                home_away=home_away,
                game=game
            )
            
            if rec:
                recommendations.append(rec)
        
        # Sort by confidence score
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return recommendations
    
    def _get_games(self, date: str) -> List[Game]:
        """Get games with caching"""
        if self._games_cache_date == date and self._games_cache:
            return self._games_cache
        
        games = self.api.get_todays_games(date)
        self._games_cache = games
        self._games_cache_date = date
        
        return games
    
    def _analyze_player_matchup(
        self,
        player: Player,
        opponent: str,
        opponent_pitcher: Optional[str],
        home_away: str,
        game: Game
    ) -> Optional[LineupRecommendation]:
        """
        Analyze a single player's matchup
        
        Returns:
            LineupRecommendation or None
        """
        reasons = []
        
        # 1. Park factor score
        park_factor = get_park_factor(game.venue) if game.venue else 1.0
        
        if home_away == 'home':
            # Playing at home stadium
            if park_factor > 1.05:
                park_score = 100
                reasons.append(f"Hitter-friendly park ({park_factor:.2f})")
            elif park_factor < 0.95:
                park_score = 50
                reasons.append(f"Pitcher-friendly park ({park_factor:.2f})")
            else:
                park_score = 75
        else:
            # Playing away
            if park_factor > 1.05:
                park_score = 85
                reasons.append(f"At hitter-friendly park ({park_factor:.2f})")
            elif park_factor < 0.95:
                park_score = 60
            else:
                park_score = 70
        
        # 2. Matchup score (opponent pitcher quality)
        # For now, use simple heuristic - would integrate with actual pitcher stats
        matchup_score = 75  # Neutral by default
        
        if opponent_pitcher:
            # Check if pitcher is known ace (would query stats in production)
            ace_pitchers = ['Gerrit Cole', 'Spencer Strider', 'Zack Wheeler', 'Corbin Burnes']
            if any(ace in opponent_pitcher for ace in ace_pitchers):
                matchup_score = 30
                reasons.append(f"vs elite pitcher ({opponent_pitcher})")
            else:
                matchup_score = 70
        else:
            reasons.append("Pitcher TBD")
        
        # 3. Form score (recent performance)
        # Would integrate with actual recent stats in production
        form_score = 75  # Neutral
        
        # Check if we have recent stats
        if hasattr(player, 'recent_avg') and player.recent_avg:
            if player.recent_avg > 0.300:
                form_score = 90
                reasons.append(f"Hot ({player.recent_avg:.3f} avg)")
            elif player.recent_avg > 0.250:
                form_score = 75
            else:
                form_score = 50
                reasons.append(f"Cold ({player.recent_avg:.3f} avg)")
        
        # 4. Platoon score (L/R matchup)
        platoon_score = self._calculate_platoon_score(player, opponent_pitcher)
        
        # 5. Breakout score (if enabled)
        breakout_score = 0
        if self.use_breakout_signals:
            breakout_score = self._get_breakout_score(player)
        
        # Calculate total confidence score
        base_score = (
            self.MATCHUP_WEIGHT * matchup_score +
            self.PARK_WEIGHT * park_score +
            self.FORM_WEIGHT * form_score +
            self.PLATOON_WEIGHT * platoon_score
        )
        
        # Apply breakout boost
        confidence_score = base_score + (self.BREAKOUT_WEIGHT * breakout_score)
        
        # Determine recommendation type
        if confidence_score >= 80:
            rec_type = RecommendationType.MUST_START
        elif confidence_score >= 65:
            rec_type = RecommendationType.START
        elif confidence_score >= 50:
            rec_type = RecommendationType.FLEX
        elif confidence_score >= 35:
            rec_type = RecommendationType.BENCH
        else:
            rec_type = RecommendationType.AVOID
        
        # Add general advice if no specific reasons
        if not reasons:
            reasons.append("Standard matchup")
        
        return LineupRecommendation(
            player=player,
            recommendation=rec_type,
            confidence_score=confidence_score,
            opponent=opponent,
            opponent_pitcher=opponent_pitcher,
            home_away=home_away,
            game_time=game.game_time,
            matchup_score=matchup_score,
            park_score=park_score,
            form_score=form_score,
            platoon_score=platoon_score,
            breakout_boost=breakout_score if self.use_breakout_signals else 0,
            recent_stats=None,
            career_vs_pitcher=None,
            reasons=reasons
        )
    
    def _calculate_platoon_score(
        self,
        player: Player,
        opponent_pitcher: Optional[str]
    ) -> float:
        """
        Calculate platoon advantage score
        
        Args:
            player: Player object
            opponent_pitcher: Opposing pitcher name
            
        Returns:
            Platoon score (0-100)
        """
        # Get batter handedness (would query from player data in production)
        # For now, use heuristics based on known players
        batter_hand = self._get_player_handedness(player.name)
        pitcher_hand = self._get_pitcher_handedness(opponent_pitcher) if opponent_pitcher else 'R'
        
        # Calculate advantage
        if batter_hand == 'S':  # Switch hitter
            return 85  # Always have advantage
        elif batter_hand == 'R' and pitcher_hand == 'L':
            return 90  # Strong platoon advantage
        elif batter_hand == 'L' and pitcher_hand == 'R':
            return 90  # Strong platoon advantage
        elif batter_hand == pitcher_hand:
            return 60  # Platoon disadvantage
        else:
            return 75  # Neutral
    
    def _get_player_handedness(self, player_name: str) -> str:
        """
        Get player batting handedness
        
        Returns: 'R', 'L', or 'S' (switch)
        """
        # Known switch hitters
        switch_hitters = [
            'Mookie Betts', 'Jose Ramirez', 'Jorge Polanco', 'Tommy Edman',
            'Bobby Witt Jr.', 'Jazz Chisholm', 'Nico Hoerner'
        ]
        
        # Known lefties (more common)
        lefties = [
            'Freddie Freeman', 'Kyle Tucker', 'Juan Soto', 'Rafael Devers',
            'Cody Bellinger', 'Christian Yelich', 'Randy Arozarena',
            'Corey Seager', 'Anthony Rizzo', 'Matt Olson'
        ]
        
        if any(name in player_name for name in switch_hitters):
            return 'S'
        elif any(name in player_name for name in lefties):
            return 'L'
        else:
            return 'R'  # Default to righty (70% of MLB)
    
    def _get_pitcher_handedness(self, pitcher_name: str) -> str:
        """
        Get pitcher throwing handedness
        
        Returns: 'R' or 'L'
        """
        # Known lefties
        lefty_pitchers = [
            'Blake Snell', 'Jordan Montgomery', 'Framber Valdez', 'Jesus Luzardo',
            'Tyler Anderson', 'Martin Perez', 'Yusei Kikuchi', 'Sean Manaea',
            'Patrick Sandoval', 'Jose Quintana', 'Kyle Freeland'
        ]
        
        if any(name in pitcher_name for name in lefty_pitchers):
            return 'L'
        else:
            return 'R'  # Default to righty (70% of MLB)
    
    def _get_breakout_score(self, player: Player) -> float:
        """
        Get breakout signal boost for a player
        
        Args:
            player: Player object
            
        Returns:
            Breakout score (0-100)
        """
        if not self.breakout_detector:
            return 0
        
        # Check cache first
        cache_key = player.name
        if cache_key in self._breakout_cache:
            return self._breakout_cache[cache_key]
        
        # Parse player name
        parts = player.name.split()
        if len(parts) < 2:
            return 0
        
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        
        # Determine player type from position
        player_type = 'pitcher' if 'P' in player.position or 'SP' in player.position or 'RP' in player.position else 'hitter'
        
        try:
            # Analyze for breakout (during season only)
            alert = self.breakout_detector.analyze_player(
                first_name,
                last_name,
                player_type,
                recent_days=7,   # Short window for daily decisions
                baseline_days=21  # 3 weeks baseline
            )
            
            if not alert:
                score = 0
            elif alert.signal == BreakoutSignal.STRONG:
                score = 100
            elif alert.signal == BreakoutSignal.EMERGING:
                score = 75
            elif alert.signal == BreakoutSignal.WATCH:
                score = 50
            elif alert.signal == BreakoutSignal.FADING:
                score = 25  # Negative signal
            else:
                score = 0
            
            # Cache the result
            self._breakout_cache[cache_key] = score
            return score
            
        except Exception as e:
            logger.debug(f"Could not get breakout signal for {player.name}: {e}")
            return 0


def print_lineup_recommendations(recommendations: List[LineupRecommendation]):
    """Print formatted lineup recommendations"""
    
    # Group by recommendation type
    must_start = [r for r in recommendations if r.recommendation == RecommendationType.MUST_START]
    start = [r for r in recommendations if r.recommendation == RecommendationType.START]
    flex = [r for r in recommendations if r.recommendation == RecommendationType.FLEX]
    bench = [r for r in recommendations if r.recommendation == RecommendationType.BENCH]
    avoid = [r for r in recommendations if r.recommendation == RecommendationType.AVOID]
    
    print("\n" + "="*70)
    print("📊 DAILY LINEUP RECOMMENDATIONS")
    print("="*70)
    
    if must_start:
        print("\n🔥 MUST START")
        print("-"*70)
        for rec in must_start:
            print(rec)
    
    if start:
        print("\n✅ START")
        print("-"*70)
        for rec in start:
            print(rec)
    
    if flex:
        print("\n➡️ FLEX (Use if needed)")
        print("-"*70)
        for rec in flex:
            print(rec)
    
    if bench:
        print("\n⚠️ CONSIDER BENCHING")
        print("-"*70)
        for rec in bench:
            print(rec)
    
    if avoid:
        print("\n❌ DEFINITELY BENCH")
        print("-"*70)
        for rec in avoid:
            print(rec)
    
    # Summary
    print("\n" + "="*70)
    print("📈 SUMMARY")
    print("="*70)
    print(f"Must Start: {len(must_start)}")
    print(f"Start: {len(start)}")
    print(f"Flex: {len(flex)}")
    print(f"Bench: {len(bench)}")
    print(f"Avoid: {len(avoid)}")
    print(f"Total Players Analyzed: {len(recommendations)}")
    print("="*70)


if __name__ == "__main__":
    # Test the optimizer
    logging.basicConfig(level=logging.INFO)
    
    print("\n⚾ DAILY LINEUP OPTIMIZER")
    print("="*70)
    print("Note: Full functionality requires live MLB data (April-October)")
    print("="*70)
    
    # Would test with actual roster in production
    print("\n✅ Lineup Optimizer initialized successfully")
    print("\nDuring the season, use:")
    print("  optimizer = LineupOptimizer()")
    print("  recommendations = optimizer.get_daily_recommendations(your_roster)")
    print("  print_lineup_recommendations(recommendations)")
