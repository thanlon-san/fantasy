# Keeper Advisor Quick Start Guide

Get up and running with the Baseball Keeper League Advisor in 5 minutes!

## Installation

```bash
cd apps/keeper-advisor
pip install -r requirements.txt
```

## Step 1: Try the Sample Data

See what the advisor can do with pre-loaded sample data:

```bash
npm run analyze
```

This shows:
- ✅ Keeper eligibility for each player
- ✅ Keeper costs and value analysis
- ✅ Top 3 recommended keepers
- ✅ Different keeper scenarios

## Step 2: Create Your Roster File

### Option A: Start from Template

```bash
# Create a template CSV
npm run template

# This creates: data/my_roster.csv
# Open it and fill in your players
```

### Option B: Manual CSV Creation

Create `data/my_roster.csv` with this format:

```csv
name,position,team,draft_round,draft_year,years_kept,adp,is_undrafted_fa,notes
Bobby Witt Jr.,SS,KC,15,2024,1,3.1,false,Late round steal - kept once
Aaron Judge,OF,NYY,3,2025,0,5.2,false,Drafted round 3 this year
Shohei Ohtani,DH,LAD,1,2025,0,1.5,false,First rounder - can't keep
```

**Required columns:**
- `name` - Player name
- `position` - 1B, 2B, SS, 3B, OF, C, SP, RP, DH
- `team` - MLB team (NYY, LAD, etc.)
- `draft_round` - Round drafted (1-12, or 13+ for undrafted FA)
- `draft_year` - Year originally drafted
- `years_kept` - How many times kept already (0 if never kept)

**Optional columns:**
- `adp` - Average Draft Position (for value analysis)
- `is_undrafted_fa` - Set to "true" for waiver pickups
- `notes` - Personal notes

## Step 3: Analyze Your Roster

```bash
npm run analyze:csv
```

Or with more options:

```bash
python3 scripts/keeper_cli.py \
  --csv data/my_roster.csv \
  --team "Your Team Name" \
  --scenarios \
  --output my_keeper_report.txt
```

## Step 4: Get AI Recommendations (Optional)

1. Add API key to `.env`:
   ```bash
   echo "ANTHROPIC_API_KEY=your_key_here" > .env
   ```

2. Run with AI:
   ```bash
   python3 scripts/keeper_cli.py --csv data/my_roster.csv --ai
   ```

The AI will provide:
- Which keeper scenario to choose
- Specific player recommendations
- Draft strategy advice
- Position scarcity insights

## Understanding the Output

### Keeper Eligibility

```
#1 - Bobby Witt Jr. (SS)
   Cost: Round 10         <- What round you'd use to keep him
   ADP: 3.1               <- Where he'd go in the draft
   Surplus Value: 89.7    <- Value score (higher = better)
   Years Left: 2          <- Years of control remaining
```

**Surplus Value explained:**
- Measures how good the keeper deal is
- Positive = good value (keep him earlier than his ADP)
- Higher = better value
- Example: ADP 3.1 but keep in round 10 = great value!

### Keeper Scenarios

Shows different keeper combinations:

1. **Top 3 keepers** - Maximum value, uses 3 picks
2. **Top 2 keepers** - Good value, saves a pick
3. **Single keeper** - Best single player, saves 2 picks
4. **No keepers** - Full draft flexibility

## Pro Tips

### Finding ADP Data

Get ADP (Average Draft Position) from:
- [FantasyPros Draft Wizard](https://www.fantasypros.com/mlb/adp/overall.php)
- [NFBC ADP](https://nfc.shgn.com/adp)
- Your league's mock drafts

ADP makes the value calculations much better!

### Interpreting Recommendations

**Strong Keeper Indicators:**
- ✅ ADP in top 50, keeper cost round 10+
- ✅ Surplus value > 50
- ✅ Multiple years of control remaining
- ✅ Position scarcity (SS, C, elite SP)

**Don't Keep:**
- ❌ First round picks (ineligible)
- ❌ Negative surplus value
- ❌ 0 years of control remaining
- ❌ Keeper cost = ADP round

### Common Scenarios

**Late round breakouts:**
- Drafted round 15, now top 10 player
- Keep for round 14 = HUGE value
- Example: Bobby Witt Jr., Julio Rodriguez

**Mid-round solid players:**
- Drafted round 6, ADP around 40-50
- Marginal keeper value
- Usually better to let go

**Waiver wire gems:**
- Picked up as FA, become 12th round keeper
- Often great value if they broke out
- Example: Corbin Carroll in 2023

## CLI Reference

```bash
# Basic analysis
python3 scripts/keeper_cli.py --sample

# Your roster
python3 scripts/keeper_cli.py --csv data/roster.csv

# With scenarios
python3 scripts/keeper_cli.py --csv data/roster.csv --scenarios

# With AI recommendations
python3 scripts/keeper_cli.py --csv data/roster.csv --ai

# Save report to file
python3 scripts/keeper_cli.py --csv data/roster.csv --output report.txt

# Use GPT instead of Claude
python3 scripts/keeper_cli.py --csv data/roster.csv --ai --use-gpt

# Create template
python3 scripts/keeper_cli.py --create-template data/my_roster.csv
```

## Troubleshooting

**"File not found" error:**
```bash
# Make sure you're in the right directory
cd apps/keeper-advisor

# Check if file exists
ls -la data/my_roster.csv
```

**"Invalid draft_round" error:**
- Make sure draft_round is a number (1-20)
- Use 13+ for undrafted free agents

**AI not working:**
- Check `.env` file has API key
- Try `--use-gpt` flag for OpenAI instead

**Negative surplus value:**
- This means the keeper cost is too high
- These players are "Don't Keep" candidates
- Either drafted too early or performed poorly

## Next Steps

1. ✅ Analyze your roster
2. Compare different keeper scenarios
3. Get AI recommendations
4. Make your keeper decisions!
5. Plan your draft strategy around your keepers

## Need More Help?

- Check `README.md` for detailed features
- See `data/roster_template.csv` for example format
- Run `python3 scripts/keeper_cli.py --help` for all options
