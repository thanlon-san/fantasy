"""
League Settings Manager
Load and validate league configuration
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LeagueSettings:
    """League configuration settings"""
    league_name: str
    team_name: str
    season: int
    platform: str
    roster_config: Dict[str, Any]
    keeper_rules: Dict[str, Any]
    scoring: Dict[str, Any]
    waiver_wire: Dict[str, Any]
    draft: Dict[str, Any]
    preferences: Dict[str, Any]
    
    @property
    def max_keepers(self) -> int:
        """Maximum number of keepers allowed"""
        return self.keeper_rules.get('max_keepers', 3)
    
    @property
    def default_late_round(self) -> int:
        """Default round for late-round picks"""
        return self.keeper_rules.get('default_late_round', 12)
    
    @property
    def adp_source(self) -> str:
        """ADP data source"""
        return self.preferences.get('adp_source', 'fantasypros')
    
    @property
    def adp_max_threshold(self) -> int:
        """Maximum ADP to consider for waiver pickups"""
        return self.preferences.get('adp_max_threshold', 400)
    
    @property
    def value_thresholds(self) -> Dict[str, float]:
        """Value gain thresholds for recommendations"""
        return {
            'strong': self.preferences.get('min_value_gain_strong', 100),
            'good': self.preferences.get('min_value_gain_good', 50),
            'consider': self.preferences.get('min_value_gain_consider', 20)
        }


class LeagueSettingsManager:
    """Manage league settings"""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "league_settings.json"
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> LeagueSettings:
        """
        Load league settings from JSON file
        
        Args:
            config_path: Path to config file (defaults to config/league_settings.json)
            
        Returns:
            LeagueSettings object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        path = config_path or cls.DEFAULT_CONFIG_PATH
        
        if not path.exists():
            raise FileNotFoundError(
                f"League settings not found: {path}\n"
                f"Create one at {cls.DEFAULT_CONFIG_PATH}"
            )
        
        with open(path) as f:
            data = json.load(f)
        
        # Validate required fields
        required = ['league_name', 'team_name', 'season', 'platform', 'roster', 'keeper_rules']
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        
        return LeagueSettings(
            league_name=data['league_name'],
            team_name=data['team_name'],
            season=data['season'],
            platform=data['platform'],
            roster_config=data['roster'],
            keeper_rules=data['keeper_rules'],
            scoring=data.get('scoring', {}),
            waiver_wire=data.get('waiver_wire', {}),
            draft=data.get('draft', {}),
            preferences=data.get('preferences', {})
        )
    
    @classmethod
    def create_default(cls, output_path: Optional[Path] = None) -> Path:
        """
        Create a default league settings file
        
        Args:
            output_path: Where to save the file (defaults to config/league_settings.json)
            
        Returns:
            Path to created file
        """
        path = output_path or cls.DEFAULT_CONFIG_PATH
        
        default_settings = {
            "league_name": "My League",
            "team_name": "My Team",
            "season": 2026,
            "platform": "yahoo",
            "roster": {
                "total_spots": 24,
                "positions": {
                    "C": 1, "1B": 1, "2B": 1, "3B": 1, "SS": 1,
                    "OF": 3, "Util": 2,
                    "SP": 6, "RP": 3, "P": 1,
                    "Bench": 4
                }
            },
            "keeper_rules": {
                "max_keepers": 3,
                "default_late_round": 12,
                "cost_calculation": "draft_round - years_kept - 1",
                "min_round": 1
            },
            "scoring": {"type": "points"},
            "waiver_wire": {"type": "continuous"},
            "draft": {"type": "snake", "total_rounds": 24},
            "preferences": {
                "adp_source": "fantasypros",
                "adp_max_threshold": 400,
                "min_value_gain_strong": 100,
                "min_value_gain_good": 50,
                "min_value_gain_consider": 20
            }
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(default_settings, f, indent=2)
        
        return path


# Convenience function for quick access
def load_league_settings(config_path: Optional[Path] = None) -> LeagueSettings:
    """Load league settings (convenience function)"""
    return LeagueSettingsManager.load(config_path)
