# 🏈 Fantasy Football API & Roast Generator - Complete Setup

## ✅ What You Have

### 1. **Working REST API**

- Running on http://localhost:8000
- 8 endpoints all tested and functional
- Auto-connects to ESPN with your cookies
- Pulls 2025 season data automatically
- Start percentages included (may be -1 for historical weeks)

### 2. **AI Roast Columnist**

- Powered by Claude Sonnet 4.5
- Configured via `.env` file
- Memory system to avoid repeating burns
- CRM/marketing jargon as easter eggs
- Smart benching roasts (only >20% start rate players)

### 3. **Complete Documentation**

- `README.md` - Project overview
- `QUICKSTART.md` - 5-minute setup
- `API_README.md` - Full API reference
- `RECAP_USAGE.md` - How to generate recaps
- `COLUMNIST_PROMPT.md` - The brain of your columnist
- `ENV_SETUP.md` - Environment variable guide

---

## 🎨 Columnist Configuration

### Format: Short & Punchy

- **50-80 words per matchup**
- One tight paragraph per game
- No forced templates
- CRM jargon as surprise gut-punches (3-5 per recap)

### Key Features

✅ **Smart benching roasts** - Only roasts benching players with >20% ESPN start rate  
✅ **CRM jargon easter eggs** - "Churn rate," "NPS score," "conversion funnel," etc.  
✅ **Data-grounded** - Every roast cites specific stats  
✅ **Natural voice** - No repetitive "What they'll tell themselves" structure  
✅ **Memory system** - Avoids repeating previous weeks' burns  
✅ **PG-13 safe** - Funny but not cruel

### Example Output

```markdown
## New Vertical Threats 167.6 def. Maia's Monstrous Team 72.62

Started a QB who scored 6.6 and still won by 95 points because Rico Dowdle (33.9),
Drake London (31.8), and Josh Jacobs (32.0) decided violence was the answer.
Meanwhile, Maia scored 72.62 total—less than some teams leave on the bench.
Churn rate: 100% of their championship hopes.

---
```

---

## 🚀 How to Use

### Generate a Recap

```bash
# Option 1: Automated (Claude Sonnet 4.5)
python3 example_generate_recap.py

# Option 2: Get context for manual LLM use
python3 recap_generator.py 7 --context-only
# Then paste output/week-7-context.txt into Claude.ai or ChatGPT
```

### Check API Data

```bash
# League info
curl http://localhost:8000/api/league | jq

# Current standings
curl http://localhost:8000/api/standings | jq

# Week 7 matchups (with start percentages!)
curl http://localhost:8000/api/matchups/7 | jq
```

---

## 📊 Available Data

Your API provides:

- Team names, scores, records
- Player stats (projected vs actual)
- Bench points by team
- **Start percentages** (percent_started field)
- Win/loss margins
- Season standings
- All player positions and slots

---

## 🎯 Smart Roasting Rules

The columnist will:
✅ **Roast benching Caleb Williams (if >20% started)** who explodes  
❌ **Not roast benching Kayshon Boutte (<20% started)** - that's just a deep sleeper going off

This prevents unfair roasts like:

- "Left Kayshon Boutte's 26.3 on the bench" ← Nobody started him!
- Better: "Left DK Metcalf's 19.5 on the bench" ← If he's commonly started

**Note:** Start % may show -1 for historical weeks. ESPN might only provide current week data.

---

## 🔐 Security

✅ `.env` file with your API keys (never committed)  
✅ `config.json` with ESPN cookies (never committed)  
✅ `recap_history.json` (never committed)  
✅ All sensitive files in `.gitignore`

---

## 📁 Project Structure

```
fantasy/
├── api.py                    # FastAPI server (includes start %)
├── fetch_league_data.py      # ESPN data fetcher
├── recap_generator.py        # AI recap system (includes start %)
├── example_generate_recap.py # Quick test script
├── test_claude_model.py      # Test Claude connection
├── config.json               # Your ESPN config (gitignored)
├── .env                      # Your API keys (gitignored)
├── env.example               # Template for .env
├── COLUMNIST_PROMPT.md       # The brain (short format, smart roasting)
├── output/                   # Generated recaps (gitignored)
└── recap_history.json        # Memory system (gitignored)
```

---

## 🎛️ Customization

### Adjust Roast/Highlight Ratio

Edit `COLUMNIST_PROMPT.md`:

```markdown
- **85% Lowlights** / **15% Highlights** (current)
```

### Add League Inside Jokes

Add to `COLUMNIST_PROMPT.md` under "League-Specific Context"

### Change Start % Threshold

Currently >20% to be roastable. Adjust in:

- `COLUMNIST_PROMPT.md` line 61
- `COLUMNIST_PROMPT.md` line 296

### More/Less CRM Jargon

Currently 3-5 easter eggs per recap. Adjust in line 288.

---

## 💡 Tips

1. **Run after Tuesday** - Wait for stat corrections
2. **Use Claude Sonnet 4.5** - Best creative writing model
3. **Let memory build** - Gets better after 3-4 weeks
4. **Review before sharing** - AI is good but not perfect
5. **Customize the prompt** - Add your league's personality

---

## 🐛 Troubleshooting

### API won't start

```bash
lsof -ti:8000 | xargs kill -9
python3 api.py
```

### Can't generate recap

```bash
# Check .env has your key
cat .env

# Test Claude connection
python3 test_claude_model.py
```

### Start % shows -1

That's normal for historical weeks. ESPN may only provide current week data.

---

## 📈 Next Steps

**Ready to use:**

1. API is running on port 8000 ✅
2. Claude Sonnet 4.5 configured ✅
3. Start percentages integrated ✅
4. CRM jargon ready ✅
5. Smart roasting rules active ✅

**To generate your first recap:**

```bash
python3 example_generate_recap.py
```

**Your league will never be the same.** 🔥

---

_Questions? Check the docs or just run it and see what happens!_
