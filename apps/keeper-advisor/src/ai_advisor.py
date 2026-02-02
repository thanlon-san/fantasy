"""
AI-Powered Keeper Recommendations
Uses LLM to provide personalized keeper advice
"""

import sys
from pathlib import Path
from typing import List, Optional
import os
from dotenv import load_dotenv

# Add paths for imports
app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.models import Player, KeeperAnalysis, Roster, KeeperScenario
from shared.llm_client import LLMClient
from shared.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class AIKeeperAdvisor:
    """Uses AI to provide keeper recommendations and analysis"""
    
    def __init__(self):
        self.llm = LLMClient()
    
    def get_keeper_advice(
        self,
        roster: Roster,
        analyses: List[KeeperAnalysis],
        scenarios: List[KeeperScenario],
        use_anthropic: bool = True
    ) -> Optional[str]:
        """
        Get AI-powered keeper recommendations
        
        Args:
            roster: The roster being analyzed
            analyses: Keeper analyses for all players
            scenarios: Different keeper scenarios
            use_anthropic: Use Claude (True) or GPT (False)
            
        Returns:
            AI-generated advice text
        """
        logger.info("Generating AI keeper recommendations...")
        
        # Build the context
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(roster, analyses, scenarios)
        
        # Generate recommendations
        try:
            if use_anthropic:
                anthropic_key = os.getenv("ANTHROPIC_API_KEY")
                if not anthropic_key:
                    logger.warning("ANTHROPIC_API_KEY not found, skipping AI recommendations")
                    return None
                
                from anthropic import Anthropic
                client = Anthropic(api_key=anthropic_key)
                
                response = self.llm.generate_with_anthropic(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    client=client,
                    model="claude-sonnet-4-5-20250929",
                    temperature=0.7,
                    max_tokens=2000
                )
            else:
                openai_key = os.getenv("OPENAI_API_KEY")
                if not openai_key:
                    logger.warning("OPENAI_API_KEY not found, skipping AI recommendations")
                    return None
                
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                
                response = self.llm.generate_with_openai(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    client=client,
                    model="gpt-4o",
                    temperature=0.7,
                    max_tokens=2000
                )
            
            return response
        
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI"""
        return """You are an expert fantasy baseball keeper league advisor. Your job is to help managers make optimal keeper decisions based on league rules, player value, and draft strategy.

Your recommendations should consider:
- Keeper cost (draft round penalty)
- Player value vs. draft position (ADP comparison)
- Years of control remaining
- League scarcity at each position
- Draft strategy implications

Provide clear, actionable recommendations with reasoning. Be concise but thorough."""
    
    def _build_user_prompt(
        self,
        roster: Roster,
        analyses: List[KeeperAnalysis],
        scenarios: List[KeeperScenario]
    ) -> str:
        """Build the user prompt with roster data"""
        
        # Get keeper candidates
        keepers = [a for a in analyses if a.recommendation == "Keep"]
        maybes = [a for a in analyses if a.recommendation == "Maybe"]
        
        prompt = f"""# Keeper Decision for {roster.team_name}

## League Rules Summary
- Keep up to 3 players
- Keepers move up one round each year
- 3 years of control (2 years for 2nd rounders)
- Round 12+ players default to 12th round keepers
- Cannot keep 1st round picks

## My Roster Analysis

### Strong Keeper Candidates ({len(keepers)})
"""
        
        for analysis in sorted(keepers, key=lambda a: a.rank or 999)[:5]:
            p = analysis.player
            prompt += f"""
**{p.name}** ({p.position}, {p.team})
- Keeper Cost: Round {analysis.keeper_round}
- ADP: {p.adp:.1f if p.adp else 'Unknown'}
- Surplus Value: {analysis.surplus_value:.1f if analysis.surplus_value else 'N/A'}
- Years Remaining: {analysis.years_remaining}
- Draft Info: Round {p.draft_round} in {p.draft_year}, kept {p.years_kept} times
"""
        
        if maybes:
            prompt += f"\n### Maybe Keepers ({len(maybes)})\n"
            for analysis in maybes[:3]:
                p = analysis.player
                prompt += f"- {p.name} ({p.position}): Round {analysis.keeper_round} cost, ADP {p.adp:.1f if p.adp else 'Unknown'}\n"
        
        # Add scenarios
        prompt += "\n## Keeper Scenarios\n"
        for i, scenario in enumerate(scenarios[:4], 1):
            prompt += f"\n{i}. {scenario.description}"
            if scenario.keepers:
                prompt += f" - Total Value: {scenario.total_value:.1f}"
                prompt += f"\n   Players: {', '.join(k.name for k in scenario.keepers)}"
                prompt += f"\n   Rounds Used: {', '.join(str(r) for r in scenario.rounds_used)}"
            prompt += "\n"
        
        prompt += """

## Questions for You

1. Which keeper scenario would you recommend and why?
2. Are there any players I should definitely keep or avoid keeping?
3. What draft strategy should I consider with these keepers?
4. Any other insights or recommendations?

Please provide specific, actionable advice."""
        
        return prompt


def format_ai_advice(advice: str) -> str:
    """Format AI advice for terminal display"""
    return f"""
{'='*80}
AI KEEPER RECOMMENDATIONS
{'='*80}

{advice}

{'='*80}
"""
