# Platoon Splits Guide

## Overview

**Platoon splits** refer to the performance difference for batters/pitchers based on handedness matchups (L vs R). Understanding and leveraging platoons is one of the most powerful edges in fantasy baseball.

## The Basics

### Why Platoons Matter

**Average OPS Advantage: +15-25 points**

When a batter faces an opposite-handed pitcher:
- Better visibility of pitch release
- Pitches break toward the batter (easier to track)
- More favorable launch angles

### The Four Matchups

| Batter | Pitcher | Advantage | OPS Impact |
|--------|---------|-----------|------------|
| RHB | LHP | **STRONG** | +20-25 OPS |
| LHB | RHP | **STRONG** | +20-25 OPS |
| RHB | RHP | Neutral | 0 OPS |
| LHB | LHB | Disadvantage | -15-20 OPS |

### Switch Hitters

**Always have advantage** - Can bat from favorable side every at-bat.

Examples: Mookie Betts, Jose Ramirez, Bobby Witt Jr., Jazz Chisholm Jr.

---

## How the Tool Uses Platoon Data

### Scoring System

Our Daily Lineup Optimizer assigns **platoon scores (0-100)**:

| Scenario | Score | Impact |
|----------|-------|--------|
| Switch hitter | 85 | Strong boost |
| RHB vs LHP | 90 | Maximum advantage |
| LHB vs RHP | 90 | Maximum advantage |
| Same handedness | 60 | Penalty |
| Neutral | 75 | No adjustment |

### Weight in Overall Score

Platoon split = **15% of total confidence score**

Combined with:
- Matchup (30%)
- Park factor (20%)
- Recent form (25%)
- Breakout signal (10%)

---

## Real-World Examples

### Example 1: Elite Platoon Advantage

**Freddie Freeman (LHB) vs Sandy Alcantara (RHP)**

```
Base confidence: 70%
Platoon boost: +9% (15% weight × 90 score)
Total: 79% → ✅ START
```

**Why**: Freeman's career OPS vs RHP is ~.900, vs LHP is ~.750

### Example 2: Platoon Disadvantage

**Matt Olson (LHB) vs Blake Snell (LHP)**

```
Base confidence: 75%
Platoon penalty: -2.25% (15% weight × 60 score)
Total: 73% → ✅ START (but lower confidence)
```

**Why**: Even elite hitters struggle against same-handed pitchers

### Example 3: Switch Hitter

**Jose Ramirez (S) vs Anyone**

```
Base confidence: 70%
Switch hitter boost: +2.25% (15% weight × 85 score)
Total: 72% → ✅ START
```

**Why**: Always bats from favorable side

---

## Advanced Platoon Strategies

### 1. Roster Construction

**Ideal lineup**: Balance of L/R/S hitters

- **Too many LHB**: Vulnerable to lefty specialists
- **Too many RHB**: Miss out on LHP advantages
- **Mix with switch hitters**: Always covered

### 2. Streaming Matchups

**High-leverage situations**:

```bash
# Check today's pitcher handedness
npm run lineup:schedule

# If 3+ lefties pitching:
# → Stream right-handed power bats
npm run waivers -- --position OF
```

### 3. Sit/Start Decisions

**When to bench a star**:

```
Juan Soto (LHB) vs Blake Snell (LHP) @ Petco Park
→ Platoon disadvantage (-15 OPS)
→ Pitcher-friendly park (-8%)
→ Elite pitcher
= 45% confidence → ⚠️ BENCH
```

**Even superstars** have bad matchups!

### 4. Two-Player Platoons

If you have depth at a position:

- **RHB + LHB at same position**
- **Start RHB on days with LHP**
- **Start LHB on days with RHP**

Example:
- **C**: William Contreras (R) vs lefties
- **C**: Sean Murphy (R) vs righties (better overall)

---

## Platoon Splits by Position

### Most Extreme Splits

| Position | Typical Split | Why |
|----------|--------------|-----|
| 1B | 80-120 OPS | Power hitters, often platoon players |
| OF | 60-100 OPS | Mix of power/speed |
| C | 40-80 OPS | Contact-oriented |
| SS | 30-60 OPS | More balanced approach |

### Position-Specific Tips

**1B/OF (Corner Positions)**:
- Biggest platoon splits
- Most roster flexibility
- **Always check handedness**

**MI (Middle Infield)**:
- Smaller splits
- Switch hitters common (Witt, Hoerner)
- **Less critical but still matters**

