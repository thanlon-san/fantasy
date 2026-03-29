## # Daily Lineup Optimizer

## Overview

The **Daily Lineup Optimizer** provides stat-backed start/sit recommendations for your roster based on:
- **Matchup Quality**: Opponent pitcher strength
- **Park Factors**: Hitter/pitcher friendly ballparks
- **Recent Form**: Hot/cold streaks (7/14/30 day rolling stats)
- **Platoon Splits**: Left/right handed matchups
- **Weather**: Wind, temperature impact on fly balls
- **Game Context**: Home/away, time of day

## How It Works

### Recommendation Algorithm

Each player gets a **confidence score (0-100%)** based on weighted factors:

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| Matchup | 35% | Opponent pitcher quality (ERA, K%, stuff) |
| Park Factor | 25% | Venue run environment |
| Recent Form | 30% | Last 7/14/30 days performance |
| Platoon Split | 10% | L/R batter vs pitcher advantage |

### Recommendation Tiers

| Tier | Confidence | Action | When To Use |
|------|------------|--------|-------------|
| 🔥 **MUST START** | 80-100% | Start with confidence | Elite matchup, hot streak, Coors Field |
| ✅ **START** | 65-79% | Recommended start | Good matchup, solid form |
| ➡️ **FLEX** | 50-64% | Use if needed | Neutral, filler spot |
| ⚠️ **BENCH** | 35-49% | Sit if possible | Poor matchup or cold streak |
| ❌ **AVOID** | 0-34% | Definitely bench | Vs elite pitcher + bad park |

---

## Usage

### Daily Recommendations
```bash
# Get today's recommendations
npm run lineup

# Specific date
npm run lineup -- --date 2026-05-15

# Demo mode (off-season)
npm run lineup -- --demo
```

### View Schedule
```bash
# See today's games with pitchers and park factors
npm run lineup:schedule
```

---

## Output Example

```
⚾ DAILY LINEUP OPTIMIZER
======================================================================
Date: 2026-05-15
======================================================================

📅 10 games scheduled:
  • Yankees @ Red Sox - 7:10 PM ET
  • Dodgers @ Giants - 9:45 PM ET
  ...

🤖 Analyzing matchups...

======================================================================
📊 DAILY LINEUP RECOMMENDATIONS
======================================================================

🔥 MUST START
----------------------------------------------------------------------

🔥 MUST_START: Mookie Betts
   vs TBD @ Giants (9:45 PM ET)
   Confidence: 85%
   Reasons: At hitter-friendly park (1.10), Hot (.347 avg)

🔥 MUST_START: Aaron Judge
   vs TBD @ Red Sox (7:10 PM ET)
   Confidence: 82%
   Reasons: Hitter-friendly park (1.10), vs weak pitcher

✅ START
----------------------------------------------------------------------

✅ START: Gunnar Henderson
   vs Jordan Montgomery @ Cardinals (8:15 PM ET)
   Confidence: 72%
   Reasons: Standard matchup, Decent form (.278 avg)

➡️ FLEX (Use if needed)
----------------------------------------------------------------------

➡️ FLEX: Bobby Witt Jr.
   vs Spencer Strider @ Braves (7:20 PM ET)
   Confidence: 58%
   Reasons: Pitcher-friendly park (0.96)

⚠️ CONSIDER BENCHING
----------------------------------------------------------------------

⚠️ BENCH: Ronald Acuña Jr.
   vs Gerrit Cole @ Yankees (7:05 PM ET)
   Confidence: 42%
   Reasons: vs elite pitcher (Gerrit Cole)

======================================================================
📈 SUMMARY
======================================================================
Must Start: 2
Start: 3
Flex: 2
Bench: 1
Avoid: 0
Total Players Analyzed: 8
======================================================================

💾 Recommendations saved to: data/lineup_recommendations_2026-05-15.txt
```

---

## Park Factors

### Most Hitter-Friendly (>1.05)
1. **Coors Field (1.25)** - Denver, elevation boost
2. **Great American Ball Park (1.15)** - Small dimensions
3. **Fenway Park (1.10)** - Green Monster LF
4. **Yankee Stadium (1.08)** - Short right porch
5. **Citizens Bank Park (1.06)** - Philadelphia wind

### Most Pitcher-Friendly (<0.95)
1. **Oracle Park (0.92)** - SF, marine layer + cold
2. **Oakland Coliseum (0.93)** - Huge foul territory
3. **T-Mobile Park (0.93)** - Seattle, marine layer
4. **Comerica Park (0.94)** - Detroit, deep CF
5. **Petco Park (0.94)** - San Diego, marine layer

### Impact on Scoring
- **Coors Field (+25%)**: Start ALL hitters playing here
- **Oracle Park (-8%)**: Bench borderline hitters

---

## Recent Form Analysis

### Hot Streak Detection
- **3+ game hitting streak** = automatic boost
- **Last 7 days > .300** = MUST START consideration
- **Last 7 days > .250** = START consideration
- **Last 7 days < .200** = BENCH consideration

### Rolling Windows
- **7 days**: Captures current form
- **14 days**: Balances recency with sample size
- **30 days**: Season-long trend

---

## Platoon Splits

### When It Matters Most

| Batter | Pitcher | Advantage |
|--------|---------|-----------|
| RHB | LHP | +15-20 OPS points |
| LHB | RHP | +15-20 OPS points |
| Switch | Any | Neutral |

