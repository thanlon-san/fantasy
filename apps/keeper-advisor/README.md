# Baseball Keeper League Advisor ⚾

AI-powered decision support tool for baseball keeper league management.

**Status**: ✅ **Fully Functional** - Ready to use!

## Features

✅ **Keeper Eligibility Analysis** - Automatically calculates who can be kept based on your league rules  
✅ **Value Calculator** - Compares keeper cost vs. draft value (ADP) to find the best deals  
✅ **Scenario Generator** - Shows different keeper combinations and their total value  
✅ **CSV Import/Export** - Easy roster management  
✅ **AI Recommendations** - Get personalized advice from Claude or GPT-4o (optional)  
✅ **League Rules Engine** - Handles complex keeper rules automatically

## Quick Start

### 1. Try it with Sample Data

```bash
cd apps/keeper-advisor
npm run analyze
```

This will analyze a sample roster and show you:
- Which players are keeper-eligible
- Keeper costs and surplus value
- Top 3 recommended keepers
- Different keeper scenarios

### 2. Analyze Your Roster

**Option A: Create a CSV file**
```bash
# Create a template
npm run template

# Edit data/my_roster.csv with your players
# Then analyze it
npm run analyze:csv
```

**Option B: Use the full CLI**
```bash
python3 scripts/keeper_cli.py --csv data/my_roster.csv --team "Your Team" --scenarios --ai
```

## Your League Rules

This tool implements your specific keeper rules:
- ✅ Keep up to 3 players from previous year
- ✅ Undrafted FA keepers must be rostered before September call-ups
- ✅ 3-year control period (draft year + 2 following years)
- ✅ Keepers move up one round each year
- ✅ Players drafted after round 12 → 12th round keepers
- ✅ Cannot keep 1st round picks
- ✅ 2nd round picks only have 2 years of control

## CLI Commands

```bash
# Analyze with sample data
npm run analyze

# Analyze your roster from CSV
npm run analyze:csv

# Get AI-powered recommendations (requires API key)
npm run analyze:ai

# Create a CSV template
npm run template

# Full CLI options
python3 scripts/keeper_cli.py --help
```

## CSV Format

Your CSV should have these columns:

```csv
name,position,team,draft_round,draft_year,years_kept,adp,is_undrafted_fa,notes
Bobby Witt Jr.,SS,KC,15,2024,1,3.1,false,Late round steal
Aaron Judge,OF,NYY,3,2025,0,5.2,false,Drafted this year
```

- **name**: Player name
- **position**: 1B, 2B, SS, 3B, OF, C, SP, RP, DH
- **team**: MLB team abbreviation
- **draft_round**: Round drafted (use 13+ for undrafted FA)
- **draft_year**: Year originally drafted
- **years_kept**: How many times already kept (0 for first time)
- **adp**: Average Draft Position (optional, for value analysis)
- **is_undrafted_fa**: true/false
- **notes**: Any notes about the player

## AI Recommendations

To get AI-powered keeper advice:

1. Set up API key in `.env`:
   ```bash
   ANTHROPIC_API_KEY=your_key_here
   # OR
   OPENAI_API_KEY=your_key_here
   ```

2. Run with `--ai` flag:
   ```bash
   python3 scripts/keeper_cli.py --sample --ai
   ```

The AI will provide:
- Recommended keeper scenario
- Specific player advice
- Draft strategy tips
- Position scarcity insights

## Example Output

```
KEEPER ANALYSIS REPORT: Sample Team
================================================================================
Total Players: 10
Keeper Eligible: 9
Recommended Keepers: 3

RECOMMENDED KEEPERS
--------------------------------------------------------------------------------
#1 - Bobby Witt Jr. (SS)
   Cost: Round 10
   ADP: 3.1
   Surplus Value: 89.7
   Years Left: 2
   Reason: Excellent value - Elite player at late-round cost

#2 - Corbin Carroll (OF)
   Cost: Round 11
   ADP: 12.3
   Surplus Value: 98.7
   Years Left: 3
   Reason: Great value with 3 years of control

#3 - Gunnar Henderson (SS)
   Cost: Round 10
   ADP: 8.5
   Surplus Value: 89.3
   Years Left: 2
   Reason: Top-10 player for round 10 pick

KEEPER SCENARIOS
--------------------------------------------------------------------------------
1. Top 3 value keepers - Total Value: 277.8
   Players: Bobby Witt Jr., Corbin Carroll, Gunnar Henderson
   Draft Picks Available: 1, 2, 3, 4, 5, 6, 7, 8, 9, 12
```

## Next Steps

- [ ] Yahoo Fantasy API integration (coming soon)
- [ ] Web UI dashboard (planned)
- [ ] Trade value calculator (planned)
- [ ] Draft strategy simulator (planned)

## Need Help?

- Check the example CSV: `data/roster_template.csv`
- Run with `--help` for all options
- See `docs/` for detailed guides
