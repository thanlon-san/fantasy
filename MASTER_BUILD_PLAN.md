# Fantasy Baseball Dashboard — Master Build Plan

The full roadmap for turning the baseball dashboard into an elite season-long weapon.
Organized into 6 phases with clear dependencies. Each phase is independently valuable —
you get real gains after every phase, not just at the end.

**Scoring categories (H2H, 12 cats):**
- Batting: R, H, HR, RBI, SB, OPS
- Pitching: SV, HR allowed, K, ERA, WHIP, QS

**Strategy reminder:** Stack closers to dominate ERA/WHIP/SV/HR-allowed (4 of 6 pitching cats).
Manufacture Ks via streaming. Win batting through lineup optimization and waiver aggression.

**Monorepo layout (pnpm workspaces):**
- `apps/baseball-engine/` — Python data engine (36 modules in `src/`, CLI scripts in `scripts/`)
- `apps/baseball-dashboard/` — Next.js 15 / React 19 frontend (18 routes, Recharts, TanStack Query)
- `apps/baseball-engine/scripts/draft_server.py` — Consolidated FastAPI server (port 8001, all endpoints)
- `apps/baseball-api/` — **DELETED** (all endpoints migrated to `draft_server.py` in Sprint 9; `main.py` removed, `railway.json` updated)
- `packages/types/` — Shared TypeScript types + Zod runtime validation schemas

---

## Post-Build Audit (2026-03-29)

All 6 phases (37 tasks, 10 sprints) are implemented. An independent audit confirmed code
exists on disk for every planned feature. Below are the remaining polish items and known gaps.

### Remaining TODO (priority order)

**Must do before season use:**

1. ~~**Install missing dependencies**~~ ✅ DONE (2026-03-29)
   - `pnpm install` from workspace root — links `@fantasy/types` package
   - `zod` added as direct dependency to `baseball-dashboard`
   - **Still manual:** `pip install apscheduler` in your Python environment

