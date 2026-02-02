# Fantasy Baseball Assistant - Product Roadmap

## 🎯 Vision

Transform from a keeper-only tool into a **year-round competitive advantage platform** that helps you dominate your fantasy baseball league through data-driven insights, automation, and advanced analytics.

---

## ✅ **Phase 0: Foundation (COMPLETED)**

### Core Infrastructure
- [x] Yahoo Fantasy API integration with OAuth 2.0
- [x] Automated ADP data fetching from FantasyPros
- [x] Keeper analysis engine with complex league rules
- [x] Draft history integration
- [x] Basic waiver wire assistant (MVP)

**Status:** All core infrastructure in place and working.

---

## 🚀 **Phase 1: In-Season Essentials** (2-4 weeks)

**Goal:** Provide immediate value during the season with must-have tools.

### 1.1 Waiver Wire Assistant Enhancement ⭐ **HIGH PRIORITY**
**Status:** MVP complete, needs polish  
**Effort:** 1-2 days  
**Value:** 🔥🔥🔥 (Win leagues here)

**Features:**
- [x] Basic pickup/drop recommendations
- [ ] Position-specific filtering (need a 2B? Show only 2B options)
- [ ] Recent performance trends (hot/cold streaks - last 7/14/30 days)
- [ ] Ownership % in similar leagues
- [ ] Upcoming schedule strength (next 7 days)
- [ ] Breakout alerts (statcast-based)
- [ ] Weekly waiver rankings
- [ ] Comparison against league rosters (who else might want this player?)

**Technical:**
```bash
# Enhanced command options
npm run waivers                    # Full analysis
npm run waivers --position 2B      # Position-specific
npm run waivers --hot-only         # Only hot players
npm run waivers --week-ahead       # Consider next week's schedule
```

**Data Sources:**
- Yahoo API (ownership %)
- MLB Stats API (recent stats)
- FantasyPros (ADP, rankings)
- Statcast (advanced metrics)

---

### 1.2 Trade Analyzer 🤝 **HIGH PRIORITY**
**Status:** Not started  
**Effort:** 3-4 days  
**Value:** 🔥🔥 (Avoid bad deals, find steals)

**Features:**
- Value comparison (ADP-based)
- Positional need analysis
- Keeper value impact (multi-year view)
- ROS (Rest of Season) projections
- League context (standings, playoff race)
- Trade fairness score
- Alternative trade suggestions
- Historical value tracking

**Usage:**
```bash
# Single trade evaluation
npm run trade:analyze "Zach Neto" "Dylan Crews, Kyle Manzardo"

# Find trade partners
npm run trade:find-partners "Mookie Betts"

# Scan for buy-low candidates
npm run trade:buy-low
```

**Output Example:**
```
🔄 TRADE ANALYSIS
══════════════════════════════════════
You Give:
  - Zach Neto (SS) - ADP 36.0
  - Value: 96 points

You Get:
  - Dylan Crews (OF) - ADP 202.4
  - Kyle Manzardo (1B) - ADP 266.0
  - Combined Value: 44 points

❌ UNFAVORABLE (-52 points)

📊 Analysis:
  - You're giving up a top-40 player for two late-rounders
  - Neto has SS eligibility (scarce position)
  - Crews has upside but unproven
  - Manzardo is roster filler

💡 Counter-offer: Ask for a player with ADP < 150
```

---

### 1.3 Start/Sit AI 📅 **MEDIUM PRIORITY**
**Status:** Not started  
**Effort:** 2-3 days  
**Value:** 🔥 (Daily edge)

**Features:**
- Daily lineup optimizer
- Matchup quality (RHP vs LHP splits)
- Ballpark factors (Coors, Camden, etc.)
- Weather conditions (wind, rain delays)
- Injury probability monitoring
- Umpire tendencies (strike zone impact)
- Fatigue tracking (back-to-back games)

**Usage:**
```bash
# Daily recommendations
npm run lineup:optimize

# Specific position
npm run lineup:optimize --position OF

# View today's matchups
npm run matchups:today
```

---

### 1.4 Real-Time Dashboard 📊 **MEDIUM PRIORITY**
**Status:** Not started  
**Effort:** 4-5 days  
**Value:** 🔥 (Situational awareness)

