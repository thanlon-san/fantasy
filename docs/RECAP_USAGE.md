# Weekly Recap Generator Usage Guide

Generate viciously funny fantasy football recaps using your API data and an LLM.

## Quick Start

### Option 1: Generate Context for Manual LLM Use

**Best for:** One-time use, testing, or if you use a web LLM interface

```bash
# Make sure API is running
python3 api.py &

# Generate context file
python3 recap_generator.py 7 --context-only
```

This creates `output/week-7-context.txt` with:

- The full columnist prompt
- All matchup data from your API
- Previous recap context (to avoid repetition)

**Then:** Copy the contents into ChatGPT, Claude, or your preferred LLM to generate the recap.

### Option 2: OpenAI Integration

**Best for:** Automated generation with GPT-4

```python
from openai import OpenAI
from recap_generator import RecapGenerator

# Initialize
client = OpenAI(api_key='your-api-key')
generator = RecapGenerator()

# Generate recap
recap = generator.generate_recap_with_openai(
    week=7,
    client=client,
    model="gpt-4"  # or "gpt-4-turbo", "gpt-3.5-turbo"
)

print(recap)
```

Output saved to: `output/week-7-recap.md`

### Option 3: Anthropic Claude Integration (Recommended!)

**Best for:** Automated generation with Claude Sonnet 4.5 (best creative writing model)

```python
from anthropic import Anthropic
from recap_generator import RecapGenerator

# Initialize
client = Anthropic(api_key='your-api-key')
generator = RecapGenerator()

# Generate recap with Claude Sonnet 4.5 (default)
recap = generator.generate_recap_with_anthropic(
    week=7,
    client=client
    # model="claude-sonnet-4-5-20250929" is the default
)

print(recap)
```

Output saved to: `output/week-7-recap.md`

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This includes:

- `anthropic` - For Claude Sonnet 4.5
- `python-dotenv` - For .env file support
- Optional: `openai` - For GPT models (if you prefer)

### 2. Set Up Your API Key

**Option A: Using .env file (Recommended)**

```bash
# Copy the example file
cp env.example .env

# Edit .env and add your key
# ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Option B: Environment Variable**

```bash
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
```

The .env file method is better because:

- ✅ Key is automatically loaded
- ✅ No need to export every time
- ✅ Already in .gitignore (won't be committed)

## How It Works

### 1. Data Collection

The script pulls from your running API:

- ✅ League info (name, teams, current week)
- ✅ All matchups (scores, lineups, bench points)
- ✅ Week statistics (highest/lowest scores, blowouts, etc.)
- ✅ Current standings
- ✅ Player-by-player performance (actual vs projected)

### 2. Context Building

Transforms API data into roast-worthy insights:

- Identifies benched players who went off
- Calculates projection misses
- Highlights bad beats and close games
- Notes season-long patterns

### 3. Memory System

Tracks previous recaps in `recap_history.json`:

- Avoids repeating the same burns
- Builds running gags (e.g., "Third week in a row benching RB1")
- Maintains consistency in manager "personas"
- References league history

### 4. LLM Generation

Uses the comprehensive `COLUMNIST_PROMPT.md` to generate:

- Punchy headline
- Cold open
- Matchup-by-matchup roasts
- Corporate cope lines
- 85% lowlights / 15% highlights

## The Columnist Persona

**"The Commissioner's Ghost"** - Your viciously funny columnist who:

- ✍️ Writes like Bill Simmons meets The Onion
- 🎯 Roasts decisions, not people
- 📊 Grounds every burn in real data
- 🎭 Uses corporate jargon as a weapon
- 🔄 Remembers past failures for callbacks
- 🎪 Keeps it PG-13 and safe

## Example Workflow

```bash
# Week 7 just finished!

# Step 1: Make sure API is running
python3 api.py &

# Step 2: Generate context
python3 recap_generator.py 7 --context-only

# Step 3: Use the output/week-7-context.txt in your LLM
# Or use Python integration:

python3 << EOF
from openai import OpenAI
from recap_generator import RecapGenerator

client = OpenAI(api_key='sk-...')
generator = RecapGenerator()
recap = generator.generate_recap_with_openai(week=7, client=client)

# Recap is saved to output/week-7-recap.md
print(f"\n{'='*60}")
print("GENERATED RECAP")
print(f"{'='*60}\n")
print(recap)
EOF
```

## Configuration

### API URL

Default: `http://localhost:8000`

Change it:

```python
generator = RecapGenerator(api_url="http://your-server:8000")
```

Or via environment variable:

```bash
export API_BASE_URL="http://your-server:8000"
python3 recap_generator.py 7
```

### Output Directory

Default: `output/`

Recaps saved as: `output/week-{N}-recap.md`

### History File

Location: `recap_history.json` (in project root)

Contains:

- Week number
- Generated recap
- Date created
- API data used

**Note:** This file is gitignored to keep your recaps private

## Customizing the Columnist

Edit `COLUMNIST_PROMPT.md` to adjust:

