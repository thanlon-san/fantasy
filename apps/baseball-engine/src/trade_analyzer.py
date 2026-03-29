#!/usr/bin/env python3
"""
Category-Impact Trade Analyzer

Evaluates trades based on your specific league standings.
1. Input: give Player A, get Player B
2. Simulate: remove A from roster projections, add B
3. Recalculate projected weekly category totals for all 12 cats
4. Compare new projections against league averages
5. Output: per-category rank changes and net weekly win probability delta.

Requires ROS projections (Phase 2A) for projected player values.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .projection_fetcher import (
    ProjectionFetcher,
    HitterProjection,
    PitcherProjection,
    _normalize,
)

logger = logging.getLogger(__name__)

REMAINING_WEEKS = 22  # ~22 weeks in a standard MLB fantasy season (adjust mid-season)


@dataclass
class CategoryImpact:
    """Impact of a trade on a single scoring category."""
    stat_id: str
    name: str
    label: str
    group: str
    better: str
    before_value: float
    after_value: float
    delta: float
    before_rank: Optional[int] = None
    after_rank: Optional[int] = None
    rank_change: int = 0  # negative = improved (lower rank number)
    verdict: str = ""     # "gain", "loss", "neutral"


@dataclass
class TradeResult:
    """Full analysis of a proposed trade."""
    give_player: str
    get_player: str
    give_is_pitcher: bool
    get_is_pitcher: bool
    categories: List[CategoryImpact] = field(default_factory=list)
    cats_gained: int = 0
    cats_lost: int = 0
    cats_neutral: int = 0
    net_rank_change: float = 0.0
    win_probability_delta: float = 0.0
    summary: str = ""
    give_ros_value: Optional[float] = None
    get_ros_value: Optional[float] = None


STAT_MAP = {
    "7":  {"name": "R",    "label": "Runs",          "group": "batting",  "better": "high"},
    "8":  {"name": "H",    "label": "Hits",           "group": "batting",  "better": "high"},
    "12": {"name": "HR",   "label": "Home Runs",      "group": "batting",  "better": "high"},
    "13": {"name": "RBI",  "label": "RBI",            "group": "batting",  "better": "high"},
    "16": {"name": "SB",   "label": "Stolen Bases",   "group": "batting",  "better": "high"},
    "55": {"name": "OPS",  "label": "OPS",            "group": "batting",  "better": "high"},
    "32": {"name": "SV",   "label": "Saves",          "group": "pitching", "better": "high"},
    "38": {"name": "HR",   "label": "HR Allowed",     "group": "pitching", "better": "low"},
    "42": {"name": "K",    "label": "Strikeouts",     "group": "pitching", "better": "high"},
    "26": {"name": "ERA",  "label": "ERA",            "group": "pitching", "better": "low"},
    "27": {"name": "WHIP", "label": "WHIP",           "group": "pitching", "better": "low"},
    "83": {"name": "QS",   "label": "Quality Starts", "group": "pitching", "better": "high"},
}


def _hitter_weekly_stats(proj: HitterProjection) -> Dict[str, float]:
    """Convert ROS hitter projection to estimated weekly category contributions."""
    weekly_pa = proj.pa / REMAINING_WEEKS
    rate = weekly_pa / 600.0  # rough scaling

    # Estimate weekly counting stats from ROS totals
    weekly_r = proj.rbi * 0.85 / REMAINING_WEEKS  # R correlates with RBI
    weekly_h = (proj.avg * weekly_pa * 0.93)       # H ~ AVG * AB (AB ≈ 93% of PA)
    weekly_hr = proj.hr / REMAINING_WEEKS
    weekly_rbi = proj.rbi / REMAINING_WEEKS
    weekly_sb = proj.sb / REMAINING_WEEKS

    # Runs: estimate from wRC+ as proxy (league avg ~4.5 R/game, 9 hitters)
    # Better hitters score more runs proportionally
    weekly_r = max(weekly_r, (proj.wrc_plus / 100.0) * 4.0 * rate)

    return {
        "7": weekly_r,
        "8": weekly_h,
        "12": weekly_hr,
        "13": weekly_rbi,
        "16": weekly_sb,
        "55": proj.ops,  # rate stat — use directly
    }


def _pitcher_weekly_stats(proj: PitcherProjection) -> Dict[str, float]:
    """Convert ROS pitcher projection to estimated weekly category contributions."""
    weekly_ip = proj.ip / REMAINING_WEEKS

    weekly_k = proj.k / REMAINING_WEEKS
    weekly_qs = proj.qs / REMAINING_WEEKS

    # HR allowed: estimate from ERA (roughly ERA * IP / 9 * 0.11)
    season_hr_allowed = proj.era * proj.ip / 9.0 * 0.11
    weekly_hr_allowed = season_hr_allowed / REMAINING_WEEKS

    return {
        "42": weekly_k,
        "26": proj.era,   # rate stat
        "27": proj.whip,  # rate stat
        "83": weekly_qs,
        "32": 0.0,        # SV not in standard projections (handled by bullpen tracker)
        "38": weekly_hr_allowed,
    }


class TradeAnalyzer:
    """Analyzes the category impact of a proposed trade."""

    def __init__(self, projections: Optional[ProjectionFetcher] = None):
        self.projections = projections or ProjectionFetcher()
        self.projections.load()

    def _get_projection(self, name: str) -> Tuple[Optional[object], bool]:
        """Look up projection, return (projection, is_pitcher)."""
        pitcher = self.projections.get_pitcher(name)
        if pitcher:
            return pitcher, True
        hitter = self.projections.get_hitter(name)
        if hitter:
            return hitter, False
        return None, False

    def _player_weekly_contribution(self, name: str) -> Tuple[Dict[str, float], bool]:
        """Get a player's weekly stat contributions from projections."""
        proj, is_pitcher = self._get_projection(name)
        if proj is None:
            return {}, False
        if is_pitcher:
            return _pitcher_weekly_stats(proj), True
        return _hitter_weekly_stats(proj), False

    def analyze(
        self,
        give_player: str,
        get_player: str,
        my_cat_values: Optional[Dict[str, float]] = None,
        league_cat_values: Optional[List[Dict[str, float]]] = None,
    ) -> TradeResult:
        """
        Analyze a trade: give_player leaves your roster, get_player joins.

        Args:
            give_player: Name of player you're trading away
            get_player: Name of player you're receiving
            my_cat_values: Your team's current season stats {stat_id: value}
            league_cat_values: List of all teams' stats [{stat_id: value}, ...]
        """
        give_weekly, give_is_pitcher = self._player_weekly_contribution(give_player)
        get_weekly, get_is_pitcher = self._player_weekly_contribution(get_player)

        give_proj, _ = self._get_projection(give_player)
        get_proj, _ = self._get_projection(get_player)

        result = TradeResult(
            give_player=give_player,
            get_player=get_player,
            give_is_pitcher=give_is_pitcher,
            get_is_pitcher=get_is_pitcher,
            give_ros_value=round(give_proj.ros_value, 1) if give_proj else None,
            get_ros_value=round(get_proj.ros_value, 1) if get_proj else None,
        )

        if not give_weekly and not get_weekly:
            result.summary = f"No projections found for either {give_player} or {get_player}."
            return result

        # Compute category-by-category impact
        rate_stats = {"55", "26", "27"}  # OPS, ERA, WHIP — compare rate changes differently

        for sid, meta in STAT_MAP.items():
            give_val = give_weekly.get(sid, 0.0)
            get_val = get_weekly.get(sid, 0.0)

            if sid in rate_stats:
                # For rate stats, the "delta" is the difference in the rate
                before = give_val if give_val else 0.0
                after = get_val if get_val else 0.0
                delta = after - before
            else:
                delta = get_val - give_val
                before = give_val
                after = get_val

            # Determine if delta is good or bad
            if meta["better"] == "high":
                is_gain = delta > 0
            else:
                is_gain = delta < 0

            threshold = 0.001 if sid in rate_stats else 0.05
            if abs(delta) < threshold:
                verdict = "neutral"
            elif is_gain:
                verdict = "gain"
            else:
                verdict = "loss"

            # Compute rank changes if league data is available
            before_rank = None
            after_rank = None
            rank_change = 0
            if my_cat_values and league_cat_values:
                my_current = my_cat_values.get(sid)
                if my_current is not None:
                    before_rank = self._compute_rank(
                        my_current, sid, meta, league_cat_values
                    )
                    adjusted = my_current + delta if sid not in rate_stats else my_current
                    if sid in rate_stats and get_val and give_val:
                        # Weighted average shift for rate stats
                        adjusted = my_current + (get_val - give_val) * 0.08
                    after_rank = self._compute_rank(
                        adjusted, sid, meta, league_cat_values
                    )
                    rank_change = after_rank - before_rank

            impact = CategoryImpact(
                stat_id=sid,
                name=meta["name"],
                label=meta["label"],
                group=meta["group"],
                better=meta["better"],
                before_value=round(before, 3),
                after_value=round(after, 3),
                delta=round(delta, 3),
                before_rank=before_rank,
                after_rank=after_rank,
                rank_change=rank_change,
                verdict=verdict,
            )
            result.categories.append(impact)

        result.cats_gained = sum(1 for c in result.categories if c.verdict == "gain")
        result.cats_lost = sum(1 for c in result.categories if c.verdict == "loss")
        result.cats_neutral = sum(1 for c in result.categories if c.verdict == "neutral")

        # Net rank change (negative = improvement)
        rank_changes = [c.rank_change for c in result.categories if c.rank_change != 0]
        result.net_rank_change = round(sum(rank_changes) / len(rank_changes), 1) if rank_changes else 0.0

        # Win probability delta: each category gained ≈ +1/12 win, lost ≈ -1/12 win
        # Weighted by how much the rank actually moved
        wp_delta = 0.0
        for c in result.categories:
            if c.rank_change < 0:
                wp_delta += abs(c.rank_change) * (100 / 12 / 6)
            elif c.rank_change > 0:
                wp_delta -= c.rank_change * (100 / 12 / 6)
        result.win_probability_delta = round(wp_delta, 1)

        # Build summary
        gains = [c.label for c in result.categories if c.verdict == "gain"]
        losses = [c.label for c in result.categories if c.verdict == "loss"]
        parts = []
        if gains:
            parts.append(f"Improves: {', '.join(gains[:4])}")
        if losses:
            parts.append(f"Hurts: {', '.join(losses[:4])}")
        if result.win_probability_delta > 0:
            parts.append(f"Net weekly win probability: +{result.win_probability_delta}%")
        elif result.win_probability_delta < 0:
            parts.append(f"Net weekly win probability: {result.win_probability_delta}%")
        else:
            parts.append("Net impact: roughly neutral")
        result.summary = " | ".join(parts)

        return result

    @staticmethod
    def _compute_rank(
        my_value: float,
        stat_id: str,
        meta: dict,
        league_values: List[Dict[str, float]],
    ) -> int:
        """Compute rank (1 = best) for a stat value against league."""
        all_vals = [my_value]
        for team_stats in league_values:
            v = team_stats.get(stat_id)
            if v is not None:
                all_vals.append(v)

        reverse = meta["better"] == "high"
        sorted_vals = sorted(all_vals, reverse=reverse)
        try:
            return sorted_vals.index(my_value) + 1
        except ValueError:
            return len(sorted_vals)

    def search_players(self, query: str, limit: int = 10) -> List[dict]:
        """Search projections for player names matching a query."""
        self.projections.load()
        query_norm = _normalize(query)
        results = []

        for key, proj in self.projections._hitter_cache.items():
            if query_norm in key:
                results.append({
                    "name": proj.name,
                    "team": proj.team,
                    "type": "hitter",
                    "ros_value": round(proj.ros_value, 1),
                })
        for key, proj in self.projections._pitcher_cache.items():
            if query_norm in key:
                results.append({
                    "name": proj.name,
                    "team": proj.team,
                    "type": "pitcher",
                    "ros_value": round(proj.ros_value, 1),
                })

        results.sort(key=lambda x: x["ros_value"], reverse=True)
        return results[:limit]
