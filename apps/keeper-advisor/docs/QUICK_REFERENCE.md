# Quick Reference Guide

## 📋 Available Commands

### Setup & Configuration
```bash
npm run setup:yahoo          # First-time Yahoo OAuth setup
npm run fetch:roster         # Sync roster from Yahoo
npm run update:adp           # Refresh ADP data from FantasyPros
```

### Analysis Tools
```bash
npm run analyze:yahoo        # Keeper cost analysis
npm run waivers              # Waiver wire recommendations (CLI)
npm run waivers:interactive  # Interactive mode with arrow keys ⭐
npm run lineup               # Daily start/sit recommendations ⭐ NEW
npm run lineup:schedule      # Today's MLB schedule ⭐ NEW
```

### Command-Line Options

#### Waiver Wire (CLI Mode)
```bash
# Filter by position
npm run waivers -- --position 2B
npm run waivers -- --position SP
npm run waivers -- --position OF

# Limit results
npm run waivers -- --top 5

# Force demo mode (uses sample data)
npm run waivers -- --demo

# Combine options
npm run waivers -- --position SP --top 3
```

#### Interactive Mode
```bash
npm run waivers:interactive
```
- Navigate with arrow keys
- Select mode (Live/Demo)
- Choose position filter
- Set number of recommendations
- View detailed breakdowns

---

## 🔧 Configuration Files

### `config/oauth2.json`
Yahoo API credentials and tokens
```json
{
  "consumer_key": "your_key",
  "consumer_secret": "your_secret",
  "access_token": "auto_generated",
  "refresh_token": "auto_generated"
}
```

### `config/league_settings.json`
League rules and preferences
```json
{
  "league_name": "California Palm League",
  "team_name": "2balls",
  "keeper_rules": {
    "max_keepers": 3,
    "default_late_round": 12
  },
  "preferences": {
    "min_value_gain_strong": 100,
    "min_value_gain_good": 50,
    "min_value_gain_consider": 20
  }
}
```

### `data/my_roster_from_yahoo.csv`
Your current roster with draft info
```csv
player_name,position,mlb_team,draft_round,is_undrafted_fa,years_kept,adp
Mookie Betts,2B,LAD,1,False,0,45.0
```

---

## 🎯 Common Workflows

### 1. Daily Routine (In-Season)
```bash
npm run lineup                          # Today's start/sit advice
npm run breakouts                       # Check for breakouts
npm run waivers                         # Waiver wire opportunities
```

### 2. Weekly Waiver Wire Check
```bash
npm run update:adp                      # Refresh ADP
npm run waivers:interactive             # Interactive analysis
npm run breakouts                       # Find emerging stars
```

### 3. Position-Specific Search
```bash
npm run waivers -- --position SP --top 5
```

### 4. Quick Keeper Analysis
```bash
npm run analyze:yahoo
```

### 5. Full Refresh
```bash
npm run fetch:roster                    # Update roster
npm run update:adp                      # Update ADP
npm run analyze:yahoo                   # Analyze keepers
npm run waivers                         # Check waivers
npm run lineup                          # Set daily lineup
```

---

## 💡 Tips & Tricks

### Name Matching
The tool now uses fuzzy matching to handle:
- Accents: `José Ramírez` = `Jose Ramirez` ✅
- Suffixes: `Ronald Acuña Jr.` = `Ronald Acuna` ✅
- Typos: `Gunner Henderson` finds `Gunnar Henderson` (94% match) ✅

### Recommendation Tiers
- **STRONG** (+100 ADP): Act immediately
- **GOOD** (+50 ADP): High priority
- **CONSIDER** (+20 ADP): Depth/streaming

### League Settings
Customize thresholds in `config/league_settings.json`:
```json
"preferences": {
  "min_value_gain_strong": 150,   // Stricter
  "min_value_gain_good": 75,
  "min_value_gain_consider": 30
}
```

---

## 🐛 Troubleshooting

### "No valid access token"
```bash
npm run setup:yahoo
```

### "No ADP found for player"
ADP data is limited to top ~400 players. Players outside this range get default ADP of 450.

### Interactive mode not working
Ensure you have `prompt_toolkit` installed:
```bash
source ../../.venv/bin/activate
pip install prompt_toolkit
```

---

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Initial setup guide
- **[ROADMAP.md](ROADMAP.md)** - Future features & vision
- **[README.md](../README.md)** - Project overview
- **[API_README.md](../../docs/API_README.md)** - Yahoo API details

---

## 🎮 Demo Mode

Test features without Yahoo API:
```bash
npm run waivers -- --demo
npm run waivers:interactive  # Choose "Demo" mode
```

Uses sample data including:
- Pete Alonso, Jazz Chisholm Jr., Brice Turang
- Ketel Marte, Wyatt Langford, Luis Robert Jr.
- Corbin Carroll, Joe Ryan, Hunter Greene