### Make it Meaner

Change ratio: `90% lowlights / 10% highlights`

### Make it Nicer

Change ratio: `70% lowlights / 30% highlights`

### Different Voice

Update the persona section:

```markdown
**Voice:** [Your desired style - e.g., "snarky British commentator"]
```

### Add Running Gags

Add to the "League Lore" section (create if needed):

```markdown
## League-Specific Lore

- Manager X always benches his studs
- The "Curse of Week 3" (3 years running!)
- Manager Y's infamous trade that shall not be named
```

### Industry-Specific Jargon

If your league has inside jokes (tech workers, finance bros, etc.):

```markdown
## Custom Jargon

- [Your industry terms and how to weaponize them]
```

## Troubleshooting

### "Failed to fetch data"

❌ **Problem:** API isn't running or wrong URL

✅ **Solution:**

```bash
# Check if API is running
curl http://localhost:8000/health

# If not, start it
python3 api.py &
```

### "No module named 'openai'"

❌ **Problem:** OpenAI package not installed

✅ **Solution:**

```bash
pip install openai
```

### "Recap is too generic"

❌ **Problem:** Not enough specific data

✅ **Solution:** The script automatically includes:

- Specific player names
- Actual vs projected points
- Bench point totals
- Win/loss margins

If still generic, the LLM might need more context. Try a better model (GPT-4 vs GPT-3.5)

### "Same roasts every week"

❌ **Problem:** Memory system not working

✅ **Check:** Does `recap_history.json` exist and contain previous recaps?

✅ **Solution:** The script automatically loads previous recaps. If it's still repetitive:

1. Increase memory context (edit `get_previous_recaps_context` limit)
2. Add explicit "DO NOT repeat these patterns" in prompt
3. Use higher temperature (0.9 instead of 0.8)

### "Too mean" or "Not safe"

❌ **Problem:** LLM crossing boundaries

✅ **Solution:** The prompt has strict safety rails, but if issues occur:

1. Add explicit examples of off-limit content to prompt
2. Use more conservative model (GPT-4 more careful than 3.5)
3. Lower temperature (0.6 instead of 0.8)

## Advanced Usage

### Batch Generate Multiple Weeks

```python
from recap_generator import RecapGenerator

generator = RecapGenerator()

for week in range(1, 8):
    print(f"\n{'='*60}")
    print(f"Generating Week {week}")
    print(f"{'='*60}")

    recap = generator.generate_recap_with_openai(
        week=week,
        client=your_openai_client
    )

    if recap:
        print(f"✅ Week {week} complete!")
```

### Custom Data Integration

```python
generator = RecapGenerator()

# Add custom league lore
custom_context = """
## League History
- 2024: Tyler won championship with worst regular season record
- Running joke: Kevin always drafts injured players
- Team names reference The Office
"""

# You can modify the context in the script or pass custom notes
```

### Export for Newsletter

```python
recap = generator.generate_recap_with_openai(week=7, client=client)

# Convert to HTML
import markdown
html = markdown.markdown(recap)

# Send via email, post to website, etc.
```

## Files Generated

```
output/
├── week-7-context.txt      # Full LLM prompt (if using --context-only)
├── week-7-recap.md         # Generated recap
├── week-7-matchups.md      # From fetch_league_data.py
├── week-7-summary.md       # From fetch_league_data.py
└── standings.md            # From fetch_league_data.py

recap_history.json          # Memory system (gitignored)
```

## Tips for Best Results

### 1. Run After All Games Complete

Wait until Tuesday when stat corrections are done.

### 2. Use GPT-4 or Claude Sonnet

Better models = funnier, more creative roasts.

### 3. Let Memory Build

First recap might be generic. By week 3-4, callbacks and running gags emerge.

### 4. Edit the Prompt

Customize `COLUMNIST_PROMPT.md` with your league's inside jokes and history.

### 5. Review Before Sharing

The AI is good but not perfect. Quick read-through ensures quality.

## Example Output Structure

```markdown
# Week 7: When Projections Go to Die

If Week 7 taught us anything, it's that "start your studs" is just
a polite way of saying "embrace chaos."

---

MATCHUP 1: New Vertical Threats 167.6 def. Maia's Monstrous Team 72.62
Subtitle: A Masterclass in Getting Absolutely Demolished

Started Russell Wilson (8.2) because apparently we're time-traveling
to 2019. Meanwhile, benched Malik Nabers who casually dropped 23.4.
That's not a lineup decision—that's performance art...

[etc.]

What they'll tell themselves: "We're optimizing our learnings for
Week 8's synergistic outcomes."

---

[More matchups...]

---

See you next week, when we discover new and creative ways to bench
our best players.
```

## Need Help?

- 📖 Read `COLUMNIST_PROMPT.md` to understand the columnist's voice
- 🔍 Check `API_README.md` for API documentation
- 💬 Open an issue with questions or suggestions

---

**Now go roast your league!** 🔥🏈
