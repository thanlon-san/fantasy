# 🏈 Obscure Football Stats APIs

Advanced, weird, and hilarious NFL data sources ESPN doesn't have.

---

## 🔥 TIER 1: ADVANCED ANALYTICS (The Good Stuff)

### 1. **nfl_data_py** - Advanced Play-by-Play Analytics
**URL:** https://github.com/nfl-data-py/nfl_data_py  
**Cost:** FREE (Python library)  
**What You Get:** The motherload of advanced stats

**Obscure Stats Available:**
- **EPA (Expected Points Added)** - How much value each play adds
- **CPOE (Completion % Over Expected)** - QB accuracy vs expected
- **Air Yards** - How far the ball traveled in the air
- **YAC (Yards After Catch)** - Receiver vs QB production
- **Target Share** - % of team targets per player
- **Snap Count %** - Time on field
- **Route Participation** - How often WRs run routes
- **Depth of Target (aDOT)** - Average depth of throws

**Example Roasts:**
```
"Your QB has a -0.12 EPA/play. League average is +0.05. 
He's literally making your team worse every time he drops back."

"Your WR1's aDOT is 3.2 yards. That's not a route tree, that's a bush."

"Target share: 28%. Catch rate: 42%. Your WR is getting targeted 
because the defense knows he won't catch it."

"Your RB's yards before contact: 0.8. Yards after contact: 0.3. 
The offensive line blocks better without him."
```

**Installation:**
```bash
pip install nfl_data_py
```

**Usage:**
```python
import nfl_data_py as nfl

# Get weekly data with advanced stats
pbp = nfl.import_pbp_data([2025])

# Get player stats with EPA, target share, etc.
weekly = nfl.import_weekly_data([2025])

# Air yards, target share, snap counts
targets = weekly[['player_name', 'air_yards', 'targets', 'target_share']]
```

---

### 2. **The Odds API** - Vegas Knows Everything
**URL:** https://the-odds-api.com/  
**Cost:** FREE tier (500 requests/month)  
**What You Get:** Real-time betting lines, player props

**Obscure Stats:**
- **Opening vs Closing Lines** - "Vegas moved the line 6 points against your QB"
- **Player Props** - "He was O/U 15.5 points. Hit 4.2."
- **Sharp Money Movement** - "The sharps faded your RB. They knew."
- **Over/Under Hit Rate** - "This team goes under 73% of the time"

**Example Roasts:**
```
"Your QB was -350 to throw a TD. He didn't. That's a 77.8% probability 
of success. You found the 22.2%."

"Vegas had your RB at O/U 65.5 rushing yards. He got 8. 
The bookies knew what your eyes couldn't see."

"Opening line: RB1 @ 18.5 points. Closing line: 12.5. 
Sharp money hammered the under. Your opponent didn't get the memo."
```

---

### 3. **Pro Football Reference (Scraped Data)**
**URL:** https://www.pro-football-reference.com/  
**Cost:** FREE (requires scraping)  
**What You Get:** Historical context, game logs, advanced stats

**Obscure Stats:**
- **Game Script** - Win probability throughout game
- **Defensive Matchup Data** - "Worst matchup in the league"
- **Career Worst Games** - "His 3rd worst game ever"
- **Home/Away Splits** - "0 TDs in road games"
- **Weather Game Performance** - "Never topped 50 yards in the rain"

**Example Roasts:**
```
"Your RB averaged 2.1 YPC against teams ranked 20+ in run defense.
This week's opponent? Ranked 32nd. He got 1.8."

"Career stats in domes: 23 PPG. Career stats outdoors: 8 PPG.
You started him in Buffalo in December."

"This was his 4th career game under 5 points. Three were this season.
All in your starting lineup."
```

---

### 4. **NFL Arrest Database API**
**URL:** http://nflarrest.com/  
**Cost:** FREE  
**What You Get:** Player arrest records (use very carefully!)

**Example Roasts (PG-13 only):**
```
"Your team has 3 players with arrest records. Their combined points: 8.
At least they showed up to the game."

"Fun fact: More players on your roster have mugshots than touchdowns this week."
```

---

### 5. **Football Sentiment API**
**URL:** Via RapidAPI  
**Cost:** Free tier available  
**What You Get:** Fan sentiment analysis

