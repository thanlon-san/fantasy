# Fantasy Sports Hub

Modern monorepo for fantasy sports tools and dashboards.

## 🎯 Apps

### [Baseball Dashboard](./apps/baseball-dashboard/)
Modern web interface for keeper league analysis, daily lineups, waiver wire, and breakout detection.
- **Live**: https://thanlon-san.github.io/fantasy/baseball/
- **Tech**: Next.js 15, React 19, Tailwind CSS

### [Keeper Advisor](./apps/keeper-advisor/)
Python-powered analytics tools for fantasy baseball keeper leagues.
- Daily lineup optimization
- Keeper value analysis
- Breakout player detection
- Waiver wire recommendations

### [ESPN Fantasy Recap](./apps/espn-fantasy-recap/)
AI-powered weekly recap generator for ESPN Fantasy Football.
- Claude/GPT-powered recaps
- Power rankings with advanced metrics
- Slack integration
- REST API + Web UI

### [Keeper API](./apps/keeper-api/)
FastAPI service that powers the baseball dashboard with live data.
- Daily lineup API
- Keeper analysis API
- Deployed on Railway

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ / pnpm 8+
- Python 3.10+

### Install Dependencies
```bash
# Install all workspace dependencies
pnpm install

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Development

```bash
# Run baseball dashboard
pnpm dev:baseball    # http://localhost:3001

# Run keeper advisor tools
cd apps/keeper-advisor
pnpm lineup          # Daily lineup optimizer
pnpm waivers         # Waiver wire scanner
pnpm breakouts       # Breakout detector

# Run ESPN recap server
cd apps/espn-fantasy-recap
pnpm dev            # http://localhost:8000
```

### Build & Deploy

```bash
# Build all apps
pnpm build

# Build specific apps
pnpm build:baseball
pnpm build:hub

# Test build locally
pnpm test:build
```

## 📚 Documentation

- [Deployment Guide](./docs/DEPLOYMENT.md) - GitHub Pages, Railway, Vercel
- [Development Setup](./docs/DEVELOPMENT.md) - Local environment setup
- [App-Specific Docs](./docs/apps/) - Per-app documentation

## 🏗️ Project Structure

```
fantasy/
├── apps/
│   ├── baseball-dashboard/    # Next.js dashboard
│   ├── fantasy-hub/           # Landing page
│   ├── keeper-advisor/        # Python analytics
│   ├── keeper-api/            # FastAPI backend
│   └── espn-fantasy-recap/    # ESPN recap generator
├── packages/
│   └── shared/                # Shared Python utilities
├── docs/                      # Documentation
└── .github/workflows/         # CI/CD automation
```

## 🔑 Environment Setup

### Baseball Dashboard + API
```bash
# apps/baseball-dashboard/.env.local
NEXT_PUBLIC_USE_API=true
NEXT_PUBLIC_API_URL=https://your-api.railway.app
```

### ESPN Recap
```bash
# apps/espn-fantasy-recap/.env
ESPN_S2=your_espn_s2_cookie
ESPN_SWID=your_espn_swid
ANTHROPIC_API_KEY=your_claude_key
SLACK_WEBHOOK_URL=your_slack_webhook
```

### Keeper Advisor (Yahoo Integration)
```bash
# Root .env
YAHOO_CLIENT_ID=your_client_id
YAHOO_CLIENT_SECRET=your_client_secret
```

## 📦 Tech Stack

- **Frontend**: Next.js 15, React 19, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python 3.10+
- **AI**: Claude Opus 4.5, OpenAI GPT-4o
- **Data**: Yahoo Fantasy API, ESPN API, MLB Statcast
- **Deployment**: GitHub Pages, Railway, Vercel
- **CI/CD**: GitHub Actions

## 🤝 Contributing

This is a personal project, but feel free to fork and adapt for your own leagues!

## 📄 License

MIT License - see [LICENSE](./LICENSE)

## 🎉 Credits

Built with ❤️ for fantasy sports enthusiasts.
