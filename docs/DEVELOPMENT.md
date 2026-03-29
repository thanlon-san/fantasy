# Development Guide

Complete guide for local development of Fantasy Sports Hub.

---

## 🔧 Prerequisites

- **Node.js**: 18+ 
- **pnpm**: 8+ (`npm install -g pnpm`)
- **Python**: 3.10+
- **Git**: Latest version

---

## 📦 Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/thanlon-san/fantasy.git
cd fantasy
```

### 2. Install Dependencies

#### JavaScript/TypeScript
```bash
# Install all workspace dependencies
pnpm install
```

#### Python
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## 🚀 Running Apps Locally

### Baseball Dashboard (Next.js)

```bash
# Development mode
pnpm dev:baseball

# Opens at http://localhost:3001
```

Features:
- Hot reload enabled
- TypeScript checking
- Tailwind CSS with JIT

### Fantasy Hub (Landing Page)

```bash
# Development mode
pnpm dev:hub

# Opens at http://localhost:3000
```

### Baseball API (FastAPI)

```bash
cd apps/baseball-api

# Make sure venv is activated
source ../../.venv/bin/activate

# Run the API
python main.py

# Opens at http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Football Recap (Python)

```bash
cd apps/football-recap

# Start the server
pnpm dev

# Check status
pnpm status

# View logs
pnpm logs:api

# Stop the server
pnpm stop
```

Access at http://localhost:8000

### Baseball Engine (Python CLI)

```bash
cd apps/baseball-engine

# Make sure venv is activated
source ../../.venv/bin/activate

# Daily lineup optimizer
pnpm lineup

# Waiver wire scanner
pnpm waivers

# Breakout detector
pnpm breakouts

# Keeper analysis
pnpm analyze
```

---

## 🔑 Environment Variables

### Baseball Dashboard

Create `apps/baseball-dashboard/.env.local`:
```bash
# Use local API
NEXT_PUBLIC_USE_API=true
NEXT_PUBLIC_API_URL=http://localhost:8000

# Or use static JSON (default)
NEXT_PUBLIC_USE_API=false
```

### Football Recap

Create `apps/football-recap/.env`:
```bash
# ESPN credentials
ESPN_S2=your_espn_s2_cookie
ESPN_SWID=your_espn_swid

# AI API keys
ANTHROPIC_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key

# Slack integration (optional)
SLACK_WEBHOOK_URL=your_slack_webhook_url

# League configuration
LEAGUE_ID=your_league_id
SEASON=2024
```

### Baseball Engine (Yahoo Integration)

Create `.env` in project root:
```bash
# Yahoo API credentials
YAHOO_CLIENT_ID=your_yahoo_client_id
YAHOO_CLIENT_SECRET=your_yahoo_client_secret
YAHOO_ACCESS_TOKEN=your_access_token
YAHOO_REFRESH_TOKEN=your_refresh_token
```

---

## 🏗️ Project Structure

```
fantasy/
├── apps/
│   ├── baseball-dashboard/      # Next.js dashboard
│   │   ├── app/                 # App router pages
│   │   ├── components/          # React components
│   │   ├── lib/                 # Utilities
│   │   └── public/              # Static assets + JSON data
│   │
│   ├── fantasy-hub/             # Landing page
│   │   ├── app/                 # App router
│   │   └── public/              # Assets
│   │
│   ├── baseball-engine/         # Python analytics
│   │   ├── src/                 # Core modules
│   │   ├── scripts/             # CLI tools
│   │   ├── data/                # CSV data files
│   │   └── config/              # Configuration
│   │
│   ├── baseball-api/            # FastAPI backend
│   │   ├── main.py              # API endpoints
│   │   └── requirements.txt     # Dependencies
│   │
│   └── football-recap/          # ESPN recap generator
│       ├── src/                 # Core application
│       ├── scripts/             # Utilities
│       ├── static/              # Web UI assets
│       └── config/              # Configuration
│
├── packages/
│   └── shared/                  # Shared Python utilities
│       ├── llm_client.py        # LLM integrations
│       ├── logger.py            # Logging utilities
│       └── slack_notifier.py    # Slack integration
│
├── docs/                        # Documentation
├── .github/workflows/           # CI/CD
└── .venv/                       # Python virtual environment
```

---

## 🔨 Common Development Tasks

### Build All Apps

```bash
# Build all apps
pnpm build

# Build specific apps
pnpm build:baseball
pnpm build:hub
```

### Linting & Type Checking

```bash
# Lint all apps
pnpm lint

# Fix lint errors
pnpm lint:fix

# Type check all apps
pnpm typecheck
```

