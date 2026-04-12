#!/usr/bin/env python3
"""
Regression Candidates Engine
Identifies buy-low / sell-high players by comparing actual stats to expected stats.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .statcast_client import StatcastClient
from .cache_manager import get_cache

logger = logging.getLogger(__name__)

HITTER_DELTA_THRESHOLD = 0.030  # 30-point BA gap
PITCHER_ERA_THRESHOLD = 0.75    # ERA vs xERA gap
PITCHER_FIP_THRESHOLD = 0.60    # FIP vs ERA gap


@dataclass
class RegressionCandidate:
    """A player flagged for positive or negative regression."""

    name: str
    player_type: str          # "hitter" or "pitcher"
    team: str
    position: str
    direction: str            # "BUY_LOW" or "SELL_HIGH"

    # Hitter fields
    ba: Optional[float] = None
    xba: Optional[float] = None
    slg: Optional[float] = None
    xslg: Optional[float] = None
    woba: Optional[float] = None
    xwoba: Optional[float] = None
    ba_delta: Optional[float] = None

    # Pitcher fields
    era: Optional[float] = None
    xera: Optional[float] = None
    fip: Optional[float] = None
    era_fip_delta: Optional[float] = None
    era_xera_delta: Optional[float] = None

    confidence: float = 0.0
    summary: str = ""
    improving_metrics: List[str] = field(default_factory=list)


class RegressionAnalyzer:
    """Scans players for regression candidates using xStats from Statcast."""

    def __init__(self):
        self.statcast = StatcastClient()
        self.cache = get_cache()

    def analyze_hitter(
        self,
        first_name: str,
        last_name: str,
        team: str = "",
        position: str = "",
        days_back: int = 60,
    ) -> Optional[RegressionCandidate]:
        """Analyze a hitter for xBA / xSLG / xwOBA regression."""
        player_name = f"{first_name} {last_name}"
        cache_key = f"regression_h_{player_name}_{datetime.now().strftime('%Y-%m-%d')}"
        cached = self.cache.get(cache_key, max_age_hours=12)
        if cached is not None:
            return cached

        pid = self.statcast.get_player_id(first_name, last_name)
        if not pid:
            return None

        start, end = self.statcast._get_analysis_dates(days_back)
        data = self.statcast.get_hitter_stats(pid, start, end)
        if data is None or data.empty:
            return None

        metrics = self.statcast.calculate_hitter_metrics(data)
        xba = metrics.get("xBA")
        xslg = metrics.get("xSLG")
        xwoba = metrics.get("xwOBA")

        if xba is None:
            return None

        # Compute actual BA from events
        if "events" not in data.columns:
            return None

        events = data[data["events"].notna()]
        pas = len(events)
        if pas < 50:
            return None

        hits = events["events"].isin(["single", "double", "triple", "home_run"]).sum()
        actual_ba = hits / pas if pas > 0 else 0

        # Compute actual SLG
        singles = (events["events"] == "single").sum()
        doubles = (events["events"] == "double").sum()
        triples = (events["events"] == "triple").sum()
        homers = (events["events"] == "home_run").sum()
        abs_count = events["events"].isin(
            ["single", "double", "triple", "home_run",
             "field_out", "strikeout", "grounded_into_double_play",
             "force_out", "double_play", "fielders_choice_out",
             "field_error", "strikeout_double_play"]
        ).sum()
        total_bases = singles + 2 * doubles + 3 * triples + 4 * homers
        actual_slg = total_bases / abs_count if abs_count > 0 else 0

        ba_delta = xba - actual_ba
        improving = []
        direction = None
        confidence = 0.0

        if ba_delta >= HITTER_DELTA_THRESHOLD:
            direction = "BUY_LOW"
            confidence = min(100, 40 + abs(ba_delta) * 800)
            improving.append(f"xBA {xba:.3f} vs BA {actual_ba:.3f} (Δ{ba_delta:+.3f})")
        elif ba_delta <= -HITTER_DELTA_THRESHOLD:
            direction = "SELL_HIGH"
            confidence = min(100, 40 + abs(ba_delta) * 800)
            improving.append(f"BA {actual_ba:.3f} vs xBA {xba:.3f} (over-performing by {-ba_delta:.3f})")

        if xslg is not None:
            slg_delta = xslg - actual_slg
            if abs(slg_delta) >= 0.040:
                improving.append(f"xSLG {xslg:.3f} vs SLG {actual_slg:.3f}")
                confidence += 10

        if xwoba is not None:
            improving.append(f"xwOBA {xwoba:.3f}")

        if direction is None:
            self.cache.set(cache_key, None)
            return None

        summary = (
            f"{player_name} is {'underperforming' if direction == 'BUY_LOW' else 'overperforming'} "
            f"expected stats. xBA {xba:.3f} vs actual BA {actual_ba:.3f}."
        )

        candidate = RegressionCandidate(
            name=player_name,
            player_type="hitter",
            team=team,
            position=position,
            direction=direction,
            ba=round(actual_ba, 3),
            xba=round(xba, 3),
            slg=round(actual_slg, 3),
            xslg=round(xslg, 3) if xslg else None,
            woba=None,
            xwoba=round(xwoba, 3) if xwoba else None,
            ba_delta=round(ba_delta, 3),
            confidence=round(confidence, 1),
            summary=summary,
            improving_metrics=improving,
        )
        self.cache.set(cache_key, candidate)
        return candidate

    def analyze_pitcher(
        self,
        first_name: str,
        last_name: str,
        team: str = "",
        position: str = "",
        days_back: int = 60,
    ) -> Optional[RegressionCandidate]:
        """Analyze a pitcher for ERA vs xERA / FIP regression."""
        player_name = f"{first_name} {last_name}"
        cache_key = f"regression_p_{player_name}_{datetime.now().strftime('%Y-%m-%d')}"
        cached = self.cache.get(cache_key, max_age_hours=12)
        if cached is not None:
            return cached

        pid = self.statcast.get_player_id(first_name, last_name)
        if not pid:
            return None

        # Get FIP data from the existing method
        fip_data = self.statcast.calculate_pitcher_fip(pid, days_back=days_back)
        if not fip_data:
            return None

        fip = fip_data["fip"]

        # Get xERA proxy from xwOBA against — compute from raw data
        start, end = self.statcast._get_analysis_dates(days_back)
        data = self.statcast.get_pitcher_stats(pid, start, end)
        if data is None or data.empty:
            return None

        metrics = self.statcast.calculate_pitcher_metrics(data)
        xwoba_against = metrics.get("xwOBA_against")

        # Estimate ERA from the raw data
        events = data[data["events"].notna()]
        batters_faced = len(events)
        if batters_faced < 30:
            return None

        out_events = events["events"].isin([
            "strikeout", "field_out", "grounded_into_double_play",
            "force_out", "double_play", "fielders_choice_out",
            "strikeout_double_play", "sac_fly", "sac_bunt",
        ])
        outs = out_events.sum()
        ip = outs / 3.0
        if ip < 10:
            return None

        # Count earned runs: this is imprecise from Statcast data; use runs scored
        # as a proxy (not all are earned but close enough for regression detection)
        runs = events["events"].isin(["home_run"]).sum()  # HR = guaranteed run
        # Better proxy: use the FIP-based ERA estimate
        # ERA ≈ FIP for FIP-based analysis; but we want *actual* ERA.
        # Since we can't compute true ERA from Statcast pitch data, we approximate:
        # xERA ≈ (xwOBA_against - .310) / .025 * 0.92 + 3.50 (rough mapping)
        xera = None
        if xwoba_against is not None and xwoba_against > 0:
            xera = max(1.0, (xwoba_against - 0.310) / 0.025 * 0.92 + 3.50)

        improving = []
        direction = None
        confidence = 0.0

        # FIP vs estimated ERA gap
        # A pitcher whose FIP is much lower than their xERA-proxy is unlucky
        if xera is not None:
            era_fip_delta = xera - fip
            if era_fip_delta >= PITCHER_FIP_THRESHOLD:
                direction = "BUY_LOW"
                confidence = min(100, 40 + abs(era_fip_delta) * 30)
                improving.append(f"FIP {fip:.2f} vs xERA ~{xera:.2f} (unlucky, Δ{era_fip_delta:+.2f})")
            elif era_fip_delta <= -PITCHER_FIP_THRESHOLD:
                direction = "SELL_HIGH"
                confidence = min(100, 40 + abs(era_fip_delta) * 30)
                improving.append(f"FIP {fip:.2f} vs xERA ~{xera:.2f} (lucky, Δ{era_fip_delta:+.2f})")
        else:
            era_fip_delta = None

        if direction is None:
            self.cache.set(cache_key, None)
            return None

        if xwoba_against is not None:
            improving.append(f"xwOBA against: {xwoba_against:.3f}")

        improving.append(f"K-BB%: {fip_data['k_bb_pct']:.1f}%")

        summary = (
            f"{player_name} {'FIP ({fip:.2f}) much lower than expected ERA — buy low'}"
            if direction == "BUY_LOW"
            else f"{player_name} over-performing peripherals — sell high"
        )

        # era_fip_delta is xera - fip (positive = pitcher is unlucky / buy-low)
        # We set `era` to fip (the peripheral-based ERA stand-in we actually use)
        # and `xera` to the xwOBA-derived expected ERA proxy, so the UI delta
        # reflects a real gap rather than comparing a value to itself.
        candidate = RegressionCandidate(
            name=player_name,
            player_type="pitcher",
            team=team,
            position=position,
            direction=direction,
            era=round(fip, 2),
            xera=round(xera, 2) if xera else None,
            fip=round(fip, 2),
            era_fip_delta=round(era_fip_delta, 2) if era_fip_delta else None,
            confidence=round(confidence, 1),
            summary=summary,
            improving_metrics=improving,
        )
        self.cache.set(cache_key, candidate)
        return candidate

    def scan_players(
        self,
        players: List[Dict],
        max_results: int = 20,
    ) -> Dict[str, List[RegressionCandidate]]:
        """Scan a list of players and return buy-low and sell-high candidates.

        Args:
            players: list of dicts with keys: name, position, team
            max_results: max per category

        Returns:
            {"buy_low": [...], "sell_high": [...]}
        """
        buy_low: List[RegressionCandidate] = []
        sell_high: List[RegressionCandidate] = []

        for p in players:
            name = p.get("name", "")
            parts = name.split()
            if len(parts) < 2:
                continue
            first = parts[0]
            last = " ".join(parts[1:])
            pos = p.get("position", "")
            team = p.get("team", "")

            is_pitcher = any(x in pos for x in ("SP", "RP", "P"))
            try:
                if is_pitcher:
                    cand = self.analyze_pitcher(first, last, team, pos)
                else:
                    cand = self.analyze_hitter(first, last, team, pos)
            except Exception as e:
                logger.debug(f"Regression analysis failed for {name}: {e}")
                continue

            if cand is None:
                continue

            if cand.direction == "BUY_LOW":
                buy_low.append(cand)
            else:
                sell_high.append(cand)

        buy_low.sort(key=lambda c: c.confidence, reverse=True)
        sell_high.sort(key=lambda c: c.confidence, reverse=True)

        return {
            "buy_low": buy_low[:max_results],
            "sell_high": sell_high[:max_results],
        }
