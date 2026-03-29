#!/usr/bin/env python3
"""
Fetch roster from Yahoo with complete draft history
Automatically matches players to their draft rounds
"""

import sys
import csv
from pathlib import Path
from typing import Dict, List

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

from src.yahoo_client import YahooFantasyClient
from shared.logger import get_logger

logger = get_logger(__name__)


def get_draft_results(client: YahooFantasyClient, league_key: str, team_key: str) -> Dict[str, Dict]:
    """
    Get draft results for ALL players in the league
    Returns dict mapping player_key to {round, drafted_by_me, team_name}
    """
    try:
        url = f"{client.BASE_URL}/league/{league_key}/draftresults?format=json"
        response = client.session.get(url)
        
        if response.status_code != 200:
            logger.error(f"Error fetching draft results: {response.text}")
            return {}
        
        data = response.json()
        draft_results = data.get('fantasy_content', {}).get('league', [{}])[1].get('draft_results', {})
        
        # Get all teams for team name lookup
        teams = client.get_league_teams(league_key)
        team_names = {t['team_key']: t['name'] for t in teams}
        
        player_draft_map = {}
        for key, value in draft_results.items():
            if key == 'count':
                continue
            
            pick_data = value.get('draft_result', {})
            player_key = pick_data.get('player_key')
            round_num = int(pick_data.get('round', 0))
            drafting_team = pick_data.get('team_key')
            
            player_draft_map[player_key] = {
                'round': round_num,
                'drafted_by_me': drafting_team == team_key,
                'team_name': team_names.get(drafting_team, 'Unknown')
            }
        
        return player_draft_map
        
    except Exception as e:
        logger.error(f"Error parsing draft results: {e}", exc_info=True)
        return {}


def main():
    config_file = app_root / "config" / "oauth2.json"
    client = YahooFantasyClient.from_config(config_file)
    
    print("🏈 Fetching your complete roster with draft history...\n")
    
    # Get league and team
    leagues = client.get_user_leagues(2025, sport="mlb")
    league = leagues[0]
    print(f"📊 League: {league['name']}")
    
    teams = client.get_league_teams(league['league_key'])
    my_team = [t for t in teams if t['manager'] == 'Tyler'][0]
    print(f"⚾ Team: {my_team['name']}\n")
    
    # Get draft results
    print("📝 Fetching draft history...")
    draft_map = get_draft_results(client, league['league_key'], my_team['team_key'])
    print(f"✅ Found {len(draft_map)} draft picks\n")
    
    # Get current roster
    print("🔍 Fetching current roster...")
    roster = client.get_team_roster(my_team['team_key'])
    print(f"✅ Found {len(roster)} players\n")
    
    # Match roster to draft
    print("🔗 Matching players to draft data...\n")
    print("📋 Your Roster:")
    print("-" * 120)
    print(f"{'Player':<30} {'Pos':<20} {'MLB':<6} {'Rd':<4} {'Status':<40}")
    print("-" * 120)
    
    roster_with_draft = []
    for player in roster:
        player_key = player.get('player_key')
        draft_info = draft_map.get(player_key)
        
        positions = ', '.join(player.get('eligible_positions', []))[:18]
        team = player.get('editorial_team_abbr', 'FA')
        
        if draft_info:
            original_round = draft_info['round']
            # Apply round 12 cap for keeper purposes
            keeper_round = min(original_round, 12)
            
            if draft_info['drafted_by_me']:
                status = f"Your pick (Rd {original_round})"
                if original_round > 12:
                    status += " → counts as 12th"
            else:
                status = f"Acquired FA (originally Rd {original_round} by {draft_info['team_name'][:15]})"
                if original_round > 12:
                    status += " → 12th"
            
            draft_round = keeper_round
        else:
            # Undrafted FAs count as 12th round keepers
            draft_round = 12
            status = "Undrafted FA (counts as 12th round keeper)"
        
        print(f"{player['name']:<30} {positions:<20} {team:<6} {str(draft_round) if draft_round else 'N/A':<4} {status:<40}")
        
        roster_with_draft.append({
            'player': player,
            'draft_round': draft_round if draft_round else '',
            'is_undrafted_fa': not bool(draft_info),  # True if never drafted
            'years_kept': 0  # Default - user can update if they kept from previous year
        })
    
    print("-" * 120)
    
    # Save to CSV
    output_file = app_root / "data" / "my_roster_from_yahoo.csv"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['player_name', 'position', 'mlb_team', 'draft_round', 'is_undrafted_fa', 'years_kept', 'notes'])
        
        for item in roster_with_draft:
            player = item['player']
            positions = ', '.join(player.get('eligible_positions', []))
            team = player.get('editorial_team_abbr', 'FA')
            
            writer.writerow([
                player['name'],
                positions,
                team,
                item['draft_round'],
                'true' if item['is_undrafted_fa'] else 'false',
                item['years_kept'],
                ''  # notes
            ])
    
    print(f"\n✅ Roster saved to: {output_file}")
    print("\n" + "="*100)
    print("📝 NEXT STEPS:")
    print("="*100)
    print(f"\n1. Review {output_file.name}")
    print("   - ✅ Draft rounds automatically filled (including FA acquisitions!)")
    print("   - ✅ Rounds 13+ automatically capped at 12")
    print("   - ✅ Undrafted FAs automatically set to round 12")
    print("   - 📝 Update 'years_kept' if any players were kept from previous seasons\n")
    print("2. Run keeper analysis:")
    print("   npm run analyze:yahoo\n")
    print("="*100)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