2. **Set required environment variables** (see `.env.example`)
   - `ODDS_API_KEY` — enables Vegas implied run totals (free at https://the-odds-api.com)
   - `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` — enables LLM scouting reports (optional)
   - `AUTO_LINEUP=true` — enables automated lineup pushing at 10am ET (optional)
   - `SLACK_WEBHOOK_URL` — enables Slack notifications for auto-lineup (optional)

3. **Run `python scripts/generate_handedness.py`** — populate full 40-man roster handedness
   data (currently seeded with ~80 well-known players)

4. **Rotate Yahoo consumer secret** — credentials were removed from git tracking (Phase 0A)
   but the old secret was in git history; rotate via Yahoo Developer Console

**Should do (functional gaps):**

5. ~~**Wire `@fantasy/types` Zod schemas into the dashboard**~~ ✅ DONE (2026-03-29)
   - 11 files updated: 3 components (`player-table`, `optimal-lineup`, `waiver-wire-table`)
     + 8 pages (`page`, `matchup`, `regression`, `projections`, `trade`, `accuracy`,
     `player/[name]`, `streamers`)
   - Inline type declarations replaced with imports from `@fantasy/types`
   - `.parse()` runtime validation added on 6 API fetch boundaries
     (regression, projections, trade, accuracy, player-profile, bullpen-alerts)
   - `PlayerProfileSchema` extended with `recent_stats` field
   - Pages with no matching shared types left untouched: `draft`, `draft/live`, `closers`,
     `trajectory`, `standings`, `planner`, `prospects`

6. ~~**Delete `apps/baseball-api/main.py`**~~ ✅ DONE (2026-03-29)
   - File deleted. `.env.example` updated (removed stale port 8000 URL).
   - `railway.json` updated to point at `apps/baseball-engine/scripts/draft_server.py`.
   - **Note:** `docs/DEVELOPMENT.md`, `docs/DEPLOYMENT.md`, and root `README.md` still
     reference `baseball-api/` in narrative text — update these if you publish docs.

7. ~~**Migrate `cache_manager.py` from shelve to SQLite**~~ ✅ DONE (2026-03-29)
   - `cache_manager.py` rewritten to delegate to `database.py` (`cache_get`, `cache_set`,
     `cache_delete`, `cache_clear_expired`). Public API unchanged — all callers work as-is.
   - The `.cache/` shelve directory can be safely deleted.

8. ~~**Fix duplicate "Prospects" entry in `mobile-nav.tsx`**~~ ✅ DONE (2026-03-29)
   - Removed duplicate `/prospects` from `MORE_ITEMS`. Unused `Star` icon import removed.

**Ongoing maintenance (during season):**

9. **Update `data/bullpen_depth.json` weekly** — Closer roles change constantly
   (trades, injuries, demotions). Stale data means wrong vulture save recommendations.

10. **Update `data/prospect_watchlist.json` periodically** — As prospects get called up or
    rankings change, update the 50-player list.

11. **Update `data/umpire_tendencies.json` weekly** — New UmpireScorecards data publishes
    after each series. Zone sizes and accuracy scores shift over the season.

12. **Update `.env.example`** to document all new optional env vars added in Sprints 3–10.
    (Partially done — stale `NEXT_PUBLIC_API_URL` reference removed from dashboard `.env.example`.)

### Architecture summary (post-build)

```
apps/baseball-engine/src/ (36 Python modules)
├── Core:        models.py, importers.py, league_settings.py, keeper_rules.py, analyzer.py
├── Data fetch:  yahoo_client.py, yahoo_oauth_manual.py, stats_fetcher.py, statcast_client.py,
│                adp_fetcher.py, daily_matchups.py, savant_leaderboards.py
├── Analytics:   lineup_optimizer.py, waiver_analyzer.py, breakout_detector.py, breakout_tracker.py,
│                accuracy_tracker.py, advanced_analytics.py, regression_analyzer.py, speed_tracker.py
├── New sources: projection_fetcher.py, odds_fetcher.py, injury_tracker.py, bullpen_tracker.py,
│                bullpen_fatigue.py, catcher_framing.py, pitch_mix_tracker.py, prospect_tracker.py
├── Features:    trade_analyzer.py, streamer_planner.py, weekly_planner.py, llm_scouting.py
├── Infra:       cache_manager.py, database.py, ai_advisor.py

apps/baseball-dashboard/app/ (18 routes)
├── /                  Main dashboard (lineup, waivers, breakouts, keepers, bullpen alerts)
├── /matchup           H2H category matchup with enhanced gap analysis
├── /standings         League category standings grid
├── /closers           Closer monitor with stats
├── /trajectory        Category rank sparklines over time
├── /draft             Pre-draft keeper board
├── /draft/live        Live draft UI
├── /regression        Buy-low / sell-high xStats scatter plot
├── /projections       Steamer ROS projections (hitters + pitchers)
├── /trade             Category-impact trade analyzer with Recharts bar chart
├── /streamers         Two-start SP streamers + bullpen fatigue / vulture alerts
├── /planner           Full-week streaming plan (daily SP options + team game counts)
├── /prospects         Minor league prospect watchlist with call-up scores
├── /player/[name]     Player profile (radar chart, Savant percentiles, rolling stats, regression)
├── /accuracy          Prediction accuracy dashboard with Recharts bar charts

packages/types/src/ (7 Zod schema files)
├── player.ts, lineup.ts, matchup.ts, breakout.ts, waiver.ts, projections.ts, accuracy.ts
```

### Data source inventory (post-build)

| Source | Module | Cache TTL | Env Var Required |
|--------|--------|-----------|------------------|
| Yahoo Fantasy API | `yahoo_client.py` | varies | `YAHOO_OAUTH_JSON` (or local `oauth2.json`) |
| MLB Stats API (schedule, injuries, umpires, MiLB) | `daily_matchups.py`, `injury_tracker.py`, `advanced_analytics.py`, `prospect_tracker.py` | 2–6h | None |
| Statcast / Baseball Savant (pybaseball) | `statcast_client.py` | pybaseball internal | None |
| Baseball Savant Leaderboards (CSV) | `savant_leaderboards.py` | 24h | None |
| FanGraphs Steamer ROS Projections | `projection_fetcher.py` | 24h | None |
| The Odds API (Vegas lines) | `odds_fetcher.py` | 2h | `ODDS_API_KEY` |
| FantasyPros ADP (scraped) | `adp_fetcher.py` | 24h | None |
| UmpireScorecards | `data/umpire_tendencies.json` | Manual | None |
| Bullpen depth charts | `data/bullpen_depth.json` | Manual | None |
| Prospect watchlist | `data/prospect_watchlist.json` | Manual | None |
| Player handedness | `data/player_handedness.json` | Monthly script | None |
| Claude / GPT (LLM reports) | `llm_scouting.py` | None | `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` |

---

## Sprint 10 — COMPLETED (2026-03-29)

All of Phase 5C + 5D + 5E + 6A + 6B + 6D completed. Automated lineup setting, LLM scouting reports, accuracy dashboard, SQLite database, background scheduler, and end-to-end type safety are live. **All 6 phases are now complete.**

---

## Sprint 9 — COMPLETED (2026-03-29)

All of Phase 5A + 5B + 6C completed. Pitch mix evolution detection, catcher framing integration, and consolidated API server are live.

---

## Sprint 8 — COMPLETED (2026-03-29)

All of Phase 3E + 3F + 4E + 4F completed. Prospect call-up watchlist, enhanced matchup with gap analysis, mobile bottom nav, and toast notifications are live.

---

## Sprint 7 — COMPLETED (2026-03-28)

All of Phase 2C + 2D + 4D completed. Savant leaderboards, live umpire assignments, and regression page (scatter plot) are live.

---

## Sprint 6 — COMPLETED (2026-03-28)

All of Phase 4A + 4B + 4C completed. Recharts charting library, TanStack Query data fetching, and player profile pages are live.

---

## Sprint 5 — COMPLETED (2026-03-28)

All of Phase 3C + 3D completed. Category-impact trade analyzer and full-week streaming planner are live.

---

## Sprint 4 — COMPLETED (2026-03-28)

All of Phase 2E + 3A + 3B completed. Bullpen depth charts, fatigue monitoring with vulture save alerts, and the two-start pitcher streamer planner are live.

---

## Sprint 3 — COMPLETED (2026-03-28)

All of Phase 2A + 2B completed. The two highest-value data sources are now integrated.

---

## Sprint 2 — COMPLETED (2026-03-28)

All of Phase 1C + 1D + 1E + 1F completed. Phase 1 is now fully done.

---

## Sprint 1 — COMPLETED (2026-03-28)

All of Phase 0 + Phase 1A + Phase 1B were completed in a single session.

---

## Phase 0: Housekeeping & Critical Fixes ✅ COMPLETE

_All 5 tasks completed._

### 0A. Remove OAuth credentials from git history ✅

- Added `apps/baseball-engine/config/oauth2.json` to `.gitignore`
- Ran `git rm --cached apps/baseball-engine/config/oauth2.json`
- **Still TODO:** Rotate the Yahoo consumer secret after the next commit/push

### 0B. Delete dead code ✅

All three files deleted:
- `apps/baseball-engine/scripts/api_server.py` — deleted (legacy Flask stub)
- `apps/baseball-engine/scripts/waiver_wire.py.backup` — deleted (syntactically broken duplicate)
- `apps/baseball-dashboard/components/filter-bar.tsx` — deleted (never imported)

### 0C. Lock down CORS ✅

Both servers now use an explicit allowlist instead of `"*"`:
- `apps/baseball-api/main.py` → `ALLOWED_ORIGINS` = GitHub Pages + localhost:3001 + localhost:3000
- `apps/baseball-engine/scripts/draft_server.py` → same `ALLOWED_ORIGINS`

### 0D. Complete the stub API endpoints ✅

`apps/baseball-api/main.py` endpoints are now live:
- `/api/waivers` → calls `WaiverAnalyzer` with real Yahoo free agents via `get_free_agents(LEAGUE_KEY, count=75)`
- `/api/breakouts` → runs `BreakoutDetector` on roster players + top 30 free agents, returns STRONG and EMERGING signals
- Startup now fetches roster from Yahoo API live (falls back to CSV if unavailable)
- Added a shared `_get_yahoo()` singleton so the Yahoo client is reused across all endpoints

### 0E. Wire up the orphaned AdvancedAnalytics module ✅

`src/advanced_analytics.py` is now integrated into `lineup_optimizer.py`:
- `AdvancedAnalytics` imported and initialized in `LineupOptimizer.__init__()`
- New `_get_advanced_adjustments()` method added, called from `_analyze_player_matchup()` as step 7
- Integrates: umpire zone adjustment, xBA regression detection (buy low / sell high), batted ball profile × park factor matching
- Fully gated with try/except — optimizer works normally when advanced data isn't available

---

## Phase 1: Core Analytics Upgrade ✅ COMPLETE

_1A–1B completed in Sprint 1. 1C–1F completed in Sprint 2._

### 1A. Replace ADP-based pitcher matchup scoring with live performance ✅

**What was done:**
- Added `calculate_pitcher_fip()` to `src/statcast_client.py` — computes FIP, K-BB%, and CSW% from raw Statcast pitch-level data over a configurable rolling window (default 30 days)
  - FIP = `((13×HR) + (3×(BB+HBP)) - (2×K)) / IP + 3.10`
  - CSW% = `(called_strikes + swinging_strikes) / total_pitches × 100`
  - Requires minimum 15 batters faced and 3.0 IP to avoid small-sample noise
- Completely rewrote `_get_pitcher_matchup_score()` in `src/lineup_optimizer.py`:
  - **Primary:** Weighted composite of FIP (60%), K-BB% (25%), CSW% (15%) from live Statcast
  - **Fallback:** ADP thresholds only when no recent stats exist (early season / off-season)
  - Results cached per-pitcher per-day (12-hour TTL)

### 1B. Add injury awareness ✅

**What was done:**
- Created `src/injury_tracker.py`:
  - Fetches from `https://statsapi.mlb.com/api/v1/injuries` (full IL + DTD list)
  - `InjuryRecord` dataclass with `.badge` property that returns "IL-10", "IL-60", "IL-15", "IL-7", "DTD"
  - 2-hour cache TTL via the existing `cache_manager`
  - API: `is_injured(name)`, `get_injury(name)`, `get_badge(name)`, `get_all_injuries()`
- Wired into `lineup_optimizer.py`:
  - `InjuryTracker` initialized in `LineupOptimizer.__init__()`
  - `_analyze_player_matchup()` short-circuits injured players to `AVOID` with confidence 0 and the injury badge + description as the reason
- Wired into `export_dashboard_data.py`:
  - Injury tracker loaded once after roster fetch
  - Every player in the lineup JSON now includes an `injury` field (badge string or `null`)
  - Refactored the 4 repeated lineup tier dicts into a shared `_fmt()` helper
- Dashboard badges added:
  - `player-table.tsx` — red destructive `<Badge>` next to player name when `player.injury` is truthy
  - `optimal-lineup.tsx` — same badge in the optimal lineup view
  - `Player` type updated in `page.tsx`, `player-table.tsx`, and `optimal-lineup.tsx` to include `injury?: string | null`

### 1C. Add sprint speed and stolen base modeling ✅

**What was done:**
- Created `src/speed_tracker.py`:
  - Fetches Statcast sprint speed leaderboard via `pybaseball.statcast_sprint_speed()`
  - Cross-references SB/CS from MLB Stats API season stats
  - `SpeedProfile` dataclass with `sb_upside_score` (0-100), tier classification (ELITE/FAST/AVERAGE/SLOW)
  - `is_buy_low` property: elite speed (>27.5 ft/s) + low SB totals (<5) = buy-low SB target
  - 24-hour cache on sprint speed data, 12-hour cache on SB game logs
- Integrated into `waiver_analyzer.py`: SB upside boost applied during pickup evaluation; buy-low SB signals appear in recommendation reasons
- Integrated into `breakout_detector.py`: sprint speed adds to breakout confidence for hitters with ELITE/FAST tier

### 1D. Build the regression candidates engine ✅

**What was done:**
- Created `src/regression_analyzer.py`:
  - `analyze_hitter()`: computes actual BA from Statcast events, compares to xBA/xSLG/xwOBA; 30+ point delta flags BUY_LOW or SELL_HIGH with confidence scoring
  - `analyze_pitcher()`: computes FIP (from existing `calculate_pitcher_fip()`), estimates xERA from xwOBA against; FIP-xERA gap flags buy/sell
  - `scan_players()`: bulk-scans a list of players, returns `{buy_low: [...], sell_high: [...]}`
  - All results cached per-player per-day (12-hour TTL)
- Added `/season/regression` endpoint to `draft_server.py`: scans my roster + top 30 free agents, 1-hour server-side cache
- Created `app/regression/page.tsx`: two-table layout (Buy Low + Sell High), split by hitters/pitchers, shows BA/xBA/delta/SLG/xSLG/xwOBA for hitters and FIP/xERA/delta for pitchers, confidence badges, auto-refreshes every 2 min
- Added "Regression" nav button to main dashboard header

### 1E. Upgrade the RecentStats dataclass ✅

**What was done:**
- Expanded `RecentStats` in `src/stats_fetcher.py`:
  - Hitter fields added: `obp`, `slg`, `ops`, `bb`, `hbp`, `h`, `ab`, `r`
  - Pitcher fields added: `sv`, `qs`, `ip`, `p_bb`, `p_h`, `holds`
  - `to_dict()` returns all new fields for JSON serialization
- Rewrote `_aggregate_hitter_stats()`: now computes OBP (PA-based), SLG (total bases / AB), OPS from game log data including doubles, triples, sac flies, HBP
- Rewrote `_aggregate_pitcher_stats()`: now computes IP, SV (from decision or saves field), QS (>=6.0 IP, <=3 ER), holds
- Updated `waiver-wire-table.tsx`: added OPS row for hitters; replaced Wins with IP + SV rows for pitchers; refactored to shared `StatWindow` type

### 1F. Fix handedness lookup reliability ✅

**What was done:**
- Created `data/player_handedness.json`: static JSON file seeded with ~80 well-known MLB players (bat side + pitch hand); covers most fantasy-relevant players immediately
- Created `scripts/generate_handedness.py`: fetches all active 40-man roster players from MLB Stats API `/teams/{id}/roster` + `/people/{id}`, writes full `player_handedness.json`; run monthly to keep updated
- Rewrote `_get_player_handedness()` and `_get_pitcher_handedness()` in `lineup_optimizer.py` with 3-tier priority:
  1. Static JSON file (instant, works offline)
  2. Persistent cache (30-day TTL)
  3. MLB API (fallback for unknowns)
  4. Default 'R' only if all three fail
- Platoon calculations are now reliable even when the MLB API is slow or down

---

## Phase 2: New Data Sources

_Estimated effort: 2–3 sessions. Plugs in the data that separates good tools from great ones._

### 2A. FanGraphs rest-of-season projections (Steamer/ZiPS) ✅

The most impactful single data source you can add. Steamer and ZiPS project
rest-of-season performance for every MLB player, updated daily.

**Access:** FanGraphs exports CSV leaderboards. You can either:
- Scrape the public leaderboard page (similar to `adp_fetcher.py`)
- Use the unofficial API: `https://www.fangraphs.com/api/projections?type=steamerr&stats=bat&pos=all`

**Data to pull (hitters):** PA, AVG, HR, RBI, SB, OPS, wRC+ projections
**Data to pull (pitchers):** IP, ERA, WHIP, K, QS, FIP, K-BB% projections

**Usage:**
- Power the "Buy Low / Sell High" page (Phase 3 plan item #2)
- Replace ADP as the baseline for waiver value calculations
- Feed the trade analyzer with projected rest-of-season value

**Files:** New `src/projection_fetcher.py`. Wire into `waiver_analyzer.py`
(replace raw ADP with projected value), `regression_analyzer.py`, and eventually
the trade analyzer.

### 2B. Vegas implied run totals ✅

Sportsbook implied run totals are the single most predictive number for
"how many runs will be scored in this game." They encode lineup info, weather,
pitcher matchup, umpire, and park factor into one number.

**Access:** The Odds API (free tier: 500 requests/month):
```
GET https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey=KEY&markets=totals&regions=us
```

**Usage:**
- Games with implied totals >10: stack hitters, avoid streaming pitchers
- Games with implied totals <7: start your pitchers, bench marginal hitters
- Add a "Vegas line" column to the daily lineup view
- Weight into the lineup optimizer's matchup score

**Files:** New `src/odds_fetcher.py`. Integrate into `lineup_optimizer.py` as
a new scoring factor. Add to `player-table.tsx` and `optimal-lineup.tsx`.

### 2C. Baseball Savant pre-computed leaderboards ✅

Instead of computing everything from raw pitch data (slow, rate-limited),
pull the pre-aggregated leaderboard CSVs from Savant:
- Statcast percentile rankings (EV, HardHit%, Barrel%, xBA, xSLG, xwOBA, Sprint Speed)
- Stuff+ scores for pitchers (pitch quality metric)
- Outs Above Average (fielding impact)

**Access:** Direct CSV download:
```
https://baseballsavant.mlb.com/leaderboard/custom?...&csv=true
```

**Usage:**
- Display Statcast percentiles in player detail dialog (the colorful Baseball Savant cards)
- Use Stuff+ for pitcher matchup quality (much better than FIP alone for daily decisions)
- Speed up breakout detection by using pre-computed percentiles instead of raw pitch data

**Files:** New `src/savant_leaderboards.py`. Wire into `breakout_detector.py`,
`player-detail-dialog.tsx`.

### 2D. Live umpire assignments ✅

Replace the hardcoded 10-umpire dict in `advanced_analytics.py` with live data.

**Access:** MLB Stats API:
```
GET https://statsapi.mlb.com/api/v1/schedule?date=2026-06-15&hydrate=officials
```
Returns the umpire crew for each game including the home plate umpire.

Cross-reference with umpire accuracy data from UmpireScorecards.com
(they publish a public API/dataset with zone size, accuracy, and favor metrics).

**Files:** Update `src/advanced_analytics.py` to fetch live umpire assignments.
New `data/umpire_tendencies.json` (updated weekly via script).

### 2E. Closer Monkey / bullpen depth charts ✅

Closer situations change constantly. Who's the setup man? Is there a committee?
Is a trade incoming?

**Access:** Scrape RosterResource.com or CloserMonkey.com bullpen depth charts,
or maintain a manually curated JSON file that gets updated weekly.

**Usage:**
- Power the "Vulture Save" feature (Phase 3 plan item #1)
- Show closer role confidence on the `/closers` page
- Flag setup men who might inherit the closer role

**Files:** New `src/bullpen_tracker.py` or `data/bullpen_depth.json`.
Update `closers/page.tsx`.

---

## Phase 3: Season-Long Features

_Estimated effort: 3–4 sessions. These are the tools you use every week from April to October._

### 3A. Bullpen fatigue monitor + vulture save alerts ✅

(From Phase 3 plan item #1)

Track daily pitch counts and appearance streaks for all MLB relievers.
Calculate a "fatigue score" based on:
- Consecutive days pitched (3+ = high fatigue)
- Pitch count in last 3 days (>45 = high fatigue)
- Innings pitched in last 7 days

When a closer is fatigued, alert that their primary setup man
(from the bullpen depth chart in 2E) is a vulture save opportunity.

**Dashboard:** New "Bullpen Alert" widget on the main dashboard.
Example: "Emmanuel Clase is fatigued (3 straight days). Add Hunter Gaddis for a
likely vulture save today."

**Files:** New `src/bullpen_fatigue.py`. New endpoint `/season/bullpen-alerts`.
Widget in `app/page.tsx`.

### 3B. Two-start pitcher streamer planner ✅

(From Phase 3 plan item #5)

Every Thursday/Friday, look ahead to next week's MLB schedule and identify:
1. All SPs with two scheduled starts
2. Filter to those on waivers (<50% rostered or not in your league)
3. Score matchups using opponent team K% + park factors + pitcher live FIP

**Dashboard:** New "Look Ahead" section, appears Thu–Sat.
"Pick up [Pitcher X] now — two starts next week vs CWS and OAK (high-K teams)."

**Files:** Update `src/daily_matchups.py` with `get_next_week_schedule()`.
New `src/streamer_planner.py`. New endpoint `/season/streamers`.
New page `app/streamers/page.tsx`.

### 3C. Category-impact trade analyzer ✅

(From Phase 3 plan item #3)

Evaluate trades based on your specific league standings:
1. Input: give Player A, get Player B
2. Simulate: remove A from roster projections, add B
3. Recalculate projected weekly category totals for all 12 cats
4. Compare new projections against league averages
5. Output: "This trade drops you from 3rd to 7th in HRs, but moves you from 9th to 2nd in SBs.
   Net weekly win probability: +8%."

**Requires:** ROS projections (Phase 2A) for projected value.

**Dashboard:** New page `app/trade/page.tsx` with player search/select inputs
and a visual category impact chart.

**Files:** New `src/trade_analyzer.py`. New endpoint `/season/trade-analyzer`.
New page.

### 3D. Full-week streaming planner ✅

Beyond two-start pitchers, build a comprehensive weekly streaming plan:
- For each day of the upcoming week, show the best available SP matchups on waivers
- Score by: opponent wRC+, park factor, pitcher recent FIP, game implied total
- Factor in team game counts (a team playing 7 games > 5 games for batting streamers)
- Show the "optimal stream" — which pitcher to pick up and drop each day

**Requires:** Vegas lines (2B), FIP scoring (1A), schedule data.

**Files:** New `src/weekly_planner.py`. New endpoint `/season/weekly-plan`.
New page `app/planner/page.tsx`.

### 3E. Prospect call-up watchlist ✅

(From Phase 3 plan item #6)

Maintain a curated list of top 25–50 fantasy-relevant prospects.
Track their recent minor league performance via MLB Stats API:
```
GET https://statsapi.mlb.com/api/v1/people/{id}/stats?stats=gameLog&group=hitting&season=2026&gameType=A
```

Alert when:
- A prospect is on a massive hot streak (14-day OPS > 1.000)
- 40-man roster status changes (DFA, option, recall)
- Service time clock is favorable for a call-up

**Dashboard:** New "Prospect Watch" section or page.

**Files:** New `data/prospect_watchlist.json` (manually curated, ~50 players).
New `src/prospect_tracker.py`. New endpoint `/season/prospects`.

### 3F. Enhanced category gap analysis ✅

Upgrade the existing matchup page with more actionable intelligence:
- Project end-of-week category totals based on remaining schedule
- Show exactly how many HRs/SBs/Ks you need to flip a category
- Recommend specific roster moves: "Start X over Y today to gain ~0.3 SB"
- Factor in the weekly streaming plan (3D) to show projected end-of-week improvement

**Files:** Update `draft_server.py` matchup endpoint. Update `matchup/page.tsx`.

---

## Phase 4: Frontend Overhaul

_Estimated effort: 2–3 sessions. Makes the data digestible and actionable._

### 4A. Add a real charting library ✅

Replace the hand-rolled SVG sparklines with Recharts (or Chart.js):
- Rolling stat lines over time (7/14/30 day windows)
- Category rank trajectories with trend lines
- Trade analyzer impact visualization
- Statcast percentile radar charts (like the Baseball Savant player cards)

Install: `pnpm add recharts` in baseball-dashboard.

### 4B. Adopt TanStack Query for data fetching ✅

Replace the manual `useState` + `useEffect` + `setInterval` pattern with
React Query / TanStack Query:
- Automatic cache invalidation and background refetching
- Deduplication of identical requests
- Loading/error states handled declaratively
- Stale-while-revalidate pattern

This eliminates the polling `setInterval` code on every page and makes
data fetching consistent across the app.

Install: `pnpm add @tanstack/react-query`

### 4C. Player profile page ✅

New route: `app/player/[name]/page.tsx`

A dedicated page for any player showing:
- Statcast percentile card (EV, HardHit%, Barrel%, xBA, xSLG, xwOBA, Sprint Speed)
- Rolling stat charts (AVG, HR, OPS over last 30 days)
- xStats vs actual stats comparison (regression indicator)
- Recent game log
- Career vs current opponent pitcher history
- Fantasy value trend (ADP at draft → current rank → ROS projection)

Click any player name anywhere in the dashboard to navigate here.

### 4D. Regression candidates page ✅

New route: `app/regression/page.tsx`

Two tables:
- **Buy Low:** Players where xBA > BA by 30+ points, sorted by delta
- **Sell High:** Players where BA > xBA by 30+ points, sorted by delta
- Include pitchers: ERA vs xERA, FIP vs ERA

Visual: scatter plot of actual vs expected performance. Players far from the
diagonal line are regression candidates.

### 4E. Mobile-responsive improvements ✅

Audit all pages for mobile viewport. Key changes:
- Collapse stat tables into card views on mobile
- Swipeable tabs instead of horizontal scroll
- Touch-friendly tap targets
- Bottom navigation bar on mobile

### 4F. Toast notifications for alerts ✅

When polling detects changes, show non-blocking toasts:
- "Breakout alert: [Player] showing STRONG signals"
- "Bullpen alert: [Closer] fatigued — pickup opportunity"
- "Prospect alert: [Player] called up — add now"

Use the existing `use-toast.ts` infrastructure.

---

## Phase 5: Advanced / Ambitious

_Estimated effort: variable. High ceiling, optional._

### 5A. Pitch mix evolution detection ✅

The strongest single predictor of pitcher breakouts in modern baseball.
Track when a pitcher:
- Adds a new pitch type (sweeper, cutter)
- Changes usage% on an existing pitch by >10%
- Gains 2+ mph on fastball
- Adds 200+ RPM on breaking balls

These changes precede ERA improvements by 2–4 weeks. You already have the
raw data via pybaseball's pitch-level Statcast data.

**Files:** New `src/pitch_mix_tracker.py`. Wire into `breakout_detector.py`.

### 5B. Catcher framing integration ✅

Top-3 framing catchers add ~15 called strikes per game, boosting their
pitcher's K rate and suppressing walks. When evaluating pitcher matchups,
check who's catching:
- Elite framers: boost pitcher's "toughness" score by 3–5 points
- Poor framers: reduce by 3–5 points

Data source: Baseball Savant catcher framing leaderboard (public CSV).

### 5C. Automated lineup setting ✅

Extend the existing "Set Lineup in Yahoo" button to run automatically:
- Cron job at 10am ET (after lineups lock decisions are made)
- Optimizer runs, generates optimal lineup
- Pushes to Yahoo via the existing `POST /api/set-lineup` endpoint
- Sends Slack notification with the lineup set

Requires confidence in the optimizer's accuracy before enabling.

### 5D. LLM-powered scouting reports ✅

Use the existing `ai_advisor.py` (Claude/GPT integration) to generate
natural language scouting reports:
- Weekly opponent scouting narrative
- Trade evaluation prose ("Here's why you should/shouldn't make this trade...")
- Breakout player deep-dives

Gate behind an env var so it's optional (API costs).

### 5E. Historical accuracy dashboard ✅

Track prediction accuracy over the season:
- Breakout detector: did the "STRONG" signals actually break out?
- Lineup optimizer: did "must start" players outperform "bench" players?
- Waiver recommendations: did the adds outperform the drops?

You already have `accuracy_tracker.py` and `breakout_tracker.py` — surface
this data in a new `/accuracy` page with charts.

---

## Phase 6: Infrastructure

_Do these whenever they'd make the current phase easier. Not a "phase" per se._

### 6A. Move to a real database ✅

Replace JSON files + shelve with SQLite (local) or Postgres (Railway/Neon):
- Player stats history (enables rolling charts)
- Prediction logs (enables accuracy tracking)
- Cache with proper TTL and eviction
- Waiver transaction history

SQLite is fine for single-user; Postgres if you ever want multi-league support.

### 6B. Background job scheduler ✅

Replace the GitHub Actions cron + manual script runs with a proper scheduler:
- APScheduler (Python) or node-cron
- Runs inside the Railway deployment
- Jobs: refresh roster (every 6h), refresh projections (daily), refresh stats (every 4h),
  refresh odds (every 2h on game days), refresh injuries (every hour on game days)

### 6C. Consolidated API server ✅

Merge `baseball-api/main.py` and `draft_server.py` into a single FastAPI app.
Currently there are two separate servers that serve overlapping data.
One server, one deployment, one URL.

### 6D. End-to-end type safety ✅

Add a shared types package (`packages/types/`) with TypeScript interfaces
that match the Python dataclass shapes. Use Zod for runtime validation on
the frontend. This prevents the "API changed but frontend didn't" class of bugs.

---

## Build Order (Recommended)

The dependency graph:

```
Phase 0 (housekeeping)
  ↓
Phase 1A–1F (core analytics) ← can be done in parallel
  ↓
Phase 2A (projections) ← unblocks 3C, 3D
Phase 2B (Vegas lines) ← unblocks 3D
Phase 2C (Savant leaderboards) ← unblocks 4C
Phase 2D (umpire data) ← standalone
Phase 2E (bullpen depth) ← unblocks 3A
  ↓
Phase 3A–3F (season features) ← most depend on Phase 2
  ↓
Phase 4A–4F (frontend) ← can start after Phase 1, accelerates with Phase 3
  ↓
Phase 5 (advanced) ← whenever
Phase 6 (infrastructure) ← whenever it becomes painful not to
```

**Sprint plan:**

| Sprint | What | Status |
|--------|------|--------|
| 1 | Phase 0 (all) + 1A + 1B | ✅ **COMPLETE** (2026-03-28) |
| 2 | 1C + 1D + 1E + 1F | ✅ **COMPLETE** (2026-03-28) |
| 3 | 2A + 2B | ✅ **COMPLETE** (2026-03-28) |
| 4 | 3A + 3B + 2E | ✅ **COMPLETE** (2026-03-28) |
| 5 | 3C + 3D | ✅ **COMPLETE** (2026-03-28) |
| 6 | 4A + 4B + 4C | ✅ **COMPLETE** (2026-03-28) |
| 7 | 2C + 2D + 4D | ✅ **COMPLETE** (2026-03-28) |
| 8 | 3E + 3F + 4E + 4F | ✅ **COMPLETE** (2026-03-29) |
| 9 | 5A + 5B + 6C | ✅ **COMPLETE** (2026-03-29) |
| 10 | 5C + 5D + 5E + 6A + 6B + 6D | ✅ **COMPLETE** (2026-03-29) |

---

## Code Conventions

**Python:**
- All new modules go in `apps/baseball-engine/src/`, scripts in `apps/baseball-engine/scripts/`
- Path setup at the top of every script:
  ```python
  APP_ROOT = Path(__file__).parent.parent
  WORKSPACE_ROOT = APP_ROOT.parent.parent
  sys.path.insert(0, str(APP_ROOT))
  ```
- File-based caching via `src/cache_manager.py`: `cache = get_cache(); cache.get(key, max_age_hours=6); cache.set(key, data)`
- New FastAPI endpoints go in `scripts/draft_server.py` under the `# ─── Season endpoints` section
- Yahoo API helper: `_yahoo_get(path)` in `draft_server.py` handles auth + token refresh

**TypeScript/React:**
- All new pages go in `apps/baseball-dashboard/app/{route}/page.tsx`
- `"use client"` directive on all interactive pages
- Dark theme: background `slate-950`, cards `slate-900/60`, borders `slate-700/60`
- UI components from `@/components/ui/` (Radix-based); icons from `lucide-react` only
- `NEXT_PUBLIC_DRAFT_API_URL` env var for season API calls, defaults to `http://localhost:8001`
- Polling pattern: `useCallback` + `setInterval` at 60s, `cache: "no-store"` on fetches
- ESLint strict: no unused variables, no unescaped entities (`'` → `&apos;`)
- No inline styles — Tailwind classes only

**Do not touch:**
- `apps/baseball-engine/config/oauth2.json` — live credentials, never commit
- `apps/baseball-dashboard/.env.local` — never overwrite
- Never push to `main` unless explicitly asked

---

## Key Moneyball Metrics Cheat Sheet

Metrics to add, ranked by how strongly they predict future performance:

| Metric | What It Measures | Why It's Predictive | Status |
|--------|-----------------|---------------------|--------|
| xwOBA | Expected offensive value from contact quality | Strips out luck and defense | 1D |
| Barrel% | Elite contact events (optimal EV + LA) | #1 predictor of future HR and SLG | ✅ already have |
| K-BB% | Pitcher dominance margin | Best simple pitcher metric, stabilizes in ~60 IP | ✅ 1A done |
| CSW% | Called strikes + whiffs per pitch | Leads ERA changes by 2–3 weeks | ✅ 1A done |
| Sprint Speed | Raw speed from Statcast | Predicts SB better than past SB totals | 1C |
| Hard Hit% Against | Quality of contact a pitcher allows | Early ERA regression indicator | ✅ already have |
| xBA − BA delta | Luck factor | 30+ point gap = screaming buy/sell signal | 1D (partially in 0E) |
| Stuff+ | Pitch quality (movement, velo, location) | Best modern pitcher evaluation metric | 2C |
| FIP | Fielding-independent pitching | Strips out defense, way more predictive than ERA | ✅ 1A done |
| wRC+ | Park/league-adjusted offensive value | The single "one number" for comparing hitters | 2A |
| Implied Run Total | Vegas oddsmakers' prediction | Encodes all factors into one number | 2B |
| Chase Rate trend | Plate discipline changes | Improving chase rate → breakout; worsening → sell | ✅ already have |

---

## New Data Sources Reference

| Source | What You Get | Access | Cost |
|--------|-------------|--------|------|
| FanGraphs | wRC+, FIP, WAR, Steamer/ZiPS ROS projections | Unofficial API or CSV scrape | Free |
| Baseball Savant Leaderboards | Statcast percentiles, Stuff+, Sprint Speed | Public CSV download | Free |
| The Odds API | Vegas lines, implied run totals | REST API | Free (500 req/mo) |
| MLB Stats API `/injuries` | Full IL + DTD list with dates | REST API | Free, no auth |
| MLB Stats API `/schedule?hydrate=officials` | Umpire assignments | REST API | Free, no auth |
| UmpireScorecards | Umpire accuracy, zone size, consistency | Public dataset | Free |
| RosterResource / CloserMonkey | Bullpen depth charts | Scrape or RSS | Free |
| MLB Stats API (MiLB) | Minor league game logs | REST API | Free, no auth |

---

## Sprint 1 Changelog (2026-03-28)

Files created, modified, or deleted — for context when picking up Sprint 2.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/src/injury_tracker.py` | New module: fetches MLB injuries API, caches 2h, provides `is_injured()` / `get_badge()` / `get_injury()` |

### Modified
| File | What Changed |
|------|-------------|
| `.gitignore` | Added `apps/baseball-engine/config/oauth2.json` |
| `apps/baseball-api/main.py` | CORS locked down; startup fetches roster from Yahoo (CSV fallback); `/api/waivers` calls `WaiverAnalyzer` with real Yahoo FAs; `/api/breakouts` runs `BreakoutDetector` on roster + FAs; added `_get_yahoo()` singleton |
| `apps/baseball-engine/scripts/draft_server.py` | CORS locked down (`ALLOWED_ORIGINS` instead of `"*"`) |
| `apps/baseball-engine/src/statcast_client.py` | Added `calculate_pitcher_fip()` — computes FIP, K-BB%, CSW% from Statcast data |
| `apps/baseball-engine/src/lineup_optimizer.py` | Imports `AdvancedAnalytics` + `InjuryTracker`; init creates both in `__init__`; `_analyze_player_matchup()` short-circuits injured players to AVOID; new `_get_advanced_adjustments()` wires umpire/xBA/batted-ball analytics; `_get_pitcher_matchup_score()` rewritten to use FIP(60%)+K-BB%(25%)+CSW%(15%) with ADP fallback |
| `apps/baseball-engine/scripts/export_dashboard_data.py` | Imports `InjuryTracker`; loads injuries after roster fetch; adds `injury` field to all lineup tier dicts; refactored tier serialization into shared `_fmt()` helper |
| `apps/baseball-dashboard/app/page.tsx` | `Player` type now includes `injury?: string \| null` |
| `apps/baseball-dashboard/components/player-table.tsx` | `Player` type updated; injury badge (red `<Badge variant="destructive">`) renders next to player name |
| `apps/baseball-dashboard/components/optimal-lineup.tsx` | `Player` type updated; injury badge renders next to player name |

### Deleted
| File | Why |
|------|-----|
| `apps/baseball-engine/scripts/api_server.py` | Legacy Flask stub with hardcoded sample data |
| `apps/baseball-engine/scripts/waiver_wire.py.backup` | Duplicate file, syntactically broken |
| `apps/baseball-dashboard/components/filter-bar.tsx` | Built but never imported anywhere |

### Git tracking removed (file still exists locally)
| File | Why |
|------|-----|
| `apps/baseball-engine/config/oauth2.json` | Contains live Yahoo OAuth credentials — now `.gitignore`d |

### Remaining post-Sprint 1 TODO
- **Rotate Yahoo consumer secret** after pushing the commit (0A follow-up)

---

## Sprint 2 Changelog (2026-03-28)

Files created, modified, or deleted — for context when picking up Sprint 3.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/src/speed_tracker.py` | New module: fetches Statcast sprint speed leaderboard via `pybaseball.statcast_sprint_speed()`, cross-references SB/CS from MLB Stats API game logs, computes `SpeedProfile` with `sb_upside_score` (0-100), classifies tiers (ELITE/FAST/AVERAGE/SLOW), identifies buy-low SB targets (elite speed + low SB totals) |
| `apps/baseball-engine/src/regression_analyzer.py` | New module: computes xBA/xSLG/xwOBA vs actual for hitters, FIP vs xERA for pitchers; classifies BUY_LOW (underperformers) and SELL_HIGH (overperformers) with confidence scoring; `scan_players()` bulk-scans roster + free agents |
| `apps/baseball-engine/data/player_handedness.json` | Static JSON of ~80 well-known MLB players with bat/pitch handedness (seed data); used as primary lookup before MLB API |
| `apps/baseball-engine/scripts/generate_handedness.py` | Script to regenerate `player_handedness.json` from MLB Stats API 40-man rosters; run monthly |
| `apps/baseball-dashboard/app/regression/page.tsx` | New dashboard page: two-table layout (Buy Low + Sell High) with hitter xStats (BA/xBA/SLG/xSLG/xwOBA) and pitcher xStats (FIP/xERA); confidence badges; auto-refreshes every 2 min from `/season/regression` |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/src/stats_fetcher.py` | `RecentStats` dataclass expanded: added `obp`, `slg`, `ops`, `bb`, `hbp`, `h`, `ab`, `r` (hitters) and `sv`, `qs`, `ip`, `p_bb`, `p_h`, `holds` (pitchers); `to_dict()` returns all new fields; `_aggregate_hitter_stats()` now computes OBP, SLG, OPS from game logs; `_aggregate_pitcher_stats()` now computes IP, SV, QS, holds |
| `apps/baseball-engine/src/lineup_optimizer.py` | Added `import json` and `from pathlib import Path`; `__init__()` loads `data/player_handedness.json` into `_handedness_static` dict; `_get_player_handedness()` and `_get_pitcher_handedness()` rewritten with 3-tier priority: static JSON → persistent cache → MLB API → default 'R' |
| `apps/baseball-engine/src/waiver_analyzer.py` | Imports `SpeedTracker`; `__init__()` loads speed tracker; `_evaluate_pickup()` applies SB upside boost for hitters with elite sprint speed; new `_get_sb_upside_boost()` method; `_generate_reason()` includes SB buy-low and elite speed signals |
| `apps/baseball-engine/src/breakout_detector.py` | Imports `SpeedTracker` (with fallback); `__init__()` initializes speed tracker; `analyze_player()` adds sprint speed boost for hitters with ELITE/FAST tier — adds `sprint_speed` to `improving_metrics` and `key_metrics` |
| `apps/baseball-engine/scripts/draft_server.py` | New `/season/regression` endpoint: scans roster + top 30 free agents via `RegressionAnalyzer.scan_players()`, returns `{buy_low: [...], sell_high: [...]}` with 1-hour cache |
| `apps/baseball-dashboard/app/page.tsx` | Added `BarChart3` icon import; added "Regression" nav button linking to `/regression`; expanded `WaiverTarget` stat window types to include `obp`, `slg`, `ops`, `bb`, `r`, `sv`, `qs`, `ip`, `holds` |
| `apps/baseball-dashboard/components/waiver-wire-table.tsx` | `WaiverTarget` type refactored to use shared `StatWindow` type with all new fields; hitter performance table adds OPS row; pitcher table adds IP and SV rows (replacing Wins row) |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/statcast_client.py` | Already had `calculate_hitter_metrics()` with xBA/xSLG/xwOBA and `calculate_pitcher_fip()` — reused by the new regression analyzer |
| `apps/baseball-engine/scripts/export_dashboard_data.py` | No changes needed — `RecentStats.to_dict()` handles new fields automatically |
| `apps/baseball-dashboard/components/player-table.tsx` | No changes needed — player table uses different data shape |
| `apps/baseball-dashboard/components/optimal-lineup.tsx` | No changes needed |

### Remaining post-Sprint 2 TODO
- **Run `python scripts/generate_handedness.py`** when MLB API is available to populate full 40-man roster handedness (currently seeded with ~80 well-known players)

---

## Sprint 3 Changelog (2026-03-28)

Files created, modified, or deleted — for context when picking up Sprint 4.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/src/projection_fetcher.py` | New module: fetches Steamer ROS projections from FanGraphs unofficial API (`/api/projections?type=steamerr`); `HitterProjection` dataclass with PA/AVG/HR/RBI/SB/OPS/wRC+/WAR + `ros_value` composite score; `PitcherProjection` dataclass with IP/ERA/WHIP/K/QS/FIP/K-BB%/WAR + `ros_value` composite score; fuzzy name matching; 24-hour cache TTL |
| `apps/baseball-engine/src/odds_fetcher.py` | New module: fetches Vegas implied run totals from The Odds API (`/v4/sports/baseball_mlb/odds/?markets=totals,h2h`); `GameOdds` dataclass with total O/U, moneylines, per-team implied runs, and `environment` classifier (high_scoring/neutral/low_scoring); requires `ODDS_API_KEY` env var (free tier: 500 req/month); 2-hour cache TTL; full MLB team abbreviation mapping |
| `apps/baseball-dashboard/app/projections/page.tsx` | New dashboard page: two-tab layout (Hitters + Pitchers) showing Steamer ROS projections for roster players and top free agents; columns include PA/AVG/HR/RBI/SB/OPS/wRC+ for hitters and IP/ERA/WHIP/K/QS/FIP/K-BB% for pitchers; source badges (Roster vs FA); ROS value score; auto-refreshes every 2 min from `/season/projections` |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/src/lineup_optimizer.py` | Imports `OddsFetcher`; `__init__()` initializes `odds_fetcher` with `load()`; default scoring weights rebalanced to include `vegas: 0.15` (matchup 0.25, park 0.15, form 0.25, platoon 0.12, breakout 0.08); new `_get_vegas_score()` method scores 0-100 based on game total (hitters boosted in >9.0 totals, pitchers boosted in <8.0 totals); `_analyze_player_matchup()` calls Vegas scoring as step 8; `LineupRecommendation` dataclass gains `vegas_total: Optional[float]` field; Vegas reasons added to player reasons list |
| `apps/baseball-engine/src/waiver_analyzer.py` | Imports `ProjectionFetcher`; `__init__()` initializes `projections` fetcher; `_evaluate_pickup()` calls new `_get_projection_boost()` — when ROS projections exist, uses projected value difference instead of raw ADP diff (scaled 5× to match ADP range); `_generate_reason()` adds ROS wRC+, ERA, and K projection signals when elite thresholds met; new `_get_projection_boost()` method compares `ros_value` between add and drop candidates |
| `apps/baseball-engine/scripts/draft_server.py` | New `/season/projections` endpoint: fetches Steamer ROS projections for roster + top 30 free agents via `ProjectionFetcher`; returns hitters and pitchers sorted by `ros_value` with 1-hour server-side cache |
| `apps/baseball-engine/scripts/export_dashboard_data.py` | `_fmt()` helper now includes `vegas_total` field from `LineupRecommendation` (passes through to `daily_lineup.json`) |
| `apps/baseball-dashboard/app/page.tsx` | `Player` type gains `vegas_total?: number \| null`; added `DollarSign` icon import; added "Projections" nav button linking to `/projections` |
| `apps/baseball-dashboard/components/player-table.tsx` | `Player` type gains `vegas_total?: number \| null`; imported `DollarSign` icon; added Vegas total chip to `parseSignals()` — green for ≥10, red for ≤7, yellow for neutral; added `vegas total` pattern to `REASON_RULES` for reason-string matching; added Vegas legend entry |
| `apps/baseball-dashboard/components/optimal-lineup.tsx` | `Player` type gains `vegas_total?: number \| null`; imported `DollarSign` icon; added Vegas chip to `parseSignals()` with same coloring logic; added `vegas total` pattern to `REASON_RULES`; added Vegas entry to signal legend |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/regression_analyzer.py` | Projections will be wired in as a Phase 3 enhancement — current regression logic uses xStats which remain the primary signal |
| `apps/baseball-engine/src/statcast_client.py` | No changes needed — existing xBA/xSLG/FIP methods are reused as-is |
| `apps/baseball-engine/src/breakout_detector.py` | No changes needed — breakout signals are independent of projections/odds |
| `apps/baseball-dashboard/components/waiver-wire-table.tsx` | No changes needed — waiver table data shape unchanged |

### Remaining post-Sprint 3 TODO
- **Set `ODDS_API_KEY` environment variable** to enable Vegas lines (get free key at https://the-odds-api.com)

---

## Sprint 4 Changelog (2026-03-28)

Files created, modified, or deleted — for context when picking up Sprint 5.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/data/bullpen_depth.json` | Curated bullpen depth charts for all 30 MLB teams: closer, primary setup man, secondary setup, committee flag; update weekly during season |
| `apps/baseball-engine/src/bullpen_tracker.py` | New module: loads `bullpen_depth.json`, provides `get_closer()`, `get_primary_setup()`, `is_committee()`, `find_team_for_closer()`, `all_closers()` |
| `apps/baseball-engine/src/bullpen_fatigue.py` | New module: fetches reliever game logs from MLB Stats API, computes `RelieverFatigue` dataclass with `fatigue_score` (0-100) based on consecutive days pitched, pitch count in last 3 days, IP in last 7 days, appearances; `fatigue_level` classification (FRESH/LOW/MODERATE/HIGH); `VultureAlert` when closer is fatigued with setup man as pickup candidate; `get_all_closer_fatigue()` scans all 30 closers; `get_vulture_alerts()` returns sorted pickup opportunities |
| `apps/baseball-engine/src/streamer_planner.py` | New module: fetches next week's MLB schedule via `get_next_week_schedule()`, identifies all SPs with 2+ scheduled starts, scores matchups using opponent team K% + park factors + pitcher FIP; `TwoStartStreamer` dataclass with `composite_score`; weighted scoring: K% matchup (65%) + FIP bonus (30%); 6-hour cache; `TEAM_K_PCT` reference data for all 30 teams |
| `apps/baseball-dashboard/app/streamers/page.tsx` | New dashboard page: combined Streamers & Bullpen view; top section shows vulture save alerts (closer name, team, fatigue level/score, consecutive days, pitches last 3d, vulture candidate); expandable full closer fatigue table sorted by fatigue score; bottom section shows two-start pitcher streamers (pitcher, team, composite score, FIP, start 1 & 2 with date/opponent/K%); auto-refreshes every 2 min from `/season/streamers` + `/season/bullpen-alerts` |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/src/daily_matchups.py` | Added `get_next_week_schedule()` — fetches full MLB schedule for next Monday–Sunday (7 days, returns flat list of `Game` objects); added `get_week_range()` — returns start/end dates of next week as ISO strings |
| `apps/baseball-engine/scripts/draft_server.py` | New `/season/bullpen-alerts` endpoint: instantiates `BullpenTracker` + `BullpenFatigueMonitor`, returns `alerts` (vulture opportunities sorted by fatigue score) and `closer_fatigue` (all 30 closers with full fatigue metrics); 30-minute server-side cache. New `/season/streamers` endpoint: instantiates `StreamerPlanner`, returns `streamers` (two-start SPs with composite scores + matchup details) and `week_dates`; 1-hour server-side cache |
| `apps/baseball-dashboard/app/page.tsx` | Imports `Flame` and `Radio` icons from lucide-react; added `BullpenAlert` type; added `bullpenAlerts` state + `fetchBullpenAlerts()` polling (60s interval alongside lineup focus); added red bullpen alert widget below lineup focus banner showing up to 4 fatigued closers with fatigue level badge, consecutive days, pitch count, and vulture candidate highlighted in green; added "Streamers" nav button linking to `/streamers` |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/lineup_optimizer.py` | Bullpen data is surfaced through its own endpoint, not mixed into lineup scoring |
| `apps/baseball-engine/src/waiver_analyzer.py` | Vulture recommendations are a separate alert system, not waiver scoring changes |
| `apps/baseball-engine/scripts/export_dashboard_data.py` | Bullpen/streamer data served live from draft_server.py, not static JSON |
| `apps/baseball-dashboard/components/player-table.tsx` | No changes needed — bullpen alerts render in page.tsx directly |
| `apps/baseball-dashboard/components/optimal-lineup.tsx` | No changes needed |

### Remaining post-Sprint 4 TODO
- **Update `data/bullpen_depth.json` weekly** as closer roles change during the season

---

## Sprint 5 Changelog (2026-03-28)

Files created, modified, or deleted — for context when picking up Sprint 6.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/src/trade_analyzer.py` | New module: category-impact trade analyzer. `TradeAnalyzer.analyze(give, get)` simulates a roster swap using Steamer ROS projections; converts projections to weekly rate contributions for all 12 H2H scoring categories; computes per-category delta, before/after league rank, and verdict (gain/loss/neutral); aggregates to `cats_gained`, `cats_lost`, `net_rank_change`, `win_probability_delta` (% weekly win change), and a human-readable summary. `search_players(query)` fuzzy-searches projection database for the trade input UI. Supports both hitter and pitcher trades with rate-stat-aware logic for OPS/ERA/WHIP. |
| `apps/baseball-engine/src/weekly_planner.py` | New module: full-week streaming planner. `WeeklyPlanner.build_plan()` fetches next week's MLB schedule, scores every SP matchup by opponent K% (30%), wRC+ (25%), park factor (20%), and Vegas game total (25%); returns `daily_streams` (top 8 options per day), `optimal_streams` (single best per day), and `team_game_counts` (all 30 teams sorted by games played — for batting streamer decisions). `TEAM_WRC_PLUS` reference data for all 30 teams. 4-hour cache. Integrates with `OddsFetcher` when `ODDS_API_KEY` is set. |
| `apps/baseball-dashboard/app/trade/page.tsx` | New dashboard page: trade analyzer with live player search (debounced autocomplete against `/season/trade-search`), "You Give" / "You Get" input panels, "Analyze Trade" button; results show ROS value comparison, category-by-category impact table (label, group badge, verdict icon, give/get values, delta, before→after rank badges with color coding), summary bar with win probability delta. |
| `apps/baseball-dashboard/app/planner/page.tsx` | New dashboard page: three-tab weekly planner. **Optimal Plan** tab: best stream per day in a clean table (day, pitcher, matchup, score, reason). **Day-by-Day** tab: per-day sections with top 8 SP options showing K%, wRC+, park factor, Vegas total, and composite score; best option highlighted green. **Team Games** tab: all 30 teams sorted by game count with opponent list; 7-game teams get green badges, 5-game get slate. Auto-refreshes every 2 min. |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/scripts/draft_server.py` | New `/season/trade-analyzer` endpoint: takes `give` and `get` query params, instantiates `TradeAnalyzer`, fetches current league standings for rank simulation, returns full `TradeResult` with per-category impact and win probability delta. New `/season/trade-search` endpoint: takes `q` query param, returns fuzzy player name matches from projection database. New `/season/weekly-plan` endpoint: instantiates `WeeklyPlanner`, returns `daily_streams`, `optimal_streams`, and `team_game_counts`; 1-hour server-side cache. |
| `apps/baseball-dashboard/app/page.tsx` | Imports `ArrowRightLeft` and `CalendarRange` icons from lucide-react; added "Trade" nav button linking to `/trade`; added "Planner" nav button linking to `/planner` |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/projection_fetcher.py` | Existing `ProjectionFetcher` and `HitterProjection`/`PitcherProjection` dataclasses reused as-is by trade analyzer |
| `apps/baseball-engine/src/odds_fetcher.py` | Existing `OddsFetcher` reused by weekly planner when API key is set |
| `apps/baseball-engine/src/daily_matchups.py` | `get_next_week_schedule()` and `get_week_range()` added in Sprint 4 are reused by weekly planner |
| `apps/baseball-engine/src/streamer_planner.py` | Two-start streamer planner is independent; weekly planner is a complementary daily-granularity tool |
| `apps/baseball-dashboard/app/streamers/page.tsx` | No changes needed — streamers page remains focused on two-start SPs and bullpen alerts |

### Remaining post-Sprint 5 TODO
- ✅ **Sprint 6:** 4A (Charts library) + 4B (TanStack Query) + 4C (Player profile page) — DONE

---

## Sprint 6 Changelog (2026-03-28)

Files created, modified, or deleted — for context when picking up Sprint 7.

### Created
| File | What |
|------|------|
| `apps/baseball-dashboard/app/providers.tsx` | New: TanStack Query `QueryClientProvider` wrapper with `QueryClient` configured for 60s stale time, 120s refetch interval, stale-while-revalidate, and retry(1). Wraps all pages via `layout.tsx`. |
| `apps/baseball-dashboard/app/player/[name]/page.tsx` | New dashboard page: player profile with Recharts `RadarChart` for hitter (Power/Speed/Contact/OPS/wRC+/Volume) and pitcher (K/ERA/WHIP/FIP/K-BB%/Volume) projections; xStats actual-vs-expected bar chart; rolling stats bar chart (7d/14d/30d); recent performance table; regression analysis with direction badge and improving metrics; injury status banner; ROS projection stat grid. Fetches from `/season/player-profile`. |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-dashboard/package.json` | Added `recharts` ^3.8.1 and `@tanstack/react-query` ^5.95.2 as dependencies |
| `apps/baseball-dashboard/app/layout.tsx` | Imports and wraps children with `<Providers>` from `app/providers.tsx` (TanStack QueryClientProvider) |
| `apps/baseball-dashboard/app/regression/page.tsx` | Refactored from `useState`+`useEffect`+`setInterval` to `useQuery` hook; added Recharts `ScatterChart` showing actual BA vs xBA with buy-low (green) and sell-high (red) scatter points and a diagonal reference line; player names now link to `/player/[name]` via `Link` |
| `apps/baseball-dashboard/app/trade/page.tsx` | Refactored trade analysis from `useState`+`useCallback` to `useMutation` hook; added Recharts `BarChart` showing per-category rank change (green=gain, red=loss); all existing functionality preserved |
| `apps/baseball-dashboard/app/projections/page.tsx` | Refactored from `useState`+`useEffect`+`setInterval` to `useQuery` hook; player names now link to `/player/[name]` via `Link` |
| `apps/baseball-dashboard/app/planner/page.tsx` | Refactored from `useState`+`useEffect`+`setInterval` to `useQuery` hook |
| `apps/baseball-dashboard/app/streamers/page.tsx` | Refactored from `useState`+`useEffect`+`setInterval` to two parallel `useQuery` hooks (one for streamers, one for bullpen alerts) |
| `apps/baseball-dashboard/components/player-table.tsx` | Imports `Link` from next/link; player name cell wrapped with `<Link href="/player/[name]">` for navigation to player profile; removed unused `useToast` import |
| `apps/baseball-dashboard/components/optimal-lineup.tsx` | Imports `Link` from next/link; player name cell in `PlayerRow` wrapped with `<Link href="/player/[name]">` with `stopPropagation` to preserve row click behavior |
| `apps/baseball-dashboard/components/waiver-wire-table.tsx` | Imports `Link` from next/link; player name in waiver card header wrapped with `<Link href="/player/[name]">` |
| `apps/baseball-engine/scripts/draft_server.py` | New `/season/player-profile` endpoint: combines ROS projections (via `ProjectionFetcher`), regression analysis (via `RegressionAnalyzer`), recent stats (via `StatsFetcher` at 7/14/30d windows), and injury status (via `InjuryTracker`) into a single player profile response; handles both hitter and pitcher profiles |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-dashboard/app/page.tsx` | Main dashboard still uses `useState`+`useEffect` for initial JSON load (static data) and `useCallback`+`setInterval` for live polling — these are appropriate for the mixed static/live data pattern on the home page |
| `apps/baseball-engine/src/projection_fetcher.py` | Existing `ProjectionFetcher` reused as-is by player profile endpoint |
| `apps/baseball-engine/src/regression_analyzer.py` | Existing `RegressionAnalyzer` reused as-is by player profile endpoint |
| `apps/baseball-engine/src/stats_fetcher.py` | Existing `StatsFetcher` reused as-is by player profile endpoint |
| `apps/baseball-engine/src/injury_tracker.py` | Existing `InjuryTracker` reused as-is by player profile endpoint |

### Remaining post-Sprint 6 TODO
- ✅ **Sprint 7:** 2C (Savant leaderboards) + 2D (umpire data) + 4D (regression page) — DONE

---

## Sprint 7 Changelog (2026-03-28)

Files created, modified, or deleted — for context when picking up Sprint 8.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/src/savant_leaderboards.py` | New module: fetches pre-aggregated Statcast leaderboard CSVs from baseballsavant.mlb.com. `HitterPercentiles` dataclass with percentile ranks (0-99) for exit velocity, hard hit%, barrel%, xBA, xSLG, xwOBA, sprint speed, chase rate, whiff%, K%, BB%. `PitcherPercentiles` dataclass with percentile ranks for exit velo against, hard hit% against, barrel% against, xBA/xSLG/xwOBA against, xERA, fastball velo, extension, whiff%, K%, BB%, and Stuff+ score. Percentiles computed relative to all qualified players in that role. 24-hour cache TTL. |
| `apps/baseball-engine/data/umpire_tendencies.json` | Curated JSON file with 27 MLB home plate umpire tendencies: zone_size (96–105), accuracy (82–97%), favor (hitters/neutral/pitchers), consistency, and run_impact (+/- runs per game). Sourced from UmpireScorecards.com. Update weekly during season. |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/src/advanced_analytics.py` | Complete rewrite. Replaced hardcoded 10-umpire `UMPIRE_FACTORS` dict with live data from MLB Stats API (`/schedule?hydrate=officials`) cross-referenced with `data/umpire_tendencies.json`. New `_fetch_todays_umpires()` fetches today's HP umpire for every game, 6-hour cache. New `UmpireAssignment` dataclass. `get_umpire_adjustment()` now accepts `team_abbr` for auto-lookup. New `get_umpire_for_team()` and `get_all_todays_umpires()` methods. Existing methods (`analyze_contact_quality_trends`, `calculate_expected_stats_boost`, `analyze_batted_ball_profile`, `get_rest_fatigue_adjustment`) preserved with cleaned-up signatures. |
| `apps/baseball-engine/src/breakout_detector.py` | Imports `SavantLeaderboards` (with fallback). `__init__()` initializes savant leaderboards. `analyze_player()` adds Savant percentile boost — when elite metrics (barrel ≥80th, hard_hit ≥80th, xwOBA ≥80th for hitters; Stuff+ ≥110, whiff ≥80th for pitchers), adds confidence boost and appends `savant_` prefixed entries to `improving_metrics`. |
| `apps/baseball-engine/scripts/draft_server.py` | `/season/player-profile` endpoint now includes `savant_percentiles` field — fetches `SavantLeaderboards`, calls `get_percentiles()`, returns full percentile dict for the player profile page's Statcast card. |
| `apps/baseball-dashboard/app/player/[name]/page.tsx` | `PlayerProfile` type gains `savant_percentiles` field. New `SavantPercentileCard` component: horizontal bar visualization for each Statcast metric (color-coded: blue→sky→amber→orange→red by percentile tier), Stuff+ badge for pitchers. Renders between regression analysis and recent stats sections. |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/lineup_optimizer.py` | Already imports `AdvancedAnalytics` — the rewritten module is backwards-compatible, existing `get_umpire_adjustment()` calls work unchanged |
| `apps/baseball-engine/src/statcast_client.py` | Savant leaderboards module operates independently — uses CSV exports rather than raw pitch data |
| `apps/baseball-dashboard/app/regression/page.tsx` | Phase 4D already complete: page created in Sprint 2 (1D), scatter plot added in Sprint 6 (4A). No further changes needed. |

### Remaining post-Sprint 7 TODO
- ✅ **Sprint 8:** 3E (Prospect call-up watchlist) + 3F (Enhanced category gap analysis) + 4E (Mobile responsive) + 4F (Toast notifications) — DONE
- **Update `data/umpire_tendencies.json` weekly** as new umpire scorecard data is published

---

## Sprint 8 Changelog (2026-03-29)

Files created, modified, or deleted — for context when picking up Sprint 9.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/data/prospect_watchlist.json` | Curated JSON of top 50 fantasy-relevant prospects with MLB player IDs, team, position, MiLB level, top-100 rank, and ETA year. Covers top prospects from all 30 teams. Update periodically as rankings change. |
| `apps/baseball-engine/src/prospect_tracker.py` | New module: `ProspectTracker` fetches MiLB game logs from MLB Stats API for all watchlist prospects (14-day window, tries both MiLB and MLB game types). `ProspectProfile` dataclass with 14-day hitting stats (AVG/OPS/HR/RBI/SB) and pitching stats (ERA/WHIP/K/IP). Detects hot streaks (hitters: 14d OPS ≥ 1.000; pitchers: 14d ERA ≤ 2.50). Checks 40-man roster status. Computes `callup_score` (0-100) based on top-100 rank, level, ETA, performance, and roster status. Generates alert reasons for hot streaks, power surges, speed bursts, and call-up eligibility. 6-hour cache on game logs, 12-hour cache on roster status. |
| `apps/baseball-dashboard/app/prospects/page.tsx` | New dashboard page: two-tab prospect watchlist. **Hot Prospects** tab: card grid layout with stat grids (AVG/OPS/HR/SB for hitters, ERA/WHIP/K/IP for pitchers), color-coded alert reasons, call-up score badges. **Full Watchlist** tab: sortable table of all 50 prospects with level badges, 14-day stats, 40-man status, and call-up scores. Auto-refreshes via TanStack Query. |
| `apps/baseball-dashboard/components/mobile-nav.tsx` | New component: fixed bottom navigation bar for mobile viewports (`md:hidden`). 5 primary nav items (Home, Matchup, Trade, Streamers, Prospects) with active state highlighting. Uses `usePathname()` for route matching. Touch-optimized 56px height with `touch-manipulation` CSS. `safe-area-bottom` for notched devices. |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/scripts/draft_server.py` | New `/season/prospects` endpoint: instantiates `ProspectTracker`, calls `scan_all()`, returns full prospect profiles + hot prospect subset; 1-hour server-side cache. New `/season/matchup-enhanced` endpoint: wraps existing `/season/matchup` with enhanced analysis — computes `days_elapsed`/`days_left` from matchup week dates, calculates `projected_my`/`projected_opp` end-of-week totals based on daily pace, `gap_to_flip` for each category showing exact amount needed, and `recommendation` with specific roster move suggestions for each swing category (e.g. "Need 3 more HR — start high-upside players", "Stream a SP with high K rate"). |
| `apps/baseball-dashboard/app/matchup/page.tsx` | Complete rewrite to use `/season/matchup-enhanced` endpoint. `EnhancedCategory` type adds `projected_my`, `projected_opp`, `gap_to_flip`, `daily_pace_my`, `recommendation`. `CategoryRow` now expands swing categories with a sub-row showing projected end-of-week values, gap-to-flip metric, and a lightbulb-icon recommendation. New "Recommended Moves" panel appears above categories when actionable suggestions exist. Added `Target` and `Lightbulb` icon imports. Matchup header card now shows day counter (Day X/7 · Y left). Opponent scouting grid uses responsive `sm:grid-cols-2`. |
| `apps/baseball-dashboard/app/layout.tsx` | Imports `MobileNav` component; renders `<MobileNav />` inside `ThemeProvider`. Adds `pb-14 md:pb-0` to `<body>` for bottom nav spacing. Exports `viewport` with `width: "device-width"`, `maximumScale: 1`, `viewportFit: "cover"` for mobile viewport meta. Imports `Viewport` type from `next`. |
| `apps/baseball-dashboard/app/page.tsx` | Imports `Sparkles` icon; added "Prospects" nav button linking to `/prospects`. Desktop nav bar wrapped in `hidden md:flex` — hidden on mobile where bottom nav takes over. New mobile-only header section with compact timestamp and theme toggle (`flex md:hidden`). Title reduced to `text-2xl sm:text-3xl` for mobile. Added `seenBreakouts` and `seenBullpen` state sets to track previously-seen alerts. `fetchBullpenAlerts` now fires toast notifications for new vulture save opportunities. New `useEffect` fires toast for STRONG breakout signals on first detection. |
| `apps/baseball-dashboard/components/ui/use-toast.ts` | `TOAST_LIMIT` increased from 1 to 3 (allows stacking multiple alert toasts). `TOAST_REMOVE_DELAY` reduced from 1000000ms to 8000ms (auto-dismiss after 8 seconds). |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/lineup_optimizer.py` | Prospect data and enhanced matchup are independent endpoints — no changes to lineup scoring |
| `apps/baseball-engine/src/daily_matchups.py` | Schedule fetching unchanged — enhanced matchup uses existing Yahoo matchup data |
| `apps/baseball-engine/src/waiver_analyzer.py` | Waiver scoring independent of prospect tracking |
| `apps/baseball-dashboard/components/player-table.tsx` | Player table unchanged — prospect data rendered on its own page |
| `apps/baseball-dashboard/components/optimal-lineup.tsx` | No changes needed |
| `apps/baseball-dashboard/app/regression/page.tsx` | No changes needed |
| `apps/baseball-dashboard/app/providers.tsx` | TanStack Query config unchanged — prospect page uses default query settings |

### Remaining post-Sprint 8 TODO
- ✅ **Sprint 9:** 5A (Pitch mix evolution) + 5B (Catcher framing) + 6C (Consolidated API) — DONE
- **Update `data/prospect_watchlist.json` periodically** as prospect rankings change during the season

---

## Sprint 9 Changelog (2026-03-29)

Files created, modified, or deleted — for context when picking up Sprint 10.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/src/pitch_mix_tracker.py` | New module: `PitchMixTracker` compares recent (14d) vs baseline (60d) pitch-level Statcast data to detect arsenal changes. `PitchTypeProfile` dataclass with per-pitch usage%, avg velo, avg spin, whiff%. Detects 5 change types: `new_pitch` (pitch type appears at ≥5% usage), `usage_increase`/`usage_decrease` (≥10% shift), `velo_gain` (fastball +2 mph), `rpm_gain` (breaking ball +200 RPM). `PitchMixEvolution` dataclass aggregates all changes with a `breakout_score` (0-100) weighted by change type and impact polarity. `scan_pitchers()` bulk-scans a pitcher list, returns sorted by breakout_score. 12-hour cache. |
| `apps/baseball-engine/src/catcher_framing.py` | New module: `CatcherFraming` fetches catcher framing leaderboard from Baseball Savant CSV export (falls back to curated top/bottom catchers). `FramingProfile` dataclass with `runs_extra_strikes`, `strike_rate`, `shadow_zone_called_strike_pct`, `framing_tier` (ELITE/GOOD/AVERAGE/POOR/LIABILITY). `get_primary_catcher(team)` returns highest-games catcher. `get_my_pitcher_boost(team)` returns ±3-5 point lineup confidence adjustment for pitchers based on their catcher's framing tier. 24-hour cache. |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/src/breakout_detector.py` | Imports `PitchMixTracker` (with fallback). `__init__()` initializes pitch mix tracker. `analyze_player()` for pitchers now calls `pitch_mix.analyze_pitcher()` — when positive arsenal changes detected (new pitch, velo gain, RPM gain), adds confidence boost (up to 2.0 points) and appends `pitch_mix:` prefixed entries to `improving_metrics` with change descriptions. |
| `apps/baseball-engine/src/lineup_optimizer.py` | Imports `CatcherFraming`. `__init__()` initializes `catcher_framing` with `load()`. `_analyze_player_matchup()` adds step 9: catcher framing adjustment — for pitchers, calls `get_my_pitcher_boost(player.team)` and applies ±3-5 confidence score adjustment; adds framing reason to player reasons list. |
| `apps/baseball-engine/scripts/draft_server.py` | **Consolidated API server (6C):** All endpoints from `apps/baseball-api/main.py` are now served by this single FastAPI app. Added `/api/lineup`, `/api/keepers`, `/api/waivers`, `/api/breakouts`, `/api/set-lineup` endpoints (migrated from port 8000 → port 8001). Lazy `_ensure_api_roster()` loads Yahoo roster once for `/api/*` endpoints. New `/season/pitch-mix` endpoint: analyzes a single pitcher by name or scans all roster pitchers for arsenal evolution; returns change list with descriptions and breakout scores. New `/season/catcher-framing` endpoint: returns full framing leaderboard or team-filtered catcher profiles with tier classifications. |
| `apps/baseball-dashboard/app/page.tsx` | Removed `API_BASE_URL` constant (previously pointed at port 8000). All API calls now use `API_BASE` (alias for `DRAFT_API_BASE`, port 8001). The `USE_API` mode fetches `/api/lineup`, `/api/waivers`, `/api/breakouts`, `/api/keepers` from the single consolidated server. |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/statcast_client.py` | Existing pitch-level data methods (`get_pitcher_stats`, `calculate_pitcher_metrics`) reused by pitch mix tracker — no changes needed |
| `apps/baseball-engine/src/advanced_analytics.py` | Umpire assignments and analytics unchanged — catcher framing is a separate module |
| `apps/baseball-engine/scripts/export_dashboard_data.py` | Static JSON export unchanged — new features are live API endpoints |
| `apps/baseball-dashboard/components/player-table.tsx` | No changes needed — pitch mix and framing data are served through API endpoints, not the player table |
| `apps/baseball-dashboard/components/optimal-lineup.tsx` | No changes needed — already uses `apiBase` prop passed from page.tsx |
| `apps/baseball-dashboard/components/mobile-nav.tsx` | No changes needed — no new pages added this sprint |
| `apps/baseball-dashboard/app/layout.tsx` | No changes needed |
| `apps/baseball-dashboard/app/providers.tsx` | TanStack Query config unchanged |

### Deprecated (still exists but superseded)
| File | Why |
|------|-----|
| `apps/baseball-api/main.py` | All endpoints migrated to `draft_server.py`. This file can be removed in a future cleanup. Port 8000 server is no longer needed — run only `draft_server.py` on port 8001. |

### Remaining post-Sprint 9 TODO
- ✅ **Sprint 10:** 5C + 5D + 5E + 6A + 6B + 6D — ALL DONE
- **Remove `apps/baseball-api/main.py`** after confirming all consumers use port 8001
- **Update `NEXT_PUBLIC_API_URL` references** in `.env.example` and README to point at port 8001

---

## Sprint 10 Changelog (2026-03-29)

Files created, modified, or deleted — the final sprint. All 6 phases are now complete.

### Created
| File | What |
|------|------|
| `apps/baseball-engine/src/database.py` | New module: SQLite database layer replacing JSON + shelve. Tables: `player_stats` (daily stat snapshots for rolling charts), `lineup_predictions` (prediction logs with actual results for accuracy tracking), `breakout_predictions` (signal logs with outcome tracking), `waiver_transactions` (add/drop history), `cache` (key-value with TTL). Provides `get_full_accuracy_report()` aggregating all prediction accuracy data. WAL mode for concurrent reads. Auto-initializes on import. |
| `apps/baseball-engine/src/llm_scouting.py` | New module: `LLMScoutingReporter` generates natural language reports via Claude (Anthropic) or GPT (OpenAI). `opponent_scouting()` generates weekly matchup narratives with category-by-category analysis. `trade_evaluation()` generates trade pros/cons in prose. `breakout_deep_dive()` generates mechanical analysis of a breakout candidate. `weekly_newsletter()` generates comprehensive 4-paragraph newsletter covering matchup, waivers, bullpen alerts. Gated behind `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` env vars — returns graceful "not configured" response when absent. |
| `apps/baseball-dashboard/app/accuracy/page.tsx` | New dashboard page: prediction accuracy tracker with Recharts bar charts. Summary cards show lineup accuracy %, breakout accuracy %, waiver move count, total predictions. Lineup accuracy chart breaks down by tier (MUST_START → AVOID) with color-coded bars. Breakout accuracy chart breaks down by signal type (STRONG/EMERGING/WATCH). Recent breakout predictions table with date, player, signal, confidence, and outcome (Hit/Miss/Pending). Empty state when no data yet (pre-season). Auto-refreshes via TanStack Query. |
| `packages/types/package.json` | New package: `@fantasy/types` — shared TypeScript types and Zod runtime validation schemas. |
| `packages/types/tsconfig.json` | TypeScript config for the types package. |
| `packages/types/src/index.ts` | Barrel export for all type modules. |
| `packages/types/src/player.ts` | Zod schemas + TS types: `PlayerSchema`, `NotPlayingPlayerSchema`, `PlayerProfileSchema` — matches Python `Player`, `LineupRecommendation`, and player profile endpoint shapes. |
| `packages/types/src/lineup.ts` | Zod schemas + TS types: `DailyLineupSchema`, `SwingCategorySchema`, `LineupFocusSchema` — matches lineup endpoint shapes. |
| `packages/types/src/matchup.ts` | Zod schemas + TS types: `MatchupCategorySchema`, `MatchupSchema`, `BullpenAlertSchema` — matches matchup and bullpen alert endpoint shapes. |
| `packages/types/src/breakout.ts` | Zod schemas + TS types: `BreakoutAlertSchema`, `PitchMixChangeSchema`, `PitchMixEvolutionSchema`, `RegressionCandidateSchema` — matches breakout/regression endpoint shapes. |
| `packages/types/src/waiver.ts` | Zod schemas + TS types: `WaiverTargetSchema` with nested `StatWindowSchema` — matches waiver wire endpoint shape. |
| `packages/types/src/projections.ts` | Zod schemas + TS types: `HitterProjectionSchema`, `PitcherProjectionSchema`, `TradeCategoryImpactSchema`, `TradeResultSchema` — matches projection and trade endpoint shapes. |
| `packages/types/src/accuracy.ts` | Zod schemas + TS types: `AccuracyReportSchema`, `LineupAccuracySchema`, `BreakoutAccuracySchema`, `BreakoutPredictionRecordSchema` — matches accuracy endpoint shape. |

### Modified
| File | What Changed |
|------|-------------|
| `apps/baseball-engine/scripts/draft_server.py` | New `/season/accuracy` endpoint: returns combined prediction accuracy report from SQLite database (lineup by tier, breakout by signal, recent predictions, waiver count). New `/season/scouting-report` endpoint: generates LLM-powered opponent scouting narrative or weekly newsletter (gated behind API key). New `/season/trade-scouting` endpoint: generates LLM-powered trade evaluation prose. New `/season/auto-lineup` POST endpoint: runs optimizer and optionally pushes to Yahoo with Slack notification; supports `dry_run=true` for preview. New `_init_scheduler()` function: initializes APScheduler `BackgroundScheduler` with 5 recurring jobs — refresh injuries (1h), refresh odds (2h), refresh projections (daily 6am ET), clear expired cache (daily 4am ET), auto-set lineup (daily 10am ET, gated by `AUTO_LINEUP=true` env var). `--no-scheduler` CLI flag to disable. Shutdown hook to stop scheduler gracefully. |
| `apps/baseball-dashboard/app/page.tsx` | Imports `Target` icon from lucide-react. Added "Accuracy" nav button linking to `/accuracy` in the desktop nav bar. |

### Not modified (no changes needed)
| File | Why |
|------|-----|
| `apps/baseball-engine/src/accuracy_tracker.py` | Existing JSONL-based tracker preserved — SQLite database is additive, not a replacement (both can coexist during migration) |
| `apps/baseball-engine/src/breakout_tracker.py` | Existing JSON-based tracker preserved — database module provides parallel storage |
| `apps/baseball-engine/src/cache_manager.py` | Existing shelve-based cache preserved — SQLite cache is available as an alternative; can be migrated gradually |
| `apps/baseball-engine/src/ai_advisor.py` | Existing keeper-focused AI advisor unchanged — `llm_scouting.py` extends LLM usage to season-long scouting without modifying the original |
| `apps/baseball-dashboard/components/mobile-nav.tsx` | No changes needed — accuracy page is accessible via desktop nav and direct URL |
| `apps/baseball-dashboard/app/layout.tsx` | No changes needed |
| `apps/baseball-dashboard/app/providers.tsx` | TanStack Query config unchanged |

### New environment variables (all optional)
| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Enable LLM scouting reports via Claude |
| `OPENAI_API_KEY` | Enable LLM scouting reports via GPT (fallback) |
| `AUTO_LINEUP` | Set to `true` to enable automated lineup pushing at 10am ET |
| `SLACK_WEBHOOK_URL` | Send auto-lineup confirmations to Slack |

### New dependencies (install manually)
| Package | Where | Purpose |
|---------|-------|---------|
| `apscheduler` | `pip install apscheduler` | Background job scheduler (6B) |
| `zod` | `packages/types/package.json` | Runtime validation for TypeScript types (6D) |

### Remaining post-Sprint 10 TODO

See **Post-Build Audit** section at the top of this file for the full prioritized list.
Key items: install `apscheduler`, wire Zod types into dashboard, delete deprecated
`baseball-api/main.py`, migrate shelve→SQLite cache, fix duplicate mobile nav entry.
