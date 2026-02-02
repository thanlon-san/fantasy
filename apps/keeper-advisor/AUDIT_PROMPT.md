# Fantasy Baseball Keeper Advisor - Complete System Audit

## Your Mission

You are a senior software architect and fantasy baseball expert conducting a comprehensive audit of a fantasy baseball intelligence system. Your goal is to:

1. **Verify system integrity** - Check all connections, imports, dependencies, and integrations
2. **Assess tool synergy** - Ensure tools work together efficiently and share data intelligently
3. **Identify improvements** - Suggest concrete enhancements to existing tools
4. **Propose innovations** - Recommend new features that leverage the existing infrastructure

---

## System Overview

This is a **Python-based fantasy baseball toolkit** with multiple interconnected tools for year-round competitive advantage. The system integrates:

- **External APIs**: Yahoo Fantasy Sports, MLB Stats API, FantasyPros ADP, pybaseball (Statcast)
- **In-season tools**: Daily lineup optimizer, waiver wire analyzer, breakout detector
- **Pre-season tools**: Keeper analyzer, draft strategy
- **Data sources**: Real-time MLB games, advanced metrics, historical performance, park factors

---

## Project Structure

```
apps/keeper-advisor/
├── src/                          # Core modules
│   ├── adp_fetcher.py           # ADP data from FantasyPros
│   ├── analyzer.py              # Keeper value analysis
│   ├── breakout_detector.py     # Statcast-based breakout detection
│   ├── daily_matchups.py        # MLB game schedule & matchups
│   ├── lineup_optimizer.py      # Daily lineup recommendations
│   ├── statcast_client.py       # Statcast data fetcher
│   ├── waiver_analyzer.py       # Waiver wire recommendations
│   ├── yahoo_client.py          # Yahoo API integration
│   ├── league_settings.py       # League config management
│   └── models.py                # Data models
│
├── scripts/                      # CLI tools
│   ├── analyze_keepers.py       # Keeper analysis CLI
│   ├── waiver_wire.py           # Waiver wire CLI
│   ├── waiver_wire_interactive.py  # Interactive waiver tool
│   ├── breakout_scanner.py      # Breakout detection CLI
│   ├── daily_lineup.py          # Daily lineup CLI
│   └── fetch_yahoo_roster.py    # Yahoo roster fetcher
│
├── config/
│   ├── league_settings.json     # League configuration
│   └── oauth2.json              # Yahoo OAuth tokens
│
└── docs/                         # Documentation
    ├── QUICKSTART.md
    ├── DAILY_LINEUP_OPTIMIZER.md
    ├── BREAKOUT_DETECTOR.md
    └── UNIFIED_INTELLIGENCE_SYSTEM.md
```

---

## Phase 1: System Integrity Audit

### 1.1 Dependency Check

Review `requirements.txt` and verify:

- [ ] All imports in source files match declared dependencies
- [ ] No missing packages
- [ ] No version conflicts
- [ ] Optional dependencies clearly marked

### 1.2 Import Chain Analysis

For each module in `src/`, verify:

- [ ] All imports resolve correctly
- [ ] No circular dependencies
- [ ] Proper error handling for missing dependencies
- [ ] Clean separation of concerns

### 1.3 Configuration Validation

Check `config/league_settings.json`:

- [ ] Schema validation works (`league_settings.schema.json`)
- [ ] All required fields present
- [ ] Default values sensible
- [ ] Settings properly consumed by modules

### 1.4 Data Flow Verification

Trace data flow from:

- **Yahoo API** → Roster data → Lineup optimizer
- **MLB Stats API** → Game schedule → Matchup analysis
- **Statcast** → Advanced metrics → Breakout detection
- **FantasyPros** → ADP data → Waiver recommendations

Ensure no broken connections.

---

## Phase 2: Tool Synergy Assessment

### 2.1 Current Integration Points

**Lineup Optimizer ↔ Breakout Detector**

- Lineup optimizer calls breakout detector for confidence boost
- Check: Is this integration optimal? Could it be deeper?

**Waiver Analyzer ↔ ADP Fetcher**

- Waiver tool uses ADP for value assessment
- Check: Any gaps in data flow?

**All Tools ↔ League Settings**

- Centralized config via `league_settings.json`
- Check: Are all tools using it? Any hardcoded values that should be config?

### 2.2 Data Caching Strategy

Review caching in:

