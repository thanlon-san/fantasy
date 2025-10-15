#!/usr/bin/env python3
"""
ESPN Fantasy Football Data Fetcher
Automatically pulls league data and generates markdown reports
"""

from espn_api.football import League
from datetime import datetime, timedelta
import json
import os
from typing import Optional, Dict, List

# Configuration
LEAGUE_ID = 228124044
YEAR = 2024
CURRENT_WEEK = 6  # Update this each week

class FantasyDataFetcher:
    """Main class for fetching and processing ESPN Fantasy Football data"""
    
    def __init__(self, league_id: int, year: int, espn_s2: str = None, swid: str = None):
        """
        Initialize the data fetcher
        
        Args:
            league_id: ESPN league ID
            year: Season year
            espn_s2: ESPN authentication cookie (for private leagues)
            swid: ESPN authentication cookie (for private leagues)
        """
        self.league_id = league_id
        self.year = year
        self.espn_s2 = espn_s2
        self.swid = swid
        self.league = None
        
    def connect(self) -> Optional[League]:
        """Connect to ESPN and fetch league data"""
        try:
            if self.espn_s2 and self.swid:
                self.league = League(
                    league_id=self.league_id, 
                    year=self.year,
                    espn_s2=self.espn_s2,
                    swid=self.swid
                )
            else:
                self.league = League(league_id=self.league_id, year=self.year)
            
            print(f"✅ Connected to league: {self.league.name if hasattr(self.league, 'name') else 'Unknown'}")
            return self.league
        except Exception as e:
            print(f"❌ Error connecting to league: {e}")
            print("Note: If league is private, you'll need to add espn_s2 and swid cookies")
            return None
    
    def generate_matchups_markdown(self, week: int) -> str:
        """Generate markdown file with matchup data"""
        if not self.league:
            return ""
            
        matchups = self.league.box_scores(week)
        output = [f"# Fantasy Football Matchups - NFL Week {week}\n"]
        
        for i, matchup in enumerate(matchups, 1):
            output.append(f"\n## Matchup {i}: {matchup.home_team.team_name} vs {matchup.away_team.team_name}\n\n")
            output.append(f"**Final Score:** {matchup.home_team.team_name} {matchup.home_score:.2f} - ")
            output.append(f"{matchup.away_score:.2f} {matchup.away_team.team_name}  \n")
            output.append(f"**Records:** {matchup.home_team.team_name} ({matchup.home_team.wins}-{matchup.home_team.losses}-{matchup.home_team.ties}) | ")
            output.append(f"{matchup.away_team.team_name} ({matchup.away_team.wins}-{matchup.away_team.losses}-{matchup.away_team.ties})  \n")
            
            # Home team lineup
            output.append(f"\n### {matchup.home_team.team_name} Starters\n")
            output.append("| Slot | Player | Team | Proj | Actual |\n")
            output.append("|------|--------|------|------|--------|\n")
            
            for player in matchup.home_lineup:
                if player.slot_position not in ['BE', 'IR']:
                    proj = getattr(player, 'projected_points', 0)
                    actual = getattr(player, 'points', 0)
                    pro_team = getattr(player, 'proTeam', 'FA')
                    output.append(f"| {player.slot_position} | {player.name} | {pro_team} | {proj:.1f} | {actual:.1f} |\n")
            
            # Bench players
            output.append(f"\n### {matchup.home_team.team_name} Bench\n")
            output.append("| Player | Team | Proj | Actual |\n")
            output.append("|--------|------|------|--------|\n")
            
            for player in matchup.home_lineup:
                if player.slot_position == 'BE':
                    proj = getattr(player, 'projected_points', 0)
                    actual = getattr(player, 'points', 0)
                    pro_team = getattr(player, 'proTeam', 'FA')
                    output.append(f"| {player.name} | {pro_team} | {proj:.1f} | {actual:.1f} |\n")
            
            # Away team lineup
            output.append(f"\n### {matchup.away_team.team_name} Starters\n")
            output.append("| Slot | Player | Team | Proj | Actual |\n")
            output.append("|------|--------|------|------|--------|\n")
            
            for player in matchup.away_lineup:
                if player.slot_position not in ['BE', 'IR']:
                    proj = getattr(player, 'projected_points', 0)
                    actual = getattr(player, 'points', 0)
                    pro_team = getattr(player, 'proTeam', 'FA')
                    output.append(f"| {player.slot_position} | {player.name} | {pro_team} | {proj:.1f} | {actual:.1f} |\n")
            
            # Bench players
            output.append(f"\n### {matchup.away_team.team_name} Bench\n")
            output.append("| Player | Team | Proj | Actual |\n")
            output.append("|--------|------|------|--------|\n")
            
            for player in matchup.away_lineup:
                if player.slot_position == 'BE':
                    proj = getattr(player, 'projected_points', 0)
                    actual = getattr(player, 'points', 0)
                    pro_team = getattr(player, 'proTeam', 'FA')
                    output.append(f"| {player.name} | {pro_team} | {proj:.1f} | {actual:.1f} |\n")
            
            output.append("\n---\n")
        
        return ''.join(output)
    
    def generate_standings_markdown(self) -> str:
        """Generate markdown file with standings and stats"""
        if not self.league:
            return ""
            
        standings = self.league.standings()
        
        output = ["# Fantasy Football League - Standings & Stats\n\n"]
        output.append("## League Standings\n\n")
        output.append("| Rank | Team | Owner | W | L | T | PCT | PF | PA | Streak |\n")
        output.append("|------|------|-------|---|---|---|-----|-------|-------|--------|\n")
        
        for i, team in enumerate(standings, 1):
            owner = team.owner.split()[0] if hasattr(team, 'owner') and team.owner else "Unknown"
            pct = team.wins / (team.wins + team.losses) if (team.wins + team.losses) > 0 else 0
            streak = getattr(team, 'streak_type', 'W') + str(getattr(team, 'streak_length', 0))
            
            output.append(f"| {i} | {team.team_name} | {owner} | {team.wins} | {team.losses} | ")
            output.append(f"{team.ties} | {pct:.3f} | {team.points_for:.1f} | {team.points_against:.1f} | {streak} |\n")
        
        output.append("\n## Statistical Leaders\n\n")
        
        # Find highest scoring team
        top_scorer = max(standings, key=lambda x: x.points_for)
        output.append(f"- **Most Points For:** {top_scorer.team_name} ({top_scorer.points_for:.1f} PF)\n")
        
        # Find best defense
        best_defense = min(standings, key=lambda x: x.points_against)
        output.append(f"- **Fewest Points Against:** {best_defense.team_name} ({best_defense.points_against:.1f} PA)\n")
        
        # Find best point differential
        best_diff = max(standings, key=lambda x: x.points_for - x.points_against)
        diff = best_diff.points_for - best_diff.points_against
        output.append(f"- **Best Point Differential:** {best_diff.team_name} (+{diff:.1f})\n")
        
        # Find most moves
        most_moves = max(standings, key=lambda x: getattr(x, 'transactions', 0))
        moves = getattr(most_moves, 'transactions', 0)
        output.append(f"- **Most Transactions:** {most_moves.team_name} ({moves} moves)\n")
        
        return ''.join(output)
    
    def calculate_week_stats(self, week: int) -> Dict:
        """Calculate interesting stats for the week"""
        if not self.league:
            return {}
            
        matchups = self.league.box_scores(week)
        stats = {
            'biggest_blowout': None,
            'closest_game': None,
            'highest_score': None,
            'lowest_score': None,
            'most_bench_points': None
        }
        
        biggest_diff = 0
        smallest_diff = float('inf')
        all_scores = []
        
        for m in matchups:
            diff = abs(m.home_score - m.away_score)
            
            # Track blowout
            if diff > biggest_diff:
                biggest_diff = diff
                winner = m.home_team if m.home_score > m.away_score else m.away_team
                loser = m.away_team if m.home_score > m.away_score else m.home_team
                stats['biggest_blowout'] = {
                    'winner': winner.team_name,
                    'loser': loser.team_name,
                    'margin': diff
                }
            
            # Track closest game
            if diff < smallest_diff:
                smallest_diff = diff
                stats['closest_game'] = {
                    'team1': m.home_team.team_name,
                    'team2': m.away_team.team_name,
                    'margin': diff
                }
            
            # Track all scores
            all_scores.append((m.home_team.team_name, m.home_score))
            all_scores.append((m.away_team.team_name, m.away_score))
            
            # Calculate bench points
            home_bench_points = sum(p.points for p in m.home_lineup if p.slot_position == 'BE')
            away_bench_points = sum(p.points for p in m.away_lineup if p.slot_position == 'BE')
            
            if not stats['most_bench_points'] or home_bench_points > stats['most_bench_points']['points']:
                stats['most_bench_points'] = {
                    'team': m.home_team.team_name,
                    'points': home_bench_points
                }
            
            if not stats['most_bench_points'] or away_bench_points > stats['most_bench_points']['points']:
                stats['most_bench_points'] = {
                    'team': m.away_team.team_name,
                    'points': away_bench_points
                }
        
        # Find highest and lowest scores
        stats['lowest_score'] = min(all_scores, key=lambda x: x[1])
        stats['highest_score'] = max(all_scores, key=lambda x: x[1])
        
        return stats
    
    def generate_week_summary(self, week: int) -> str:
        """Generate a summary with key stats for the week"""
        stats = self.calculate_week_stats(week)
        
        output = [f"\n## Week {week} Summary\n\n"]
        output.append("### 🏆 Awards & Lowlights\n\n")
        
        if stats.get('highest_score'):
            output.append(f"**👑 Week Winner:** {stats['highest_score'][0]} ({stats['highest_score'][1]:.1f} points)\n\n")
        
        if stats.get('lowest_score'):
            output.append(f"**🗑️ Dumpster Fire:** {stats['lowest_score'][0]} ({stats['lowest_score'][1]:.1f} points)\n\n")
        
        if stats.get('biggest_blowout'):
            b = stats['biggest_blowout']
            output.append(f"**💥 Biggest Blowout:** {b['winner']} destroyed {b['loser']} by {b['margin']:.1f} points\n\n")
        
        if stats.get('closest_game'):
            c = stats['closest_game']
            output.append(f"**😰 Nail Biter:** {c['team1']} vs {c['team2']} decided by {c['margin']:.1f} points\n\n")
        
        if stats.get('most_bench_points'):
            bp = stats['most_bench_points']
            output.append(f"**🪑 Bench Points Champion:** {bp['team']} left {bp['points']:.1f} points on the bench\n\n")
        
        return ''.join(output)

