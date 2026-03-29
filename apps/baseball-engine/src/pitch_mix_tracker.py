#!/usr/bin/env python3
"""
Pitch Mix Evolution Detector

Tracks when a pitcher:
- Adds a new pitch type (sweeper, cutter, etc.)
- Changes usage% on an existing pitch by >10%
- Gains 2+ mph on fastball velocity
- Adds 200+ RPM on breaking balls

These changes precede ERA improvements by 2–4 weeks — the strongest
single predictor of pitcher breakouts in modern baseball.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .statcast_client import StatcastClient
from .cache_manager import get_cache

logger = logging.getLogger(__name__)

PITCH_TYPE_NAMES = {
    "FF": "4-Seam Fastball",
    "SI": "Sinker",
    "FT": "2-Seam Fastball",
    "FC": "Cutter",
    "SL": "Slider",
    "CU": "Curveball",
    "KC": "Knuckle Curve",
    "SV": "Sweeper",
    "CS": "Slow Curve",
    "CH": "Changeup",
    "FS": "Splitter",
    "SC": "Screwball",
    "KN": "Knuckleball",
    "ST": "Sweeper",
    "EP": "Eephus",
}

FASTBALL_TYPES = {"FF", "SI", "FT", "FC"}
BREAKING_TYPES = {"SL", "CU", "KC", "SV", "CS", "ST"}
OFFSPEED_TYPES = {"CH", "FS", "SC"}

MIN_PITCHES_RECENT = 50
MIN_PITCHES_BASELINE = 100
NEW_PITCH_MIN_USAGE_PCT = 5.0
USAGE_CHANGE_THRESHOLD = 10.0
VELO_GAIN_THRESHOLD = 2.0
RPM_GAIN_THRESHOLD = 200


@dataclass
class PitchTypeProfile:
    """Profile for a single pitch type in a given window."""
    pitch_type: str
    name: str
    usage_pct: float
    avg_velo: Optional[float]
    avg_spin: Optional[float]
    whiff_pct: Optional[float]
    count: int


@dataclass
class PitchMixChange:
    """A detected change in a pitcher's arsenal."""
    change_type: str  # "new_pitch" | "usage_increase" | "usage_decrease" | "velo_gain" | "rpm_gain"
    pitch_type: str
    pitch_name: str
    description: str
    magnitude: float  # size of change (pct points, mph, or RPM)
    impact: str       # "positive" | "negative" | "neutral"


@dataclass
class PitchMixEvolution:
    """Full pitch mix evolution analysis for a pitcher."""
    pitcher_name: str
    pitcher_id: int
    changes: List[PitchMixChange] = field(default_factory=list)
    recent_mix: List[PitchTypeProfile] = field(default_factory=list)
    baseline_mix: List[PitchTypeProfile] = field(default_factory=list)
    total_changes: int = 0
    breakout_score: float = 0.0  # 0-100 contribution to breakout confidence
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "pitcher_name": self.pitcher_name,
            "pitcher_id": self.pitcher_id,
            "changes": [
                {
                    "change_type": c.change_type,
                    "pitch_type": c.pitch_type,
                    "pitch_name": c.pitch_name,
                    "description": c.description,
                    "magnitude": round(c.magnitude, 1),
                    "impact": c.impact,
                }
                for c in self.changes
            ],
            "recent_mix": [
                {
                    "pitch_type": p.pitch_type,
                    "name": p.name,
                    "usage_pct": round(p.usage_pct, 1),
                    "avg_velo": round(p.avg_velo, 1) if p.avg_velo else None,
                    "avg_spin": round(p.avg_spin, 0) if p.avg_spin else None,
                    "whiff_pct": round(p.whiff_pct, 1) if p.whiff_pct else None,
                    "count": p.count,
                }
                for p in self.recent_mix
            ],
            "baseline_mix": [
                {
                    "pitch_type": p.pitch_type,
                    "name": p.name,
                    "usage_pct": round(p.usage_pct, 1),
                    "avg_velo": round(p.avg_velo, 1) if p.avg_velo else None,
                    "avg_spin": round(p.avg_spin, 0) if p.avg_spin else None,
                    "whiff_pct": round(p.whiff_pct, 1) if p.whiff_pct else None,
                    "count": p.count,
                }
                for p in self.baseline_mix
            ],
            "total_changes": self.total_changes,
            "breakout_score": round(self.breakout_score, 1),
            "summary": self.summary,
        }


