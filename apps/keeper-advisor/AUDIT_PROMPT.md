# Fantasy Baseball Daily Lineup System - Comprehensive Audit

## Mission

You are a senior software architect and fantasy baseball expert conducting a **deep technical audit** of the Fantasy Baseball Intelligence System, with **primary focus on the Daily Lineup Optimizer** - the most critical, daily-use feature.

Your goals:
1. **Verify data quality** - Ensure lineup decisions are based on accurate, reliable data
2. **Validate intelligence integration** - Confirm all data sources feed properly into lineup logic
3. **Assess performance** - Check speed, caching, and API reliability
4. **Identify gaps** - Find missing data sources or logic flaws that impact lineup quality
5. **Recommend improvements** - Suggest concrete enhancements to lineup accuracy

---

## System Architecture Overview

### Current Deployment (Fully Automated)

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions (Daily at 8am ET)                           │
│  ├─ Runs Python analysis tools                              │
│  ├─ Generates JSON data files                               │
│  └─ Auto-commits & deploys to GitHub Pages                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Baseball Dashboard (Next.js on GitHub Pages)               │
│  └─ Displays daily lineup recommendations to user           │
└─────────────────────────────────────────────────────────────┘
```

### Python Intelligence System

```
apps/keeper-advisor/
├── src/                          # Core Intelligence
│   ├── lineup_optimizer.py       # ⭐ PRIMARY FOCUS - Daily lineup engine
│   ├── breakout_detector.py      # Statcast breakout signals → lineup
│   ├── daily_matchups.py         # MLB game schedule & pitcher matchups
│   ├── statcast_client.py        # Advanced metrics (exit velo, etc.)
│   ├── adp_fetcher.py            # Player rankings/value
│   ├── waiver_analyzer.py        # Pickup recommendations
│   ├── cache_manager.py          # Persistent caching layer
│   ├── league_settings.py        # Configurable weights & rules
│   └── models.py                 # Data structures
│
├── scripts/
│   ├── daily_lineup.py           # CLI for lineup recs
│   ├── export_dashboard_data.py  # ⭐ Daily automation entry point
│   ├── scan_breakouts.py         # Breakout scanning
│   └── waiver_wire.py            # Waiver analysis
│
├── config/
│   └── league_settings.json      # Lineup weights, roster config
│
└── .cache/                        # Persistent cache (TTL-based)
```

---

## PRIMARY FOCUS: Daily Lineup Optimizer

The **Daily Lineup Optimizer** (`src/lineup_optimizer.py`) is the **most critical component**. It runs **daily** and directly impacts **daily fantasy decisions**. This must be rock-solid.

### How It Works

```python
LineupOptimizer.get_daily_recommendations(roster)
    │
    ├─ Load today's MLB games (daily_matchups.py)
    ├─ For each player on roster:
    │   ├─ Find their game & opponent
    │   ├─ Calculate matchup score (opponent pitcher quality)
    │   ├─ Calculate park score (hitter-friendly venues)
    │   ├─ Calculate form score (recent hot/cold streak from Statcast)
    │   ├─ Calculate platoon score (L/R advantage)
    │   ├─ Get breakout boost (from breakout_detector.py)
    │   └─ Compute weighted confidence score
    │
    └─ Sort players into tiers:
        ├─ Must Start (confidence >= 80)
        ├─ Start (65-79)
        ├─ Flex (50-64)
        ├─ Bench (<50)
        └─ Not Playing (no game today)
