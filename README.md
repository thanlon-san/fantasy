# Fantasy Football Data Fetcher 🏈

Automated ESPN Fantasy Football data fetcher and report generator. Pull league stats, matchups, and standings directly from ESPN's API and generate beautiful markdown reports.

## Features

- 📊 **Automatic Data Fetching** - Pull all league data with one command
- 📝 **Markdown Reports** - Generate clean, formatted reports for:
  - Weekly matchups with full lineups
  - League standings and stats
  - Week summaries with awards
- 🏆 **Statistical Analysis** - Automatically calculate:
  - Highest/lowest scores
  - Biggest blowouts
  - Closest games
  - Bench points leaders
- 🔄 **Weekly Updates** - Run each week for fresh reports

## Installation

```bash
# Clone the repository
git clone https://github.com/thanlon-san/fantasy.git
cd fantasy

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `fetch_league_data.py` to set your league details:

```python
LEAGUE_ID = 228124044  # Your ESPN league ID
YEAR = 2024           # Current season
CURRENT_WEEK = 6      # Current week number
```

### Private Leagues

If your league is private, you'll need ESPN authentication cookies:

1. Log into ESPN Fantasy Football in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies
4. Find and copy:
   - `espn_s2` cookie value
   - `SWID` cookie value

Then update the fetcher initialization:

```python
fetcher = FantasyDataFetcher(
    LEAGUE_ID, 
    YEAR,
    espn_s2='YOUR_ESPN_S2_HERE',
    swid='YOUR_SWID_HERE'
)
```

## Usage

### Basic Usage

```bash
# Fetch all data for the current week
python fetch_league_data.py
```

This generates three files in the `output/` directory:
- `week-{N}-matchups.md` - All matchups with lineups
- `standings.md` - Current standings and season stats
- `week-{N}-summary.md` - Weekly awards and highlights

### Advanced Usage

```python
from fetch_league_data import FantasyDataFetcher

# Initialize fetcher
fetcher = FantasyDataFetcher(league_id=228124044, year=2024)
fetcher.connect()

# Get specific week data
week_stats = fetcher.calculate_week_stats(week=6)

# Generate custom reports
matchups_md = fetcher.generate_matchups_markdown(week=6)
standings_md = fetcher.generate_standings_markdown()
```

## Output Examples

### Weekly Summary
```markdown
## Week 6 Summary

### 🏆 Awards & Lowlights

**👑 Week Winner:** New Vertical Threats (167.6 points)
**🗑️ Dumpster Fire:** Laser Focused (52.9 points)
**💥 Biggest Blowout:** New Vertical Threats destroyed Maia's Monstrous Team by 94.98 points
**😰 Nail Biter:** High Qual Completion vs Team Tang decided by 3.3 points
**🪑 Bench Points Champion:** Fly PCIO Fly left 76.1 points on the bench
```

## Weekly Recap Generator

Want to generate savage weekly recaps? Check out `recap_generator.py` for automated roast generation based on the fetched data!

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built using [espn-api](https://github.com/cwendt94/espn-api) by cwendt94
- Inspired by the need to automate fantasy football suffering documentation

---

*May your waivers clear and your projections lie.* 🎲