def main():
    """Main execution function"""
    print("🏈 ESPN Fantasy Football Data Fetcher")
    print(f"📊 League ID: {LEAGUE_ID}")
    print(f"📅 Processing Week {CURRENT_WEEK} data...\n")
    
    # Create output directory
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Initialize fetcher
    fetcher = FantasyDataFetcher(LEAGUE_ID, YEAR)
    
    # Connect to league
    league = fetcher.connect()
    if not league:
        return
    
    # Generate matchups file
    print("📝 Generating matchups markdown...")
    matchups_content = fetcher.generate_matchups_markdown(CURRENT_WEEK)
    output_path = os.path.join(output_dir, f'week-{CURRENT_WEEK}-matchups.md')
    with open(output_path, 'w') as f:
        f.write(matchups_content)
    print(f"✅ Saved to {output_path}")
    
    # Generate standings file
    print("📝 Generating standings markdown...")
    standings_content = fetcher.generate_standings_markdown()
    output_path = os.path.join(output_dir, 'standings.md')
    with open(output_path, 'w') as f:
        f.write(standings_content)
    print(f"✅ Saved to {output_path}")
    
    # Generate week summary
    print("📝 Generating week summary...")
    summary_content = fetcher.generate_week_summary(CURRENT_WEEK)
    output_path = os.path.join(output_dir, f'week-{CURRENT_WEEK}-summary.md')
    with open(output_path, 'w') as f:
        f.write(summary_content)
    print(f"✅ Saved to {output_path}")
    
    # Print summary stats to console
    stats = fetcher.calculate_week_stats(CURRENT_WEEK)
    print("\n" + "="*50)
    print(f"📊 WEEK {CURRENT_WEEK} QUICK STATS")
    print("="*50)
    
    if stats.get('highest_score'):
        print(f"🚀 Highest Score: {stats['highest_score'][0]} - {stats['highest_score'][1]:.1f} pts")
    
    if stats.get('lowest_score'):
        print(f"💩 Lowest Score: {stats['lowest_score'][0]} - {stats['lowest_score'][1]:.1f} pts")
    
    if stats.get('biggest_blowout'):
        b = stats['biggest_blowout']
        print(f"💥 Biggest Blowout: {b['winner']} beat {b['loser']} by {b['margin']:.1f}")
    
    if stats.get('most_bench_points'):
        bp = stats['most_bench_points']
        print(f"🪑 Most Bench Points: {bp['team']} - {bp['points']:.1f} pts")
    
    print("\n✨ All files generated successfully!")

if __name__ == "__main__":
    main()
