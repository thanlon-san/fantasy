# Breakout Detector

## Overview

The **Breakout Detector** uses MLB Statcast data to identify players showing signs of breaking out based on advanced metrics like exit velocity, hard-hit rate, barrel percentage, and more.

## How It Works

### Data Source
- **Baseball Savant / Statcast** - MLB's official tracking system
- Measures bat speed, exit velocity, spin rate, and 30+ other metrics
- Updated in real-time during the season

### Analysis Method
1. **Compare Time Periods**: Recent 14 days vs. previous 30 days
2. **Track Key Metrics**: Exit velocity, hard-hit %, barrel %, chase rate, etc.
3. **Calculate Confidence**: Weight improvements by metric importance
4. **Generate Alerts**: STRONG, EMERGING, WATCH, or FADING signals

### Key Metrics

#### Hitters
| Metric | Why It Matters | Breakout Threshold |
|--------|---------------|-------------------|
| Exit Velocity | Raw power | +1.5 mph |
| Hard-Hit % | Quality of contact | +5% |
| Barrel % | Optimal contact | +3% |
| Sweet Spot % | Launch angle quality | +4% |
| Chase Rate | Plate discipline | -3% (lower is better) |
| Whiff % | Contact ability | -2% (lower is better) |
| K% | Strikeout rate | -3% (lower is better) |
| BB% | Walk rate | +2% |

#### Pitchers
| Metric | Why It Matters | Breakout Threshold |
|--------|---------------|-------------------|
| Whiff % | Swing-and-miss | +3% |
| K% | Strikeout rate | +3% |
| BB% | Walk rate | -2% (lower is better) |
| Hard-Hit % (allowed) | Contact quality | -5% (lower is better) |
| Barrel % (allowed) | Damage limitation | -3% (lower is better) |
| Fastball Velocity | Stuff | +1 mph |

---

## Usage

### Scan Free Agents
```bash
# Scan all hitters
npm run breakouts

# Scan pitchers
npm run breakouts:pitchers

# Custom time frames
npm run breakouts -- --recent-days 7 --baseline-days 21
```

### Analyze Specific Player
```bash
npm run breakouts -- --player "Gunnar Henderson"
npm run breakouts -- --player "Hunter Greene" --pitchers
```

### Demo Mode (Off-Season)
```bash
npm run breakouts -- --demo
```

---

## Signal Types

### 🔥 STRONG (60%+ confidence, 3+ improving metrics)
- **Action**: Immediate add - Don't wait
- **Confidence**: 80%+ = Elite breakout candidate
- **Example**: Exit velocity +2 mph, hard-hit +8%, barrel +5%

### ⚡ EMERGING (40-60% confidence, 2+ improving metrics)
- **Action**: High priority - Add ASAP
- **Example**: Whiff rate +4%, chase rate -5%

### 👀 WATCH (20-40% confidence, 1+ improving metrics)
- **Action**: Add to watchlist
- **Example**: Exit velocity +1 mph

### ⚠️ FADING (Declining metrics)
- **Action**: Sell high
- **Example**: Exit velocity -2 mph, hard-hit -6%

---

## Output

### Console Display
```
🔥 STRONG BREAKOUT ALERT: Gunnar Henderson
======================================================================
Type: Hitter
Confidence: 87.3%

📈 Improving Metrics:
  • exit_velocity_avg: 89.2 → 91.5 (+2.3)
  • hard_hit_percent: 42.1 → 50.8 (+8.7)
  • barrel_percent: 8.3 → 12.1 (+3.8)
  • chase_rate: 28.5 → 24.2 (-4.3)

Summary: This hitter is showing multiple strong indicators of a breakout.
4 key metrics have improved significantly over the past 2 weeks.

💡 Action: 🔥 IMMEDIATE ADD - Don't wait, this player is breaking out NOW
======================================================================
```

### JSON Export
Alerts are automatically saved to `data/breakout_scan_YYYYMMDD_HHMMSS.json`:

```json
{
  "timestamp": "2026-05-15T10:30:00",
  "total_scanned": 50,
  "alerts": [
    {
      "player_name": "Gunnar Henderson",
      "signal": "STRONG",
      "confidence": 87.3,
      "summary": "This hitter is showing multiple strong...",
      "advice": "IMMEDIATE ADD - Don't wait..."
    }
  ]
}
```

---

