# Quick Start Guide 🚀

Get your Fantasy Football API running in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- ESPN Fantasy Football league
- League ID (find it in your ESPN league URL)

## Step 1: Install Dependencies

```bash
cd /path/to/fantasy
pip install -r requirements.txt
```

Or use pip3 if pip isn't available:

```bash
python3 -m pip install -r requirements.txt
```

## Step 2: Create Configuration

Copy the example config:

```bash
cp config.example.json config.json
```

## Step 3: Get Your ESPN Cookies

**Only required for private leagues** (skip if your league is public)

### On Chrome/Edge:

1. Go to [ESPN Fantasy Football](https://fantasy.espn.com)
2. Log in to your account
3. Press **F12** to open Developer Tools
4. Click **Application** tab (top menu)
5. In left sidebar: **Cookies** → `https://fantasy.espn.com`
6. Find and copy:
   - `espn_s2` - Copy the entire Value (very long string)
   - `SWID` - Copy the Value (includes `{` braces `}`)

### On Firefox:

1. Go to [ESPN Fantasy Football](https://fantasy.espn.com)
2. Log in to your account
3. Press **F12** to open Developer Tools
4. Click **Storage** tab (top menu)
5. In left sidebar: **Cookies** → `https://fantasy.espn.com`
6. Find and copy the same cookies as above

### On Safari:

1. Enable Developer menu: Preferences → Advanced → Show Develop menu
2. Go to [ESPN Fantasy Football](https://fantasy.espn.com)
3. Log in
4. Develop menu → Show Web Inspector
5. Storage tab → Cookies → `fantasy.espn.com`
6. Find and copy the same cookies

## Step 4: Configure Your League

Edit `config.json`:

```json
{
  "league_id": YOUR_LEAGUE_ID_HERE,
  "year": 2025,
  "private_league": true,
  "espn_s2": "PASTE_YOUR_ESPN_S2_HERE",
  "swid": "{PASTE-YOUR-SWID-HERE}"
}
```

**Find your League ID:**

- It's in your ESPN league URL: `fantasy.espn.com/football/league?leagueId=XXXXXXXX`
- The number after `leagueId=` is your league ID

## Step 5: Start the API

```bash
python3 api.py
```

You should see:

```
🏈 Starting Fantasy Football API on port 8000...
📖 API Documentation: http://localhost:8000/docs
🔍 Interactive API: http://localhost:8000/redoc
✅ Connected to league: [Your League Name]
```

## Step 6 (Optional): Set Up AI Recap Generation

If you want to generate AI-powered roast recaps:

```bash
# Copy the environment template
cp env.example .env

# Edit .env and add your Anthropic API key
# Get your key at: https://console.anthropic.com/
# Add this line to .env:
# ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

Then you can generate recaps:

```bash
python3 example_generate_recap.py
```

## Step 6: Test It Out

Open in your browser:

- **Interactive API**: http://localhost:8000/docs
- **Get league info**: http://localhost:8000/api/league
- **See standings**: http://localhost:8000/api/standings

Or use curl:

```bash
curl http://localhost:8000/api/league
```

## Troubleshooting

### "Failed to connect to ESPN API"

❌ **Problem:** Your cookies are missing or incorrect

✅ **Solution:**

1. Make sure `private_league: true` in config.json
2. Re-copy your ESPN cookies (they might have expired)
3. Make sure SWID includes the `{` braces `}`

### "Address already in use"

❌ **Problem:** Port 8000 is already in use

✅ **Solution:**

```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Start again
python3 api.py
```

### "Module not found"

❌ **Problem:** Dependencies not installed

✅ **Solution:**

```bash
python3 -m pip install -r requirements.txt
```

### Can't start the server

❌ **Problem:** Server won't run in foreground

✅ **Solution:** Run in background:

```bash
nohup python3 api.py > api.log 2>&1 &
```

## Next Steps

- 📖 Read the full [README.md](README.md)
- 🔍 Explore the [API Documentation](API_README.md)
- 🌐 Try the interactive docs at http://localhost:8000/docs
- 📝 Generate markdown reports: `python3 fetch_league_data.py`

## Common API Endpoints

```bash
# League information
curl http://localhost:8000/api/league

# Current standings
curl http://localhost:8000/api/standings

# All teams
curl http://localhost:8000/api/teams

# Current week matchups (week auto-detected!)
curl http://localhost:8000/api/matchups/7

# Week statistics
curl http://localhost:8000/api/stats/week/7

# Specific team details
curl http://localhost:8000/api/teams/1
```

## Need Help?

- Check [API_README.md](API_README.md) for detailed API documentation
- View [README.md](README.md) for full project documentation
- Open an issue on GitHub

---

**Happy Fantasy Football tracking!** 🏈🔥
