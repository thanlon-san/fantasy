# Fantasy Football API Documentation

🏈 **Your Fantasy Football API is now running!**

## 🚀 Server Status

✅ API is running on: **http://localhost:8000**

- 📖 Interactive API Docs: http://localhost:8000/docs
- 🔍 Alternative Docs: http://localhost:8000/redoc
- ❤️ Health Check: http://localhost:8000/health

## 🔐 Authentication Setup (Required for Private Leagues)

Your league appears to be private and requires ESPN authentication. To fix the "Failed to connect to ESPN API" error:

### Step 1: Get Your ESPN Cookies

1. Open your browser and go to [ESPN Fantasy Football](https://fantasy.espn.com)
2. Log in to your account
3. Open Developer Tools (Press **F12** or **Right-click → Inspect**)
4. Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)
5. Navigate to **Cookies** → `https://fantasy.espn.com`
6. Find and copy these two cookie values:
   - `espn_s2` (long string, starts with something like "AEB...")
   - `SWID` (format: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`)

### Step 2: Update config.json

Open `/Users/tyler.hanlon/Documents/GitHub/fantasy/config.json` and update:

```json
{
  "league_id": 228124044,
  "year": 2024,
  "current_week": 6,
  "private_league": true,
  "espn_s2": "YOUR_ESPN_S2_COOKIE_HERE",
  "swid": "{YOUR-SWID-HERE}",
  ...
}
```

### Step 3: Restart the API

After updating the config, restart the API:

```bash
# Find and kill the current process
pkill -f "python3 api.py"

# Start the API again
cd /Users/tyler.hanlon/Documents/GitHub/fantasy
python3 api.py
```

## 📚 Available Endpoints

### Base Endpoints

#### `GET /`

Returns API information and list of available endpoints.

**Example:**

```bash
curl http://localhost:8000/
```

#### `GET /health`

Health check endpoint.

**Example:**

```bash
curl http://localhost:8000/health
```

### League Endpoints

#### `GET /api/league`

Get basic league information.

**Response:**

```json
{
  "league_id": 228124044,
  "year": 2024,
  "league_name": "Your League Name",
  "current_week": 6,
  "total_teams": 12
}
```

**Example:**

```bash
curl http://localhost:8000/api/league
```

#### `GET /api/standings`

Get current league standings with statistical leaders.

**Response:**

```json
{
  "standings": [
    {
      "rank": 1,
      "team_id": 1,
      "team_name": "Team Name",
      "owner": "Owner",
      "wins": 5,
      "losses": 1,
      "ties": 0,
      "win_pct": 0.833,
      "points_for": 725.5,
      "points_against": 650.2,
      "point_differential": 75.3,
      "streak": "W3"
    }
  ],
  "leaders": {
    "most_points": {...},
    "fewest_points_against": {...},
    "best_differential": {...}
  }
}
```

**Example:**

```bash
curl http://localhost:8000/api/standings
```

### Matchup Endpoints

#### `GET /api/matchups/{week}`

Get all matchups for a specific week with full lineup details.

**Parameters:**

- `week` (path): Week number (1-18)

**Response:**

```json
{
  "week": 6,
  "total_matchups": 6,
  "matchups": [
    {
      "matchup_id": 1,
      "home_team": {
        "team_id": 1,
        "team_name": "Team A",
        "score": 125.5,
        "record": "5-1-0",
        "starters": [...],
        "bench": [...]
      },
      "away_team": {
        "team_id": 2,
        "team_name": "Team B",
        "score": 110.2,
        "record": "3-3-0",
        "starters": [...],
        "bench": [...]
      },
      "winner": "Team A",
      "margin": 15.3
    }
  ]
}
```

**Example:**

```bash
curl http://localhost:8000/api/matchups/6
```

### Statistics Endpoints

#### `GET /api/stats/week/{week}`

Get statistical analysis for a specific week (highest/lowest scores, blowouts, etc.).

**Parameters:**

- `week` (path): Week number (1-18)

**Response:**

```json
{
  "week": 6,
  "highest_score": {
    "team": "Team Name",
    "points": 167.6
  },
  "lowest_score": {
    "team": "Team Name",
    "points": 52.9
  },
  "biggest_blowout": {
    "winner": "Winner",
    "loser": "Loser",
    "margin": 94.98
  },
  "closest_game": {
    "team1": "Team A",
    "team2": "Team B",
    "margin": 3.3
  },
  "most_bench_points": {
    "team": "Team Name",
    "points": 76.1
  }
}
```

**Example:**

```bash
curl http://localhost:8000/api/stats/week/6
```

### Team Endpoints

#### `GET /api/teams`

Get list of all teams in the league.

**Response:**

```json
{
  "total_teams": 12,
  "teams": [
    {
      "team_id": 1,
      "team_name": "Team Name",
      "owner": "Owner",
      "wins": 5,
      "losses": 1,
      "ties": 0,
      "points_for": 725.5,
      "points_against": 650.2
    }
  ]
}
```

**Example:**

```bash
curl http://localhost:8000/api/teams
```

#### `GET /api/teams/{team_id}`

Get detailed information about a specific team including full roster.

**Parameters:**

- `team_id` (path): Team ID

**Response:**

```json
{
  "team_id": 1,
  "team_name": "Team Name",
  "owner": "Owner",
  "record": {
    "wins": 5,
    "losses": 1,
    "ties": 0
  },
  "points": {
    "for": 725.5,
    "against": 650.2,
    "differential": 75.3
  },
  "streak": {
    "type": "W",
    "length": 3
  },
  "roster": [
    {
      "name": "Player Name",
      "position": "QB",
      "pro_team": "KC",
      "projected_total": 250.5,
      "total_points": 265.3
    }
  ]
}
```

**Example:**

```bash
curl http://localhost:8000/api/teams/1
```

## 🧪 Testing the API

### Using curl

```bash
# Test root endpoint
curl http://localhost:8000/

# Get league info
curl http://localhost:8000/api/league | jq

# Get standings
curl http://localhost:8000/api/standings | jq

# Get week 6 matchups
curl http://localhost:8000/api/matchups/6 | jq

# Get week 6 stats
curl http://localhost:8000/api/stats/week/6 | jq

# Get all teams
curl http://localhost:8000/api/teams | jq

# Get specific team (replace 1 with actual team_id)
curl http://localhost:8000/api/teams/1 | jq
```

### Using Python

```python
import requests

# Get league info
response = requests.get('http://localhost:8000/api/league')
print(response.json())

# Get standings
response = requests.get('http://localhost:8000/api/standings')
standings = response.json()
print(f"Top team: {standings['standings'][0]['team_name']}")

# Get matchups for week 6
response = requests.get('http://localhost:8000/api/matchups/6')
matchups = response.json()
for matchup in matchups['matchups']:
    print(f"{matchup['home_team']['team_name']} vs {matchup['away_team']['team_name']}")
```

### Using JavaScript/Fetch

```javascript
// Get league info
fetch("http://localhost:8000/api/league")
  .then((response) => response.json())
  .then((data) => console.log(data));

// Get standings
fetch("http://localhost:8000/api/standings")
  .then((response) => response.json())
  .then((data) => {
    console.log("Standings:", data.standings);
  });
```

## 🛠️ Management Commands

### Start the API

```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy
python3 api.py
```

### Stop the API

```bash
pkill -f "python3 api.py"
```

### Check if API is running

```bash
curl http://localhost:8000/health
```

### View API logs (if running in foreground)

The API will print logs directly to the terminal.

## 🔧 Configuration

Edit `config.json` to customize:

```json
{
  "league_id": 228124044, // Your ESPN league ID
  "year": 2024, // Season year
  "current_week": 6, // Current week (for reference)
  "private_league": false, // Set to true if private
  "espn_s2": "", // ESPN auth cookie
  "swid": "", // ESPN auth cookie
  "output_directory": "output" // For markdown outputs
}
```

## 🌐 CORS

CORS is enabled for all origins, allowing you to call this API from any frontend application.

## 📝 Notes

- The API uses your existing `fetch_league_data.py` module
- All endpoints return JSON
- Error responses include a `detail` field with error information
- The API caches the league connection for performance
- Player stats are pulled directly from ESPN's API

## 🐛 Troubleshooting

### "Failed to connect to ESPN API"

→ Add your ESPN authentication cookies to `config.json` (see Authentication Setup above)

### "Connection refused"

→ Make sure the API is running: `python3 api.py`

### Port 8000 already in use

→ Stop the existing process or set a different port:

```bash
PORT=8080 python3 api.py
```

## 🚀 Next Steps

1. Set up your ESPN authentication cookies
2. Explore the interactive API docs at http://localhost:8000/docs
3. Build a frontend dashboard to visualize the data
4. Add custom endpoints for your specific needs
5. Deploy to a server for remote access

---

**Happy Fantasy Football tracking! 🏈🔥**