## Integration with Waiver Wire

The Breakout Detector complements the standard Waiver Wire Assistant:

1. **Waiver Wire** - Finds value based on ADP (proven players)
2. **Breakout Detector** - Finds emerging players (before ADP adjusts)

### Combined Workflow
```bash
# Step 1: Check standard waivers (ADP-based)
npm run waivers

# Step 2: Check for breakout candidates
npm run breakouts

# Step 3: Cross-reference
# Players on both lists = highest priority adds
```

---

## Real-World Example

**Scenario**: You run `npm run breakouts` during Week 3 of the season

**Alert**:
```
🔥 STRONG: Jazz Chisholm Jr.
Confidence: 82.4%

Improving:
  • exit_velocity_avg: 88.1 → 91.3 (+3.2)
  • hard_hit_percent: 38.5 → 47.2 (+8.7)
  • barrel_percent: 7.1 → 11.8 (+4.7)
  • bb_percent: 6.2 → 9.8 (+3.6)

Action: IMMEDIATE ADD
```

**What This Means**:
- Jazz's exit velocity jumped 3.2 mph (huge)
- Contact quality drastically improved
- More walks = better plate discipline
- **Translation**: He's figured something out. Add him NOW before his stats explode.

**Fantasy Impact**:
- Current ADP: ~100
- Projected ADP after breakout: ~30-40
- **Window**: 3-7 days before league notices

---

## Configuration

### Customize Thresholds
Edit `src/breakout_detector.py`:

```python
# More aggressive (catch breakouts earlier, more false positives)
HITTER_BREAKOUT_THRESHOLDS = {
    'exit_velocity_avg': 1.0,   # Lower threshold
    'hard_hit_percent': 3.0,
    # ...
}

# More conservative (fewer alerts, higher accuracy)
HITTER_BREAKOUT_THRESHOLDS = {
    'exit_velocity_avg': 2.5,   # Higher threshold
    'hard_hit_percent': 8.0,
    # ...
}
```

### Adjust Time Windows
```bash
# Shorter recent window (more reactive)
npm run breakouts -- --recent-days 7 --baseline-days 21

# Longer window (more stable signals)
npm run breakouts -- --recent-days 21 --baseline-days 45
```

---

## Tips

### Best Time to Run
- **Weekly**: Monday mornings (after weekend games)
- **Daily**: During hot streaks/slumps
- **After Injuries**: Monitor players returning from IL

### Position Priorities
1. **OF/Util** - Most likely to find gems
2. **2B/SS** - High scarcity, big impact
3. **SP** - Velocity/whiff rate spikes = gold

### Red Flags
- Small sample sizes (< 30 ABs / 15 IP)
- Outlier performances (1-2 game hot streaks)
- Extreme changes (usually noise, not signal)

### Green Flags
- Multiple metrics improving together
- Sustained over 10+ games
- Matches scouting reports/prospect pedigree

---

## Limitations

1. **Season Only**: Statcast data only available during MLB season (April-October)
2. **Sample Size**: Needs 2+ weeks of games for reliable signals
3. **Context**: Doesn't account for ballpark, weather, or opponents
4. **Injuries**: Can't predict injury risks

---

## API Rate Limits

The Statcast client uses caching to minimize API calls:

- **First Run**: ~2-3 seconds per player
- **Subsequent Runs**: Instant (uses cache)
- **Cache Duration**: 24 hours

To clear cache:
```bash
rm -rf ~/.pybaseball/cache
```

---

## Troubleshooting

### "No data available"
**Cause**: Off-season or player hasn't played recently  
**Fix**: Use `--demo` mode during off-season

### "Could not find player"
**Cause**: Name mismatch or rookie not in database  
**Fix**: Try alternative spellings or check Baseball Reference

### Slow performance
**Cause**: First run downloads player database  
**Fix**: Wait for initial cache to build (~30 seconds)

---

## Future Enhancements

Planned features:
- [ ] Email/Slack alerts for strong signals
- [ ] Historical tracking (breakout success rate)
- [ ] ML model for breakout prediction
- [ ] Integration with lineup optimizers
- [ ] Multi-league scanning

---

## References

- [Baseball Savant](https://baseballsavant.mlb.com/)
- [Statcast Glossary](https://www.mlb.com/glossary/statcast)
- [pybaseball Documentation](https://github.com/jldbc/pybaseball)
