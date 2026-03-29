# ESPN Fantasy Football Recap Generator

AI-powered weekly recap generator for ESPN Fantasy Football leagues with a hilarious roast columnist persona.

## Features

- **Weekly Recaps**: Generate entertaining weekly recaps using Claude Opus 4.5 or GPT-4o
- **Power Rankings**: Advanced opponent-adjusted scoring (adjPF) with season-phase weighting
- **Slack Integration**: Automatically post recaps to Slack
- **Web UI**: Modern dashboard for viewing stats, matchups, and generating recaps
- **REST API**: Full-featured API for league data and analytics

## Quick Start

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy and configure environment
cp config/env.example .env
# Edit .env with your ESPN credentials and API keys
```

### Configuration

See `config/config.example.json` for league configuration.

### Running the Server

```bash
# Start the API server
npm run dev

# Check status
npm run status

# View logs
npm run logs:api

# Stop the server
npm run stop
```

### Generating Recaps

Visit http://localhost:8000 for the web UI, or use the API:

```bash
curl -X POST http://localhost:8000/api/recaps/generate \
  -H "Content-Type: application/json" \
  -d '{"week": 6, "model_provider": "claude-opus-4.5"}'
```

## Documentation

See the `docs/` directory for detailed documentation:
- `QUICKSTART.md` - Getting started guide
- `API_README.md` - API documentation
- `SLACK_INTEGRATION.md` - Slack setup
- `WEB_UI_GUIDE.md` - Web UI guide

## Project Structure

```
football-recap/
├── src/           # Core application code
├── scripts/       # Utility scripts
├── static/        # Web UI assets
├── docs/          # Documentation
└── config/        # Configuration examples
```