### Examples
- **Ronald Acuña Jr. (RHB)** vs **Blake Snell (LHP)** = MUST START
- **Freddie Freeman (LHB)** vs **Sandy Alcantara (RHP)** = MUST START
- **Mookie Betts (RHB)** vs **Gerrit Cole (RHP)** = Neutral

---

## Weather Impact

### Wind
- **Wind out to RF/LF (10+ mph)**: +10% boost for RHB/LHB
- **Wind in from RF/LF (10+ mph)**: -10% for power hitters

### Temperature
- **85°F+**: Ball carries better, boost hitters
- **50°F or below**: Ball doesn't carry, favor pitchers

### Game Time
- **Day games**: Slightly favor hitters (sun in pitchers' eyes)
- **Night games**: Neutral

---

## Advanced Strategies

### 1. Stack Hitters from Same Team
When a team is playing at:
- Coors Field
- vs a bad pitcher
- With favorable weather

→ Start 2-3 hitters from that team

### 2. Stream Based on Schedule
- **Two-start pitchers**: Automatic MUST START
- **@ Coors or Great American**: Bench your pitcher
- **vs Top offense**: Bench risky pitchers

### 3. Leverage Platoons
If you have:
- RHB and LHB at same position
- Check opponent pitcher handedness
- Start favorable matchup

---

## Integration with Other Tools

### 1. Waiver Wire + Daily Lineup
```bash
# Monday: Find streaming pitcher for two-start week
npm run waivers -- --position SP

# Daily: Set lineup based on matchups
npm run lineup
```

### 2. Breakouts + Daily Lineup
```bash
# Weekly: Find breakout candidates
npm run breakouts

# Daily: If breakout player is in lineup, check matchup
npm run lineup
```

### 3. Full Workflow
```bash
# Sunday night: Next week's schedule
npm run lineup:schedule

# Monday: Waiver wire for streaming
npm run waivers

# Daily: Lineup optimization
npm run lineup

# Weekly: Breakout detection
npm run breakouts
```

---

## Data Sources

### Current Implementation
- **MLB Stats API**: Games, starting pitchers, weather
- **Park Factors**: Historical multi-year data
- **Recent Stats**: pybaseball Statcast data

### Future Enhancements
- [ ] Live Vegas betting lines (implied runs)
- [ ] Umpire strike zone data
- [ ] Batter vs pitcher career stats
- [ ] Weather API integration
- [ ] Pitcher "stuff" metrics (spin rate, velo)

---

## Configuration

### Customize Scoring Weights

Edit `src/lineup_optimizer.py`:

```python
class LineupOptimizer:
    # Adjust these to your preference
    MATCHUP_WEIGHT = 0.40  # More emphasis on pitcher quality
    PARK_WEIGHT = 0.20     # Less on park
    FORM_WEIGHT = 0.30
    PLATOON_WEIGHT = 0.10
```

### Customize Thresholds

```python
# Make recommendations more/less aggressive
if confidence_score >= 75:  # Lower from 80 = more MUST STARTs
    rec_type = RecommendationType.MUST_START
```

---

## Tips & Best Practices

### 1. Daily Routine
- **Morning**: Check `npm run lineup` for today
- **1 hour before game**: Final check (late scratches)
- **After games**: Review what worked

### 2. Position Priorities
1. **Starting Pitchers**: Matchup matters MOST
2. **Power Hitters**: Park factor critical
3. **Speed Guys**: Less park dependent
4. **Catchers**: Almost always start (scarcity)

### 3. Trust the Data, But...
- **Gut check**: Don't bench superstars
- **Sample size**: 7-day streaks can be noise
- **Context**: Injured, personal issues, etc.

### 4. Late News Monitoring
- Check Twitter/ESPN 30 min before games
- Lineup changes, weather delays
- Scratches/late additions

---

## Limitations

1. **Season Only**: Requires live MLB games (April-October)
2. **Probable Pitchers**: Sometimes TBD until game day
3. **Sample Size**: Early season = less reliable form data
4. **Injuries**: Doesn't track real-time injury reports
5. **Lineup Position**: Doesn't consider batting order yet

---

## FAQ

### Q: How early are recommendations available?
**A**: Typically 6-12 hours before first game. Probable pitchers announced ~24 hours ahead.

### Q: What if my player isn't playing?
**A**: They won't appear in recommendations. Check schedule with `npm run lineup:schedule`.

### Q: Can I use this for DFS?
**A**: Absolutely! The park factors and matchup scores are perfect for DFS.

### Q: What about doubleheaders?
**A**: Analyzes each game separately. Player will appear twice if playing both.

### Q: Does it work for playoffs?
**A**: Yes! Works through October playoffs.

---

## Future Features

Planned enhancements:
- [ ] **Interactive lineup setter** - Drag/drop UI
- [ ] **Batter vs pitcher career stats** - Historical matchups
- [ ] **Vegas implied runs** - Betting market context
- [ ] **Umpire factor** - Strike zone impact
- [ ] **Weather alerts** - Game postponements
- [ ] **Lineup position** - 1-9 batting order impact
- [ ] **DFS pricing** - Salary cap optimization
- [ ] **Multi-day projections** - Weekly outlook

---

## References

- [MLB Stats API](https://statsapi.mlb.com/)
- [Baseball Savant Park Factors](https://baseballsavant.mlb.com/leaderboard/statcast-park-factors)
- [FanGraphs Park Factors](https://www.fangraphs.com/guts.aspx?type=pf)
- [Weather Impact Studies](https://tht.fangraphs.com/the-effects-of-temperature-on-batted-ball-distance/)