**Features:**
- Current standings with projected finish
- Weekly matchup preview
- Hot/cold player streaks
- Roster health (IL, DTD, day-off tracking)
- Category tracker (winning/losing categories)
- Playoff probability calculator
- Schedule difficulty (ROS)

**Tech Stack:**
- React (for web UI)
- TailwindCSS (styling)
- Recharts (data viz)
- WebSockets (live updates)

---

## 🎯 **Phase 2: Competitive Advantage** (1-2 months)

**Goal:** Features that most fantasy players don't have access to.

### 2.1 Breakout Detector 🔥 **GAME CHANGER**
**Status:** Not started  
**Effort:** 1-2 weeks  
**Value:** 🔥🔥🔥 (Get players before the hype)

**Signals to Track:**
- **Statcast:**
  - Exit velocity increase (sustained 2+ weeks)
  - Barrel rate spike
  - Hard-hit % improvement
  - Expected stats (xBA, xSLG) vs actual (regression candidates)
- **Playing Time:**
  - Moved up in batting order
  - Role change (platoon → everyday starter)
  - Minor league promotion with elite metrics
- **Performance Trends:**
  - Multi-week hot streak
  - Plate discipline improvement (BB%, K%)
  - Power surge (ISO increase)
- **Schedule:**
  - Upcoming easy matchups
  - Home-heavy stretch

**ML Model:**
- Train on historical data (past breakouts)
- Features: Statcast, playing time, age, team context
- Output: Breakout probability score (0-100)

**Alert Types:**
- 🚀 High Confidence (80%+): "Add immediately"
- ⚡ Medium Confidence (60-80%): "Monitor closely"
- 👀 Watch List (40-60%): "Speculative add"

---

### 2.2 Schedule Analyzer 📅 **VALUABLE**
**Status:** Not started  
**Effort:** 3-4 days  
**Value:** 🔥🔥 (Strategic planning)

**Features:**
- Weekly opponent difficulty ratings
- Streaming opportunities (pitchers vs weak offenses)
- Playoff schedule strength (weeks 22-26)
- Two-start pitcher finder
- Back-to-back doubleheader alerts
- Rest day forecasting

**Usage:**
```bash
# View upcoming schedule
npm run schedule:view --weeks 2

# Find streaming targets
npm run schedule:stream --position SP

# Playoff schedule analysis
npm run schedule:playoff
```

---

### 2.3 Statcast Integration ⚾ **UNIQUE EDGE**
**Status:** Not started  
**Effort:** 1 week  
**Value:** 🔥🔥🔥 (Data others ignore)

**Metrics to Track:**
- **Batters:**
  - Exit velocity (average, max, 95th percentile)
  - Launch angle (optimal zone: 10-30°)
  - Barrel rate (sweet spot percentage)
  - Hard-hit rate (>= 95 mph)
  - Sprint speed (SB potential)
  - xBA, xSLG (expected vs actual)
- **Pitchers:**
  - Average fastball velocity
  - Spin rate (breaking ball quality)
  - Whiff rate (swing-and-miss stuff)
  - Chase rate (fooling hitters)
  - Hard contact allowed

**Integration:**
- MLB Statcast API (free, official)
- Daily updates
- Historical trends (7/14/30 day rolling averages)
- Alerts on significant changes

**Views:**
```bash
# Player statcast report
npm run statcast:player "Zach Neto"

# Find elite metrics
npm run statcast:elite --metric "exit_velocity"

# Regression candidates
npm run statcast:regression
```

---

### 2.4 News & Injury Monitoring 📰 **CRITICAL**
**Status:** Not started  
**Effort:** 1-2 weeks  
**Value:** 🔥🔥 (React faster than competition)

**Data Sources:**
- **MLB Transaction Wire** (official)
- **Twitter/X** (beat reporters)
- **Reddit** (/r/fantasybaseball)
- **FantasyPros news feed**
- **RotoWire injury reports**

**Alert Types:**
- 🚨 **Critical:** IL move, trade, release
- ⚠️ **Important:** DTD status, lineup change
- 📢 **Notable:** Call-up, option, DFA
- 💬 **Rumor:** Trade speculation, injury concern

