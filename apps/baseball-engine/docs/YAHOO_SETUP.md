# Yahoo Fantasy API Setup Guide

Complete guide to connecting the Keeper Advisor to your Yahoo Fantasy Baseball league.

## Quick Start

```bash
cd apps/keeper-advisor
npm run setup:yahoo
```

Follow the interactive prompts to set up Yahoo API access.

## Detailed Setup Instructions

### Step 1: Create a Yahoo Developer App

1. **Go to Yahoo Developer Portal**
   - Visit: https://developer.yahoo.com/apps/create/
   - Sign in with your Yahoo account (the one you use for fantasy)

2. **Create a New App**
   - Click "Create an App" button
   - Fill out the form:
     ```
     Application Name: Fantasy Keeper Advisor
     Application Type: Installed Application
     Description: Keeper decision tool for fantasy baseball
     Home Page URL: (leave blank)
     Redirect URI(s): oob
     API Permissions: Fantasy Sports (Read)
     ```
   
3. **Get Your Credentials**
   - After creating the app, you'll see:
     - **Consumer Key** (also called Client ID)
     - **Consumer Secret** (also called Client Secret)
   - Copy both of these - you'll need them next

### Step 2: Configure OAuth Credentials

Create a file at `config/oauth2.json`:

```json
{
  "consumer_key": "your_consumer_key_here",
  "consumer_secret": "your_consumer_secret_here"
}
```

**Or use the setup script:**
```bash
npm run setup:yahoo
```

### Step 3: First-Time Authentication

The first time you connect, you'll need to authorize the app:

1. Run the setup script
2. A browser window will open (or you'll get a URL)
3. Log in to Yahoo and click "Agree" to authorize
4. You'll get a verification code
5. Paste the code back into the terminal

**This only needs to be done once!** The token is saved for future use.

### Step 4: Import Your Roster

After authentication, the script will:
1. Show your Yahoo Fantasy Baseball leagues
2. Let you select which league to import
3. Fetch your current roster
4. Export it to `data/my_roster_from_yahoo.csv`

### Step 5: Add Draft Information

**Important:** Yahoo API doesn't provide historical draft data, so you need to add it manually.

Open `data/my_roster_from_yahoo.csv` and fill in for each player:
- **draft_round** - What round you drafted them (1-12, or 13+ for FA)
- **draft_year** - What year you drafted them
- **years_kept** - How many times you've kept them already (0 for first time)
- **adp** - (Optional) Their current Average Draft Position

Example:
```csv
name,position,team,draft_round,draft_year,years_kept,adp,notes
Bobby Witt Jr.,SS,KC,1,2025,0,3.1,Drafted 1st round pick 2
Aaron Judge,OF,NYY,3,2025,0,5.2,Drafted round 3
Corbin Carroll,OF,ARI,18,2024,1,12.3,Waiver pickup - kept once
```

### Step 6: Analyze!

```bash
npm run analyze:csv
```

## Finding Player ADP Data

For the best value analysis, add ADP (Average Draft Position) data:

**ADP Resources:**
- [FantasyPros ADP](https://www.fantasypros.com/mlb/adp/overall.php)
- [NFBC ADP](https://nfc.shgn.com/adp/baseball)
- Your league's mock draft results

ADP helps the analyzer calculate keeper value - how much you're "saving" by keeping a player vs. drafting them.

## Troubleshooting

### "Invalid Consumer Key/Secret"
- Double-check you copied them correctly from Yahoo Developer Portal
- Make sure there are no extra spaces
- Verify the app is set to "Installed Application" type

### "Authorization Failed"
- Make sure you're logged into Yahoo with the correct account
- Try clearing your browser cookies for yahoo.com
- Make sure the Redirect URI is set to "oob"

### "No Leagues Found"
- Check you're using the correct year (2026 for current season)
- Make sure you have a Fantasy Baseball league for that year
- Try `client.get_leagues(year=2025, sport="mlb")` for last year

### "Token Expired"
- Delete the token file (usually in your home directory)
- Run the setup again to re-authenticate
- The new token will be saved automatically

### Can't Find Draft History
- Yahoo API doesn't provide draft history easily
- You need to look at your draft results from the Yahoo website
- Check "League" → "Draft Recap" in Yahoo Fantasy
- Or check your league's historical draft boards

## Advanced: Using the API Directly

If you want to fetch data programmatically:

```python
from src.yahoo_client import YahooFantasyClient

# Initialize client
client = YahooFantasyClient("config/oauth2.json")
client.authenticate()

# Get your leagues
leagues = client.get_leagues(year=2026, sport="mlb")
for league in leagues:
    print(f"{league['name']} - {league['league_id']}")

# Connect to a specific league
client.connect_to_league("YOUR_LEAGUE_ID")

# Get your roster
roster_data = client.get_roster()
for player in roster_data:
    print(f"{player['name']} - {player['position']} - {player['team']}")
```

## Security Notes

- **Never commit `config/oauth2.json` to git** - it's in `.gitignore`
- **Keep your Consumer Secret private** - don't share it
- **Token file** is stored in your home directory - keep it secure
- If you think your credentials are compromised, regenerate them in Yahoo Developer Portal

## Next Steps

Once setup is complete:
1. ✅ Your roster is imported
2. ✅ Draft information is added
3. ✅ Ready to analyze keepers!

Run:
```bash
npm run analyze:csv        # Basic analysis
npm run analyze:csv --ai   # With AI recommendations
```

## Need Help?

- Check Yahoo Developer documentation: https://developer.yahoo.com/fantasysports/guide/
- Yahoo Fantasy API docs: https://yahoo-fantasy-api.readthedocs.io/
- Open an issue if you're stuck!
