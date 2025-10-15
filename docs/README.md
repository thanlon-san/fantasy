# Fantasy Football Data Fetcher & API 🏈

**Automated ESPN Fantasy Football data fetcher with REST API and markdown report generator.** Pull league stats, matchups, and standings directly from ESPN's API via a beautiful REST API or generate markdown reports.

## Features

- 🚀 **REST API** - FastAPI server with full league data access
- 😈 **AI Recap Generator** - Viciously funny weekly recaps powered by LLM
  - Roasts bad decisions with surgical precision
  - Remembers past failures for callbacks
  - 85% lowlights, 15% grudging highlights
  - Safe, PG-13, grounded in real stats
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
- 🔄 **Auto-Updates** - Automatically tracks current week
- 🔐 **Private League Support** - Works with private ESPN leagues

## Quick Start

**New to this project?** → **[See QUICKSTART.md](QUICKSTART.md)** for a step-by-step guide with screenshots!

```bash
# Clone the repository
git clone https://github.com/thanlon-san/fantasy.git
cd fantasy

# Install dependencies
pip install -r requirements.txt

# Copy and configure settings
cp config.example.json config.json
# Edit config.json with your league ID and ESPN cookies (see below)

# Start the API server
python3 api.py
```

**API now running at:** http://localhost:8000  
**Interactive docs:** http://localhost:8000/docs

## Configuration

### 1. Create `config.json`

Copy the example configuration:

```bash
cp config.example.json config.json
```

### 2. Edit `config.json`

```json
{
  "league_id": 228124044, // Your ESPN league ID
  "year": 2025, // Current season
  "current_week": 7, // Auto-detected from ESPN (fallback only)
  "private_league": true, // Set to true if your league is private
  "espn_s2": "YOUR_ESPN_S2_HERE", // Required for private leagues
  "swid": "{YOUR-SWID-HERE}" // Required for private leagues
}
```

### 3. Get ESPN Cookies (Required for Private Leagues)

If your league is private, you'll need ESPN authentication cookies:

1. Log into ESPN Fantasy Football in your browser
2. Open Developer Tools (Press **F12**)
3. Go to **Application** tab (Chrome) or **Storage** tab (Firefox)
4. Navigate to **Cookies** → `https://fantasy.espn.com`
5. Find and copy:
   - `espn_s2` - Long string (copy the entire value)
   - `SWID` - Format: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}` (include braces)
6. Paste these values into your `config.json`

## Usage

### REST API (Recommended)

**Start the API server:**

```bash
python3 api.py
```

The API will be available at http://localhost:8000

**Available Endpoints:**

- `GET /api/league` - League information
- `GET /api/standings` - Current standings
- `GET /api/teams` - All teams
- `GET /api/teams/{id}` - Specific team details
- `GET /api/matchups/{week}` - Week matchups with lineups
- `GET /api/stats/week/{week}` - Week statistics and highlights

**Interactive Documentation:**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Example API Calls:**

```bash
# Get league info
curl http://localhost:8000/api/league

# Get current standings
curl http://localhost:8000/api/standings

# Get week 7 matchups
curl http://localhost:8000/api/matchups/7

# Get week 7 stats
curl http://localhost:8000/api/stats/week/7
```

### AI Weekly Recaps (The Fun Part!)

**Generate viciously funny weekly roasts:**

```bash
# Option 1: Generate context for your LLM (ChatGPT, Claude, etc.)
python3 recap_generator.py 7 --context-only

# Option 2: Automated with OpenAI/Anthropic (see RECAP_USAGE.md)
```

**Example output:**

```markdown
# Week 7: When Projections Go to Die

Started Russell Wilson (8.2) because apparently we're time-traveling to 2019.
Meanwhile, benched Malik Nabers who dropped 23.4. That's not strategy—that's
performance art...

What they'll tell themselves: "We're optimizing our learnings for Week 8's
synergistic outcomes."
```

📖 **Full guide:** [RECAP_USAGE.md](RECAP_USAGE.md)

### Markdown Reports (Command Line)

**Generate markdown reports:**

```bash
python3 fetch_league_data.py
```

This generates three files in the `output/` directory:

- `week-{N}-matchups.md` - All matchups with lineups
- `standings.md` - Current standings and season stats
- `week-{N}-summary.md` - Weekly awards and highlights

### Python Module Usage

```python
from fetch_league_data import FantasyDataFetcher

# Initialize fetcher
fetcher = FantasyDataFetcher(league_id=228124044, year=2025)
fetcher.connect()

# Get specific week data
week_stats = fetcher.calculate_week_stats(week=7)

# Generate custom reports
matchups_md = fetcher.generate_matchups_markdown(week=7)
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

## API Management

### Start the API

```bash
python3 api.py
```

### Stop the API

```bash
lsof -ti:8000 | xargs kill -9
```

### Check API Status

```bash
curl http://localhost:8000/health
```

## Project Structure

```
fantasy/
├── api.py                   # FastAPI REST server
├── fetch_league_data.py     # Core data fetcher and markdown generator
├── recap_generator.py       # AI-powered weekly recap generator
├── config.json              # Your configuration (create from example)
├── config.example.json      # Example configuration
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── API_README.md           # Detailed API documentation
├── COLUMNIST_PROMPT.md     # AI columnist persona and instructions
├── RECAP_USAGE.md          # Guide for generating AI recaps
└── QUICKSTART.md           # 5-minute setup guide
```

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide for new users
- **[API_README.md](API_README.md)** - Complete API documentation with examples
- **[RECAP_USAGE.md](RECAP_USAGE.md)** - Guide for generating AI-powered recaps
- **[COLUMNIST_PROMPT.md](COLUMNIST_PROMPT.md)** - The brain of your roast columnist
- **[Interactive API Docs](http://localhost:8000/docs)** - Available when server is running

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built using [espn-api](https://github.com/cwendt94/espn-api) by cwendt94
- Inspired by the need to automate fantasy football suffering documentation

---

_May your waivers clear and your projections lie._ 🎲