- `adp_fetcher.py` - ADP cache
- `daily_matchups.py` - Games cache
- `breakout_detector.py` - Analysis cache
- `lineup_optimizer.py` - Breakout cache

Questions:

- [ ] Is cache invalidation handled correctly?
- [ ] Are cache keys unique and collision-free?
- [ ] Do caches persist across CLI runs? Should they?
- [ ] Is there a global cache manager opportunity?

### 2.3 Shared Data Structures

Check consistency of:

- `Player` model usage across modules
- `Roster` representation
- Date/time handling (timezone awareness?)
- Position abbreviations (OF vs LF/CF/RF)

### 2.4 Cross-Tool Opportunities

**Questions:**

1. Should the waiver analyzer use breakout signals automatically?
2. Could daily lineup recommendations feed into keeper decisions?
3. Should there be a unified "player profile" that aggregates:
   - ADP ranking
   - Keeper value
   - Recent performance
   - Breakout signals
   - Upcoming matchups
4. Is there a "player database" opportunity to reduce API calls?

---

## Phase 3: Tool-Specific Improvements

### 3.1 Daily Lineup Optimizer

**Current Features:**

- Park factors
- Opponent matchup quality
- Recent form (rolling stats)
- Platoon splits (L/R)
- Breakout signals

**Audit Questions:**

- [ ] Are the scoring weights optimal? (Currently: 30% matchup, 20% park, 25% form, 15% platoon, 10% breakout)
- [ ] Should weather be integrated? (Wind, temperature for hitters)
- [ ] Is "recent form" window (last 14 days) appropriate?
- [ ] Could it suggest specific lineup configurations, not just start/sit?
- [ ] Should it consider your league's scoring system from `league_settings.json`?
- [ ] Injury status awareness?

**Improvement Ideas:**

- [ ] Add "slate optimizer" - optimize entire starting lineup simultaneously
- [ ] "Vegas lines" integration - implied runs per game
- [ ] "Stack suggestions" - recommend hitter/pitcher combos from same game
- [ ] Historical matchup data - "Player X vs Pitcher Y career stats"
- [ ] "Confidence intervals" - show range of likely outcomes

### 3.2 Breakout Detector

**Current Features:**

- Statcast metrics (exit velo, hard-hit%, barrel%, K%, BB%, spin rate)
- Time period comparison (recent vs baseline)
- Confidence scoring
- Signal strength (STRONG, EMERGING, WATCH, FADING)

**Audit Questions:**

- [ ] Are the thresholds calibrated correctly?
- [ ] Does it distinguish between "hot streak" vs "true talent change"?
- [ ] Should it track persistence of signals over time?
- [ ] Integration with minor league stats for prospect breakouts?
- [ ] Injury recovery tracking (players coming off IL)?

**Improvement Ideas:**

- [ ] "Breakout timeline" - track when signal first emerged
- [ ] "Similar player comps" - find historical similar profiles
- [ ] "Regression risk" - predict likelihood of cooling off
- [ ] "Sell-high alerts" - when to trade a breakout player
- [ ] "League context" - how many other teams noticed this player?

### 3.3 Waiver Wire Analyzer

**Current Features:**

- ADP-based value identification
- Position filtering
- Keeper value assessment
- Fuzzy name matching

**Audit Questions:**

- [ ] Does it consider team needs (weak positions)?
- [ ] Should it integrate with breakout detector automatically?
- [ ] Does it account for league trends (ownership %)?
- [ ] Should it suggest drop candidates from your roster?
- [ ] Does it prioritize based on league settings (scoring categories)?

**Improvement Ideas:**

- [ ] "ROS (Rest of Season) projections" from multiple sources
- [ ] "Waiver wire tiers" - group similar value players
- [ ] "Schedule analysis" - upcoming favorable matchups
- [ ] "Handcuff suggestions" - backup for injury-prone players
- [ ] "FAAB bid suggestions" - recommend dollar amounts (if applicable)
- [ ] "Drop candidates" - suggest who to drop for pickups

### 3.4 Keeper Analyzer

**Current Features:**

- ADP vs keeper cost analysis
- Value surplus calculation
- Round adjustment

**Audit Questions:**

- [ ] Should it consider keeper deadline strategy (pickup before deadline)?
- [ ] Does it account for dynasty/keeper format differences?
- [ ] Integration with breakout detector for young players?
- [ ] Does it suggest draft strategy based on keepers?

**Improvement Ideas:**

