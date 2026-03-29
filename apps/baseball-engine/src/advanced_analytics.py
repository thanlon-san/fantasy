#!/usr/bin/env python3
"""
Advanced Analytics Module
Sophisticated metrics and indicators for elite-level lineup recommendations
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# Umpire strike zone data (sourced from UmpireScorecards.com and similar services)
# These are approximate values - in production, would fetch from a live API
UMPIRE_FACTORS = {
    # Conservative/Pitcher-friendly umps (larger zone)
    'Angel Hernandez': {'zone_size': 105, 'favor': 'pitchers', 'consistency': 82},  # Controversial
    'C.B. Bucknor': {'zone_size': 104, 'favor': 'pitchers', 'consistency': 85},
    'Joe West': {'zone_size': 103, 'favor': 'pitchers', 'consistency': 88},
    'Laz Diaz': {'zone_size': 102, 'favor': 'pitchers', 'consistency': 90},
    
    # Hitter-friendly umps (smaller zone)
    'Pat Hoberg': {'zone_size': 96, 'favor': 'hitters', 'consistency': 97},  # Most accurate
    'John Libka': {'zone_size': 97, 'favor': 'hitters', 'consistency': 94},
    'Dan Bellino': {'zone_size': 98, 'favor': 'hitters', 'consistency': 92},
    
    # Neutral umps
    'Mike Estabrook': {'zone_size': 100, 'favor': 'neutral', 'consistency': 93},
    'Jim Reynolds': {'zone_size': 100, 'favor': 'neutral', 'consistency': 91},
    'Rob Drake': {'zone_size': 100, 'favor': 'neutral', 'consistency': 90},
}


@dataclass
class AdvancedMatchupMetrics:
    """Advanced metrics for a matchup"""
    
    # Expected stats (Statcast)
    xBA: Optional[float] = None          # Expected batting average
    xSLG: Optional[float] = None         # Expected slugging
    xwOBA: Optional[float] = None        # Expected weighted on-base average
    
    # Quality of contact trends
    hard_hit_trend: Optional[str] = None  # 'improving', 'declining', 'stable'
    barrel_trend: Optional[str] = None
    
    # Batted ball profile
    gb_percent: Optional[float] = None
    fb_percent: Optional[float] = None
    ld_percent: Optional[float] = None
    
    # Discipline metrics
    chase_rate: Optional[float] = None
    zone_contact_rate: Optional[float] = None
    
    # Umpire impact
    umpire_adjustment: float = 0  # -5 to +5 points
    
    # Matchup-specific
    pitch_type_advantage: bool = False  # Batter good vs pitcher's primary pitch
    velocity_advantage: bool = False    # Pitcher losing velocity


class AdvancedAnalytics:
    """Advanced analytics for enhanced lineup recommendations"""
    
    def __init__(self):
        """Initialize advanced analytics module"""
        pass
    
    def get_umpire_adjustment(
        self,
        umpire_name: Optional[str],
        player_type: str  # 'hitter' or 'pitcher'
    ) -> Tuple[float, Optional[str]]:
        """
        Get lineup adjustment based on home plate umpire
        
        Args:
            umpire_name: Name of home plate umpire
            player_type: Whether this is for a hitter or pitcher
            
        Returns:
            Tuple of (adjustment value, reason string)
        """
        if not umpire_name or umpire_name not in UMPIRE_FACTORS:
            return 0, None
        
        umpire_data = UMPIRE_FACTORS[umpire_name]
        zone_size = umpire_data['zone_size']
        favor = umpire_data['favor']
        
        # Large zone helps pitchers (more strikes called)
        if zone_size > 102:
            if player_type == 'pitcher':
                adjustment = min(5, (zone_size - 100) / 2)
                reason = f"Umpire has large zone (favorable)"
            else:  # hitter
                adjustment = -min(5, (zone_size - 100) / 2)
                reason = f"Umpire has large zone (unfavorable)"
        
        # Small zone helps hitters (fewer strikes called)
        elif zone_size < 98:
            if player_type == 'hitter':
                adjustment = min(5, (100 - zone_size) / 2)
                reason = f"Umpire has small zone (favorable)"
            else:  # pitcher
                adjustment = -min(5, (100 - zone_size) / 2)
                reason = f"Umpire has small zone (unfavorable)"
        else:
            adjustment = 0
            reason = None
        
        return adjustment, reason
    
    def analyze_contact_quality_trends(
        self,
        recent_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float]
    ) -> Dict[str, str]:
        """
        Analyze if contact quality is improving or declining
        
        Args:
            recent_metrics: Last 7-14 days metrics
            baseline_metrics: Previous 30 days metrics
            
        Returns:
            Dictionary of trend indicators
        """
        trends = {}
        
        # Hard hit rate trend
        if 'hard_hit_percent' in recent_metrics and 'hard_hit_percent' in baseline_metrics:
            recent_hh = recent_metrics['hard_hit_percent']
            baseline_hh = baseline_metrics['hard_hit_percent']
            diff = recent_hh - baseline_hh
            
            if diff > 5:
                trends['hard_hit_trend'] = 'improving'
            elif diff < -5:
                trends['hard_hit_trend'] = 'declining'
            else:
                trends['hard_hit_trend'] = 'stable'
        
        # Barrel rate trend
        if 'barrel_percent' in recent_metrics and 'barrel_percent' in baseline_metrics:
            recent_barrel = recent_metrics['barrel_percent']
            baseline_barrel = baseline_metrics['barrel_percent']
            diff = recent_barrel - baseline_barrel
            
            if diff > 2:
                trends['barrel_trend'] = 'improving'
            elif diff < -2:
                trends['barrel_trend'] = 'declining'
            else:
                trends['barrel_trend'] = 'stable'
        
        # Exit velocity trend
        if 'exit_velocity_avg' in recent_metrics and 'exit_velocity_avg' in baseline_metrics:
            recent_ev = recent_metrics['exit_velocity_avg']
            baseline_ev = baseline_metrics['exit_velocity_avg']
            diff = recent_ev - baseline_ev
            
            if diff > 1.5:
                trends['exit_velo_trend'] = 'improving'
            elif diff < -1.5:
                trends['exit_velo_trend'] = 'declining'
            else:
                trends['exit_velo_trend'] = 'stable'
        
        return trends
    
    def calculate_expected_stats_boost(
        self,
        actual_avg: float,
        xBA: Optional[float]
    ) -> Tuple[float, Optional[str]]:
        """
        Determine if player is getting unlucky/lucky based on expected stats
        
        Args:
            actual_avg: Actual batting average
            xBA: Expected batting average from Statcast
            
        Returns:
            Tuple of (adjustment, reason)
        """
        if not xBA:
            return 0, None
        
        diff = xBA - actual_avg
        
        # Getting very unlucky (xBA 30+ points higher)
        if diff > 0.030:
            adjustment = 5
            reason = f"Due for positive regression (xBA: {xBA:.3f})"
        # Somewhat unlucky (xBA 15+ points higher)
        elif diff > 0.015:
            adjustment = 3
            reason = f"Hitting ball better than results show"
        # Getting lucky (actual 20+ points higher than xBA)
        elif diff < -0.020:
            adjustment = -3
            reason = f"Results outpacing contact quality"
        else:
            adjustment = 0
            reason = None
        
        return adjustment, reason
    
    def analyze_batted_ball_profile(
        self,
        gb_percent: Optional[float],
        fb_percent: Optional[float],
        park_factor: float
    ) -> Tuple[float, Optional[str]]:
        """
        Match batted ball profile with park factors
        
        Args:
            gb_percent: Ground ball percentage
            fb_percent: Fly ball percentage
            park_factor: Park factor (>1.0 = hitter friendly)
            
        Returns:
            Tuple of (adjustment, reason)
        """
        if not gb_percent or not fb_percent:
            return 0, None
        
        # Fly ball hitters in hitter-friendly parks
        if fb_percent > 45 and park_factor > 1.05:
            adjustment = 3
            reason = "Fly ball hitter in HR-friendly park"
        # Ground ball hitters in pitcher-friendly parks (still make contact)
        elif gb_percent > 50 and park_factor < 0.95:
            adjustment = 2
            reason = "Ground ball approach suits park"
        # Fly ball hitters in pitcher parks (power suppressed)
        elif fb_percent > 45 and park_factor < 0.95:
            adjustment = -2
            reason = "Power suppressed in this park"
        else:
            adjustment = 0
            reason = None
        
        return adjustment, reason
    
    def get_rest_fatigue_adjustment(
        self,
        is_pitcher: bool,
        days_since_last_game: int,
        games_in_last_week: int
    ) -> Tuple[float, Optional[str]]:
        """
        Adjust for rest and fatigue factors
        
        Args:
            is_pitcher: True for pitchers, False for hitters
            days_since_last_game: Days of rest
            games_in_last_week: Games played in last 7 days
            
        Returns:
            Tuple of (adjustment, reason)
        """
        if is_pitcher:
            # Pitchers need 4-5 days rest typically
            if days_since_last_game < 4:
                adjustment = -5
                reason = "On short rest"
            elif days_since_last_game > 6:
                adjustment = -2
                reason = "Extra rest (rust factor)"
            else:
                adjustment = 0
                reason = None
        else:
            # Hitters - fatigue from too many games
            if games_in_last_week >= 7:
                adjustment = -3
                reason = "Potential fatigue (7 straight games)"
            elif games_in_last_week <= 3 and days_since_last_game <= 1:
                adjustment = 2
                reason = "Well-rested"
            else:
                adjustment = 0
                reason = None
        
        return adjustment, reason


def get_advanced_analytics() -> AdvancedAnalytics:
    """Get advanced analytics singleton"""
    return AdvancedAnalytics()


if __name__ == "__main__":
    # Test advanced analytics
    logging.basicConfig(level=logging.INFO)
    
    analytics = AdvancedAnalytics()
    
    print("\n📊 Advanced Analytics Module")
    print("="*70)
    
    # Test umpire adjustment
    adj, reason = analytics.get_umpire_adjustment("Pat Hoberg", "hitter")
    print(f"Umpire adjustment (Pat Hoberg, hitter): {adj:+.1f}")
    if reason:
        print(f"  Reason: {reason}")
    
    # Test expected stats
    adj, reason = analytics.calculate_expected_stats_boost(0.250, 0.285)
    print(f"\nExpected stats adjustment: {adj:+.1f}")
    if reason:
        print(f"  Reason: {reason}")
    
    print("\n✅ Advanced Analytics ready for integration")
