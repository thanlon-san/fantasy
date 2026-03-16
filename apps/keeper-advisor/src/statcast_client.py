#!/usr/bin/env python3
"""
Statcast Data Client
Fetch advanced metrics from MLB's Statcast system via Baseball Savant
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pybaseball import statcast_batter, statcast_pitcher, playerid_lookup
from pybaseball.cache import enable as enable_cache

logger = logging.getLogger(__name__)

# Enable caching to avoid hitting API repeatedly
enable_cache()


class StatcastClient:
    """Client for fetching Statcast data from Baseball Savant"""
    
    # Key metrics for breakout detection
    HITTER_METRICS = [
        'exit_velocity_avg',
        'hard_hit_percent',
        'barrel_percent',
        'sweet_spot_percent',
        'launch_angle_avg',
        'chase_rate',
        'whiff_percent',
        'k_percent',
        'bb_percent',
    ]
    
    PITCHER_METRICS = [
        'exit_velocity_avg',
        'hard_hit_percent',
        'barrel_percent',
        'whiff_percent',
        'k_percent',
        'bb_percent',
        'avg_fastball_velocity',
        'avg_spin_rate',
    ]
    
    def __init__(self):
        self._player_cache = {}
    
    def _get_analysis_dates(
        self, 
        days_back: int,
        use_previous_season_if_offseason: bool = True
    ) -> Tuple[str, str]:
        """
        Get appropriate start/end dates for analysis, handling offseason
        
        Args:
            days_back: Number of days to look back
            use_previous_season_if_offseason: Use end of previous season during offseason
            
        Returns:
            Tuple of (start_date, end_date) as YYYY-MM-DD strings
        """
        current_date = datetime.now()
        current_month = current_date.month
        current_day = current_date.day

        # Spring training: ~Feb 15 through early April (before Opening Day)
        is_spring_training = (
            (current_month == 2 and current_day >= 15) or
            (current_month == 3) or
            (current_month == 4 and current_day < 5)
        )

        # True offseason: November through mid-February
        is_offseason = (
            current_month in [11, 12, 1] or
            (current_month == 2 and current_day < 15)
        )

        if is_spring_training:
            # Use current spring training window so pybaseball returns
            # spring training Statcast data (game_type S is included by default)
            spring_start = datetime(current_date.year, 2, 15)
            end_date = current_date
            start_date = max(spring_start, end_date - timedelta(days=days_back))
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        elif is_offseason and use_previous_season_if_offseason:
            # Use end of previous regular season
            previous_year = current_date.year if current_month >= 11 else current_date.year - 1
            end_date = datetime(previous_year, 10, 1)
            start_date = end_date - timedelta(days=days_back)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        else:
            # Normal in-season: rolling window from today
            end_date = current_date
            start_date = end_date - timedelta(days=days_back)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def get_player_id(self, first_name: str, last_name: str) -> Optional[int]:
        """
        Look up MLB player ID
        
        Args:
            first_name: Player's first name
            last_name: Player's last name
            
        Returns:
            MLB player ID (key_mlbam) or None
        """
        cache_key = f"{first_name} {last_name}".lower()
        
        if cache_key in self._player_cache:
            return self._player_cache[cache_key]
        
        try:
            results = playerid_lookup(last_name, first_name)
            
            if results.empty:
                logger.warning(f"No player found: {first_name} {last_name}")
                return None
            
            # Get most recent player (highest mlb_played_last)
            results = results.sort_values('mlb_played_last', ascending=False)
            player_id = int(results.iloc[0]['key_mlbam'])
            
            self._player_cache[cache_key] = player_id
            logger.debug(f"Found player ID for {first_name} {last_name}: {player_id}")
            
            return player_id
            
        except Exception as e:
            logger.error(f"Error looking up player {first_name} {last_name}: {e}")
            return None
    
    def get_hitter_stats(
        self,
        player_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_previous_season_if_offseason: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get Statcast hitting data for a player
        
        Args:
            player_id: MLB player ID
            start_date: Start date (YYYY-MM-DD), defaults to 30 days ago (or end of previous season)
            end_date: End date (YYYY-MM-DD), defaults to today (or end of previous season)
            use_previous_season_if_offseason: Use end of previous season during offseason
            
        Returns:
            DataFrame with Statcast data or None
        """
        if not start_date or not end_date:
            start_date, end_date = self._get_analysis_dates(30, use_previous_season_if_offseason)
        
        try:
            logger.info(f"Fetching hitter stats for player {player_id} ({start_date} to {end_date})")
            data = statcast_batter(start_date, end_date, player_id)
            
            if data.empty:
                logger.warning(f"No hitting data found for player {player_id}")
                return None
            
            logger.info(f"Retrieved {len(data)} at-bats for player {player_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching hitter stats: {e}")
            return None
    
    def get_pitcher_stats(
        self,
        player_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_previous_season_if_offseason: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get Statcast pitching data for a player
        
        Args:
            player_id: MLB player ID
            start_date: Start date (YYYY-MM-DD), defaults to 30 days ago (or end of previous season)
            end_date: End date (YYYY-MM-DD), defaults to today (or end of previous season)
            use_previous_season_if_offseason: Use end of previous season during offseason
            
        Returns:
            DataFrame with Statcast data or None
        """
        if not start_date or not end_date:
            start_date, end_date = self._get_analysis_dates(30, use_previous_season_if_offseason)
        
        try:
            logger.info(f"Fetching pitcher stats for player {player_id} ({start_date} to {end_date})")
            data = statcast_pitcher(start_date, end_date, player_id)
            
            if data.empty:
                logger.warning(f"No pitching data found for player {player_id}")
                return None
            
            logger.info(f"Retrieved {len(data)} pitches for player {player_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching pitcher stats: {e}")
            return None
    
    def calculate_hitter_metrics(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate aggregate metrics for a hitter
        
        Args:
            data: Raw Statcast data
            
        Returns:
            Dictionary of calculated metrics
        """
        if data.empty:
            return {}
        
        metrics = {}
        
        # Exit velocity
        if 'launch_speed' in data.columns:
            metrics['exit_velocity_avg'] = data['launch_speed'].mean()
            metrics['exit_velocity_95th'] = data['launch_speed'].quantile(0.95)
        
        # Hard hit rate (95+ mph)
        if 'launch_speed' in data.columns:
            hard_hits = (data['launch_speed'] >= 95).sum()
            total_hits = data['launch_speed'].notna().sum()
            metrics['hard_hit_percent'] = (hard_hits / total_hits * 100) if total_hits > 0 else 0
        
        # Barrel rate
        if 'barrel' in data.columns:
            barrels = data['barrel'].sum()
            batted_balls = data['barrel'].notna().sum()
            metrics['barrel_percent'] = (barrels / batted_balls * 100) if batted_balls > 0 else 0
        
        # Launch angle
        if 'launch_angle' in data.columns:
            metrics['launch_angle_avg'] = data['launch_angle'].mean()
            
            # Sweet spot (8-32 degrees)
            sweet_spot = ((data['launch_angle'] >= 8) & (data['launch_angle'] <= 32)).sum()
            total_la = data['launch_angle'].notna().sum()
            metrics['sweet_spot_percent'] = (sweet_spot / total_la * 100) if total_la > 0 else 0
        
        # Chase rate (swings outside zone)
        if 'zone' in data.columns and 'description' in data.columns:
            outside_zone = data['zone'].isin(['11', '12', '13', '14'])
            swings = data['description'].str.contains('swing|foul', case=False, na=False)
            chases = (outside_zone & swings).sum()
            outside_pitches = outside_zone.sum()
            metrics['chase_rate'] = (chases / outside_pitches * 100) if outside_pitches > 0 else 0
        
        # Whiff rate
        if 'description' in data.columns:
            swings = data['description'].str.contains('swing|foul', case=False, na=False).sum()
            whiffs = data['description'].str.contains('swing.*miss', case=False, na=False).sum()
            metrics['whiff_percent'] = (whiffs / swings * 100) if swings > 0 else 0
        
        # K% and BB%
        if 'events' in data.columns:
            pas = data['events'].notna().sum()
            if pas > 0:
                strikeouts = (data['events'] == 'strikeout').sum()
                walks = (data['events'] == 'walk').sum()
                metrics['k_percent'] = (strikeouts / pas * 100)
                metrics['bb_percent'] = (walks / pas * 100)
        
        # Expected stats (xBA, xSLG, xwOBA) if available
        if 'estimated_ba_using_speedangle' in data.columns:
            metrics['xBA'] = data['estimated_ba_using_speedangle'].mean()
        
        if 'estimated_slg_using_speedangle' in data.columns:
            metrics['xSLG'] = data['estimated_slg_using_speedangle'].mean()
        
        if 'estimated_woba_using_speedangle' in data.columns:
            metrics['xwOBA'] = data['estimated_woba_using_speedangle'].mean()
        
        # Batted ball type distribution
        if 'bb_type' in data.columns:
            total_bb = data['bb_type'].notna().sum()
            if total_bb > 0:
                metrics['ground_ball_percent'] = ((data['bb_type'] == 'ground_ball').sum() / total_bb * 100)
                metrics['line_drive_percent'] = ((data['bb_type'] == 'line_drive').sum() / total_bb * 100)
                metrics['fly_ball_percent'] = ((data['bb_type'] == 'fly_ball').sum() / total_bb * 100)
        
        # Pull rate (spray chart analysis)
        if 'hit_location' in data.columns:
            # For RHB: 3-5 is pull side, 6 is center, 7-9 is opposite
            # For LHB: 7-9 is pull side, 6 is center, 3-5 is opposite
            # Simplification: 3,4,5,7,8,9 are directional hits
            total_directional = data['hit_location'].notna().sum()
            if total_directional > 0:
                # Pull fields are typically 3-5 for RHB, 7-9 for LHB
                # We'll estimate based on common patterns
                pull_hits = data['hit_location'].isin([3, 4, 5, 7, 8, 9]).sum()
                metrics['pull_percent'] = (pull_hits / total_directional * 100) if total_directional > 0 else 0
        
        # Max exit velocity (indicator of raw power)
        if 'launch_speed' in data.columns:
            metrics['exit_velocity_max'] = data['launch_speed'].max()
        
        return metrics
    
    def calculate_pitcher_metrics(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate aggregate metrics for a pitcher
        
        Args:
            data: Raw Statcast data
            
        Returns:
            Dictionary of calculated metrics
        """
        if data.empty:
            return {}
        
        metrics = {}
        
        # Exit velocity (for contact)
        if 'launch_speed' in data.columns:
            metrics['exit_velocity_avg'] = data['launch_speed'].mean()
        
        # Hard hit rate
        if 'launch_speed' in data.columns:
            hard_hits = (data['launch_speed'] >= 95).sum()
            total_contact = data['launch_speed'].notna().sum()
            metrics['hard_hit_percent'] = (hard_hits / total_contact * 100) if total_contact > 0 else 0
        
        # Barrel rate
        if 'barrel' in data.columns:
            barrels = data['barrel'].sum()
            batted_balls = data['barrel'].notna().sum()
            metrics['barrel_percent'] = (barrels / batted_balls * 100) if batted_balls > 0 else 0
        
        # Whiff rate
        if 'description' in data.columns:
            swings = data['description'].str.contains('swing|foul', case=False, na=False).sum()
            whiffs = data['description'].str.contains('swing.*miss', case=False, na=False).sum()
            metrics['whiff_percent'] = (whiffs / swings * 100) if swings > 0 else 0
        
        # K% and BB%
        if 'events' in data.columns:
            batters_faced = data['events'].notna().sum()
            if batters_faced > 0:
                strikeouts = (data['events'] == 'strikeout').sum()
                walks = (data['events'] == 'walk').sum()
                metrics['k_percent'] = (strikeouts / batters_faced * 100)
                metrics['bb_percent'] = (walks / batters_faced * 100)
        
        # Velocity by pitch type
        if 'pitch_type' in data.columns and 'release_speed' in data.columns:
            fastballs = data[data['pitch_type'].isin(['FF', 'FT', 'SI'])]['release_speed']
            if not fastballs.empty:
                metrics['avg_fastball_velocity'] = fastballs.mean()
                metrics['max_fastball_velocity'] = fastballs.max()
        
        # Spin rate (breaking balls)
        if 'release_spin_rate' in data.columns and 'pitch_type' in data.columns:
            # Overall spin rate
            metrics['avg_spin_rate'] = data['release_spin_rate'].mean()
            
            # Breaking ball spin rate (more relevant for breakout detection)
            breaking_pitches = data[data['pitch_type'].isin(['SL', 'CU', 'KC', 'SV', 'CS'])]
            if not breaking_pitches.empty:
                metrics['breaking_spin_rate'] = breaking_pitches['release_spin_rate'].mean()
        
        # Pitch arsenal usage (pitch mix changes can indicate breakout)
        if 'pitch_type' in data.columns:
            total_pitches = len(data)
            if total_pitches > 0:
                # Fastball usage (FF, FT, SI, FC)
                fastball_count = data['pitch_type'].isin(['FF', 'FT', 'SI', 'FC']).sum()
                metrics['fastball_usage'] = (fastball_count / total_pitches * 100)
                
                # Breaking ball usage (SL, CU, KC, SV, CS)
                breaking_count = data['pitch_type'].isin(['SL', 'CU', 'KC', 'SV', 'CS']).sum()
                metrics['breaking_usage'] = (breaking_count / total_pitches * 100)
                
                # Offspeed usage (CH, FS, SC)
                offspeed_count = data['pitch_type'].isin(['CH', 'FS', 'SC']).sum()
                metrics['offspeed_usage'] = (offspeed_count / total_pitches * 100)
        
        # Expected stats against (xBA, xSLG, xwOBA)
        if 'estimated_ba_using_speedangle' in data.columns:
            metrics['xBA_against'] = data['estimated_ba_using_speedangle'].mean()
        
        if 'estimated_slg_using_speedangle' in data.columns:
            metrics['xSLG_against'] = data['estimated_slg_using_speedangle'].mean()
        
        if 'estimated_woba_using_speedangle' in data.columns:
            metrics['xwOBA_against'] = data['estimated_woba_using_speedangle'].mean()
        
        return metrics
    
    def compare_time_periods(
        self,
        player_id: int,
        player_type: str = 'hitter',
        recent_days: int = 14,
        baseline_days: int = 30,
        use_previous_season_if_offseason: bool = True
    ) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        """
        Compare recent performance to baseline
        
        Args:
            player_id: MLB player ID
            player_type: 'hitter' or 'pitcher'
            recent_days: Days for recent sample
            baseline_days: Days for baseline comparison (before recent)
            use_previous_season_if_offseason: If True and currently offseason, analyze end of previous season
            
        Returns:
            Tuple of (recent_metrics, baseline_metrics, changes)
        """
        current_date = datetime.now()
        current_month = current_date.month
        
        # Detect offseason (November through February)
        is_offseason = current_month in [11, 12, 1, 2]
        
        if is_offseason and use_previous_season_if_offseason:
            # Use end of previous season for draft analysis
            # MLB season typically ends early October
            previous_year = current_date.year if current_month >= 11 else current_date.year - 1
            
            # Recent = last 2 weeks of season (Sept 15 - Oct 1)
            end_date = datetime(previous_year, 10, 1)
            recent_start = end_date - timedelta(days=recent_days)
            
            # Baseline = month before that (Aug 15 - Sept 15)
            baseline_end = recent_start
            baseline_start = baseline_end - timedelta(days=baseline_days)
            
            logger.info(f"Offseason mode: Analyzing end of {previous_year} season (Sept-Oct)")
        else:
            # Normal in-season analysis
            end_date = current_date
            recent_start = end_date - timedelta(days=recent_days)
            baseline_start = recent_start - timedelta(days=baseline_days)
            baseline_end = recent_start
        
        recent_start_str = recent_start.strftime('%Y-%m-%d')
        baseline_start_str = baseline_start.strftime('%Y-%m-%d')
        baseline_end_str = baseline_end.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        if player_type == 'hitter':
            recent_data = self.get_hitter_stats(player_id, recent_start_str, end_date_str)
            baseline_data = self.get_hitter_stats(player_id, baseline_start_str, baseline_end_str)
            
            recent_metrics = self.calculate_hitter_metrics(recent_data) if recent_data is not None else {}
            baseline_metrics = self.calculate_hitter_metrics(baseline_data) if baseline_data is not None else {}
        else:
            recent_data = self.get_pitcher_stats(player_id, recent_start_str, end_date_str)
            baseline_data = self.get_pitcher_stats(player_id, baseline_start_str, baseline_end_str)
            
            recent_metrics = self.calculate_pitcher_metrics(recent_data) if recent_data is not None else {}
            baseline_metrics = self.calculate_pitcher_metrics(baseline_data) if baseline_data is not None else {}
        
        # Calculate changes
        changes = {}
        for key in recent_metrics:
            if key in baseline_metrics:
                change = recent_metrics[key] - baseline_metrics[key]
                changes[key] = change
        
        return recent_metrics, baseline_metrics, changes


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)
    
    client = StatcastClient()
    
    # Test with Gunnar Henderson (example)
    print("\n🔬 Testing Statcast Client")
    print("="*70)
    
    player_id = client.get_player_id("Gunnar", "Henderson")
    if player_id:
        print(f"✅ Found Gunnar Henderson (ID: {player_id})")
        
        # This would work during the season
        # recent, baseline, changes = client.compare_time_periods(player_id, 'hitter')
        # print(f"\n📊 Recent Stats:")
        # for key, val in recent.items():
        #     print(f"  {key}: {val:.2f}")
    else:
        print("❌ Could not find player")