**Delivery:**
- Slack/Discord webhooks
- Email digest (morning/evening)
- In-app notifications
- SMS for critical alerts (optional)

**Smart Filtering:**
- Only players on your roster/watch list
- League-relevant (ignore AL players in NL-only league)
- Sentiment analysis (filter noise)

---

### 2.5 Trade Market Scanner 🔍 **STRATEGIC**
**Status:** Not started  
**Effort:** 1 week  
**Value:** 🔥🔥 (Find mutually beneficial deals)

**Features:**
- Scan all league rosters for needs
- Identify "buy low" targets (underperforming studs)
- Find "sell high" candidates (overperforming)
- Generate trade proposals automatically
- Track trade history (who trades with whom?)
- Collusion detection (suspicious patterns)

**Algorithm:**
- Analyze positional needs (surplus/shortage)
- Compare ADP to current performance
- Factor in keeper implications
- Consider team standings (buyer vs seller)

**Output:**
```
💼 TRADE OPPORTUNITIES

1. Trade with "Team Name"
   You need: SP
   They need: OF
   
   Suggested trade:
   You give: Randy Arozarena (OF, ADP 79)
   You get: Garrett Crochet (SP, ADP 11)
   
   Why this works:
   - You have OF depth (4 top-100 OFs)
   - They're weak at OF (best is ADP 120)
   - Both teams improve
   - Fair value trade (regression adjustments)
```

---

## 💎 **Phase 3: Advanced Analytics** (2-3 months)

**Goal:** Cutting-edge features for serious competitors.

### 3.1 Monte Carlo Playoff Simulator 🎲 **STRATEGIC**
**Status:** Not started  
**Effort:** 2 weeks  
**Value:** 🔥🔥 (Big-picture strategy)

**Features:**
- Run 10,000 season simulations
- Championship probability by team
- Must-win week identification
- Optimal strategy recommendations (safe vs aggressive)
- Trade impact simulation (before/after)
- Draft pick value (for keeper leagues)

**Usage:**
```bash
# Run simulation
npm run sim:playoff

# Specific scenario
npm run sim:trade-impact "Trade Mookie Betts for Paul Skenes"
```

**Output:**
```
🎲 PLAYOFF PROBABILITY REPORT

Current Season Outlook:
  Championship: 12.4%
  Playoffs: 67.8%
  Miss Playoffs: 32.2%

Must-Win Weeks:
  Week 15: vs Team ABC (critical)
  Week 18: vs Team XYZ (important)

Optimal Strategy:
  - Be aggressive weeks 15-18
  - Play conservatively after clinching
  - Target pitching in trades (biggest weakness)
```

---

### 3.2 Custom Scoring Integration ⚙️ **FLEXIBILITY**
**Status:** Not started  
**Effort:** 1 week  
**Value:** 🔥 (League-specific accuracy)

**Features:**
- Support custom league scoring
- Points leagues (non-standard points)
- Category leagues (custom categories)
- OBP instead of AVG
- QS instead of W
- Holds, Saves+Holds
- Custom roster sizes

**Config:**
```json
{
  "scoring": {
    "HR": 4,
    "R": 1,
    "RBI": 1,
    "SB": 2,
    "OBP": "category",
    "QS": 1
  },
  "roster": {
    "C": 2,
    "1B": 1,
    "MI": 1,
    "UTIL": 3
  }
}
```

---

### 3.3 Dynasty Mode 👑 **LONG-TERM**
**Status:** Not started  
**Effort:** 2-3 weeks  
**Value:** 🔥🔥 (Dynasty leagues)

**Features:**
- Prospect tracking (top 100)
- Service time monitoring (arbitration, FA)
- Dynasty trade value (10-year projections)
- Rebuild vs compete analysis
- Farm system rankings
- Age curve adjustments
- Contract year tracking

---

### 3.4 Machine Learning Projections 🤖 **CUTTING EDGE**
**Status:** Not started  
**Effort:** 1-2 months  
**Value:** 🔥🔥🔥 (Best projections)

**Approach:**
- Ensemble model (combine Steamer, THE BAT, Marcel, ZiPS)
- Factor in Statcast data
- Injury history weighting
- Park factors
- Team context (lineup quality)
- Age adjustments