- [ ] "Keeper simulator" - test different keeper combinations
- [ ] "Trade value calculator" - what's fair value for keeper trades?
- [ ] "Keeper vs redraft flexibility" - should you keep or get fresh pick?

---

## Phase 4: New Feature Proposals

### 4.1 Unified Player Intelligence Dashboard

Create a `PlayerIntelligence` class that aggregates:

```python
class PlayerIntelligence:
    player: Player
    adp: Optional[int]
    keeper_value: Optional[KeeperValue]
    breakout_signal: Optional[BreakoutAlert]
    recent_performance: Dict[str, float]
    upcoming_matchups: List[Matchup]
    ownership_trend: Optional[str]
    recommendation: str  # "ACQUIRE", "HOLD", "SELL", "DROP"
```

This becomes the "single source of truth" for any player analysis.

### 4.2 Trade Analyzer

Evaluate proposed trades:

- Compare player values (ADP, keeper, projections)
- Assess team need fit
- Calculate "win-now" vs "future value" tradeoffs
- Generate trade suggestions based on league inefficiencies

### 4.3 Playoff Optimizer

Different from daily lineup:

- Focus on championship weeks
- Prioritize high ceiling over safety
- Consider opponent's team in H2H matchups
- "Must-win" recommendations

### 4.4 Schedule Analyzer

Look ahead at upcoming weeks:

- Which teams have favorable schedules?
- Who plays in good hitting parks next week?
- Identify "streaming targets" for SP-heavy weeks

### 4.5 Injury Tracker & Replacement Finder

- Monitor injury reports
- Automatically suggest waiver replacements
- Track expected return dates
- Recommend IL strategy (when to hold vs drop)

### 4.6 League Context Analyzer

If you can access league data:

- Identify teams in need (trade targets)
- Find undervalued players league-wide
- Suggest "buy low" and "sell high" candidates
- Predict other teams' moves (waiver claims)

### 4.7 Notification System

Proactive alerts:

- "Player X just joined waivers (strong breakout signal)"
- "Your player Y has tough matchup today"
- "Injury update: Player Z to IL"
- "ADP riser alert: Player A jumped 50 spots"

### 4.8 Historical Performance Tracker

Store and analyze:

- Your lineup decisions (were they correct?)
- Waiver successes and misses
- Breakout prediction accuracy
- Generate "season report card"

---

## Phase 5: Architecture Recommendations

### 5.1 Suggested Architectural Improvements

**Consider:**

1. **Service Layer Pattern** - Separate business logic from CLI scripts
2. **Repository Pattern** - Abstract data access (API calls, caching)
3. **Dependency Injection** - Make testing easier, reduce coupling
4. **Event System** - Publish/subscribe for cross-tool notifications
5. **Background Jobs** - Daily data refresh, cache warming

**Example Structure:**

```
src/
├── services/              # Business logic
│   ├── lineup_service.py
│   ├── waiver_service.py
│   └── breakout_service.py
├── repositories/          # Data access
│   ├── mlb_repo.py
│   ├── yahoo_repo.py
│   └── statcast_repo.py
├── models/                # Domain models
└── utils/                 # Shared utilities
```

### 5.2 Testing Strategy

Currently missing tests. Recommend:

- Unit tests for each service
- Integration tests for API clients
- Mock data for CLI testing
- Regression tests for value calculations

### 5.3 Performance Optimization

- [ ] Profile API call frequency - are we rate-limited?
- [ ] Batch operations where possible
- [ ] Async/await for parallel API calls
- [ ] Database consideration for historical data (SQLite?)

---

## Phase 6: Web Frontend Integration Opportunities

Given the new web frontend (`apps/baseball-dashboard/`):

### 6.1 Backend API Design

What API endpoints would best serve the frontend?

```
GET  /api/lineup/daily              # Today's recommendations
GET  /api/lineup/schedule           # Upcoming games
POST /api/lineup/optimize           # Custom lineup optimization

GET  /api/waivers                   # Top waiver targets
GET  /api/waivers/:position         # Position-filtered
POST /api/waivers/analyze           # Analyze specific players

GET  /api/breakouts                 # Current breakout alerts
GET  /api/breakouts/:playerId       # Specific player analysis

GET  /api/roster                    # Your current roster
POST /api/roster/import             # Import from Yahoo
```

### 6.2 Real-time Updates

Should the system support:

- WebSocket connections for live updates?
- Polling intervals for daily refreshes?
- Server-Sent Events for notifications?

