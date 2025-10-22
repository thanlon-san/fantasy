# V2 Recap Format Guide

## Overview

The V2 format is a **structured, all-matchups approach** that gives every matchup a moment while ordering them by drama for maximum engagement.

**Key Differences from V1:**
- **V1**: Stream-of-consciousness, 400-500 words, all matchups treated equally
- **V2**: Structured sections, 750-1000 words, all matchups included and drama-ordered; full power rankings for all teams with movement

---

## V2 Structure

### 1. Header + League Pulse + Stat of Week (~50 words)
- **Punchy headline** (6-10 words)
- **League Pulse**: 1-2 sentences to set the tone
- **Stat of the Week**: One wild/unexpected/hilarious stat

### 2. Matchups — All Games (~440 words)
- **All matchups**, 50-60 words each
- Order by drama: nail-biters (<5), upsets (proj diff ≥10), shootouts (both >120), blowouts (≥30), disasters (both <90)
- Micro-structure: Tagline → Burn-led paragraph with exactly one killer stat (setup → stat → burn; or burn → stat → bigger burn; or narrator gag → stat → understatement)

### 3. 🏆 Power Rankings (All Teams) (~160-220 words)
- ONE sentence per team with movement indicator (↕ +2/−1/—)
- Include record and PF; add a 5–9 word identity tag

Scoring model (canonical, opponent-adjusted PF):
- Win percentage (season record): see season-phase weights
- Opponent-adjusted Points For (adjPF): see season-phase weights
- Recent form (last 3 weeks adjPF + W/L): see season-phase weights
- Coaching efficiency (negative management gap trend): see season-phase weights

Season-phase weights:
- Early (Weeks 1–3): Record 0.40, adjPF 0.40, Recent 0.15, Coaching 0.05
- Mid (Weeks 4–10): Record 0.35, adjPF 0.40, Recent 0.20, Coaching 0.05
- Late (Weeks 11+): Record 0.30, adjPF 0.45, Recent 0.20, Coaching 0.05

Tie-breakers (in order):
1) Head-to-head result this season
2) Higher adjPF last week
3) Lower PF variance this season (more consistent)

Movement (↕):
- Compare this week’s rank vs last week’s: show +N/−N/— (— if no prior data)

Context one-liner (historical):
- Base on streaks (W/L), weekly finishes, variance identity, bench/waiver patterns, notable head-to-head callbacks
- Avoid repeating last week’s angle when possible

Data fallbacks:
- If opponent-adjusted PF is unavailable, substitute raw PF and add explicit SOS factor: Early +0.00, Mid +0.10, Late +0.15 (normalize remaining weights proportionally); never invent stats

Computing opponent-adjusted PF (adjPF):
- For each game, compute an opponent defensive index at the team level: `def_index = league_avg_points_allowed / opponent_points_allowed` (use your league’s scoring, season-to-date; optionally position-weighted)
- Game-level adjusted points: `adj_points = raw_points * def_index`
- Team adjPF = average of `adj_points` across games played; clamp `def_index` to [0.75, 1.25] to reduce outlier impact; require min 3 games before applying full adjustment (linearly ramp from Weeks 1–3)

Example entries:
1. **@maia.craver's Maia's Monstrous Team** (5–2, PF 872) [↕ +2] — Efficient menace  
   W3, back-to-back 120+, coaching gap shrinking; H2H win over No. 3.
2. **@kevin.agresto's Hot Chubb Time Machine** (4–3, PF 905) [↕ —] — High-octane chaos  
   Top-3 PF but boom/bust variance; last week 142, variance trend rising.

### 4. 🏈 Preview (~50 words)
- **2-3 bullets** max: Game of the Week, Trap Game, League Forecast

### 5. 🧘 Closing (~20 words)
- **One sentence** that drops the mic

---

## Total Word Count: 750-1000 words

**Breakdown:**
- 8 matchups × 55 words = 440 words
- Other sections ≈ 300 words
- Total = ~750 words

---

## Usage

### Using V2 Format (Default)

```python
from anthropic import Anthropic
from src.recap_generator import RecapGenerator

client = Anthropic(api_key='your-key')
generator = RecapGenerator()

# V2 format is default
recap = generator.generate_recap_with_anthropic(
    week=7, 
    client=client,
    use_v2_format=True  # Default
)
```

### Using V1 Format (Legacy)

```python
# Explicitly use V1 if you prefer the old format
recap = generator.generate_recap_with_anthropic(
    week=7, 
    client=client,
    use_v2_format=False
)
```

---

## Key V2 Principles

1. **TIGHT writing**: Every word counts. 50-60 words per matchup MAX.
2. **Drama-first ordering**: Nail-biters → Upsets → Shootouts → Blowouts → Disasters.
3. **One killer stat** per matchup; humor first, stats second; never invent stats.
4. **Power Rankings**: ONE sentence per team with movement; include record, PF, and a short identity tag.
5. **CRM jargon cap**: 5–8 total across the article; avoid more than 1 every 2–3 matchups.
6. **Ownership roast rules (summary)**: Bench roast if percent_started ≥ 60% and player ≥ 20; Start roast if percent_started ≤ 3% and player ≤ 5; avoid medium-ownership hindsight (10–60%) unless truly egregious.

---

## Example V2 Matchup

```markdown
### **@kevin.agresto's Hot Chubb Time Machine (142.3) def. @maia.craver's Maia's Monstrous Team (129.9)**
**Tagline:** "The Clash of Mid: Both tried. Only one succeeded."

Last week's high scorer facing the guy who hasn't stopped talking since draft day. Kevin's Josh Allen delivered a Monday-night miracle (34.6 points) that sealed it. Maia left 38 points on the bench, proving once again that coaching matters. Customer acquisition cost: unsustainable.
```

**Word count**: 56 words ✅

---

## When to Use V2 vs V1

**Use V2 when:**
- You want more structure and organization
- You have 16 teams (helps manage info overload)
- You want clearer tiers and power rankings
- You want preview/coaching disaster sections

**Use V1 when:**
- You prefer stream-of-consciousness style
- You want shorter recaps (400-500 words)
- You don't need the extra structure

---

## Notes

- V2 is now the **default** format as of this update
- Both formats use the same data from the API
- Both formats use the same roasting rules and tone
- V2 just adds structure and new sections

