"""
Data importers for keeper advisor
Import roster data from CSV, JSON, or manual entry
"""

import csv
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.models import Player, Roster


class CSVImporter:
    """Import roster data from CSV file"""
    
    @staticmethod
    def import_roster(
        csv_path: str,
        team_name: str = "My Team",
        league_name: str = "My League",
        year: int = 2026
    ) -> Roster:
        """
        Import roster from CSV file
        
        CSV Format:
        name,position,team,draft_round,draft_year,years_kept,adp,is_undrafted_fa,notes
        
        Args:
            csv_path: Path to CSV file
            team_name: Your team name
            league_name: League name
            year: Current year
            
        Returns:
            Roster object with all players
        """
        roster = Roster(
            team_name=team_name,
            league_name=league_name,
            year=year
        )
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Handle both 'name' and 'player_name' formats
                player_name = row.get('player_name') or row.get('name')
                if not player_name or not player_name.strip():
                    continue
                
                # Handle both 'team' and 'mlb_team' formats
                mlb_team = row.get('mlb_team') or row.get('team', 'FA')
                
                # Parse draft_round (skip if empty)
                draft_round_str = row.get('draft_round', '').strip()
                if not draft_round_str:
                    # Empty draft round means undrafted FA (default to 12 per league rules)
                    draft_round = 12
                    is_undrafted_fa = True
                else:
                    draft_round = int(draft_round_str)
                    is_undrafted_fa = draft_round > 12 or row.get('is_undrafted_fa', '').lower() in ('true', 'yes', '1')
                
                player = Player(
                    name=player_name.strip(),
                    position=row.get('position', 'UTIL').strip(),
                    team=mlb_team.strip(),
                    draft_round=draft_round,
                    draft_year=int(row.get('draft_year', year - 1)),
                    years_kept=int(row.get('years_kept', 0)),
                    adp=float(row['adp']) if row.get('adp') and row['adp'].strip() else None,
                    is_undrafted_fa=is_undrafted_fa,
                    notes=row.get('notes', '').strip()
                )
                
                roster.add_player(player)
        
        return roster
    
    @staticmethod
    def export_roster(roster: Roster, csv_path: str):
        """Export roster to CSV file"""
        with open(csv_path, 'w', newline='') as f:
            fieldnames = [
                'name', 'position', 'team', 'draft_round', 'draft_year',
                'years_kept', 'adp', 'is_undrafted_fa', 'notes'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for player in roster.players:
                writer.writerow({
                    'name': player.name,
                    'position': player.position,
                    'team': player.team,
                    'draft_round': player.draft_round,
                    'draft_year': player.draft_year,
                    'years_kept': player.years_kept,
                    'adp': player.adp if player.adp else '',
                    'is_undrafted_fa': 'true' if player.is_undrafted_fa else 'false',
                    'notes': player.notes
                })
    
    @staticmethod
    def create_template(csv_path: str):
        """Create a template CSV file with headers and example"""
        with open(csv_path, 'w', newline='') as f:
            fieldnames = [
                'name', 'position', 'team', 'draft_round', 'draft_year',
                'years_kept', 'adp', 'is_undrafted_fa', 'notes'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Add example row
            writer.writerow({
                'name': 'Aaron Judge',
                'position': 'OF',
                'team': 'NYY',
                'draft_round': '3',
                'draft_year': '2025',
                'years_kept': '0',
                'adp': '5.2',
                'is_undrafted_fa': 'false',
                'notes': 'Drafted in 2025, first year'
            })
            writer.writerow({
                'name': 'Bobby Witt Jr.',
                'position': 'SS',
                'team': 'KC',
                'draft_round': '15',
                'draft_year': '2024',
                'years_kept': '1',
                'adp': '3.1',
                'is_undrafted_fa': 'false',
                'notes': 'Late round steal, kept once'
            })


class JSONImporter:
    """Import roster data from JSON file"""
    
    @staticmethod
    def import_roster(json_path: str) -> Roster:
        """Import roster from JSON file"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        roster = Roster(
            team_name=data.get('team_name', 'My Team'),
            league_name=data.get('league_name', 'My League'),
            year=data.get('year', 2026)
        )
        
        for player_data in data.get('players', []):
            player = Player(
                name=player_data['name'],
                position=player_data.get('position', 'UTIL'),
                team=player_data.get('team', 'FA'),
                draft_round=player_data['draft_round'],
                draft_year=player_data.get('draft_year', 2025),
                years_kept=player_data.get('years_kept', 0),
                adp=player_data.get('adp'),
                is_undrafted_fa=player_data.get('is_undrafted_fa', False),
                notes=player_data.get('notes', '')
            )
            roster.add_player(player)
        
        return roster
    
    @staticmethod
    def export_roster(roster: Roster, json_path: str):
        """Export roster to JSON file"""
        data = {
            'team_name': roster.team_name,
            'league_name': roster.league_name,
            'year': roster.year,
            'players': [
                {
                    'name': p.name,
                    'position': p.position,
                    'team': p.team,
                    'draft_round': p.draft_round,
                    'draft_year': p.draft_year,
                    'years_kept': p.years_kept,
                    'adp': p.adp,
                    'is_undrafted_fa': p.is_undrafted_fa,
                    'notes': p.notes
                }
                for p in roster.players
            ]
        }
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)


def create_sample_roster() -> Roster:
    """Create a sample roster for testing"""
    roster = Roster(
        team_name="Sample Team",
        league_name="Fantasy Baseball League",
        year=2026
    )
    
    # Add some sample players with realistic scenarios
    sample_players = [
        # Elite early pick (can't keep)
        Player("Shohei Ohtani", "DH", "LAD", draft_round=1, draft_year=2025, 
               adp=1.5, notes="1st round pick - cannot keep"),
        
        # Mid-round solid player
        Player("Aaron Judge", "OF", "NYY", draft_round=3, draft_year=2025, 
               adp=5.2, notes="Drafted round 3, solid value"),
        
        # Late round breakout (great keeper value)
        Player("Bobby Witt Jr.", "SS", "KC", draft_round=15, draft_year=2024, 
               years_kept=1, adp=3.1, notes="Late round steal! Kept once"),
        
        # Another late round gem
        Player("Gunnar Henderson", "SS", "BAL", draft_round=18, draft_year=2024,
               years_kept=1, adp=8.5, notes="Waiver wire pickup, great find"),
        
        # Undrafted FA keeper
        Player("Corbin Carroll", "OF", "ARI", draft_round=20, draft_year=2025,
               is_undrafted_fa=True, adp=12.3, notes="Picked up as FA"),
        
        # Players drafted after round 12 (become 12th rounders)
        Player("Luis Robert Jr.", "OF", "CHW", draft_round=14, draft_year=2025,
               adp=45.2, notes="Later round pick"),
        
        # Player with no years left (kept 3 times already)
        Player("Ronald Acuña Jr.", "OF", "ATL", draft_round=10, draft_year=2023,
               years_kept=3, adp=2.1, notes="Maxed out control years"),
        
        # Marginal keeper (negative value)
        Player("Jazz Chisholm Jr.", "OF", "NYY", draft_round=6, draft_year=2025,
               adp=65.0, notes="Drafted too early, not good value"),
        
        # Second round pick (only 2 years control)
        Player("Juan Soto", "OF", "NYY", draft_round=2, draft_year=2025,
               years_kept=0, adp=4.2, notes="2nd rounder - special rules"),
        
        # Good value mid-round keeper
        Player("Elly De La Cruz", "SS", "CIN", draft_round=8, draft_year=2025,
               adp=15.3, notes="Good mid-round value"),
    ]
    
    for player in sample_players:
        roster.add_player(player)
    
    return roster
