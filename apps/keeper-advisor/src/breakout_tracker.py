#!/usr/bin/env python3
"""
Breakout Prediction Tracker
Track historical breakout predictions and measure accuracy over time
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BreakoutPrediction:
    """A logged breakout prediction"""
    
    date: str
    player_name: str
    player_id: int
    player_type: str  # 'hitter' or 'pitcher'
    signal: str  # 'STRONG', 'EMERGING', 'WATCH'
    confidence: float
    
    # Key metrics at time of prediction
    improving_metrics: List[str]
    declining_metrics: List[str]
    key_metric_changes: Dict[str, float]
    
    # Fantasy context
    adp_at_prediction: Optional[float] = None
    rostered_percent_at_prediction: Optional[float] = None
    
    # Outcome tracking (filled in later)
    outcome_tracked_date: Optional[str] = None
    adp_30_days_later: Optional[float] = None
    stats_30_days_later: Optional[Dict[str, float]] = None
    was_successful: Optional[bool] = None  # Did the breakout materialize?
    success_score: Optional[float] = None  # 0-100 score based on improvement


@dataclass
class TrackerStats:
    """Aggregate statistics for breakout predictions"""
    
    total_predictions: int
    strong_signals: int
    emerging_signals: int
    watch_signals: int
    
    # Outcomes (for predictions with 30+ days of data)
    total_tracked: int
    successful_breakouts: int
    false_positives: int
    success_rate: float
    
    # By signal type
    strong_success_rate: float
    emerging_success_rate: float
    watch_success_rate: float
    
    # Most predictive metrics
    top_predictive_metrics: List[Dict[str, any]]
    
    # Recommendations for threshold tuning
    threshold_recommendations: Dict[str, str]


class BreakoutTracker:
    """Track and analyze breakout prediction accuracy"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize tracker
        
        Args:
            data_dir: Directory to store tracking data
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "breakout_tracking"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.predictions_file = self.data_dir / "predictions.json"
        self.predictions = self._load_predictions()
    
    def _load_predictions(self) -> List[BreakoutPrediction]:
        """Load existing predictions from file"""
        if not self.predictions_file.exists():
            return []
        
        try:
            with open(self.predictions_file, 'r') as f:
                data = json.load(f)
                return [BreakoutPrediction(**p) for p in data]
        except Exception as e:
            logger.error(f"Error loading predictions: {e}")
            return []
    
    def _save_predictions(self):
        """Save predictions to file"""
        try:
            with open(self.predictions_file, 'w') as f:
                json.dump(
                    [asdict(p) for p in self.predictions],
                    f,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Error saving predictions: {e}")
    
    def log_prediction(
        self,
        player_name: str,
        player_id: int,
        player_type: str,
        signal: str,
        confidence: float,
        improving_metrics: List[str],
        declining_metrics: List[str],
        key_metric_changes: Dict[str, float],
        adp: Optional[float] = None,
        rostered_percent: Optional[float] = None
    ):
        """
        Log a new breakout prediction
        
        Args:
            player_name: Player's full name
            player_id: MLB player ID
            player_type: 'hitter' or 'pitcher'
            signal: Signal strength
            confidence: Confidence score (0-100)
            improving_metrics: List of improving metric names
            declining_metrics: List of declining metric names
            key_metric_changes: Dict of metric_name -> change value
            adp: Average draft position at time of prediction
            rostered_percent: Roster % at time of prediction
        """
        prediction = BreakoutPrediction(
            date=datetime.now().strftime('%Y-%m-%d'),
            player_name=player_name,
            player_id=player_id,
            player_type=player_type,
            signal=signal,
            confidence=confidence,
            improving_metrics=improving_metrics,
            declining_metrics=declining_metrics,
            key_metric_changes=key_metric_changes,
            adp_at_prediction=adp,
            rostered_percent_at_prediction=rostered_percent
        )
        
        # Check for duplicate (same player within 7 days)
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        existing = [
            p for p in self.predictions
            if p.player_id == player_id and p.date >= cutoff_date
        ]
        
        if existing:
            logger.info(f"Skipping duplicate prediction for {player_name} (logged within 7 days)")
            return
        
        self.predictions.append(prediction)
        self._save_predictions()
        
        logger.info(f"Logged {signal} breakout prediction for {player_name} (confidence: {confidence:.1f}%)")
    
    def update_outcomes(self, statcast_client):
        """
        Update outcomes for predictions that are 30+ days old
        
        Args:
            statcast_client: StatcastClient instance to fetch updated stats
        """
        from .statcast_client import StatcastClient
        from .adp_fetcher import ADPFetcher
        
        adp_fetcher = ADPFetcher()
        today = datetime.now()
        updated_count = 0
        
        for prediction in self.predictions:
            # Skip if already tracked
            if prediction.outcome_tracked_date:
                continue
            
            # Check if 30+ days old
            pred_date = datetime.strptime(prediction.date, '%Y-%m-%d')
            days_since = (today - pred_date).days
            
            if days_since < 30:
                continue
            
            logger.info(f"Tracking outcome for {prediction.player_name} ({days_since} days since prediction)")
            
            try:
                # Get current stats (30 days of recent data)
                if prediction.player_type == 'hitter':
                    data = statcast_client.get_hitter_stats(
                        prediction.player_id,
                        start_date=(today - timedelta(days=30)).strftime('%Y-%m-%d'),
                        end_date=today.strftime('%Y-%m-%d')
                    )
                    if data is not None and not data.empty:
                        stats = statcast_client.calculate_hitter_metrics(data)
                        prediction.stats_30_days_later = stats
                else:
                    data = statcast_client.get_pitcher_stats(
                        prediction.player_id,
                        start_date=(today - timedelta(days=30)).strftime('%Y-%m-%d'),
                        end_date=today.strftime('%Y-%m-%d')
                    )
                    if data is not None and not data.empty:
                        stats = statcast_client.calculate_pitcher_metrics(data)
                        prediction.stats_30_days_later = stats
                
                # Get current ADP
                current_adp = adp_fetcher.get_player_adp(prediction.player_name)
                prediction.adp_30_days_later = current_adp
                
                # Calculate success
                success_score = self._calculate_success(prediction)
                prediction.success_score = success_score
                prediction.was_successful = success_score >= 60  # 60+ = successful breakout
                
                prediction.outcome_tracked_date = today.strftime('%Y-%m-%d')
                updated_count += 1
                
                logger.info(f"  → Success score: {success_score:.1f} ({'SUCCESS' if prediction.was_successful else 'MISS'})")
                
            except Exception as e:
                logger.error(f"Error tracking outcome for {prediction.player_name}: {e}")
        
        if updated_count > 0:
            self._save_predictions()
            logger.info(f"Updated outcomes for {updated_count} predictions")
    
    def _calculate_success(self, prediction: BreakoutPrediction) -> float:
        """
        Calculate success score (0-100) based on whether metrics continued to improve
        
        Args:
            prediction: Prediction to evaluate
            
        Returns:
            Success score (0-100)
        """
        if not prediction.stats_30_days_later:
            return 0.0
        
        score = 50.0  # Start at neutral
        
        # Check if improving metrics sustained/improved further
        for metric in prediction.improving_metrics[:5]:  # Top 5 metrics
            if metric in prediction.stats_30_days_later:
                # Metric sustained = good
                score += 5
        
        # ADP improvement (major signal of success)
        if prediction.adp_at_prediction and prediction.adp_30_days_later:
            adp_improvement = prediction.adp_at_prediction - prediction.adp_30_days_later
            if adp_improvement > 50:  # Jumped 50+ spots
                score += 30
            elif adp_improvement > 20:
                score += 20
            elif adp_improvement > 10:
                score += 10
            elif adp_improvement < -20:  # ADP got worse
                score -= 20
        
        return max(0.0, min(100.0, score))
    
    def get_stats(self) -> TrackerStats:
        """
        Calculate aggregate statistics
        
        Returns:
            TrackerStats with success rates and recommendations
        """
        total = len(self.predictions)
        if total == 0:
            return TrackerStats(
                total_predictions=0,
                strong_signals=0,
                emerging_signals=0,
                watch_signals=0,
                total_tracked=0,
                successful_breakouts=0,
                false_positives=0,
                success_rate=0.0,
                strong_success_rate=0.0,
                emerging_success_rate=0.0,
                watch_success_rate=0.0,
                top_predictive_metrics=[],
                threshold_recommendations={}
            )
        
        # Count by signal type
        strong = len([p for p in self.predictions if p.signal == 'STRONG'])
        emerging = len([p for p in self.predictions if p.signal == 'EMERGING'])
        watch = len([p for p in self.predictions if p.signal == 'WATCH'])
        
        # Tracked outcomes
        tracked = [p for p in self.predictions if p.was_successful is not None]
        total_tracked = len(tracked)
        
        if total_tracked == 0:
            return TrackerStats(
                total_predictions=total,
                strong_signals=strong,
                emerging_signals=emerging,
                watch_signals=watch,
                total_tracked=0,
                successful_breakouts=0,
                false_positives=0,
                success_rate=0.0,
                strong_success_rate=0.0,
                emerging_success_rate=0.0,
                watch_success_rate=0.0,
                top_predictive_metrics=[],
                threshold_recommendations={}
            )
        
        successful = len([p for p in tracked if p.was_successful])
        success_rate = (successful / total_tracked * 100)
        
        # Success by signal type
        strong_tracked = [p for p in tracked if p.signal == 'STRONG']
        emerging_tracked = [p for p in tracked if p.signal == 'EMERGING']
        watch_tracked = [p for p in tracked if p.signal == 'WATCH']
        
        strong_success = (len([p for p in strong_tracked if p.was_successful]) / len(strong_tracked) * 100) if strong_tracked else 0
        emerging_success = (len([p for p in emerging_tracked if p.was_successful]) / len(emerging_tracked) * 100) if emerging_tracked else 0
        watch_success = (len([p for p in watch_tracked if p.was_successful]) / len(watch_tracked) * 100) if watch_tracked else 0
        
        # Identify most predictive metrics
        top_metrics = self._identify_top_metrics(tracked)
        
        # Generate threshold recommendations
        recommendations = self._generate_recommendations(
            success_rate, strong_success, emerging_success, watch_success
        )
        
        return TrackerStats(
            total_predictions=total,
            strong_signals=strong,
            emerging_signals=emerging,
            watch_signals=watch,
            total_tracked=total_tracked,
            successful_breakouts=successful,
            false_positives=total_tracked - successful,
            success_rate=success_rate,
            strong_success_rate=strong_success,
            emerging_success_rate=emerging_success,
            watch_success_rate=watch_success,
            top_predictive_metrics=top_metrics,
            threshold_recommendations=recommendations
        )
    
    def _identify_top_metrics(self, tracked: List[BreakoutPrediction]) -> List[Dict]:
        """Identify which metrics are most predictive of success"""
        metric_performance = defaultdict(lambda: {'appearances': 0, 'successes': 0})
        
        for pred in tracked:
            is_success = pred.was_successful
            
            for metric in pred.improving_metrics:
                metric_performance[metric]['appearances'] += 1
                if is_success:
                    metric_performance[metric]['successes'] += 1
        
        # Calculate success rate per metric
        metric_stats = []
        for metric, stats in metric_performance.items():
            if stats['appearances'] >= 3:  # At least 3 appearances
                success_rate = (stats['successes'] / stats['appearances'] * 100)
                metric_stats.append({
                    'metric': metric,
                    'success_rate': success_rate,
                    'appearances': stats['appearances']
                })
        
        # Sort by success rate
        metric_stats.sort(key=lambda x: x['success_rate'], reverse=True)
        return metric_stats[:10]
    
    def _generate_recommendations(
        self,
        overall_success: float,
        strong_success: float,
        emerging_success: float,
        watch_success: float
    ) -> Dict[str, str]:
        """Generate recommendations for threshold tuning"""
        recommendations = {}
        
        if overall_success < 40:
            recommendations['overall'] = "Success rate low. Consider increasing thresholds to be more selective."
        elif overall_success > 80:
            recommendations['overall'] = "Success rate high. Consider lowering thresholds to catch more breakouts."
        else:
            recommendations['overall'] = "Success rate good. Current thresholds are well-calibrated."
        
        if strong_success < 70:
            recommendations['strong'] = "STRONG signals underperforming. Increase confidence threshold for STRONG classification."
        
        if emerging_success < 50:
            recommendations['emerging'] = "EMERGING signals weak. Review EMERGING criteria."
        
        return recommendations
    
    def print_report(self):
        """Print a detailed tracking report"""
        stats = self.get_stats()
        
        print("\n" + "="*70)
        print("🔬 BREAKOUT PREDICTION TRACKER - PERFORMANCE REPORT")
        print("="*70)
        
        print(f"\n📊 Overall Statistics:")
        print(f"  Total Predictions: {stats.total_predictions}")
        print(f"  • STRONG signals: {stats.strong_signals}")
        print(f"  • EMERGING signals: {stats.emerging_signals}")
        print(f"  • WATCH signals: {stats.watch_signals}")
        
        if stats.total_tracked > 0:
            print(f"\n✅ Outcomes Tracked (30+ days old):")
            print(f"  Total Tracked: {stats.total_tracked}")
            print(f"  Successful Breakouts: {stats.successful_breakouts}")
            print(f"  False Positives: {stats.false_positives}")
            print(f"  Overall Success Rate: {stats.success_rate:.1f}%")
            
            print(f"\n📈 Success Rate by Signal Type:")
            print(f"  STRONG: {stats.strong_success_rate:.1f}%")
            print(f"  EMERGING: {stats.emerging_success_rate:.1f}%")
            print(f"  WATCH: {stats.watch_success_rate:.1f}%")
            
            if stats.top_predictive_metrics:
                print(f"\n🎯 Most Predictive Metrics:")
                for metric in stats.top_predictive_metrics[:5]:
                    print(f"  • {metric['metric']}: {metric['success_rate']:.1f}% ({metric['appearances']} samples)")
            
            if stats.threshold_recommendations:
                print(f"\n💡 Recommendations:")
                for category, rec in stats.threshold_recommendations.items():
                    print(f"  • {category.title()}: {rec}")
        else:
            print(f"\n⏳ No outcomes tracked yet (need 30+ days of data)")
        
        print("\n" + "="*70 + "\n")
