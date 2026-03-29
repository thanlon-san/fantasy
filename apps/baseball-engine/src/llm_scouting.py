#!/usr/bin/env python3
"""
LLM-Powered Scouting Reports

Generates natural language scouting reports using Claude or GPT:
- Weekly opponent scouting narrative
- Trade evaluation prose
- Breakout player deep-dives

Gated behind ANTHROPIC_API_KEY or OPENAI_API_KEY env vars (optional).
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

APP_ROOT = Path(__file__).parent.parent
WORKSPACE = APP_ROOT.parent.parent
sys.path.insert(0, str(WORKSPACE / "packages"))

from shared.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert fantasy baseball analyst for a competitive 12-team H2H categories league.

Scoring categories:
- Batting: R, H, HR, RBI, SB, OPS
- Pitching: SV, HR allowed, K, ERA, WHIP, QS

League strategy: Stack closers to dominate ERA/WHIP/SV/HR-allowed (4 of 6 pitching cats).
Manufacture Ks via streaming. Win batting through lineup optimization and waiver aggression.

Write concise, actionable scouting reports. Use specific numbers when available.
Prioritize what the manager should DO, not just observe. Keep reports under 500 words."""


class LLMScoutingReporter:
    """Generate LLM-powered scouting reports for fantasy baseball."""

    def __init__(self):
        self.llm = LLMClient()
        self._anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self._openai_key = os.environ.get("OPENAI_API_KEY")

    @property
    def available(self) -> bool:
        return bool(self._anthropic_key or self._openai_key)

    def _generate(self, user_prompt: str, max_tokens: int = 1500) -> Optional[str]:
        if self._anthropic_key:
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=self._anthropic_key)
                return self.llm.generate_with_anthropic(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    client=client,
                    model="claude-sonnet-4-5-20250929",
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.warning(f"Anthropic generation failed: {e}")

        if self._openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self._openai_key)
                return self.llm.generate_with_openai(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    client=client,
                    model="gpt-4o",
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.warning(f"OpenAI generation failed: {e}")

        return None

    def opponent_scouting(self, matchup_data: dict, opponent_data: dict) -> Optional[str]:
        """Generate a weekly opponent scouting narrative."""
        if not self.available:
            return None

        cats = matchup_data.get("categories", [])
        cat_lines = []
        for c in cats:
            my = c.get("my_value", "?")
            opp = c.get("opp_value", "?")
            status = c.get("status", "unknown")
            cat_lines.append(f"  {c['label']}: Me {my} vs Opp {opp} ({status})")

        opp_name = matchup_data.get("opp_team", "Unknown")
        strengths = opponent_data.get("their_strengths", [])
        weaknesses = opponent_data.get("their_weaknesses", [])
        advantages = opponent_data.get("your_advantages", [])

        prompt = f"""Generate a weekly matchup scouting report.

Opponent: {opp_name}
Week: {matchup_data.get('week', '?')}

Category Breakdown:
{chr(10).join(cat_lines)}

Opponent Strengths: {', '.join(strengths) if strengths else 'None identified'}
Opponent Weaknesses: {', '.join(weaknesses) if weaknesses else 'None identified'}
My Advantages: {', '.join(advantages) if advantages else 'None identified'}

Write a 3-paragraph scouting report: (1) overall matchup assessment, (2) categories to target and protect, (3) specific lineup/streaming moves for the week."""

        return self._generate(prompt)

    def trade_evaluation(self, trade_result: dict) -> Optional[str]:
        """Generate a trade evaluation narrative."""
        if not self.available:
            return None

        give = trade_result.get("give_player", "?")
        get_p = trade_result.get("get_player", "?")
        cats = trade_result.get("categories", [])
        summary = trade_result.get("summary", "")
        win_delta = trade_result.get("win_probability_delta", 0)

        cat_lines = []
        for c in cats:
            verdict = c.get("verdict", "neutral")
            delta = c.get("delta", 0)
            cat_lines.append(f"  {c['label']}: {verdict} ({delta:+.1f})")

        prompt = f"""Evaluate this proposed fantasy baseball trade.

Trade: Give {give}, Get {get_p}
Win Probability Change: {win_delta:+.1f}%
Summary: {summary}

Category Impact:
{chr(10).join(cat_lines)}

Write a 2-paragraph analysis: (1) whether to make this trade and why, (2) how it changes your roster construction and weekly strategy."""

        return self._generate(prompt)

    def breakout_deep_dive(self, alert_data: dict) -> Optional[str]:
        """Generate a breakout player deep-dive."""
        if not self.available:
            return None

        name = alert_data.get("player", alert_data.get("player_name", "?"))
        signal = alert_data.get("signal", "?")
        confidence = alert_data.get("confidence", 0)
        improving = alert_data.get("improving", alert_data.get("improving_metrics", []))
        summary = alert_data.get("summary", "")

        prompt = f"""Write a breakout deep-dive for a fantasy baseball player.

Player: {name}
Signal: {signal} (confidence: {confidence:.0f}%)
Improving Metrics: {', '.join(improving[:5]) if improving else 'N/A'}
Summary: {summary}

Write a 2-paragraph analysis: (1) what's changed mechanically and why it matters for fantasy, (2) how aggressively to acquire this player and in which league formats."""

        return self._generate(prompt)

    def weekly_newsletter(
        self,
        matchup_data: Optional[dict] = None,
        breakout_alerts: Optional[list] = None,
        waiver_targets: Optional[list] = None,
        bullpen_alerts: Optional[list] = None,
    ) -> Optional[str]:
        """Generate a comprehensive weekly newsletter."""
        if not self.available:
            return None

        sections = []

        if matchup_data and matchup_data.get("opp_team"):
            sections.append(f"Matchup: vs {matchup_data['opp_team']} (Week {matchup_data.get('week', '?')})")
            swing = [c for c in matchup_data.get("categories", []) if c.get("status", "").startswith("close_")]
            if swing:
                sections.append(f"Swing categories: {', '.join(c['label'] for c in swing)}")

        if breakout_alerts:
            strong = [a for a in breakout_alerts if a.get("signal") == "STRONG"]
            if strong:
                names = ", ".join(a.get("player", "?") for a in strong[:3])
                sections.append(f"Breakout alerts (STRONG): {names}")

        if waiver_targets:
            top = waiver_targets[:3]
            names = ", ".join(t.get("player", "?") for t in top)
            sections.append(f"Top waiver targets: {names}")

        if bullpen_alerts:
            closers = ", ".join(f"{a.get('closer', '?')} ({a.get('fatigue_level', '?')})" for a in bullpen_alerts[:3])
            sections.append(f"Bullpen alerts: {closers}")

        if not sections:
            return None

        prompt = f"""Write a concise weekly fantasy baseball newsletter (4-5 paragraphs) covering:

{chr(10).join(f'- {s}' for s in sections)}

Structure: (1) headline move of the week, (2) matchup strategy, (3) waiver priorities, (4) closing notes and what to watch."""

        return self._generate(prompt, max_tokens=2000)