### 6.3 Authentication & Multi-User

Currently single-user. Consider:

- Multi-league support
- User authentication
- Shared recommendations
- League-mate analysis

---

## Phase 7: Data Quality & Reliability

### 7.1 Error Handling Audit

For each API integration, check:

- [ ] Rate limiting handling
- [ ] Timeout handling
- [ ] Graceful degradation (fallback to cached data)
- [ ] User-friendly error messages
- [ ] Logging for debugging

### 7.2 Data Validation

- [ ] Input validation for all user inputs
- [ ] API response validation
- [ ] Type hints and runtime type checking
- [ ] Schema validation for JSON configs

### 7.3 Edge Cases

Test scenarios:

- Off-season (no games scheduled)
- All-Star break
- Trade deadline
- Playoffs
- Suspended games
- Player traded mid-season
- Newly called-up players (no stats)

---

## Deliverables

Please provide:

### 1. **Connectivity Report**

- List of all integration points
- Any broken connections found
- Import/dependency issues
- Configuration problems

### 2. **Synergy Assessment**

- Current tool interactions (diagram if helpful)
- Missed opportunities for integration
- Data flow inefficiencies
- Caching strategy recommendations

### 3. **Tool Improvement Roadmap**

For each tool (Lineup, Breakout, Waiver, Keeper):

- Quick wins (< 1 day)
- Medium enhancements (1-3 days)
- Major features (1 week+)
- Prioritized by impact vs effort

### 4. **New Feature Proposals**

- Top 3-5 most impactful new features
- Implementation complexity estimate
- Dependencies and prerequisites
- Expected user value

### 5. **Architecture Recommendations**

- Code organization improvements
- Design pattern suggestions
- Testing strategy
- Performance optimizations

### 6. **Implementation Plan**

Prioritized action items:

1. Critical fixes (must do)
2. Quick wins (should do)
3. Strategic enhancements (nice to have)
4. Future innovations (vision)

---

## Context & Constraints

**What's Working Well:**

- Modular design with clear separation
- Good documentation
- Active integration of multiple data sources
- User-friendly CLI tools

**Known Limitations:**

- No automated tests
- Single-user only (for now)
- Manual data refresh
- CLI-only (web frontend is new)
- Off-season data availability

**User's Goals:**

1. Daily lineup optimization for maximum points
2. Identify undervalued waiver pickups before others
3. Spot breakout players early
4. Make optimal keeper decisions
5. Gain competitive advantage through data

**Success Metrics:**

- More fantasy points scored
- Better waiver acquisitions
- Earlier breakout detection
- Optimal keeper selection
- Winning the championship 🏆

---

## Getting Started

1. Read the project structure above
2. Review key files:
   - `apps/keeper-advisor/src/lineup_optimizer.py` - Main lineup logic
   - `apps/keeper-advisor/src/breakout_detector.py` - Breakout detection
   - `apps/keeper-advisor/src/waiver_analyzer.py` - Waiver recommendations
   - `apps/keeper-advisor/docs/UNIFIED_INTELLIGENCE_SYSTEM.md` - System overview
3. Test the CLI tools in `scripts/`
4. Trace the data flow through the system
5. Identify gaps, inefficiencies, and opportunities

---

## Questions to Answer

1. **Integration**: Are all tools properly connected and sharing data efficiently?
2. **Configuration**: Is `league_settings.json` being fully utilized?
3. **Caching**: Is the caching strategy optimal?
4. **Weights/Thresholds**: Are scoring weights and breakout thresholds well-calibrated?
5. **Data Quality**: Are we getting the best available data from each source?
6. **User Experience**: Are the CLI tools intuitive? Is output actionable?
7. **Missing Features**: What obvious capabilities are absent?
8. **Competitive Edge**: What would give this system a clear advantage over competitors?
9. **Scalability**: Can this system handle multiple users/leagues?
10. **Maintainability**: Is the code easy to update and extend?

---

## Your Expertise

Apply your knowledge of:

- **Software Architecture** - Clean code, design patterns, scalability
- **Fantasy Baseball** - Winning strategies, key metrics, edge cases
- **Data Science** - Statistical analysis, feature engineering, validation
- **API Design** - RESTful design, caching, rate limiting
- **User Experience** - Actionable insights, clear recommendations

**Be thorough, be critical, be innovative.** This system should be a league-winning advantage.

Good luck! 🏆⚾
