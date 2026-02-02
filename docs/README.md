# Fantasy Sports Applications

A monorepo of AI-powered fantasy sports applications and tools.

## Applications

### 🏈 [ESPN Fantasy Recap](./apps/espn-fantasy-recap/)
AI-generated weekly recaps for ESPN Fantasy Football leagues with a hilarious roast columnist persona.

**Status**: ✅ Production Ready

**Features**:
- Weekly AI-generated recaps (Claude Opus 4.5 / GPT-4o)
- Advanced power rankings with opponent-adjusted scoring
- Slack integration
- Web UI dashboard
- REST API

[View Documentation →](./apps/espn-fantasy-recap/README.md)

### ⚾ [Baseball Keeper Advisor](./apps/keeper-advisor/)
AI-powered decision support for baseball keeper league management.

**Status**: 🚧 In Development

**Features** (Planned):
- Yahoo Fantasy API integration
- Keeper cost calculator
- AI-powered keeper recommendations
- Trade value analysis
- Draft strategy advisor

[View Documentation →](./apps/keeper-advisor/README.md)

## Shared Packages

### 📦 [Shared Utilities](./packages/shared/)
Common utilities used across all fantasy applications:
- LLM clients (OpenAI, Anthropic)
- Slack notifications
- Logging configuration

## Quick Start

### ESPN Fantasy Recap

```bash
# Install dependencies
cd apps/espn-fantasy-recap
pip install -r requirements.txt

# Configure your league
cp config/env.example .env
# Edit .env with your credentials

# Start the server
npm run dev
```

Visit http://localhost:8000 to access the web UI.

### Keeper Advisor

```bash
# Install dependencies
cd apps/keeper-advisor
pip install -r requirements.txt

# Run analysis
npm run analyze
```

## Project Structure

```
fantasy/
├── apps/                      # Applications
│   ├── espn-fantasy-recap/   # ESPN weekly recap generator
│   └── keeper-advisor/        # Baseball keeper advisor
│
├── packages/                  # Shared utilities
│   └── shared/               # Common LLM, Slack, logging utils
│
├── docs/                      # Workspace documentation
├── package.json              # Workspace root
└── pnpm-workspace.yaml       # pnpm workspace config
```

## Development

### Workspace Commands

```bash
# ESPN Recap
npm run espn:dev       # Start ESPN recap server
npm run espn:status    # Check server status
npm run espn:stop      # Stop server

# Keeper Advisor
npm run keeper:analyze # Run keeper analysis
```

### Adding a New Application

1. Create new directory in `apps/`
2. Add `package.json` with name `@fantasy/your-app`
3. Create `requirements.txt` with dependencies
4. Import shared utilities: `from shared.llm_client import LLMClient`

### Using Shared Utilities

```python
# In any app, import from shared package
from shared.llm_client import LLMClient
from shared.slack_notifier import SlackNotifier
from shared.logger import get_logger

# Use shared utilities
logger = get_logger(__name__)
client = LLMClient()
```

## Requirements

- Python 3.8+
- Node.js 18+ (for npm scripts)
- pnpm (recommended) or npm

## License

MIT

---

**Questions?** Check the individual app READMEs or open an issue.
