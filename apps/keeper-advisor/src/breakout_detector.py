#!/usr/bin/env python3
"""
Breakout Detector
Identify players showing signs of breaking out based on Statcast metrics
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .statcast_client import StatcastClient

logger = logging.getLogger(__name__)


class BreakoutSignal(Enum):
    """Types of breakout signals"""
    STRONG = "STRONG"      # Multiple improving metrics, high confidence
    EMERGING = "EMERGING"  # Some positive trends
    WATCH = "WATCH"        # Early signs, monitor closely
    FADING = "FADING"      # Negative trends, sell high


@dataclass
class BreakoutAlert:
    """A breakout alert for a player"""
    
    player_name: str
    player_id: int
    player_type: str  # 'hitter' or 'pitcher'
    signal: BreakoutSignal
    confidence_score: float  # 0-100
    key_metrics: Dict[str, Tuple[float, float]]  # metric_name -> (baseline, recent)
    improving_metrics: List[str]
    declining_metrics: List[str]
    summary: str
    actionable_advice: str
    
    def __str__(self) -> str:
        return (
            f"\n{'='*70}\n"
            f"🚨 {self.signal.value} BREAKOUT ALERT: {self.player_name}\n"
            f"{'='*70}\n"
            f"Type: {self.player_type.title()}\n"
            f"Confidence: {self.confidence_score:.1f}%\n\n"
            f"📈 Improving Metrics:\n"
            + "\n".join([f"  • {m}" for m in self.improving_metrics[:5]]) + "\n\n"
            f"Summary: {self.summary}\n\n"
            f"💡 Action: {self.actionable_advice}\n"
            f"{'='*70}\n"
        )


class BreakoutDetector:
    """Detect potential breakout players using Statcast data"""
    
    # Thresholds for breakout detection (hitters)
    HITTER_BREAKOUT_THRESHOLDS = {
        'exit_velocity_avg': 1.5,        # +1.5 mph improvement
        'hard_hit_percent': 5.0,         # +5% improvement
        'barrel_percent': 3.0,           # +3% improvement
        'sweet_spot_percent': 4.0,       # +4% improvement
        'chase_rate': -3.0,              # -3% improvement (lower is better)
        'whiff_percent': -2.0,           # -2% improvement (lower is better)
        'k_percent': -3.0,               # -3% improvement (lower is better)
        'bb_percent': 2.0,               # +2% improvement
        # Expected stats (regression/progression indicators)
        'xBA': 0.020,                    # +20 points of xBA
        'xSLG': 0.040,                   # +40 points of xSLG
        'xwOBA': 0.025,                  # +25 points of xwOBA
        # Batted ball profile shifts
        'fly_ball_percent': 5.0,         # +5% more fly balls (power breakout)
        'ground_ball_percent': -5.0,     # -5% fewer ground balls (paired with FB increase)
        'line_drive_percent': 3.0,       # +3% more line drives (contact quality)
        'pull_percent': 5.0,             # +5% pull rate (power approach)
    }
    
    # Thresholds for breakout detection (pitchers)
    PITCHER_BREAKOUT_THRESHOLDS = {
        'whiff_percent': 3.0,            # +3% improvement
        'k_percent': 3.0,                # +3% improvement
        'bb_percent': -2.0,              # -2% improvement (lower is better)
        'hard_hit_percent': -5.0,        # -5% improvement (lower is better)
        'barrel_percent': -3.0,          # -3% improvement (lower is better)
        'avg_fastball_velocity': 1.0,   # +1 mph improvement
        # Pitch arsenal changes
        'fastball_usage': 5.0,           # +5% usage (pitch mix optimization)
        'breaking_usage': 5.0,           # +5% breaking ball usage
        'offspeed_usage': 5.0,           # +5% offspeed usage
        'avg_spin_rate': 100,            # +100 RPM on breaking balls
        # Expected stats
        'xBA_against': -0.020,           # -20 points of xBA against
        'xSLG_against': -0.040,          # -40 points of xSLG against
        'xwOBA_against': -0.025,         # -25 points of xwOBA against
    }
    
    # Weight of each metric (higher = more important)
    HITTER_METRIC_WEIGHTS = {
        'exit_velocity_avg': 1.5,
        'hard_hit_percent': 2.0,
        'barrel_percent': 2.5,
        'sweet_spot_percent': 1.0,
        'chase_rate': 1.5,
        'whiff_percent': 1.5,
        'k_percent': 1.0,
        'bb_percent': 1.0,
        # Expected stats (high weight - predictive of future performance)
        'xBA': 2.0,
        'xSLG': 2.5,
        'xwOBA': 2.5,
        # Batted ball profile
        'fly_ball_percent': 1.5,
        'ground_ball_percent': 1.0,
        'line_drive_percent': 1.5,
        'pull_percent': 1.0,
    }
    
    PITCHER_METRIC_WEIGHTS = {
        'whiff_percent': 2.5,
        'k_percent': 2.0,
        'bb_percent': 1.5,
        'hard_hit_percent': 2.0,
        'barrel_percent': 2.5,
        'avg_fastball_velocity': 1.5,
        # Pitch arsenal
        'fastball_usage': 1.0,
        'breaking_usage': 1.5,
        'offspeed_usage': 1.5,
        'avg_spin_rate': 1.5,
        # Expected stats
        'xBA_against': 2.0,
        'xSLG_against': 2.5,
        'xwOBA_against': 2.5,
    }
    
    def __init__(self, enable_tracking: bool = True):
        """
        Initialize breakout detector
        
        Args:
            enable_tracking: Whether to log predictions for historical tracking
        """
        self.statcast = StatcastClient()
        self.enable_tracking = enable_tracking
        
        if enable_tracking:
            try:
                from .breakout_tracker import BreakoutTracker
                self.tracker = BreakoutTracker()
            except Exception as e:
                logger.warning(f"Could not initialize breakout tracker: {e}")
                self.tracker = None
        else:
            self.tracker = None
    
    def analyze_player(
        self,
        first_name: str,
        last_name: str,
        player_type: str = 'hitter',
        recent_days: int = 14,
        baseline_days: int = 30
    ) -> Optional[BreakoutAlert]:
        """
        Analyze a player for breakout potential
        
        Args:
            first_name: Player's first name
            last_name: Player's last name
            player_type: 'hitter' or 'pitcher'
            recent_days: Days for recent sample (default: 14)
            baseline_days: Days for baseline comparison (default: 30)
            
        Returns:
            BreakoutAlert if significant trends found, else None
        """
        # Get player ID
        player_id = self.statcast.get_player_id(first_name, last_name)
        if not player_id:
            logger.warning(f"Could not find player: {first_name} {last_name}")
            return None
        
        player_name = f"{first_name} {last_name}"
        
        # Get comparative metrics (automatically uses previous season during offseason)
        try:
            recent, baseline, changes = self.statcast.compare_time_periods(
                player_id, player_type, recent_days, baseline_days,
                use_previous_season_if_offseason=True
            )
        except Exception as e:
            logger.error(f"Error comparing metrics for {player_name}: {e}")
            return None
        
        if not changes:
            logger.info(f"No data available for {player_name} (likely off-season)")
            return None

        # Require a minimum sample size in the recent window to avoid spring
        # training noise.  recent_pa / recent_bf is stored as 'pa' / 'bf' if
        # the statcast client returns it; fall back to checking recent dict size.
        recent_pa = recent.get("pa") or recent.get("bf") or len(recent)
        MIN_RECENT_PA = 30
        if recent_pa < MIN_RECENT_PA:
            logger.info(
                f"Skipping {player_name}: only {recent_pa} recent PA/BF (min {MIN_RECENT_PA})"
            )
            return None

        # Analyze changes
        thresholds = (self.HITTER_BREAKOUT_THRESHOLDS if player_type == 'hitter' 
                      else self.PITCHER_BREAKOUT_THRESHOLDS)
        weights = (self.HITTER_METRIC_WEIGHTS if player_type == 'hitter' 
                   else self.PITCHER_METRIC_WEIGHTS)
        
        improving = []
        declining = []
        confidence_points = 0
        max_points = 0
        
        key_metrics = {}
        
        for metric, change in changes.items():
            if metric not in thresholds:
                continue
            
            threshold = thresholds[metric]
            weight = weights.get(metric, 1.0)
            max_points += abs(threshold) * weight
            
            # Store for display
            key_metrics[metric] = (baseline.get(metric, 0), recent.get(metric, 0))
            
            # Check if change exceeds threshold
            if threshold > 0:  # Higher is better
                if change >= threshold:
                    improving.append(f"{metric}: {baseline.get(metric, 0):.1f} → {recent.get(metric, 0):.1f} (+{change:.1f})")
                    confidence_points += abs(change / threshold) * weight
                elif change < -threshold:
                    declining.append(f"{metric}: {baseline.get(metric, 0):.1f} → {recent.get(metric, 0):.1f} ({change:.1f})")
            else:  # Lower is better
                if change <= threshold:
                    improving.append(f"{metric}: {baseline.get(metric, 0):.1f} → {recent.get(metric, 0):.1f} ({change:.1f})")
                    confidence_points += abs(change / threshold) * weight
                elif change > -threshold:
                    declining.append(f"{metric}: {baseline.get(metric, 0):.1f} → {recent.get(metric, 0):.1f} (+{change:.1f})")
        
        # Calculate confidence score (0-100)
        confidence_score = min(100, (confidence_points / max_points * 100)) if max_points > 0 else 0
        
        # Determine signal strength
        if confidence_score >= 60 and len(improving) >= 3:
            signal = BreakoutSignal.STRONG
        elif confidence_score >= 40 and len(improving) >= 2:
            signal = BreakoutSignal.EMERGING
        elif confidence_score >= 20 and len(improving) >= 1:
            signal = BreakoutSignal.WATCH
        elif len(declining) > len(improving):
            signal = BreakoutSignal.FADING
        else:
            # Not significant enough
            return None
        
        # Generate summary
        summary = self._generate_summary(player_type, improving, declining, signal)
        advice = self._generate_advice(signal, player_type, confidence_score)
        
        alert = BreakoutAlert(
            player_name=player_name,
            player_id=player_id,
            player_type=player_type,
            signal=signal,
            confidence_score=confidence_score,
            key_metrics=key_metrics,
            improving_metrics=improving,
            declining_metrics=declining,
            summary=summary,
            actionable_advice=advice
        )
        
        # Log prediction for historical tracking
        if self.tracker and signal in [BreakoutSignal.STRONG, BreakoutSignal.EMERGING]:
            try:
                self.tracker.log_prediction(
                    player_name=player_name,
                    player_id=player_id,
                    player_type=player_type,
                    signal=signal.value,
                    confidence=confidence_score,
                    improving_metrics=[m.split(':')[0].strip() for m in improving],
                    declining_metrics=[m.split(':')[0].strip() for m in declining],
                    key_metric_changes={k: v[1] - v[0] for k, v in key_metrics.items()}
                )
            except Exception as e:
                logger.warning(f"Could not log prediction to tracker: {e}")
        
        return alert
    
    def _generate_summary(
        self,
        player_type: str,
        improving: List[str],
        declining: List[str],
        signal: BreakoutSignal
    ) -> str:
        """Generate human-readable summary"""
        
        if signal == BreakoutSignal.STRONG:
            return (f"This {player_type} is showing multiple strong indicators of a breakout. "
                    f"{len(improving)} key metrics have improved significantly over the past 2 weeks. "
                    f"High-priority add if available.")
        elif signal == BreakoutSignal.EMERGING:
            return (f"Emerging trends suggest this {player_type} may be turning a corner. "
                    f"{len(improving)} metrics trending positively. Worth monitoring closely.")
        elif signal == BreakoutSignal.WATCH:
            return (f"Early signs of improvement in {len(improving)} area(s). "
                    f"Add to watchlist and track over next 1-2 weeks.")
        else:  # FADING
            return (f"Warning: {len(declining)} metrics declining. "
                    f"Consider selling high if you own this player.")
    
    def _generate_advice(
        self,
        signal: BreakoutSignal,
        player_type: str,
        confidence: float
    ) -> str:
        """Generate actionable advice"""
        
        if signal == BreakoutSignal.STRONG:
            if confidence >= 80:
                return "🔥 IMMEDIATE ADD - Don't wait, this player is breaking out NOW"
            else:
                return "⚡ HIGH PRIORITY - Add ASAP before others notice"
        elif signal == BreakoutSignal.EMERGING:
            return "👀 MONITOR CLOSELY - Check back in 3-5 days, prepare to add"
        elif signal == BreakoutSignal.WATCH:
            return "📝 WATCHLIST - Track for another week before deciding"
        else:  # FADING
            return "💰 SELL HIGH - Trade while value is still elevated"
    
    def scan_free_agents(
        self,
        free_agents: List[Dict],
        player_type: str = 'hitter'
    ) -> List[BreakoutAlert]:
        """
        Scan a list of free agents for breakout candidates
        
        Args:
            free_agents: List of player dictionaries with 'name' field
            player_type: 'hitter' or 'pitcher'
            
        Returns:
            List of BreakoutAlert objects, sorted by confidence
        """
        alerts = []
        
        for fa in free_agents:
            name = fa.get('name', '')
            if not name:
                continue
            
            # Parse name
            parts = name.split()
            if len(parts) < 2:
                continue
            
            first_name = parts[0]
            last_name = ' '.join(parts[1:])  # Handle multi-part last names
            
            # Analyze player
            alert = self.analyze_player(first_name, last_name, player_type)
            if alert:
                alerts.append(alert)
        
        # Sort by confidence score
        alerts.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return alerts


if __name__ == "__main__":
    # Test the detector
    logging.basicConfig(level=logging.INFO)
    
    detector = BreakoutDetector()
    
    print("\n🔬 Testing Breakout Detector")
    print("="*70)
    print("Note: This requires live MLB data (works during the season)\n")
    
    # Example test (would work during season)
    # alert = detector.analyze_player("Gunnar", "Henderson", "hitter")
    # if alert:
    #     print(alert)
    # else:
    #     print("No significant breakout signals detected (or off-season)")
    
    print("✅ Breakout Detector initialized successfully")
    print("\nDuring the season, you can use:")
    print("  detector.analyze_player('Gunnar', 'Henderson', 'hitter')")
    print("  detector.scan_free_agents(free_agents_list, 'hitter')")