**Example Roasts:**
```
"Public sentiment on your QB: -0.73 (scale -1 to +1).
Even the internet hates your decision."

"Your team's sentiment score is lower than the Jets'.
The. Jets."
```

---

## 🎯 TIER 2: NICHE BUT HILARIOUS

### 6. **Sleeper API** - More Detailed Fantasy Stats
**URL:** https://docs.sleeper.app/  
**Cost:** FREE  
**What You Get:** Ownership %, trends, projections

**Obscure Stats:**
- **Roster %** across all fantasy leagues
- **Trending** - Players being added/dropped
- **Projections vs Actual** - "Off by 22 points"

**Example Roasts:**
```
"Your RB2 is rostered in 0.3% of Sleeper leagues. You're the 0.3%.
There's a reason for that."

"He's the #1 trending DROP this week. You're starting him.
Contrarian genius or just bad?"
```

---

### 7. **NextGen Stats** (Via Web Scraping)
**URL:** https://nextgenstats.nfl.com/  
**Cost:** FREE (scrape or manual check)  
**What You Get:** Player tracking data

**Obscure Stats:**
- **Max Speed** - "Reached 18.2 MPH on one carry for 2 yards"
- **Cushion** - Average yards of separation
- **Time to Throw** - QB decision speed
- **Completion Probability** - On individual throws

**Example Roasts:**
```
"Your WR averaged 0.8 yards of separation. That's single coverage.
He couldn't get open if the DB took the play off."

"Your QB's time to throw: 3.1 seconds. League average: 2.5.
He's not waiting for routes, he's frozen in fear."
```

---

### 8. **Sharp Football Stats / Grinding the Mocks**
**URL:** https://www.sharpfootballstats.com/  
**Cost:** Some free data  
**What You Get:** Matchup-specific advanced analytics

**Obscure Stats:**
- **Red Zone Opportunity %**
- **Targets Inside the 10**
- **Pass Rate Over Expected (PROE)**
- **Matchup-specific grades**

**Example Roasts:**
```
"Red zone opportunity share: 43%. Red zone production: 0 TDs.
He's getting the chances. He's just bad."

"Your QB faced the 32nd-ranked pass defense. 
Still couldn't crack 200 yards. Impressive, honestly."
```

---

### 9. **Player Injury Reports / Practice Status**
**URL:** NFL.com, various sources  
**Cost:** FREE  
**What You Get:** Injury designations, practice participation

**Example Roasts:**
```
"Your RB was 'Questionable' all week. Zero practice. You started him anyway.
He played 3 snaps. Shocked?"

"DNP Wednesday. Limited Thursday. DNP Friday. Inactive Sunday.
The writing was on the wall. You just don't read."
```

---

### 10. **Reddit/Twitter Sentiment (Manual or Scraped)**
**URL:** Various  
**Cost:** FREE  
**What You Get:** Real-time fan reactions

**Example Roasts:**
```
"Your QB has 47 Reddit posts calling for him to be benched.
You started him. Community consensus: 1. You: 0."
```

---

## 🛠️ IMPLEMENTATION PRIORITY

### Week 1: **nfl_data_py** (Advanced Analytics)
- EPA/CPOE for QBs
- Air yards & target share for WRs/TEs
- Yards before/after contact for RBs
- Snap count %

### Week 2: **The Odds API** (Vegas Lines)
- Player prop O/U
- Line movement
- Sharp money indicators

### Week 3: **Pro Football Reference** (Historical Context)
- Career worst games
- Matchup history
- Home/away splits

### Week 4+: **Sentiment, NextGen, Sleeper**
- Only when genuinely hilarious

---

## 📊 EXAMPLE: NFL_DATA_PY INTEGRATION

### Install
```bash
pip install nfl_data_py
```

