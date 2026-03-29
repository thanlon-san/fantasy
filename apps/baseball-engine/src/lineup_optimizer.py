#!/usr/bin/env python3
"""
Daily Lineup Optimizer
Stat-backed daily roster recommendations based on matchups, park factors, and recent performance
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

from .daily_matchups import MLBStatsAPI, Game, PlayerMatchup, get_park_factor
from .models import Player, Roster
from .breakout_detector import BreakoutDetector, BreakoutSignal
from .cache_manager import get_cache
from .league_settings import load_league_settings
from .adp_fetcher import ADPFetcher
from .advanced_analytics import AdvancedAnalytics
from .injury_tracker import InjuryTracker
from .odds_fetcher import OddsFetcher
from .catcher_framing import CatcherFraming

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
    
    # Supporting data (non-defaults must come before defaults)
    recent_stats: Optional[Dict]
    career_vs_pitcher: Optional[Dict]
    
    # Default fields (must come last)
    breakout_boost: float = 0
    vegas_total: Optional[float] = None
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
    
    # Default scoring weights (can be overridden by config)
    DEFAULT_WEIGHTS = {
        'matchup': 0.25,
        'park': 0.15,
        'form': 0.25,
        'platoon': 0.12,
        'breakout': 0.08,
        'vegas': 0.15,
    }
    
    # Platoon split advantages (OPS points)
    PLATOON_ADVANTAGE = {
        'RHB_vs_LHP': 20,  # Right-handed batter vs lefty pitcher
        'LHB_vs_RHP': 20,  # Left-handed batter vs righty pitcher
        'RHB_vs_RHP': 0,   # Neutral
        'LHB_vs_LHP': 0,   # Neutral
        'SWITCH': 10,      # Switch hitters always have slight edge
    }
    
    # Pitcher ADP thresholds (pitchers have different ADP ranges than hitters)
    PITCHER_ADP_THRESHOLDS = {
        'elite': 50,      # Top-50 pitcher (aces, high-K guys)
        'good': 150,      # Solid starter (consistent, reliable)
        'average': 250,   # Back-end rotation (matchup dependent)
        'streamer': 400   # Waiver wire / spot start
    }
    
    def __init__(self, use_breakout_signals: bool = True):
        self.api = MLBStatsAPI()
        self.cache = get_cache()
        self.adp_fetcher = ADPFetcher()
        self._games_cache = None
        self._games_cache_date = None
        
        # Load weights from config
        try:
            settings = load_league_settings()
            weights = settings.preferences.get('lineup_weights', {})
            self.MATCHUP_WEIGHT = weights.get('matchup', self.DEFAULT_WEIGHTS['matchup'])
            self.PARK_WEIGHT = weights.get('park', self.DEFAULT_WEIGHTS['park'])
            self.FORM_WEIGHT = weights.get('form', self.DEFAULT_WEIGHTS['form'])
            self.PLATOON_WEIGHT = weights.get('platoon', self.DEFAULT_WEIGHTS['platoon'])
            self.BREAKOUT_WEIGHT = weights.get('breakout', self.DEFAULT_WEIGHTS['breakout'])
            self.VEGAS_WEIGHT = weights.get('vegas', self.DEFAULT_WEIGHTS['vegas'])
            logger.debug(f"Loaded lineup weights from config")
        except Exception as e:
            logger.debug(f"Using default weights: {e}")
            self.MATCHUP_WEIGHT = self.DEFAULT_WEIGHTS['matchup']
            self.PARK_WEIGHT = self.DEFAULT_WEIGHTS['park']
            self.FORM_WEIGHT = self.DEFAULT_WEIGHTS['form']
            self.PLATOON_WEIGHT = self.DEFAULT_WEIGHTS['platoon']
            self.BREAKOUT_WEIGHT = self.DEFAULT_WEIGHTS['breakout']
            self.VEGAS_WEIGHT = self.DEFAULT_WEIGHTS['vegas']
        
        # Optional: integrate breakout detector
        self.use_breakout_signals = use_breakout_signals
        if use_breakout_signals:
            self.breakout_detector = BreakoutDetector()
            self._breakout_cache = {}  # Cache analyses
        else:
            self.breakout_detector = None
            self._breakout_cache = {}
        
        # Advanced analytics (umpire zone, xBA regression, batted ball × park, fatigue)
        try:
            self.advanced = AdvancedAnalytics()
        except Exception:
            self.advanced = None
        
        # Injury awareness — filter out IL / DTD players
        try:
            self.injury_tracker = InjuryTracker()
            self.injury_tracker.load()
        except Exception:
            self.injury_tracker = None

        # Vegas implied run totals — boost/penalize based on game environment
        try:
            self.odds_fetcher = OddsFetcher()
            self.odds_fetcher.load()
        except Exception:
            self.odds_fetcher = None
        
        # Catcher framing — boost/penalize pitcher matchups based on catcher quality
        try:
            self.catcher_framing = CatcherFraming()
            self.catcher_framing.load()
        except Exception:
            self.catcher_framing = None

        # Static handedness lookup (primary source — reliable even when API is down)
        self._handedness_static: Dict[str, Dict] = {}
        try:
            handedness_path = Path(__file__).parent.parent / "data" / "player_handedness.json"
            if handedness_path.exists():
                with open(handedness_path) as f:
                    self._handedness_static = json.load(f)
                logger.debug(f"Loaded static handedness for {len(self._handedness_static)} players")
        except Exception:
            pass
    
    def get_daily_recommendations(
        self,
        roster: Roster,
        date: Optional[str] = None,
        show_all_players: bool = True
    ) -> List[LineupRecommendation]:
        """
        Get daily lineup recommendations for entire roster
        
        Args:
            roster: User's roster
            date: Date in YYYY-MM-DD (defaults to today)
            show_all_players: If True, include players not playing today
            
        Returns:
            List of LineupRecommendation objects
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Get today's games
        games = self._get_games(date)
        
        # Build game lookup - support multiple games per team (double-headers)
        game_by_team = {}  # team -> list of (home_away, game) tuples
        if games:
            for game in games:
                if game.away_team not in game_by_team:
                    game_by_team[game.away_team] = []
                game_by_team[game.away_team].append(('away', game))
                
                if game.home_team not in game_by_team:
                    game_by_team[game.home_team] = []
                game_by_team[game.home_team].append(('home', game))
        
        recommendations = []
        
        for player in roster.players:
            # Check if player has a game
            if player.team not in game_by_team:
                if show_all_players:
                    # Create a "not playing" recommendation
                    rec = LineupRecommendation(
                        player=player,
                        recommendation=RecommendationType.BENCH,
                        confidence_score=0,
                        opponent="No game",
                        opponent_pitcher=None,
                        home_away="",
                        game_time=None,
                        matchup_score=0,
                        park_score=0,
                        form_score=0,
                        platoon_score=0,
                        breakout_boost=0,
                        recent_stats=None,
                        career_vs_pitcher=None,
                        reasons=["Not playing today"]
                    )
                    recommendations.append(rec)
                else:
                    logger.debug(f"{player.name} ({player.team}) not playing today")
                continue
            
            # Get all games for this team (handles double-headers)
            team_games = game_by_team[player.team]
            
            # Analyze each game (for double-headers)
            for game_num, (home_away, game) in enumerate(team_games, 1):
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
                    # Add game number label for double-headers
                    if len(team_games) > 1:
                        rec.reasons.insert(0, f"Game {game_num} of {len(team_games)}")
                    recommendations.append(rec)
        
        # Sort by confidence score (players not playing go to bottom)
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return recommendations
    
    def _get_games(self, date: str) -> List[Game]:
        """Get games with persistent caching"""
        # Check in-memory cache first
        if self._games_cache_date == date and self._games_cache:
            return self._games_cache
        
        # Check persistent cache (4 hour TTL - lineups can change)
        cache_key = f"games_{date}"
        cached_games = self.cache.get(cache_key, max_age_hours=4)
        if cached_games:
            self._games_cache = cached_games
            self._games_cache_date = date
            return cached_games
        
        # Fetch from API
        games = self.api.get_todays_games(date)
        
        # Save to both caches
        self._games_cache = games
        self._games_cache_date = date
        self.cache.set(cache_key, games)
        
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
        # Short-circuit: injured players should not be recommended
        if self.injury_tracker:
            injury = self.injury_tracker.get_injury(player.name)
            if injury:
                badge = injury.badge
                return LineupRecommendation(
                    player=player,
                    recommendation=RecommendationType.AVOID,
                    confidence_score=0,
                    opponent=opponent,
                    opponent_pitcher=opponent_pitcher,
                    home_away=home_away,
                    game_time=game.game_time,
                    matchup_score=0, park_score=0, form_score=0, platoon_score=0,
                    recent_stats=None, career_vs_pitcher=None,
                    breakout_boost=0,
                    reasons=[f"{badge}: {injury.injury}" if injury.injury else badge],
                )

        reasons = []
        
        # 1. Park factor score (with weather adjustment)
        base_park_factor = get_park_factor(game.venue) if game.venue else 1.0
        park_factor = self._adjust_park_for_weather(base_park_factor, game.weather)
        
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
        
        # Add weather-specific reasons
        if game.weather:
            weather_reasons = self._get_weather_reasons(game.weather)
            reasons.extend(weather_reasons)
        
        # 2. Matchup score (opponent pitcher quality)
        matchup_score = self._get_pitcher_matchup_score(opponent_pitcher, opponent)
        if matchup_score < 50 and opponent_pitcher:
            reasons.append(f"vs tough pitcher ({opponent_pitcher})")
        elif matchup_score > 80 and opponent_pitcher:
            reasons.append(f"vs weak pitcher ({opponent_pitcher})")
        elif not opponent_pitcher:
            reasons.append("Pitcher TBD")
        
        # 3. Form score (recent performance from Statcast/MLB API)
        form_score, has_recent_data = self._get_recent_form(player)
        if not has_recent_data:
            reasons.append("Limited recent data")
        elif form_score > 80:
            reasons.append("Hot streak")
        elif form_score < 60:
            reasons.append("Cold streak")
        
        # 4. Platoon score (L/R matchup)
        platoon_score = self._calculate_platoon_score(player, opponent_pitcher)
        
        # 5. Breakout score (if enabled)
        breakout_score = 0
        if self.use_breakout_signals:
            breakout_score = self._get_breakout_score(player)
        
        # 6. Historical matchup boost/penalty (batter vs pitcher history)
        history_adjustment = self._get_matchup_history_adjustment(player, opponent_pitcher)
        if history_adjustment > 5:
            reasons.append(f"Career success vs this pitcher")
        elif history_adjustment < -5:
            reasons.append(f"Career struggles vs this pitcher")
        
        # 7. Advanced analytics adjustments (gated — skipped when data unavailable)
        advanced_adjustment = 0
        if self.advanced:
            advanced_adjustment = self._get_advanced_adjustments(
                player, game, park_factor, reasons
            )
        
        # 8. Vegas implied run total adjustment
        vegas_score = 75  # neutral default
        vegas_total = None
        if self.odds_fetcher:
            vegas_score, vegas_total = self._get_vegas_score(player, game, reasons)

        # 9. Catcher framing adjustment (pitchers benefit from elite framing catchers)
        framing_adjustment = 0.0
        if self.catcher_framing:
            is_pitcher = any(p in player.position for p in ['SP', 'RP', 'P'])
            if is_pitcher:
                adj, framing_reason = self.catcher_framing.get_my_pitcher_boost(player.team)
                if adj and framing_reason:
                    framing_adjustment = adj
                    reasons.append(framing_reason)

        # Calculate total confidence score
        base_score = (
            self.MATCHUP_WEIGHT * matchup_score +
            self.PARK_WEIGHT * park_score +
            self.FORM_WEIGHT * form_score +
            self.PLATOON_WEIGHT * platoon_score +
            self.VEGAS_WEIGHT * vegas_score
        )
        
        # Apply breakout boost
        confidence_score = base_score + (self.BREAKOUT_WEIGHT * breakout_score)
        
        # Apply historical matchup adjustment (±5-10 points for significant history)
        confidence_score += history_adjustment
        
        # Apply advanced analytics adjustment (umpire, xBA regression, park×batted ball, fatigue)
        confidence_score += advanced_adjustment
        
        # Apply catcher framing adjustment
        confidence_score += framing_adjustment
        
        # Slightly reduce confidence when no recent data available
        if not has_recent_data:
            confidence_score *= 0.95
        
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
            vegas_total=vegas_total,
            recent_stats=None,
            career_vs_pitcher=None,
            reasons=reasons
        )
    
    def _get_advanced_adjustments(
        self,
        player: Player,
        game: Game,
        park_factor: float,
        reasons: List[str],
    ) -> float:
        """Aggregate adjustments from AdvancedAnalytics (umpire, xBA, park×batted ball, fatigue)."""
        total = 0.0
        try:
            # Umpire strike zone adjustment
            umpire_name = game.weather.get("umpire") if game.weather else None
            if umpire_name:
                adj, reason = self.advanced.get_umpire_adjustment(umpire_name, "hitter")
                if adj and reason:
                    total += adj
                    reasons.append(reason)

            # xBA regression detection
            if self.breakout_detector:
                parts = player.name.split()
                if len(parts) >= 2:
                    pid = self.breakout_detector.statcast.get_player_id(parts[0], " ".join(parts[1:]))
                    if pid:
                        cache_key = f"adv_xba_{player.name}"
                        cached = self.cache.get(cache_key, max_age_hours=12)
                        if cached is not None:
                            adj_val, adj_reason = cached
                        else:
                            data = self.breakout_detector.statcast.get_hitter_stats(pid)
                            if data is not None and not data.empty:
                                metrics = self.breakout_detector.statcast.calculate_hitter_metrics(data)
                                xba = metrics.get("xBA")
                                if xba and "events" in data.columns:
                                    pas = data["events"].notna().sum()
                                    hits = data["events"].isin(["single", "double", "triple", "home_run"]).sum()
                                    actual_avg = hits / pas if pas > 0 else 0
                                    adj_val, adj_reason = self.advanced.calculate_expected_stats_boost(actual_avg, xba)
                                else:
                                    adj_val, adj_reason = 0, None

                                # Batted ball × park factor
                                bb_adj, bb_reason = self.advanced.analyze_batted_ball_profile(
                                    metrics.get("ground_ball_percent"),
                                    metrics.get("fly_ball_percent"),
                                    park_factor,
                                )
                                adj_val += bb_adj
                                if bb_reason:
                                    adj_reason = f"{adj_reason}; {bb_reason}" if adj_reason else bb_reason
                            else:
                                adj_val, adj_reason = 0, None
                            self.cache.set(cache_key, (adj_val, adj_reason))

                        if adj_val and adj_reason:
                            total += adj_val
                            for r in adj_reason.split("; "):
                                reasons.append(r)
        except Exception as e:
            logger.debug(f"Advanced analytics skipped for {player.name}: {e}")
        return total

    def _get_vegas_score(
        self,
        player: Player,
        game: Game,
        reasons: List[str],
    ) -> tuple:
        """Score based on Vegas implied run total for the game.
        Returns (score 0-100, game_total or None)."""
        if not self.odds_fetcher:
            return 75, None

        odds = self.odds_fetcher.get_game_odds(player.team)
        if not odds or odds.total is None:
            return 75, None

        total = odds.total
        is_pitcher = any(p in player.position for p in ['SP', 'RP', 'P'])

        if is_pitcher:
            # Pitchers benefit from low-scoring environments
            if total <= 7.0:
                score = 95
                reasons.append(f"Vegas total {total:.1f} — pitcher-friendly game")
            elif total <= 8.0:
                score = 80
            elif total <= 9.0:
                score = 65
            elif total <= 10.0:
                score = 45
                reasons.append(f"Vegas total {total:.1f} — risky for pitchers")
            else:
                score = 25
                reasons.append(f"Vegas total {total:.1f} — avoid pitching in shootout")
        else:
            # Hitters benefit from high-scoring environments
            if total >= 10.0:
                score = 95
                reasons.append(f"Vegas total {total:.1f} — projected slugfest")
            elif total >= 9.0:
                score = 85
                reasons.append(f"Vegas total {total:.1f} — hitter-friendly game")
            elif total >= 8.0:
                score = 75
            elif total >= 7.0:
                score = 60
            else:
                score = 40
                reasons.append(f"Vegas total {total:.1f} — low-scoring game")

        return score, total

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
        Get player batting handedness.
        Priority: static JSON file → persistent cache → MLB API → default 'R'.
        
        Returns: 'R', 'L', or 'S' (switch)
        """
        # 1. Static file (instant, reliable)
        static = self._handedness_static.get(player_name)
        if static and static.get("bat"):
            return static["bat"]

        # 2. Persistent cache (30-day TTL)
        cache_key = f"handedness_bat_{player_name}"
        cached = self.cache.get(cache_key, max_age_hours=720)
        if cached:
            return cached
        
        # 3. MLB API (fallback for players not in the static file)
        try:
            parts = player_name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
                if self.breakout_detector:
                    player_id = self.breakout_detector.statcast.get_player_id(first_name, last_name)
                    if player_id:
                        bat_side, _ = self.api.get_player_handedness(player_id)
                        if bat_side:
                            self.cache.set(cache_key, bat_side)
                            return bat_side
        except Exception as e:
            logger.debug(f"Could not get handedness for {player_name}: {e}")
        
        default = 'R'
        self.cache.set(cache_key, default)
        return default
    
    def _get_pitcher_handedness(self, pitcher_name: str) -> str:
        """
        Get pitcher throwing handedness.
        Priority: static JSON file → persistent cache → MLB API → default 'R'.
        
        Returns: 'R' or 'L'
        """
        # 1. Static file
        static = self._handedness_static.get(pitcher_name)
        if static and static.get("pitch"):
            return static["pitch"]

        # 2. Persistent cache (30-day TTL)
        cache_key = f"handedness_pitch_{pitcher_name}"
        cached = self.cache.get(cache_key, max_age_hours=720)
        if cached:
            return cached
        
        # 3. MLB API fallback
        try:
            parts = pitcher_name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
                if self.breakout_detector:
                    player_id = self.breakout_detector.statcast.get_player_id(first_name, last_name)
                    if player_id:
                        _, pitch_hand = self.api.get_player_handedness(player_id)
                        if pitch_hand:
                            self.cache.set(cache_key, pitch_hand)
                            return pitch_hand
        except Exception as e:
            logger.debug(f"Could not get handedness for {pitcher_name}: {e}")
        
        default = 'R'
        self.cache.set(cache_key, default)
        return default
    
    def _adjust_park_for_weather(self, base_factor: float, weather: Optional[Dict]) -> float:
        """
        Adjust park factor based on weather conditions
        
        Args:
            base_factor: Base park factor
            weather: Weather dict from MLB API
            
        Returns:
            Adjusted park factor
        """
        if not weather:
            return base_factor
        
        adjusted_factor = base_factor
        
        # Wind direction and speed
        wind = weather.get('wind', '')
        if wind:
            wind_lower = wind.lower()
            # Wind blowing out (to outfield) helps hitters
            if 'out' in wind_lower and ('mph' in wind_lower or 'kt' in wind_lower):
                # Extract wind speed if possible
                try:
                    import re
                    speed_match = re.search(r'(\d+)', wind_lower)
                    if speed_match:
                        speed = int(speed_match.group(1))
                        if speed >= 15:  # Strong wind
                            adjusted_factor *= 1.10  # +10% for strong wind out
                        elif speed >= 10:  # Moderate wind
                            adjusted_factor *= 1.05  # +5% for moderate wind out
                except:
                    adjusted_factor *= 1.05  # Default boost for wind out
            
            # Wind blowing in (from outfield) helps pitchers
            elif 'in' in wind_lower and ('mph' in wind_lower or 'kt' in wind_lower):
                try:
                    import re
                    speed_match = re.search(r'(\d+)', wind_lower)
                    if speed_match:
                        speed = int(speed_match.group(1))
                        if speed >= 15:  # Strong wind
                            adjusted_factor *= 0.90  # -10% for strong wind in
                        elif speed >= 10:  # Moderate wind
                            adjusted_factor *= 0.95  # -5% for moderate wind in
                except:
                    adjusted_factor *= 0.95  # Default reduction for wind in
        
        # Temperature (cold weather suppresses power)
        temp = weather.get('temp', '')
        if temp:
            try:
                # Extract temperature number
                import re
                temp_match = re.search(r'(\d+)', temp)
                if temp_match:
                    temp_num = int(temp_match.group(1))
                    if temp_num < 50:  # Cold weather
                        adjusted_factor *= 0.95  # -5% for cold weather
                    elif temp_num > 85:  # Hot weather (ball travels better)
                        adjusted_factor *= 1.03  # +3% for hot weather
            except:
                pass
        
        return adjusted_factor
    
    def _get_weather_reasons(self, weather: Optional[Dict]) -> List[str]:
        """Generate weather-based reasons for lineup decisions"""
        reasons = []
        
        if not weather:
            return reasons
        
        # Wind
        wind = weather.get('wind', '')
        if wind:
            wind_lower = wind.lower()
            if 'out' in wind_lower:
                try:
                    import re
                    speed_match = re.search(r'(\d+)', wind_lower)
                    if speed_match and int(speed_match.group(1)) >= 10:
                        reasons.append("Wind helping hitters")
                except:
                    pass
            elif 'in' in wind_lower:
                try:
                    import re
                    speed_match = re.search(r'(\d+)', wind_lower)
                    if speed_match and int(speed_match.group(1)) >= 10:
                        reasons.append("Wind suppressing power")
                except:
                    pass
        
        # Temperature
        temp = weather.get('temp', '')
        if temp:
            try:
                import re
                temp_match = re.search(r'(\d+)', temp)
                if temp_match:
                    temp_num = int(temp_match.group(1))
                    if temp_num < 50:
                        reasons.append("Cold weather suppressing power")
            except:
                pass
        
        return reasons
    
    def _get_matchup_history_adjustment(self, player: Player, opponent_pitcher: Optional[str]) -> float:
        """
        Adjust confidence based on historical batter vs pitcher performance
        
        Args:
            player: Batter player object
            opponent_pitcher: Opposing pitcher name
            
        Returns:
            Adjustment value (-10 to +10 points)
        """
        if not opponent_pitcher or not self.breakout_detector:
            return 0
        
        # Check cache
        cache_key = f"history_{player.name}_{opponent_pitcher}"
        cached = self.cache.get(cache_key, max_age_hours=168)  # Cache for 1 week
        if cached:
            return cached
        
        try:
            # Get player IDs
            batter_parts = player.name.split()
            pitcher_parts = opponent_pitcher.split()
            
            if len(batter_parts) < 2 or len(pitcher_parts) < 2:
                return 0
            
            batter_id = self.breakout_detector.statcast.get_player_id(
                batter_parts[0], ' '.join(batter_parts[1:])
            )
            pitcher_id = self.breakout_detector.statcast.get_player_id(
                pitcher_parts[0], ' '.join(pitcher_parts[1:])
            )
            
            if not batter_id or not pitcher_id:
                self.cache.set(cache_key, 0)
                return 0
            
            # Get historical matchup stats
            history = self.api.get_batter_vs_pitcher_stats(batter_id, pitcher_id)
            
            if not history or history['abs'] < 10:  # Need minimum 10 AB for significance
                self.cache.set(cache_key, 0)
                return 0
            
            # Calculate adjustment based on historical performance
            ops = history['ops']
            abs_count = history['abs']
            
            # Strong historical success (OPS > 1.000 with 15+ AB)
            if ops >= 1.000 and abs_count >= 15:
                adjustment = 10
                logger.debug(f"{player.name} owns {opponent_pitcher}: {ops:.3f} OPS in {abs_count} AB")
            # Good historical success (OPS > 0.850 with 12+ AB)
            elif ops >= 0.850 and abs_count >= 12:
                adjustment = 7
            # Moderate success (OPS > 0.750 with 10+ AB)
            elif ops >= 0.750 and abs_count >= 10:
                adjustment = 3
            # Historical struggles (OPS < 0.550 with 12+ AB)
            elif ops < 0.550 and abs_count >= 12:
                adjustment = -10
                logger.debug(f"{player.name} struggles vs {opponent_pitcher}: {ops:.3f} OPS in {abs_count} AB")
            # Poor performance (OPS < 0.650 with 10+ AB)
            elif ops < 0.650 and abs_count >= 10:
                adjustment = -5
            else:
                adjustment = 0
            
            self.cache.set(cache_key, adjustment)
            return adjustment
            
        except Exception as e:
            logger.debug(f"Could not get matchup history for {player.name} vs {opponent_pitcher}: {e}")
            self.cache.set(cache_key, 0)
            return 0
    
    def _get_pitcher_matchup_score(self, pitcher_name: Optional[str], team: str) -> float:
        """
        Score matchup difficulty using live FIP + K-BB% + CSW%.
        Falls back to ADP only when no recent stats exist (early season / off-season).

        Returns 0-100 (lower = tougher matchup for hitters).
        """
        if not pitcher_name:
            return 75  # Neutral for TBD

        date_key = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"pitcher_fip_{pitcher_name}_{date_key}"
        cached = self.cache.get(cache_key, max_age_hours=12)
        if cached is not None:
            return cached

        score = None  # will be set by FIP path or ADP fallback

        # --- Primary: FIP + K-BB% + CSW% from Statcast ---
        if self.breakout_detector:
            try:
                parts = pitcher_name.split()
                if len(parts) >= 2:
                    pid = self.breakout_detector.statcast.get_player_id(
                        parts[0], " ".join(parts[1:])
                    )
                    if pid:
                        fip_data = self.breakout_detector.statcast.calculate_pitcher_fip(pid, days_back=30)
                        if fip_data:
                            fip = fip_data["fip"]
                            k_bb = fip_data["k_bb_pct"]
                            csw = fip_data["csw_pct"]

                            # FIP component (60% weight) — lower FIP = tougher
                            if fip <= 2.50:
                                fip_score = 10
                            elif fip <= 3.20:
                                fip_score = 25
                            elif fip <= 3.80:
                                fip_score = 45
                            elif fip <= 4.50:
                                fip_score = 65
                            elif fip <= 5.50:
                                fip_score = 80
                            else:
                                fip_score = 92

                            # K-BB% component (25% weight) — higher = tougher
                            if k_bb >= 20:
                                kbb_score = 10
                            elif k_bb >= 15:
                                kbb_score = 25
                            elif k_bb >= 10:
                                kbb_score = 50
                            elif k_bb >= 5:
                                kbb_score = 70
                            else:
                                kbb_score = 90

                            # CSW% component (15% weight) — higher = tougher
                            if csw >= 32:
                                csw_score = 10
                            elif csw >= 30:
                                csw_score = 25
                            elif csw >= 27:
                                csw_score = 50
                            elif csw >= 24:
                                csw_score = 70
                            else:
                                csw_score = 90

                            score = 0.60 * fip_score + 0.25 * kbb_score + 0.15 * csw_score
                            logger.debug(
                                f"FIP matchup for {pitcher_name}: "
                                f"FIP={fip} K-BB%={k_bb} CSW%={csw} → score={score:.0f}"
                            )
            except Exception as e:
                logger.debug(f"FIP calc failed for {pitcher_name}: {e}")

        # --- Fallback: ADP (pre-season / insufficient data) ---
        if score is None:
            score = 75
            pitcher_adp = self.adp_fetcher.get_player_adp(pitcher_name)
            if pitcher_adp:
                if pitcher_adp < self.PITCHER_ADP_THRESHOLDS['elite']:
                    score = 25
                elif pitcher_adp < self.PITCHER_ADP_THRESHOLDS['good']:
                    score = 45
                elif pitcher_adp < self.PITCHER_ADP_THRESHOLDS['average']:
                    score = 65
                elif pitcher_adp < self.PITCHER_ADP_THRESHOLDS['streamer']:
                    score = 80
                else:
                    score = 90

        score = max(0, min(100, score))
        self.cache.set(cache_key, score)
        return score
    
    def _get_recent_form(self, player: Player) -> Tuple[float, bool]:
        """
        Get player's recent form score (last 14 days)
        
        Returns:
            Tuple of (form_score, has_recent_data)
            - form_score: 0-100, 75 = neutral
            - has_recent_data: True if we have real data, False if defaulting
        """
        # Check persistent cache (12-hour TTL - refreshes daily)
        date_key = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"form_{player.name}_{date_key}"
        cached = self.cache.get(cache_key, max_age_hours=12)
        if cached:
            # Cached value includes both score and has_data flag
            return cached
        
        # Try to get recent stats from breakout detector's statcast client
        if not self.breakout_detector:
            result = (75, False)  # Neutral if no detector
            self.cache.set(cache_key, result)
            return result
        
        # Parse player name
        parts = player.name.split()
        if len(parts) < 2:
            result = (75, False)
            self.cache.set(cache_key, result)
            return result
        
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        
        # Determine if pitcher or hitter
        is_pitcher = any(p in player.position for p in ['SP', 'RP', 'P'])
        
        try:
            # Get player ID
            player_id = self.breakout_detector.statcast.get_player_id(first_name, last_name)
            if not player_id:
                result = (75, False)
                self.cache.set(cache_key, result)
                return result
            
            if is_pitcher:
                # For pitchers: check recent ERA, K rate
                data = self.breakout_detector.statcast.get_pitcher_stats(
                    player_id, 
                    start_date=(datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d')
                )
                if data is None or data.empty:
                    result = (75, False)
                    self.cache.set(cache_key, result)
                    return result
                
                metrics = self.breakout_detector.statcast.calculate_pitcher_metrics(data)
                
                # Score based on K% and hard hit %
                score = 75
                k_pct = metrics.get('k_percent', 20)
                hard_hit = metrics.get('hard_hit_percent', 40)
                
                if k_pct > 25:
                    score += 10
                if k_pct > 30:
                    score += 5
                if hard_hit < 35:
                    score += 10
                
                final_score = min(100, score)
                result = (final_score, True)  # Has real data
                self.cache.set(cache_key, result)
                return result
            else:
                # For hitters: check recent exit velo, hard hit%
                data = self.breakout_detector.statcast.get_hitter_stats(
                    player_id,
                    start_date=(datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d')
                )
                if data is None or data.empty:
                    result = (75, False)
                    self.cache.set(cache_key, result)
                    return result
                
                metrics = self.breakout_detector.statcast.calculate_hitter_metrics(data)
                
                # Score based on hard hit% and barrel%
                score = 75
                hard_hit = metrics.get('hard_hit_percent', 35)
                barrel = metrics.get('barrel_percent', 8)
                
                if hard_hit > 40:
                    score += 10
                if hard_hit > 50:
                    score += 5
                if barrel > 10:
                    score += 10
                
                final_score = min(100, score)
                result = (final_score, True)  # Has real data
                self.cache.set(cache_key, result)
                return result
                
        except Exception as e:
            logger.debug(f"Could not get recent form for {player.name}: {e}")
            result = (75, False)
            self.cache.set(cache_key, result)
            return result
    
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
        cache_key = f"breakout_{player.name}"
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
    
    # Separate playing vs not playing
    playing = [r for r in recommendations if r.opponent != "No game"]
    not_playing = [r for r in recommendations if r.opponent == "No game"]
    
    # Group playing by recommendation type
    must_start = [r for r in playing if r.recommendation == RecommendationType.MUST_START]
    start = [r for r in playing if r.recommendation == RecommendationType.START]
    flex = [r for r in playing if r.recommendation == RecommendationType.FLEX]
    bench = [r for r in playing if r.recommendation == RecommendationType.BENCH]
    avoid = [r for r in playing if r.recommendation == RecommendationType.AVOID]
    
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
    
    # Players not playing today
    if not_playing:
        print("\n💤 NOT PLAYING TODAY")
        print("-"*70)
        for rec in not_playing:
            print(f"   {rec.player.name} ({rec.player.position}) - {rec.player.team}")
    
    # Summary
    print("\n" + "="*70)
    print("📈 SUMMARY")
    print("="*70)
    print(f"Playing Today: {len(playing)}")
    print(f"  • Must Start: {len(must_start)}")
    print(f"  • Start: {len(start)}")
    print(f"  • Flex: {len(flex)}")
    print(f"  • Bench: {len(bench)}")
    print(f"  • Avoid: {len(avoid)}")
    print(f"Not Playing: {len(not_playing)}")
    print(f"Total Roster: {len(recommendations)}")
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