```

### Data Sources (Critical for Audit)

| Component | Source | Purpose | Failure Impact |
|-----------|--------|---------|----------------|
| **Game Schedule** | MLB Stats API | Find who's playing today | ❌ Critical - no games = no recs |
| **Opponent Pitcher** | MLB Stats API | Matchup difficulty | ⚠️ High - affects 30% of score |
| **Park Factors** | Hardcoded dict | Home run friendliness | ⚠️ Medium - affects 20% of score |
| **Recent Form** | Statcast (pybaseball) | Hot/cold streaks | ⚠️ Medium - affects 25% of score |
| **Platoon Splits** | Heuristic (L/R) | Batting side advantage | ⚠️ Medium - affects 15% of score |
| **Breakout Signals** | Statcast via breakout_detector | Emerging talent | ⚠️ Medium - affects 10% of score |
| **Pitcher Quality** | ADP + Statcast | Opponent strength | ⚠️ High - affects matchup score |

### Scoring Algorithm

```python
# From lineup_optimizer.py
confidence_score = (
    matchup_score * MATCHUP_WEIGHT +      # 30% - Pitcher difficulty
    park_score * PARK_WEIGHT +            # 20% - Venue advantage
    form_score * FORM_WEIGHT +            # 25% - Recent performance
    platoon_score * PLATOON_WEIGHT +      # 15% - L vs R advantage
    breakout_boost * BREAKOUT_WEIGHT      # 10% - Statcast signals
)
```

**Weights are configurable** in `config/league_settings.json` → `preferences.lineup_weights`

---

## Audit Checklist

### ⭐ CRITICAL: Daily Lineup Optimizer

#### Data Quality & Reliability

- [ ] **Game Schedule Accuracy**
  - Check `daily_matchups.py` → `MLBStatsAPI.get_todays_games()`
  - Verify correct date handling (timezone issues?)
  - Confirm retry logic works (what if MLB API is down?)
  - Check cache TTL (4 hours) - is this optimal?

- [ ] **Opponent Pitcher Detection**
  - Review `MLBStatsAPI.get_todays_games()` → How are pitchers identified?
  - What if pitcher is TBD? (How does scoring handle this?)
  - Are pitchers matched correctly to home/away teams?

- [ ] **Pitcher Quality Scoring**
  - Check `lineup_optimizer.py` → `_get_pitcher_matchup_score()`
  - Verify ADP integration (`adp_fetcher.py`)
  - Validate Statcast recent performance lookup
  - What if pitcher not found in ADP? (Fallback logic?)
  - Is caching working? (Should cache pitcher scores)

- [ ] **Park Factors**
  - Review `daily_matchups.py` → `get_park_factor()`
  - Are all 30 MLB parks covered?
  - Are factors up-to-date? (Park factors change over time)
  - How are neutral parks handled?

- [ ] **Recent Form Scoring**
  - Check `lineup_optimizer.py` → `_get_recent_form()`
  - Verify Statcast data pull (last 14 days)
  - What if player not in Statcast? (Minor leaguers, rookies?)
  - Are metrics appropriate?
    - Hitters: hard hit %, barrel %
    - Pitchers: K %, hard hit % allowed
  - Is 14-day window optimal?

- [ ] **Platoon Scoring**
  - Review logic in `lineup_optimizer.py` → `_analyze_player_matchup()`
  - Is L vs R logic sound?
  - What about switch hitters?
  - Does it handle unknown pitcher handedness?

- [ ] **Breakout Integration**
  - Check `lineup_optimizer.py` → `_get_breakout_score()`
  - Verify `breakout_detector.py` is called correctly
  - Confirm breakout signals are cached (performance?)
  - Validate signal strength mapping:
    - STRONG = 100 points
    - EMERGING = 75 points
    - WATCH = 50 points
  - What if Statcast API fails? (Graceful degradation?)

#### Performance & Caching

- [ ] **Cache Effectiveness**
  - Review `cache_manager.py` → Persistent caching with TTL
  - Check hit rates (are we avoiding redundant API calls?)
  - Verify TTL values:
    - ADP: 24 hours ✅
    - Games: 4 hours ✅
    - Pitcher stats: ? (check if cached)
    - Form scores: ? (check if cached)
  - Is cache shared across runs? (Should be persisted in `.cache/`)

- [ ] **API Reliability**
  - Check retry logic in `daily_matchups.py` and `adp_fetcher.py`
  - Confirm 3 retries with exponential backoff
  - Verify 30-second timeout on all requests
  - Test: What happens if MLB API returns 500 error?

- [ ] **Speed**
  - Time `LineupOptimizer.get_daily_recommendations()` execution
  - Should be <5 seconds for 24-player roster
  - If using breakout signals, <10 seconds acceptable
  - Identify bottlenecks (Statcast queries are slowest)

#### Logic Validation

- [ ] **Confidence Score Calculation**
  - Verify weighted average math
  - Check that scores are 0-100 range
  - Confirm tier thresholds make sense:
    - Must Start: >= 80 (only studs)
    - Start: 65-79 (solid plays)
    - Flex: 50-64 (situational)
    - Bench: < 50 (avoid)

- [ ] **Edge Cases**
  - Player with no game today → Should show in "Not Playing"
  - Pitcher TBD → How is matchup scored? (Should default to neutral)
  - Player just called up (no Statcast history) → Should degrade gracefully
  - Double-header → Are both games considered?
  - Rainout/postponement → Is game removed from list?

- [ ] **Reason Generation**
  - Check `_analyze_player_matchup()` → reasons list
  - Are reasons helpful? ("Hot streak", "vs elite pitcher", etc.)
  - Do reasons match the actual scoring factors?

#### Configuration & Customization

- [ ] **Lineup Weights**
  - Verify `league_settings.json` → `preferences.lineup_weights`
  - Confirm weights are loaded in `LineupOptimizer.__init__()`
  - Check fallback to defaults if config missing
  - Are default weights sensible?

- [ ] **User Roster**
  - Review `importers.py` → CSV roster loading
  - Confirm player positions are parsed correctly
  - Check team abbreviations match MLB API (e.g., "LAA" vs "ANA")
  - What if roster has invalid/outdated players?

### Data Source Integration

#### MLB Stats API (`daily_matchups.py`)

- [ ] **Game Schedule**
  - Endpoint: `/api/v1/schedule`
  - Date format: YYYY-MM-DD
  - Timezone handling: Does it use UTC or local?
  - Returns: home_team, away_team, game_time, pitchers

- [ ] **Recent Stats**
  - Endpoint: `/api/v1/people/{player_id}/stats`
  - Used for: Player recent performance
  - Cache duration: ? (check if implemented)

- [ ] **Error Handling**
  - Retry logic: ✅ Implemented (3 retries, exponential backoff)
  - Timeout: ✅ 30 seconds
  - Rate limits: ? (Check if handled)
  - Fallback: ? (What if all retries fail?)

#### Statcast (`statcast_client.py`)

- [ ] **Hitter Stats**
  - Method: `get_hitter_stats(player_id, start_date, end_date)`
  - Metrics: exit_velocity_avg, hard_hit_percent, barrel_percent
  - Used by: `_get_recent_form()` in lineup_optimizer

- [ ] **Pitcher Stats**
  - Method: `get_pitcher_stats(player_id, start_date, end_date)`
  - Metrics: k_percent, hard_hit_percent, avg_exit_velocity
  - Used by: `_get_recent_form()` and `_get_pitcher_matchup_score()`

- [ ] **Player ID Lookup**
  - Method: `get_player_id(first_name, last_name)`
  - Accuracy: ? (Test with common names like "Mike Trout")
  - Fallback: What if player not found?

- [ ] **Performance**
  - Statcast queries are SLOW (~1-2s each)
  - Are queries cached? (Check `_breakout_cache` usage)
  - Should batch queries? (Possible optimization)

#### ADP Fetcher (`adp_fetcher.py`)

- [ ] **FantasyPros Scraping**
  - URL: FantasyPros ADP page
  - Parse method: BeautifulSoup
  - Data freshness: Cached 24 hours ✅
  - What if site structure changes? (Brittle scraping)

- [ ] **Player Name Matching**
  - Uses fuzzy matching (`fuzzywuzzy`)
  - Threshold: ? (Check accuracy)
  - Handles nicknames? (e.g., "Mike" vs "Michael")

- [ ] **ADP Usage**
  - Used by: `_get_pitcher_matchup_score()` to rank pitcher quality
  - Used by: Waiver analyzer for value calculation
  - Critical: ADP must be current during season

#### Breakout Detector (`breakout_detector.py`)

- [ ] **Integration with Lineup**
  - Called by: `_get_breakout_score()` in lineup_optimizer
  - Purpose: Add bonus for players showing Statcast breakout signals
  - Impact: +0 to +100 points (scaled by signal strength)

- [ ] **Signal Quality**
  - Verify signal definitions (STRONG, EMERGING, WATCH, FADING)
  - Check thresholds (exit velo change, K% change, etc.)
  - Are signals actionable? (Review docs/BREAKOUT_DETECTOR.md)

- [ ] **Cache Usage**
  - Breakout analyses should be cached (expensive Statcast queries)
  - Check `_breakout_cache` in LineupOptimizer
  - Is cache keyed correctly? (by player name)

### Configuration Management

- [ ] **League Settings (`config/league_settings.json`)**
  - Lineup weights: Are defaults sensible?
  - Roster positions: Matches league rules?
  - Preferences: adp_source, thresholds, etc.

- [ ] **Schema Validation**
  - File: `league_settings.schema.json`
  - Does it validate correctly? (Test with invalid config)

### Automation & Deployment

- [ ] **GitHub Actions Workflow**
  - File: `.github/workflows/update-data.yml`
  - Schedule: Daily at 8am ET (12pm UTC) ✅
  - Steps:
    1. Install Python dependencies
    2. Run `export_dashboard_data.py`
    3. Commit updated JSON
    4. Push to trigger GitHub Pages deploy
  - Error handling: What if Python script fails?

- [ ] **Export Script (`scripts/export_dashboard_data.py`)**
  - Calls: `LineupOptimizer.get_daily_recommendations()`
  - Output: `apps/baseball-dashboard/public/api/daily_lineup.json`
  - Format: Must match dashboard TypeScript types
  - Error handling: Graceful degradation if lineup fails?

- [ ] **Dashboard Data Contract**
  - Check JSON structure matches frontend expectations
  - Required fields: player, position, team, opponent, confidence, etc.
  - Handle missing data: What if some fields are null?

---

## Specific Audit Tasks

### Task 1: Trace a Sample Lineup Recommendation

Pick one player from the roster (e.g., "Mookie Betts") and trace the entire data flow:

1. **Input**: Player object with name, position, team
2. **Game lookup**: Find Mookie's game today (LAD vs ?)
3. **Opponent pitcher**: Identify opposing pitcher
4. **Matchup score**: Calculate based on pitcher ADP + recent stats
5. **Park score**: Get Dodger Stadium park factor
6. **Form score**: Query Statcast for last 14 days
7. **Platoon score**: Check L vs R
8. **Breakout boost**: Check for signals
9. **Final confidence**: Weighted average
10. **Tier assignment**: Must Start / Start / Flex / Bench
11. **Reasons**: Generated list of factors

**Document every step** - Where does data come from? What if it's missing?

### Task 2: Test Error Scenarios

Simulate failures and check graceful degradation:

- [ ] MLB Stats API returns 500 error
- [ ] Statcast has no data for a player
- [ ] ADP scraping fails
- [ ] Player not found in any API
- [ ] Pitcher is TBD
- [ ] No games scheduled (off-day)

**Expected**: System should still produce recommendations with available data

### Task 3: Validate Cache Performance

Run lineup optimizer twice:

1. **Cold start**: Clear `.cache/` directory, time execution
2. **Warm start**: Run again, time execution

**Expected**: Warm start should be 5-10x faster

### Task 4: Check Data Freshness

Verify data is current:

- [ ] ADP data: Last updated timestamp
- [ ] Game schedule: Today's games
- [ ] Statcast stats: Recent window (last 14 days)
- [ ] Cache expiry: TTL working correctly

### Task 5: Scoring Accuracy Review

Compare lineup recommendations to actual results (if historical data available):

- [ ] Do high-confidence players actually perform better?
- [ ] Are "hot streak" players accurately identified?
- [ ] Is pitcher quality scoring predictive?

---

## Deliverables

### 1. Executive Summary (Required)

- Overall system health (Red/Yellow/Green)
- Critical issues found (if any)
- Top 3 recommendations for lineup optimizer
- Quick wins vs. longer-term improvements

### 2. Detailed Findings Report

For each audit task:
- What was checked
- What was found (good and bad)
- Specific code references (file:line)
- Severity: Critical / High / Medium / Low

### 3. Data Quality Assessment

- Which data sources are reliable?
- Which data sources are fragile?
- What data is missing that could improve lineup quality?

### 4. Improvement Recommendations

Prioritized list of enhancements:

**High Priority** (Impacts daily decisions)
- Missing data sources
- Logic flaws
- Performance issues
- Cache inefficiencies

**Medium Priority** (Nice to have)
- Better error messages
- Additional metrics
- UI improvements

**Low Priority** (Future enhancements)
- Advanced analytics
- Machine learning
- Historical backtesting

---

## Context: Recent Improvements

The system has undergone significant upgrades. These should be validated:

### Phase 1: Performance & Reliability ✅

1. **Global Cache Manager** (`cache_manager.py`)
   - Persistent caching with TTL
   - Reduces API calls by ~90%
   - Verify: Is it working? Check cache hit rates

2. **API Retry Logic** (`daily_matchups.py`, `adp_fetcher.py`)
   - 3 retries with exponential backoff
   - 30-second timeout
   - Verify: Test with simulated failures

3. **Breakout Integration** (`waiver_analyzer.py`, `lineup_optimizer.py`)
   - Statcast signals integrated into lineup scoring
   - Verify: Are breakout boosts applied correctly?

### Phase 2: Intelligence Upgrades ✅

4. **Real Form Scoring** (replaced hardcoded 75)
   - Uses actual Statcast data (last 14 days)
   - Hitters: hard hit %, barrel %
   - Pitchers: K %, hard hit % allowed
   - Verify: Logic correctness

5. **Pitcher Quality Scoring** (replaced hardcoded ace list)
   - Uses ADP + recent Statcast performance
   - Elite (ADP <50), Good (50-100), Average (100-200), Weak (>200)
   - Verify: Scoring ranges make sense

6. **Position Need Scoring** (`waiver_analyzer.py`)
   - Prioritizes pickups that fill roster gaps
   - +0 to +50 point boost
   - Verify: Math is correct

7. **Configurable Weights** (`league_settings.json`)
   - User can customize lineup scoring factors
   - Verify: Weights are loaded and applied

### Phase 3: Automation ✅

8. **GitHub Actions Workflow**
   - Daily automated updates at 8am ET
   - Verify: Workflow runs successfully

9. **Dashboard Export** (`export_dashboard_data.py`)
   - Generates JSON for web dashboard
   - Verify: Output format is correct

---

## Success Criteria

A successful audit will:

1. ✅ Validate that lineup recommendations are based on **accurate, reliable data**
2. ✅ Confirm all data sources are **properly integrated** and **cached**
3. ✅ Identify any **missing data** that could improve lineup quality
4. ✅ Verify **error handling** degrades gracefully
5. ✅ Provide **actionable recommendations** to improve the daily lineup feature
6. ✅ Assess whether the system is **production-ready** for daily use

---

## Notes

- **Focus first on lineup optimizer** - It's used daily and most critical
- **Data quality > New features** - Lineup decisions must be trustworthy
- **Be specific** - Reference exact files, functions, and line numbers
- **Test edge cases** - Real-world data is messy
- **Consider user impact** - Bad lineup recs lose games

**The lineup optimizer must be rock-solid. Audit accordingly.**
