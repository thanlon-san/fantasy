# ADP Data Management

## Overview

The Keeper Advisor now includes **automated ADP (Average Draft Position) data fetching** from FantasyPros. This eliminates the need to manually update player rankings.

## Quick Start

### Update ADP Data (Before Your Draft)

```bash
npm run update:adp
```

This will:
- Fetch the latest consensus ADP from FantasyPros (aggregates Yahoo, CBS, NFBC, RTS, Fantrax)
- Update all players in your `my_roster_from_yahoo.csv` file
- Default to 450.0 for players not in the top ~500

### Full Workflow

```bash
# 1. Fetch your roster from Yahoo (includes draft history)
npm run fetch:roster

# 2. Update with latest ADP data
npm run update:adp

# 3. Analyze keepers
npm run analyze:yahoo
```

## How It Works

### Automated Web Scraping

The `ADPFetcher` class (`src/adp_fetcher.py`) automatically:
- Scrapes FantasyPros' ADP page
- Parses player names and consensus ADP values
- Matches players by exact name or fuzzy match
- Handles 500+ players

### Manual Fallback

If you need to manually update a specific player's ADP:

```python
from src.adp_fetcher import ADPFetcher

fetcher = ADPFetcher()
adp = fetcher.get_player_adp("Zach Neto")
print(f"Zach Neto ADP: {adp}")  # 36.0
```

## Alternative Data Sources

### Option 1: FantasyPros API (Paid)
- Official API with rate limits
- More reliable than scraping
- Requires subscription: https://www.fantasypros.com/api/

### Option 2: Yahoo API
- You're already authenticated via `setup:yahoo`
- Could add Yahoo-specific ADP fetching
- See `src/yahoo_client.py` for examples

### Option 3: Manual CSV Import
Create `data/adp_overrides.csv`:

```csv
player_name,adp
Zach Neto,36.0
Kyle Bradish,85.0
```

Then modify `auto_update_adp.py` to merge this data.

## Troubleshooting

### Player Not Found

If a player isn't found, check for name variations:
- FantasyPros: "Agustin Ramirez" (no accent)
- Your CSV: "Agustín Ramírez" (with accent)

**Solution**: Add name mapping in `adp_fetcher.py`:

```python
NAME_ALIASES = {
    'Agustín Ramírez': 'Agustin Ramirez',
    'José Ramírez': 'Jose Ramirez',
}
```

### ADP Data Outdated

ADP changes rapidly as the draft approaches. Run `npm run update:adp` frequently:
- Weekly during offseason
- Daily in the week before your draft
- Right before your draft!

## Data Freshness

FantasyPros updates their consensus ADP:
- **Daily** during the season
- **Multiple times per day** near draft season

The scraper fetches **real-time data** every time you run it.

## Future Enhancements

Potential improvements:
1. **Caching**: Store ADP data locally with timestamps
2. **Multiple sources**: Aggregate Yahoo, ESPN, CBS directly
3. **Historical tracking**: Track ADP changes over time
4. **Position-specific ADP**: Separate ADP for catchers, etc.
5. **League-type filtering**: Roto vs H2H, different scoring

## Credits

ADP data sourced from [FantasyPros](https://www.fantasypros.com/mlb/adp/overall.php), which aggregates:
- Yahoo Fantasy
- CBS Sports
- RTS (RotoWire)
- NFBC (National Fantasy Baseball Championship)
- Fantrax
