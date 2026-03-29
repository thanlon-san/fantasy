# Stats Fetcher Module

## Overview

The Stats Fetcher module provides robust, real-time player statistics from the MLB Stats API with intelligent caching for performance.

## Features

### 1. **Multi-Window Statistics**
Fetches player performance over multiple time windows:
- **Last 7 days**: Recent hot/cold streaks
- **Last 14 days**: Medium-term trends
- **Last 30 days**: Season baseline

### 2. **Player Type Support**
- **Hitters**: AVG, HR, RBI, SB
- **Pitchers**: ERA, WHIP, K, Wins

### 3. **Trending Analysis**
Automatically classifies players as:
- **HOT**: Recent performance significantly better than baseline
- **COLD**: Recent performance significantly worse than baseline
- **STABLE**: Consistent performance

### 4. **Intelligent Caching**
- Caches API responses for 6 hours
- Dramatically reduces API calls and improves performance
- Automatic cache expiration

## Usage

### Basic Usage

```python
from src.stats_fetcher import StatsFetcher

# Initialize with caching enabled
fetcher = StatsFetcher(use_cache=True)

# Get stats for a hitter
stats = fetcher.get_recent_stats("Aaron Judge", is_pitcher=False, days=30)
print(f"AVG: {stats.avg:.3f}")
print(f"HR: {stats.hr}")
print(f"Games: {stats.games}")
```

### Multi-Window Analysis

```python
# Get all three windows at once
stats = fetcher.get_multi_window_stats("Aaron Judge", is_pitcher=False)

for window, data in stats.items():
    print(f"{window}: {data.avg:.3f} AVG in {data.games} games")
```

### Trending Detection

```python
trending = fetcher.get_trending_status("Aaron Judge", is_pitcher=False)
print(f"Trending: {trending}")  # "HOT", "COLD", or "STABLE"
```

## Integration with Waiver Analyzer

The Stats Fetcher is fully integrated into the Waiver Analyzer:

```python
from src.waiver_analyzer import WaiverAnalyzer

# Enable recent stats fetching
analyzer = WaiverAnalyzer(
    roster,
    use_breakout_signals=True,
    fetch_recent_stats=True  # <-- New feature
)

# Free agents will now be enriched with:
# - recent_stats (7/14/30 day windows)
# - trending status
# - rostered percentage estimate
recommendations = analyzer.analyze_free_agents(free_agents)
```

## Data Sources

### Primary: MLB Stats API
- **Endpoint**: `https://statsapi.mlb.com/api/v1`
- **Cost**: Free, no authentication required
- **Rate Limits**: Reasonable, but we cache to be respectful
- **Data**: Official MLB game logs and statistics

### Cache Location
- **Path**: `apps/keeper-advisor/cache/stats/`
- **Format**: JSON files named `PlayerName_Xd.json`
- **Duration**: 6 hours per entry

## Dashboard Export

The export script (`export_dashboard_data.py`) now generates full waiver wire data:

```json
{
  "targets": [
    {
      "player": "Aaron Judge",
      "position": "OF",
      "team": "NYY",
      "rostered_pct": 95,
      "trending": "HOT",
      "last_7_days": {
        "avg": 0.385,
        "hr": 3,
        "rbi": 8,
        "sb": 0,
        "games": 6
      },
      "last_14_days": { ... },
      "last_30_days": { ... },
      "statcast_changes": {
        "exit_velo": "+2.1 mph",
        "hard_hit_pct": "+8.5%",
        "barrel_rate": "+4.2%"
      }
    }
  ]
}
```

## Testing

Run the test script to verify everything works:

```bash
cd apps/keeper-advisor
python scripts/test_stats_fetcher.py
```

This will:
1. Fetch stats for a known hitter (Aaron Judge)
2. Fetch stats for a known pitcher (Gerrit Cole)
3. Test cache performance

## Performance

### Without Cache
- First API call: ~2-3 seconds per player
- 10 players: ~20-30 seconds

### With Cache (After First Run)
- Subsequent calls: ~0.01 seconds per player
- 10 players: ~0.1 seconds
- **~200x faster!**

## Error Handling

The module gracefully handles:
- Player names not found in MLB system
- API timeouts or errors
- Missing game log data (off-season, injured players)
- Cache file corruption

Failed lookups return `None` rather than crashing.

## Limitations

### Current
- **Off-season**: No stats available when MLB season isn't active
- **Minor Leaguers**: Only tracks MLB players
- **Real-time**: Stats update after games are official (~30 min after game end)

### Future Enhancements
- Add schedule data (upcoming opponents)
- Add role change detection (batting order, rotation spot)
- Integrate with Baseball Savant for more Statcast metrics
- Support for international leagues (NPB, KBO)

## Troubleshooting

### "Player not found" errors
- Check spelling (use full name: "Aaron Judge" not "A. Judge")
- Player might not have MLB stats yet (minor leaguer, rookie call-up)
- Try without middle names/suffixes

### Cache issues
- Delete cache files: `rm -rf apps/keeper-advisor/cache/stats/*`
- Disable cache temporarily: `StatsFetcher(use_cache=False)`

### Slow performance
- First run is always slow (building cache)
- Check internet connection to MLB API
- Consider running export script overnight for full roster

## API Respect

We use caching to minimize API calls and be respectful of MLB's free API:
- **Cache duration**: 6 hours (stats don't change that fast)
- **Timeouts**: 10 seconds per request
- **Error handling**: Graceful fallbacks, no retry storms

## Architecture

```
stats_fetcher.py
├── StatsFetcher
│   ├── get_recent_stats()      # Single window
│   ├── get_multi_window_stats() # All windows
│   ├── get_trending_status()   # HOT/COLD/STABLE
│   ├── _find_player_id()       # MLB player lookup
│   ├── _fetch_game_logs()      # API call
│   ├── _parse_game_logs()      # Data extraction
│   ├── _aggregate_*_stats()    # Hitter/Pitcher aggregation
│   ├── _load_from_cache()      # Cache read
│   └── _save_to_cache()        # Cache write
└── RecentStats (dataclass)
    ├── Hitting: avg, hr, rbi, sb
    ├── Pitching: era, whip, k, w
    └── Meta: games
```

## Contributing

To add new stats or metrics:
1. Update `RecentStats` dataclass with new fields
2. Add parsing logic in `_aggregate_*_stats()`
3. Update frontend types to match
4. Update this documentation

---

**Built with ❤️ for fantasy baseball domination** ⚾