class PitchMixTracker:
    """Track pitch mix evolution for pitcher breakout detection."""

    CHANGE_WEIGHTS = {
        "new_pitch": 25,
        "velo_gain": 20,
        "rpm_gain": 15,
        "usage_increase": 10,
        "usage_decrease": 5,
    }

    def __init__(self):
        self.statcast = StatcastClient()
        self._cache = get_cache()

    def analyze_pitcher(
        self,
        pitcher_name: str,
        recent_days: int = 14,
        baseline_days: int = 60,
    ) -> Optional[PitchMixEvolution]:
        """
        Analyze a pitcher's pitch mix evolution.

        Compares recent pitch mix (last `recent_days`) against a baseline
        window (`baseline_days` before the recent window) to detect
        arsenal changes that predict future performance gains.
        """
        cache_key = f"pitch_mix_{pitcher_name}_{recent_days}_{baseline_days}"
        cached = self._cache.get(cache_key, max_age_hours=12)
        if cached is not None:
            return cached

        parts = pitcher_name.split()
        if len(parts) < 2:
            return None

        player_id = self.statcast.get_player_id(parts[0], " ".join(parts[1:]))
        if not player_id:
            return None

        recent_start, recent_end = self.statcast._get_analysis_dates(recent_days)
        baseline_end = recent_start
        from datetime import datetime, timedelta
        baseline_start_dt = datetime.strptime(baseline_end, "%Y-%m-%d") - timedelta(days=baseline_days)
        baseline_start = baseline_start_dt.strftime("%Y-%m-%d")

        recent_data = self.statcast.get_pitcher_stats(player_id, recent_start, recent_end)
        baseline_data = self.statcast.get_pitcher_stats(player_id, baseline_start, baseline_end)

        if recent_data is None or recent_data.empty:
            return None
        if baseline_data is None or baseline_data.empty:
            return None

        recent_data = recent_data.dropna(subset=["pitch_type"])
        baseline_data = baseline_data.dropna(subset=["pitch_type"])

        if len(recent_data) < MIN_PITCHES_RECENT or len(baseline_data) < MIN_PITCHES_BASELINE:
            return None

        recent_profiles = self._build_pitch_profiles(recent_data)
        baseline_profiles = self._build_pitch_profiles(baseline_data)

        changes = self._detect_changes(recent_profiles, baseline_profiles)

        breakout_score = self._calculate_breakout_score(changes)
        summary = self._generate_summary(pitcher_name, changes)

        result = PitchMixEvolution(
            pitcher_name=pitcher_name,
            pitcher_id=player_id,
            changes=changes,
            recent_mix=list(recent_profiles.values()),
            baseline_mix=list(baseline_profiles.values()),
            total_changes=len(changes),
            breakout_score=breakout_score,
            summary=summary,
        )

        self._cache.set(cache_key, result)
        return result

    def _build_pitch_profiles(self, data) -> Dict[str, PitchTypeProfile]:
        """Build per-pitch-type profiles from raw Statcast data."""
        profiles = {}
        total_pitches = len(data)
        if total_pitches == 0:
            return profiles

        for pt, group in data.groupby("pitch_type"):
            pt_str = str(pt)
            count = len(group)
            usage_pct = (count / total_pitches) * 100

            avg_velo = None
            if "release_speed" in group.columns:
                valid_velo = group["release_speed"].dropna()
                if len(valid_velo) > 0:
                    avg_velo = float(valid_velo.mean())

            avg_spin = None
            if "release_spin_rate" in group.columns:
                valid_spin = group["release_spin_rate"].dropna()
                if len(valid_spin) > 0:
                    avg_spin = float(valid_spin.mean())

            whiff_pct = None
            if "description" in group.columns:
                swings = group["description"].str.contains("swing|foul", case=False, na=False).sum()
                whiffs = group["description"].str.contains("swinging_strike|foul_tip", case=False, na=False).sum()
                if swings > 0:
                    whiff_pct = (whiffs / swings) * 100

            profiles[pt_str] = PitchTypeProfile(
                pitch_type=pt_str,
                name=PITCH_TYPE_NAMES.get(pt_str, pt_str),
                usage_pct=usage_pct,
                avg_velo=avg_velo,
                avg_spin=avg_spin,
                whiff_pct=whiff_pct,
                count=count,
            )

        return profiles

    def _detect_changes(
        self,
        recent: Dict[str, PitchTypeProfile],
        baseline: Dict[str, PitchTypeProfile],
    ) -> List[PitchMixChange]:
        """Compare recent vs baseline to find meaningful arsenal changes."""
        changes: List[PitchMixChange] = []

        recent_types = set(recent.keys())
        baseline_types = set(baseline.keys())

        for pt in recent_types - baseline_types:
            profile = recent[pt]
            if profile.usage_pct >= NEW_PITCH_MIN_USAGE_PCT:
                changes.append(PitchMixChange(
                    change_type="new_pitch",
                    pitch_type=pt,
                    pitch_name=profile.name,
                    description=f"Added {profile.name} ({profile.usage_pct:.1f}% usage)",
                    magnitude=profile.usage_pct,
                    impact="positive",
                ))

        for pt in recent_types & baseline_types:
            r = recent[pt]
            b = baseline[pt]

            usage_delta = r.usage_pct - b.usage_pct
            if abs(usage_delta) >= USAGE_CHANGE_THRESHOLD:
                if usage_delta > 0:
                    is_whiff_pitch = (r.whiff_pct or 0) > 25
                    impact = "positive" if is_whiff_pitch else "neutral"
                    changes.append(PitchMixChange(
                        change_type="usage_increase",
                        pitch_type=pt,
                        pitch_name=r.name,
                        description=f"{r.name} usage up {usage_delta:+.1f}% ({b.usage_pct:.0f}→{r.usage_pct:.0f}%)",
                        magnitude=usage_delta,
                        impact=impact,
                    ))
                else:
                    changes.append(PitchMixChange(
                        change_type="usage_decrease",
                        pitch_type=pt,
                        pitch_name=r.name,
                        description=f"{r.name} usage down {usage_delta:+.1f}% ({b.usage_pct:.0f}→{r.usage_pct:.0f}%)",
                        magnitude=abs(usage_delta),
                        impact="neutral",
                    ))

            if (
                r.avg_velo is not None
                and b.avg_velo is not None
                and pt in FASTBALL_TYPES
            ):
                velo_delta = r.avg_velo - b.avg_velo
                if velo_delta >= VELO_GAIN_THRESHOLD:
                    changes.append(PitchMixChange(
                        change_type="velo_gain",
                        pitch_type=pt,
                        pitch_name=r.name,
                        description=f"{r.name} velo up {velo_delta:+.1f} mph ({b.avg_velo:.1f}→{r.avg_velo:.1f})",
                        magnitude=velo_delta,
                        impact="positive",
                    ))

            if (
                r.avg_spin is not None
                and b.avg_spin is not None
                and pt in BREAKING_TYPES
            ):
                rpm_delta = r.avg_spin - b.avg_spin
                if rpm_delta >= RPM_GAIN_THRESHOLD:
                    changes.append(PitchMixChange(
                        change_type="rpm_gain",
                        pitch_type=pt,
                        pitch_name=r.name,
                        description=f"{r.name} spin up {rpm_delta:+.0f} RPM ({b.avg_spin:.0f}→{r.avg_spin:.0f})",
                        magnitude=rpm_delta,
                        impact="positive",
                    ))

        return changes

    def _calculate_breakout_score(self, changes: List[PitchMixChange]) -> float:
        """Calculate a 0-100 breakout contribution score from detected changes."""
        if not changes:
            return 0.0

        score = 0.0
        for c in changes:
            base = self.CHANGE_WEIGHTS.get(c.change_type, 5)
            if c.impact == "positive":
                score += base
            elif c.impact == "neutral":
                score += base * 0.5

        return min(100.0, score)

    def _generate_summary(self, name: str, changes: List[PitchMixChange]) -> str:
        if not changes:
            return f"{name}: no significant pitch mix changes detected."

        positive = [c for c in changes if c.impact == "positive"]
        if len(positive) >= 2:
            descs = [c.description for c in positive[:3]]
            return f"{name}: {len(positive)} positive arsenal changes — {'; '.join(descs)}. ERA improvement likely within 2-4 weeks."
        elif len(positive) == 1:
            return f"{name}: {positive[0].description}. Monitor for sustained improvement."
        else:
            descs = [c.description for c in changes[:2]]
            return f"{name}: pitch mix shifting — {'; '.join(descs)}."

    def scan_pitchers(self, pitcher_names: List[str]) -> List[PitchMixEvolution]:
        """Scan a list of pitchers for pitch mix changes. Returns sorted by breakout_score."""
        results = []
        for name in pitcher_names:
            try:
                evo = self.analyze_pitcher(name)
                if evo and evo.total_changes > 0:
                    results.append(evo)
            except Exception as e:
                logger.debug(f"Pitch mix scan failed for {name}: {e}")
        results.sort(key=lambda r: r.breakout_score, reverse=True)
        return results