### Code Sample
```python
# src/nfl_advanced_stats.py
import nfl_data_py as nfl
from datetime import datetime

class AdvancedStatsEnricher:
    """Fetch obscure NFL stats for roasting"""
    
    def __init__(self):
        self.season = datetime.now().year
        self.weekly_data = None
    
    def load_weekly_data(self, week):
        """Load advanced stats for the week"""
        self.weekly_data = nfl.import_weekly_data([self.season], ['QB', 'RB', 'WR', 'TE'])
        return self.weekly_data[self.weekly_data['week'] == week]
    
    def get_player_advanced_stats(self, player_name):
        """Get EPA, target share, air yards, etc."""
        player = self.weekly_data[self.weekly_data['player_name'] == player_name]
        
        if player.empty:
            return None
        
        return {
            'epa': player['fantasy_points_ppr'].values[0],
            'target_share': player.get('target_share', 0),
            'air_yards': player.get('air_yards', 0),
            'avg_depth_of_target': player.get('average_depth_of_target', 0),
            'yards_after_catch': player.get('yards_after_catch', 0),
            'snap_pct': player.get('snap_pct', 0),
        }
    
    def generate_roast(self, player_name, stats):
        """Generate roast based on advanced stats"""
        roasts = []
        
        # Low target share roast
        if stats.get('target_share', 0) < 0.10:
            roasts.append(f"{player_name}'s target share: {stats['target_share']:.1%}. He's basically a decoy.")
        
        # Low air yards roast
        if stats.get('avg_depth_of_target', 0) < 5:
            roasts.append(f"Average depth of target: {stats['avg_depth_of_target']:.1f} yards. That's not a route, that's a shuffle.")
        
        # Low snap % roast
        if stats.get('snap_pct', 0) < 0.40:
            roasts.append(f"Snap count: {stats['snap_pct']:.1%}. Even his own coach doesn't trust him.")
        
        return roasts

# Usage in recap_generator.py
from src.nfl_advanced_stats import AdvancedStatsEnricher

enricher = AdvancedStatsEnricher()
weekly_stats = enricher.load_weekly_data(current_week)

for player in lineup:
    advanced = enricher.get_player_advanced_stats(player.name)
    if advanced:
        roasts = enricher.generate_roast(player.name, advanced)
        # Add to context
```

---

## 🎯 ROAST EXAMPLES BY STAT TYPE

### **EPA (Expected Points Added)**
```
"Your QB's EPA: -0.08 per play. Every snap makes you worse.
Kneeling would be more productive."
```

### **Air Yards vs YAC**
```
"Air yards: 45. YAC: 3. Your QB threw it 45 yards so your WR
could catch it and immediately fall down."
```

### **Target Share**
```
"28% target share. 12% catch rate. The defense knows who to ignore."
```

### **Snap Count**
```
"Played 18 snaps (32%). Scored 2.1 points. 
0.12 points per snap. Generational inefficiency."
```

### **Vegas Lines**
```
"O/U: 75.5 yards. Actual: 8 yards. You didn't just miss the over,
you insulted it."
```

### **Historical Context**
```
"Career stats against this defense: 3 games, 11 total points.
You thought week 4 would be different. It wasn't."
```

---

## 🚀 QUICK START

1. Install `nfl_data_py`:
   ```bash
   pip install nfl_data_py
   ```

2. Create `src/nfl_advanced_stats.py` (see code above)

3. Update `recap_generator.py`:
   ```python
   from src.nfl_advanced_stats import AdvancedStatsEnricher
   
   enricher = AdvancedStatsEnricher()
   stats = enricher.load_weekly_data(week)
   # Add to context
   ```

4. Update `COLUMNIST_PROMPT.md`:
   ```markdown
   ## Advanced Stats Available
   - EPA (Expected Points Added)
   - Target Share
   - Air Yards / aDOT
   - Snap Count %
   - Vegas Player Props
   ```

---

## ⚠️ IMPORTANT NOTES

- **nfl_data_py updates weekly** - Usually by Tuesday afternoon
- **Vegas lines** - Most accurate right before game time
- **Sentiment data** - Use sparingly, can be toxic
- **Arrest data** - PG-13 only, no specific details
- **Historical stats** - Cache them, don't fetch every time

---

## 💡 THE NUCLEAR OPTION: COMBINE EVERYTHING

```
"Let's talk about your RB2. EPA: -0.14 (bottom 5%). Target share: 8% 
(backup territory). Air yards: 2.1 (checkdown central). Snap count: 37% 
(even his coach doesn't believe). Vegas had him O/U 45.5 yards—sharps 
hammered the under to 38.5 by kickoff. He got 6. Career stats vs this 
defense: 3 games, 14 total yards. You started him anyway. Fan sentiment: 
-0.81 (scale -1 to +1). The internet tried to warn you. 

What they'll tell themselves: 'We're still gathering data for our cohort analysis.'"
```

---

**Ready to implement? nfl_data_py is the best place to start!**
