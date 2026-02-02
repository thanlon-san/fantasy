# 📁 Project Structure

## Overview

This document describes the organized structure of the Fantasy Football project.

```
fantasy/
├── src/                          # Core application code
│   ├── __init__.py               # Package initialization
│   ├── api.py                    # FastAPI server (main entry point)
│   ├── api_improvements.py       # Health checks, rate limiting, validation
│   ├── constants.py              # Configuration constants & thresholds
│   ├── fetch_league_data.py      # ESPN Fantasy API data fetcher
│   ├── logger.py                 # Centralized logging system
│   ├── prompt_builder.py         # Modular prompt system (optional)
│   ├── recap_generator.py        # AI-powered recap generation
│   └── trend_tracker.py          # Multi-week trend analysis
│
├── scripts/                      # Utility & example scripts
│   ├── example_generate_recap.py # Example: Generate a recap
│   ├── split_prompt.py           # Tool: Split prompts into modules
│   ├── test_claude_model.py      # Tool: Test Claude API connection
│   └── test_env_loading.py       # Tool: Test environment variables
│
├── docs/                         # Documentation
│   ├── README.md                 # Main project documentation
│   ├── API_README.md             # API endpoint documentation
│   ├── QUICKSTART.md             # 5-minute setup guide
│   ├── RECAP_USAGE.md            # How to generate recaps
│   ├── INTEGRATION_GUIDE.md      # Integration instructions
│   ├── PROJECT_AUDIT.md          # Code quality audit report
│   ├── PROMPT_ARCHITECTURE.md    # Prompt system architecture
│   ├── COLUMNIST_PROMPT.md       # LLM prompt for columnist
│   ├── ENV_SETUP.md              # Environment setup guide
│   ├── SUMMARY.md                # Project summary
│   └── PROJECT_STRUCTURE.md      # This file
│
├── config/                       # Configuration templates
│   ├── config.example.json       # Example league configuration
│   └── env.example               # Example environment variables
│
├── logs/                         # Application logs (gitignored)
│   └── YYYYMMDD.log              # Daily log files
│
├── output/                       # Generated recaps (gitignored)
│   └── week-N-recap.md           # Weekly recap files
│
├── .env                          # Environment variables (gitignored)
├── .gitignore                    # Git ignore rules
├── .vscode/                      # VS Code settings
├── config.json                   # User configuration (gitignored)
├── LICENSE                       # MIT License
├── README.md                     # Symlink to docs/README.md
├── recap_history.json            # Recap history (gitignored)
├── requirements.txt              # Python dependencies
└── trend_history.json            # Trend data (gitignored)
```

---

## Directory Purposes

### `src/` - Core Application
**What:** Production code that powers the application  
**Contains:** API server, data fetchers, generators, utilities  
**Import path:** `from src.module_name import ...`

### `scripts/` - Utilities & Tools
**What:** Helper scripts, examples, and testing tools  
**Contains:** Example usage, testing utilities, data migration scripts  
**Run:** `python3 scripts/script_name.py`

### `docs/` - Documentation
**What:** All project documentation and guides  
**Contains:** Setup guides, API docs, architecture docs  
**Format:** Markdown files

### `config/` - Configuration Templates
**What:** Example configurations for new users  
**Contains:** Template config files (NOT actual config)  
**Usage:** Copy to root and customize

---

## Running the Application

### Start the API Server
```bash
# Recommended: Use npm scripts for easy management
npm run dev

# Alternative: Direct Python module execution (runs in foreground)
python3 -m src.api

# Alternative: Using uvicorn directly (advanced)
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Generate a Recap
```bash
python3 scripts/example_generate_recap.py
```

### Test Components
```bash
python3 scripts/test_claude_model.py
python3 scripts/test_env_loading.py
```

---

## Importing Modules

### Within `src/` files (importing other src modules)
```python
from src.logger import get_logger
from src.constants import NOTABLE_PLAYER_THRESHOLD
from src.trend_tracker import TrendTracker
```

### From scripts (importing src modules)
```python
import sys
sys.path.insert(0, '..')  # If script is in scripts/

from src.api import app
from src.recap_generator import RecapGenerator
```

---

## Configuration Files

### User Configuration (gitignored)
- `.env` - API keys and secrets
- `config.json` - League settings
- `recap_history.json` - Generated content history
- `trend_history.json` - Trend data

### Templates (version controlled)
- `config/config.example.json` - Copy to `config.json`
- `config/env.example` - Copy to `.env`

---

## Log Files

Logs are stored in `logs/YYYYMMDD.log` (one file per day)

**View logs:**
```bash
# Today's logs
cat logs/$(date +%Y%m%d).log

# Live tail
tail -f logs/$(date +%Y%m%d).log
```

---

## Generated Files

### Recaps
- Location: `output/week-N-recap.md`
- Format: Markdown
- Gitignored: Yes

### History
- `recap_history.json` - Last 10 weeks of recaps
- `trend_history.json` - Last 6 weeks of trends
- Auto-cleaned: Yes

---

## Benefits of This Structure

✅ **Clear organization** - Everything has its place  
✅ **Professional** - Industry-standard structure  
✅ **Scalable** - Easy to add new features  
✅ **IDE-friendly** - Better autocomplete and navigation  
✅ **Import clarity** - `from src.` makes imports obvious  
✅ **Documentation** - All docs in one place  
✅ **Clean root** - No clutter in main directory  

---

## Migration Notes

**Old structure** (all files in root):
```python
from api import app                    # ❌ Old way
from logger import get_logger          # ❌ Old way
```

**New structure** (organized):
```python
from src.api import app                # ✅ New way
from src.logger import get_logger      # ✅ New way
```

All imports have been updated automatically. Your existing code will continue to work!

---

## Adding New Files

### New Core Module
Add to `src/` and import with `from src.module_name import ...`

### New Utility Script
Add to `scripts/` - can import from `src/`

### New Documentation
Add to `docs/` as Markdown file

### New Configuration
Add example to `config/` (actual config stays in root)

---

**Last Updated:** October 14, 2025

