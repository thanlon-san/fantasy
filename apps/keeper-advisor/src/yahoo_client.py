"""
Yahoo Fantasy Sports API client for fetching league and roster data
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
from shared.logger import get_logger
from .yahoo_oauth_manual import YahooOAuth2
from .models import Player

logger = get_logger(__name__)


class YahooFantasyClient:
    """Client for Yahoo Fantasy Sports API"""
    
    BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"
    
    def __init__(self, oauth: YahooOAuth2):
        self.oauth = oauth
        self.session = oauth.get_session()
    
    def get_user_leagues(self, year: int, sport: str = "mlb") -> List[Dict]:
        """
        Get all leagues for the authenticated user in a given year
        
        Args:
            year: Season year (e.g., 2025)
            sport: Sport code (default: mlb for baseball)
            
        Returns:
            List of league dictionaries
        """
        try:
            # First get the game_key for the year/sport
            url = f"{self.BASE_URL}/users;use_login=1/games?format=json"
            response = self.session.get(url)
            
            if response.status_code != 200:
                logger.error(f"Error fetching games: {response.text}")
                return []
            
            data = response.json()
            games = data.get('fantasy_content', {}).get('users', {}).get('0', {}).get('user', [{}])[1].get('games', {})
            
            # Find the game_key for the requested year/sport
            game_key = None
            for key, value in games.items():
                if key == 'count':
                    continue
                game = value.get('game', [])
                if isinstance(game, list) and len(game) > 0:
                    game_info = game[0]
                    if game_info.get('code') == sport and game_info.get('season') == str(year):
                        game_key = game_info.get('game_key')
                        break
            
            if not game_key:
                logger.warning(f"No {sport} game found for year {year}")
                return []
            
            # Now get leagues for this game
            url = f"{self.BASE_URL}/users;use_login=1/games;game_keys={game_key}/leagues?format=json"
            response = self.session.get(url)
            
            if response.status_code != 200:
                logger.error(f"Error fetching leagues: {response.text}")
                return []
            
            data = response.json()
            leagues_data = data.get('fantasy_content', {}).get('users', {}).get('0', {}).get('user', [{}])[1].get('games', {}).get('0', {}).get('game', [{}])[1].get('leagues', {})
            
            leagues = []
            for key, value in leagues_data.items():
                if key == 'count':
                    continue
                league_info = value.get('league', [])
                if isinstance(league_info, list) and len(league_info) > 0:
                    league = league_info[0]
                    leagues.append({
                        'league_key': league.get('league_key'),
                        'league_id': league.get('league_id'),
                        'name': league.get('name'),
                        'season': league.get('season'),
                        'num_teams': league.get('num_teams'),
                    })
            
            return leagues
            
        except Exception as e:
            logger.error(f"Error fetching user leagues: {e}", exc_info=True)
            return []
    
    def get_free_agents(self, league_key: str, count: int = 50) -> List[Dict]:
        """
        Fetch available free agents in a league
        
        Args:
            league_key: Yahoo league key (e.g., '449.l.123456')
            count: Number of free agents to fetch (default 50)
            
        Returns:
            List of free agent player dictionaries
        """
        url = f"{self.BASE_URL}/league/{league_key}/players;status=A;count={count}"
        
        response = self.oauth.make_request(url)
        
        if not response or 'league' not in response:
            return []
        
        league = response['league']
        
        # Navigate to players array
        if isinstance(league, list):
            for item in league:
                if isinstance(item, dict) and 'players' in item:
                    players_data = item['players']
                    break
            else:
                return []
        else:
            if 'players' not in league:
                return []
            players_data = league['players']
        
        # Parse players
        players = []

        if isinstance(players_data, dict):
            if 'player' in players_data:
                # Flat list under a single 'player' key
                player_list = players_data['player']
                if not isinstance(player_list, list):
                    player_list = [player_list]
            else:
                # Numbered-key format: {"count": N, "0": {"player": [...]}, ...}
                player_list = [
                    v for k, v in players_data.items()
                    if k != 'count' and isinstance(v, dict) and 'player' in v
                ]
        else:
            player_list = players_data if isinstance(players_data, list) else []
        
        # Parse each player
        for player_entry in player_list:
            if not isinstance(player_entry, dict) or 'player' not in player_entry:
                continue
            
            player_array = player_entry['player']
            if not isinstance(player_array, list) or len(player_array) == 0:
                continue
            
            # Extract player data from the array format
            player_properties = player_array[0] if isinstance(player_array[0], list) else player_array
            
            player_info = {}
            for prop in player_properties:
                if not isinstance(prop, dict):
                    continue
                
                if 'player_key' in prop:
                    player_info['player_key'] = prop['player_key']
                elif 'name' in prop:
                    player_info['name'] = prop['name'].get('full', 'Unknown')
                elif 'editorial_team_abbr' in prop:
                    player_info['editorial_team_abbr'] = prop['editorial_team_abbr']
                elif 'eligible_positions' in prop:
                    positions = prop['eligible_positions']
                    if isinstance(positions, list):
                        player_info['eligible_positions'] = [
                            p.get('position') if isinstance(p, dict) else p
                            for p in positions
                        ]
            
            if 'name' in player_info:
                players.append(player_info)
        
        return players
    
    def get_team_roster(self, team_key: str) -> List[Dict]:
        """
        Get roster for a specific team
        
        Args:
            team_key: Yahoo team key (e.g., '431.l.12345.t.1')
            
        Returns:
            List of player dictionaries
        """
        try:
            url = f"{self.BASE_URL}/team/{team_key}/roster?format=json"
            response = self.session.get(url)
            
            if response.status_code != 200:
                logger.error(f"Error fetching roster: {response.text}")
                return []
            
            data = response.json()
            roster_data = data.get('fantasy_content', {}).get('team', [{}])[1].get('roster', {}).get('0', {}).get('players', {})
            
            players = []
            for key, value in roster_data.items():
                if key == 'count':
                    continue
                    
                player_array = value.get('player', [])
                if not isinstance(player_array, list) or len(player_array) == 0:
                    continue
                
                # Yahoo's structure: player is [[{prop1}, {prop2}, ...]]
                if isinstance(player_array[0], list):
                    properties = player_array[0]
                else:
                    properties = player_array
                
                # Extract player info from the property list
                player_info = {}
                for prop in properties:
                    if isinstance(prop, dict):
                        if 'player_key' in prop:
                            player_info['player_key'] = prop['player_key']
                        if 'player_id' in prop:
                            player_info['player_id'] = prop['player_id']
                        if 'name' in prop:
                            player_info['name'] = prop['name'].get('full')
                            player_info['first_name'] = prop['name'].get('first')
                            player_info['last_name'] = prop['name'].get('last')
                        if 'position_type' in prop:
                            player_info['position_type'] = prop['position_type']
                        if 'eligible_positions' in prop:
                            # eligible_positions is a list of dicts: [{'position': 'OF'}, ...]
                            positions = prop['eligible_positions']
                            if isinstance(positions, list):
                                player_info['eligible_positions'] = [
                                    p.get('position') if isinstance(p, dict) else p
                                    for p in positions
                                ]
                            else:
                                player_info['eligible_positions'] = []
                        if 'display_position' in prop:
                            player_info['display_position'] = prop['display_position']
                        if 'editorial_team_abbr' in prop:
                            player_info['editorial_team_abbr'] = prop['editorial_team_abbr']
                        if 'uniform_number' in prop:
                            player_info['uniform_number'] = prop['uniform_number']
                
                if 'name' in player_info:
                    players.append(player_info)
            
            return players
            
        except Exception as e:
            logger.error(f"Error fetching team roster: {e}", exc_info=True)
            return []
    
    def get_league_teams(self, league_key: str) -> List[Dict]:
        """
        Get all teams in a league
        
        Args:
            league_key: Yahoo league key (e.g., '431.l.12345')
            
        Returns:
            List of team dictionaries
        """
        try:
            url = f"{self.BASE_URL}/league/{league_key}/teams?format=json"
            response = self.session.get(url)
            
            if response.status_code != 200:
                logger.error(f"Error fetching teams: {response.text}")
                return []
            
            data = response.json()
            teams_data = data.get('fantasy_content', {}).get('league', [{}])[1].get('teams', {})
            
            teams = []
            for key, value in teams_data.items():
                if key == 'count':
                    continue
                    
                team_array = value.get('team', [])
                if not isinstance(team_array, list) or len(team_array) == 0:
                    continue
                
                # Yahoo's structure: team is [[{prop1}, {prop2}, ...]]
                # First element is a list of property dicts
                if isinstance(team_array[0], list):
                    properties = team_array[0]
                else:
                    properties = team_array
                
                # Extract team info from the property list
                team_info = {}
                for prop in properties:
                    if isinstance(prop, dict):
                        if 'team_key' in prop:
                            team_info['team_key'] = prop['team_key']
                        if 'team_id' in prop:
                            team_info['team_id'] = prop['team_id']
                        if 'name' in prop:
                            team_info['name'] = prop['name']
                        if 'managers' in prop:
                            managers = prop['managers']
                            if isinstance(managers, list) and len(managers) > 0:
                                mgr = managers[0].get('manager', {})
                                team_info['manager'] = mgr.get('nickname', 'Unknown')
                
                if 'team_key' in team_info:
                    teams.append({
                        'team_key': team_info.get('team_key'),
                        'team_id': team_info.get('team_id'),
                        'name': team_info.get('name', 'Unknown'),
                        'manager': team_info.get('manager', 'Unknown'),
                    })
            
            return teams
            
        except Exception as e:
            logger.error(f"Error fetching league teams: {e}", exc_info=True)
            return []
    
    @classmethod
    def from_config(cls, config_path: Path):
        """Load client from saved OAuth config"""
        oauth = YahooOAuth2.load_from_file(str(config_path))
        return cls(oauth)