**C (Catcher)**:
- Moderate splits
- Limited depth → harder to platoon
- **Play your starter unless extreme disadvantage**

---

## Historical Platoon Splits (2023-2024)

### Biggest Platoon Hitters

| Player | vs RHP | vs LHP | Split |
|--------|--------|--------|-------|
| Kyle Schwarber (L) | .850 OPS | .650 OPS | +200 |
| Jesse Winker (L) | .820 OPS | .630 OPS | +190 |
| Teoscar Hernández (R) | .790 OPS | .950 OPS | +160 |

**Takeaway**: These players MUST face favorable matchups

### Reverse Platoon Hitters (Unusual)

| Player | vs Same Hand | vs Opposite | Split |
|--------|-------------|-------------|-------|
| Juan Soto (L) | .900 OPS | .950 OPS | -50 (minimal) |
| Manny Machado (R) | .850 OPS | .820 OPS | +30 (small) |

**Takeaway**: Elite hitters transcend platoons

---

## Integration with Breakout Detector

### Synergy Example

**Player**: Jazz Chisholm Jr. (S)

**Breakout Signal**: 🔥 STRONG (85% confidence)
- Exit velo: 88 → 91 mph (+3)
- Hard-hit%: 38 → 47% (+9)

**Today's Matchup**: vs Gerrit Cole (R) @ Yankee Stadium

**Analysis**:
```
Matchup score: 40 (vs ace)
Park score: 85 (short porch)
Form score: 90 (hot streak)
Platoon score: 85 (switch hitter)
Breakout boost: 100 (STRONG signal)

Total: 78% → ✅ START
```

**Decision**: Despite facing an ace, breakout + platoon advantage + park = START

---

## Common Mistakes

### ❌ Mistake 1: Ignoring Platoons Entirely

**Problem**: Starting LHB vs elite LHP

**Solution**: Check handedness daily with `npm run lineup:schedule`

### ❌ Mistake 2: Over-Weighting Platoons

**Problem**: Benching superstar with minor disadvantage

**Solution**: Trust the tool's weighted scoring

### ❌ Mistake 3: Not Tracking Switch Hitters

**Problem**: Missing value of Mookie Betts, Jose Ramirez

**Solution**: Prioritize switch hitters in draft/trades

---

## Daily Workflow

### Morning Routine

```bash
# 1. Check today's games and pitcher handedness
npm run lineup:schedule

# 2. Get recommendations (includes platoon analysis)
npm run lineup

# 3. Review platoon advantages
# Look for: RHB vs LHP or LHB vs RHP matchups
```

### Key Platoon Decisions

**High-Confidence Starts** (Platoon + Other Factors):
- ✅ LHB vs LHP at Coors Field → MUST START
- ✅ Switch hitter on hot streak → MUST START

**Consider Benching**:
- ⚠️ LHB vs elite LHP at pitcher park → BENCH
- ⚠️ Platoon player in bad matchup → BENCH

---

## Future Enhancements

Planned improvements:
- [ ] **Career platoon splits** - Historical vs L/R data
- [ ] **Rolling platoon performance** - Last 30 days vs L/R
- [ ] **Pitcher-specific** - How player does vs THIS pitcher
- [ ] **Park + platoon combos** - Best/worst scenarios
- [ ] **Auto-platoon suggestions** - "Bench X, start Y" swaps

---

## Quick Reference

### Platoon Scoring Cheat Sheet

| Matchup | Score | Action |
|---------|-------|--------|
| RHB vs LHP | 90 | Strong start |
| LHB vs RHP | 90 | Strong start |
| Switch vs any | 85 | Always good |
| RHB vs RHP | 75 | Neutral |
| LHB vs LHP | 60 | Consider benching |
| RHB vs RHP (vs ace) | 40 | Bench if possible |

### Priority Order

When multiple factors conflict:

1. **Superstar** - Always start
2. **Breakout signal** - STRONG = start anyway
3. **Park factor** - Coors = start anyway
4. **Platoon** - Then check handedness
5. **Recent form** - Hot = boost, cold = penalty

---

## References

- [FanGraphs Platoon Splits](https://www.fangraphs.com/leaders/splits-leaderboards)
- [Baseball Reference Split Stats](https://www.baseball-reference.com/)
- [The Book: Playing the Percentages in Baseball](http://www.insidethebook.com/)
