# Changelog

## [Unreleased] - 2026-02-01

### Added - Daily Lineup Optimizer 🆕
- **Stat-Backed Recommendations** - Daily start/sit advice based on real data
- **Park Factors** - 30 MLB ballparks with hitter/pitcher ratings
- **Matchup Analysis** - Opponent pitcher quality scoring
- **Hot Streak Detection** - Rolling 7/14/30 day performance
- **Confidence Scoring** - 0-100% confidence on every recommendation
- **5-Tier System** - MUST START, START, FLEX, BENCH, AVOID

## [Unreleased] - 2026-02-01

### Added - Quick Wins ✅
- **Position Filtering** - Filter waiver recommendations by position (2B, SP, OF, etc.)
- **Interactive CLI Mode** - Arrow key navigation with `npm run waivers:interactive`
- **League Settings File** - Centralized configuration in `config/league_settings.json`
- **Fuzzy Name Matching** - Handle accents, suffixes, and typos in player names
- **Demo Mode** - Test features without Yahoo API connection
- **Quick Reference Guide** - `docs/QUICK_REFERENCE.md` for common commands

### Improved
- **Name Normalization** - Automatically matches `José Ramírez` / `Jose Ramirez`
- **Suffix Handling** - `Ronald Acuña Jr.` = `Ronald Acuna`
- **Typo Tolerance** - Fuzzy matching finds closest matches (85%+ similarity)
- **Configurable Thresholds** - Customize recommendation tiers in settings
- **Better Error Handling** - Graceful fallbacks to demo mode

### Technical
- Integrated `fuzzywuzzy` and `python-Levenshtein` for name matching
- Added `prompt_toolkit` for interactive CLI
- Created `LeagueSettings` dataclass for type-safe config
- Implemented `ADPFetcher._adp_cache` for performance
- Added `normalize_name()` and `find_similar_names()` utilities

---

## [0.2.0] - 2026-01-30

### Added - Waiver Wire Assistant
- **Waiver Wire Analyzer** - Compare free agents to roster
- **ADP-Based Recommendations** - Calculate value gain
- **Keeper Cost Integration** - Factor in keeper eligibility
- **Tiered Confidence Levels** - STRONG, GOOD, CONSIDER
- **Command-Line Interface** - `npm run waivers`

### Added - Yahoo API Integration
- **OAuth 2.0 Flow** - Manual implementation for Yahoo
- **Roster Syncing** - Fetch current roster via API
- **Draft Data Integration** - Link players to draft rounds
- **Free Agent Fetching** - Query available pickups
- **Token Management** - Auto-refresh expired tokens

### Added - ADP Data Automation
- **Web Scraping** - Fetch ADP from FantasyPros
- **Auto-Update Script** - `npm run update:adp`
- **Player Matching** - Map roster to ADP database
- **Data Caching** - Reduce API calls

---

## [0.1.0] - 2026-01-15

### Initial Release
- **Keeper Rules Engine** - Calculate keeper costs
- **CSV Import** - Load roster from file
- **Keeper Analysis** - Identify best keepers
- **Draft Round Tracking** - Handle 13+ rounds → Round 12
- **Undrafted FA Rules** - Start as Round 12 keepers
- **Basic CLI** - `npm run analyze`

### Documentation
- **QUICKSTART.md** - Setup instructions
- **README.md** - Project overview
- **KEEPER_RULES.md** - League-specific rules

---

## Coming Next

### Phase 2: Breakout Detector 🚀
- [ ] Statcast API integration
- [ ] Breakout prediction algorithm
- [ ] Alert system for emerging players
- [ ] Historical trend analysis

### Phase 3: Trade Analyzer
- [ ] Multi-player trade evaluation
- [ ] Keeper cost impact
- [ ] Positional needs assessment
- [ ] Trade suggestion engine

### Phase 4: Schedule Analyzer
- [ ] Opponent strength ratings
- [ ] Streaming recommendations
- [ ] Two-start pitcher alerts
- [ ] Weekly projections

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| Unreleased | 2026-02-01 | Quick wins completed |
| 0.2.0 | 2026-01-30 | Waiver Wire + Yahoo API |
| 0.1.0 | 2026-01-15 | Initial release |