**Features:**
- ROS projections
- Rest-of-week projections
- Confidence intervals
- Boom/bust probability
- Breakout/breakdown risk

---

## 🎨 **Phase 4: Polish & Scale** (Ongoing)

**Goal:** Professional product quality and user experience.

### 4.1 Web Dashboard 💻 **USER EXPERIENCE**
**Status:** Not started  
**Effort:** 3-4 weeks  
**Value:** 🔥🔥 (Accessibility)

**Features:**
- Modern React UI (Next.js)
- Mobile-responsive design
- Dark/light mode
- Interactive charts (Recharts, D3.js)
- Drag-and-drop lineup builder
- Real-time updates (WebSockets)
- Multi-league support
- Shareable reports

**Tech Stack:**
- Next.js 14 (App Router)
- TypeScript
- TailwindCSS
- Shadcn/ui components
- tRPC (type-safe API)
- Vercel deployment

---

### 4.2 Mobile App 📱 **ACCESSIBILITY**
**Status:** Not started  
**Effort:** 2-3 months  
**Value:** 🔥 (On-the-go access)

**Approach:**
- React Native (cross-platform)
- Push notifications
- Quick actions (add/drop)
- Lineup management
- News feed

---

### 4.3 Multi-Platform Support 🌐 **REACH**
**Status:** Not started  
**Effort:** Varies by platform  
**Value:** 🔥🔥 (More users)

**Platforms:**
- [x] Yahoo Fantasy
- [ ] ESPN
- [ ] CBS Sports
- [ ] Fantrax
- [ ] Sleeper
- [ ] NFBC/high-stakes

---

### 4.4 Testing & Reliability 🧪 **QUALITY**
**Status:** Minimal  
**Effort:** Ongoing  
**Value:** 🔥🔥 (Confidence)

**Needs:**
- Unit tests (pytest)
- Integration tests
- E2E tests (Playwright)
- Performance monitoring
- Error tracking (Sentry)
- Automated CI/CD (GitHub Actions)
- Load testing

---

## 📊 **Success Metrics**

### User Value
- Hours saved per week
- League wins attributed to tool
- Trade success rate
- Waiver wire hits vs league average

### Technical
- API uptime (>99.5%)
- Response time (<2s for all queries)
- Data freshness (<5 minutes)
- Error rate (<0.1%)

### Engagement
- Daily active users
- Features used per session
- Session duration
- Return rate

---

## 🎯 **Recommended Priority Order**

### Immediate (Next 2 weeks)
1. ✅ Waiver Wire Assistant polish
2. Trade Analyzer MVP
3. Schedule Analyzer basics

### Short-term (Next month)
4. Breakout Detector
5. Start/Sit AI
6. Statcast integration

### Medium-term (Next 3 months)
7. News/Injury monitoring
8. Web Dashboard
9. Trade Market Scanner
10. Monte Carlo simulator

### Long-term (6+ months)
11. ML Projections
12. Mobile app
13. Multi-platform support
14. Dynasty mode

---

## 💡 **Feature Combinations** (Maximum Impact)

### "Waiver Wire Dominator" Bundle
- Waiver Wire Assistant
- Breakout Detector
- Statcast Integration
- Schedule Analyzer
→ **Win leagues by owning breakouts before others**

### "Trade Master" Bundle
- Trade Analyzer
- Trade Market Scanner
- ML Projections
- Playoff Simulator
→ **Make optimal trades that propel you to championships**

### "Daily Edge" Bundle
- Start/Sit AI
- News Alerts
- Real-time Dashboard
- Matchup Analyzer
→ **Maximize points every single day**

---

## 🚀 **Getting Started**

Current working features:
```bash
npm run fetch:roster   # Get your roster from Yahoo
npm run update:adp     # Refresh ADP data
npm run analyze:yahoo  # Keeper analysis
npm run waivers        # Waiver wire recommendations
```

---

## 📝 **Notes**

- All phases can be worked on in parallel if needed
- Features can be reprioritized based on user feedback
- Effort estimates assume single developer
- Value ratings are subjective but based on league impact
- Consider monetization after Phase 2 (freemium model?)

---

**Last Updated:** February 1, 2026  
**Version:** 2.0  
**Status:** Active Development
