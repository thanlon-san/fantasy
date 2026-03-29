# Fantasy Baseball API

FastAPI service that powers the baseball dashboard with live data from your Python tools.

## Features

- 🎯 **Daily Lineup API** - Real-time lineup recommendations
- ⭐ **Keeper Analysis API** - Top keeper candidates with value analysis
- 🔬 **Breakout Detection API** - Statcast-powered breakout alerts (coming soon)
- 🎯 **Waiver Wire API** - Smart pickup recommendations (coming soon)

## Local Development

### Prerequisites
- Python 3.10+
- Virtual environment

### Setup

```bash
# From project root
cd apps/baseball-api

# Create virtual environment (if not exists)
python3 -m venv ../../.venv
source ../../.venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API
python main.py

# API will be available at http://localhost:8000
```

### Test the API

```bash
# Health check
curl http://localhost:8000/

# Get daily lineup
curl http://localhost:8000/api/lineup

# Get keeper recommendations
curl http://localhost:8000/api/keepers
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Deployment

### Railway (Recommended - Free Tier)

1. **Sign up for Railway**
   - Go to https://railway.app
   - Sign in with GitHub

2. **Deploy from GitHub**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select this repository
   - Set root directory: `apps/baseball-api`
   - Railway auto-detects Python and uses `railway.json` config

3. **Get your API URL**
   - Railway provides: `https://your-app.railway.app`
   - Copy this URL for dashboard configuration

4. **Update Dashboard**
   ```bash
   cd apps/baseball-dashboard
   
   # Create .env.local
   echo "NEXT_PUBLIC_USE_API=true" > .env.local
   echo "NEXT_PUBLIC_API_URL=https://your-app.railway.app" >> .env.local
   ```

### Alternative: Render.com (Free Tier with Sleep)

1. Sign up at https://render.com
2. Create new "Web Service"
3. Connect GitHub repo
4. Configure:
   - Root directory: `apps/baseball-api`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Note: Free tier sleeps after 15min inactivity (first request takes ~30s to wake up)

## Environment Variables

None required for basic operation. The API reads roster data from:
- `../baseball-engine/data/my_roster_from_yahoo.csv`

For future Yahoo API integration, you'll need:
- `YAHOO_CLIENT_ID`
- `YAHOO_CLIENT_SECRET`
- `YAHOO_ACCESS_TOKEN`
- `YAHOO_REFRESH_TOKEN`

## API Endpoints

### `GET /`
Health check and service status

### `GET /api/lineup`
Daily lineup recommendations
- Returns: Must start, start, flex, bench, and not playing tiers
- Includes confidence scores and matchup details

### `GET /api/keepers`
Keeper value analysis
- Returns: Top 3 keeper recommendations with surplus value

### `GET /api/waivers`
Waiver wire recommendations (placeholder - needs Yahoo API)

### `GET /api/breakouts`
Breakout candidate detection (placeholder - needs free agent data)

## Architecture

```
apps/baseball-api/
├── main.py              # FastAPI app and endpoints
├── requirements.txt     # Python dependencies
├── railway.json         # Railway deployment config
└── README.md           # This file

Uses shared code from:
└── apps/baseball-engine/src/   # All your Python tools
```

## Performance

- **Cold start**: ~2-3 seconds (Railway)
- **Warm requests**: ~200-500ms
- **Memory**: ~150MB
- **Cost**: Free on Railway ($5/month credit, uses ~$0.50/month)

## Troubleshooting

### "Module not found" errors
Make sure you're running from the project root and the venv is activated:
```bash
cd /path/to/fantasy
source .venv/bin/activate
cd apps/baseball-api
python main.py
```

### CORS errors
Check that the dashboard URL is allowed in `main.py`:
```python
allow_origins=["*"]  # Change to your domain in production
```

### Slow responses
- First request after sleep: Normal (Railway doesn't sleep on free tier)
- Every request slow: Check Railway logs for errors

## Next Steps

1. ✅ Deploy to Railway
2. ⬜ Add Yahoo API integration for live waiver/breakout scanning
3. ⬜ Add caching layer (Redis) for faster responses
4. ⬜ Add authentication for private leagues