### Clean & Rebuild

```bash
# Clean all build artifacts and dependencies
pnpm clean

# Full rebuild
pnpm clean && pnpm install && pnpm build
```

### Test Full Build Locally

```bash
# Simulates CI/CD pipeline
pnpm test:build
```

---

## 🐛 Debugging

### Next.js Apps

1. **Check browser console** (F12) for errors
2. **Check terminal** for build errors
3. **Clear `.next` cache**: `rm -rf apps/baseball-dashboard/.next`
4. **Reinstall deps**: `rm -rf node_modules && pnpm install`

### Python Apps

1. **Check virtual environment**: `which python` should show `.venv`
2. **Reinstall deps**: `pip install -r requirements.txt`
3. **Check logs**: Most apps write to `logs/` directory
4. **Enable debug mode**: Set `LOG_LEVEL=DEBUG` in `.env`

### API Issues

**Baseball API not responding:**
```bash
# Check if it's running
curl http://localhost:8000/

# Check for port conflicts
lsof -i :8000

# Restart with fresh data
cd apps/baseball-api
python main.py
```

**Football Recap API:**
```bash
# Check server status
cd apps/football-recap
pnpm status

# View real-time logs
pnpm logs:api

# Restart server
pnpm restart
```

---

## 📊 Working with Data

### Export Dashboard Data

```bash
cd apps/baseball-engine

# Export all data to JSON
python scripts/export_dashboard_data.py

# Files are created in:
# - apps/baseball-dashboard/public/api/*.json
# - apps/baseball-engine/data/dashboard/*.json
```

### Update ADP Data

```bash
cd apps/baseball-engine

# Auto-update ADP from FantasyPros
pnpm update:adp
```

### Fetch Yahoo Roster

```bash
cd apps/baseball-engine

# Setup Yahoo OAuth (first time)
pnpm setup:yahoo

# Fetch your roster
pnpm fetch:roster
```

---

## 🧪 Testing

### Manual Testing Checklist

**Baseball Dashboard:**
- [ ] Homepage loads
- [ ] Daily lineup displays correctly
- [ ] Waiver wire loads
- [ ] Breakouts table shows data
- [ ] Keeper analysis displays
- [ ] Mobile responsive

**Baseball API:**
- [ ] Health check: `curl http://localhost:8000/`
- [ ] Lineup endpoint: `curl http://localhost:8000/api/lineup`
- [ ] Keepers endpoint: `curl http://localhost:8000/api/keepers`
- [ ] API docs load: http://localhost:8000/docs

**ESPN Recap:**
- [ ] Web UI loads
- [ ] Can generate recap
- [ ] Stats display correctly
- [ ] Power rankings work

---

## 🔄 Git Workflow

### Before Committing

```bash
# Check what changed
git status

# Review changes
git diff

# Lint & type check
pnpm lint
pnpm typecheck

# Build test
pnpm build:local
```

### Committing Changes

```bash
# Add files
git add .

# Commit with descriptive message
git commit -m "feat: add new feature"

# Push to GitHub
git push origin main
```

### Commit Message Conventions

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks

---

## 📚 Additional Resources

### Documentation
- [Deployment Guide](./DEPLOYMENT.md)
- [Baseball Dashboard Docs](./apps/baseball-dashboard.md)
- [Baseball Engine Docs](./apps/baseball-engine.md)
- [ESPN Recap Docs](./apps/espn-recap.md)

### API References
- [Next.js Docs](https://nextjs.org/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [pnpm Docs](https://pnpm.io/)
- [Tailwind CSS](https://tailwindcss.com/docs)

### External APIs
- [Yahoo Fantasy API](https://developer.yahoo.com/fantasysports/)
- [ESPN Fantasy API](https://github.com/cwendt94/espn-api)
- [MLB Stats API](https://statsapi.mlb.com/)
- [Baseball Savant](https://baseballsavant.mlb.com/)

---

## 💡 Tips & Best Practices

1. **Always activate venv** before running Python commands
2. **Use pnpm** instead of npm for consistency
3. **Test builds locally** before pushing to GitHub
4. **Keep dependencies updated** regularly
5. **Document new features** as you add them
6. **Check logs** when debugging issues
7. **Clear caches** when things act weird
8. **Use TypeScript** for new code
9. **Follow existing code style**
10. **Have fun!** 🎉

---

## 🆘 Getting Help

- **Check logs** in `logs/` directory
- **Review GitHub Actions** for deployment issues
- **Search documentation** in `docs/` folder
- **Check app-specific READMEs** in each app directory

Happy coding! 🚀
