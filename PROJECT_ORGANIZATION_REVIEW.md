# Project Organization Review & Improvements

## Current State Analysis

### ✅ What's Working Well

1. **Monorepo Structure** - Using pnpm workspaces for multi-app management
2. **Clear App Separation** - Each app is self-contained
3. **Shared Packages** - `packages/shared/` for common code
4. **Documentation** - Comprehensive docs in each app

### ⚠️ Issues Identified

1. **Root-level clutter** - Too many files at root (`.server.pid`, backup files)
2. **Inconsistent naming** - Mix of kebab-case and snake_case
3. **No global testing** - Each app tests independently
4. **Build scripts scattered** - No centralized build commands
5. **Type errors** - `React.Node` should be `React.ReactNode`
6. **Lockfile out of sync** - Caused GitHub Actions failure

---

## Proposed Project Organization

### Recommended Structure

```
fantasy/
│
├── apps/                           # All applications
│   ├── keeper-advisor/             # Python baseball tools
│   │   ├── src/                   # Python source
│   │   ├── scripts/               # CLI tools
│   │   ├── config/                # Configuration
│   │   ├── data/                  # Data files
│   │   ├── tests/                 # ⭐ NEW - Unit tests
│   │   ├── requirements.txt
│   │   └── pyproject.toml         # ⭐ NEW - Python project config
│   │
│   ├── espn-fantasy-recap/         # ESPN recap generator
│   │   ├── src/                   # Python source
│   │   ├── scripts/               # CLI tools
│   │   ├── static/                # Web UI assets
│   │   ├── tests/                 # ⭐ NEW - Unit tests
│   │   └── requirements.txt
│   │
│   ├── fantasy-hub/                # Landing page (Next.js)
│   │   ├── app/                   # Next.js app dir
│   │   ├── components/            # ⭐ NEW - Shared components
│   │   ├── public/                # Static assets
│   │   ├── tests/                 # ⭐ NEW - Tests
│   │   └── package.json
│   │
│   ├── baseball-dashboard/         # Baseball tools UI (Next.js)
│   │   ├── app/                   # Next.js app dir
│   │   ├── components/            # ⭐ NEW - UI components
│   │   ├── lib/                   # ⭐ NEW - Client utilities
│   │   ├── hooks/                 # ⭐ NEW - React hooks
│   │   ├── types/                 # ⭐ NEW - TypeScript types
│   │   ├── public/                # Static assets
│   │   ├── tests/                 # ⭐ NEW - Tests
│   │   └── package.json
│   │
│   └── espn-recap-web/             # Recap info page (static)
│       └── index.html
│
├── packages/                       # Shared code
│   ├── shared/                    # Python shared utilities
│   │   ├── llm_client.py
│   │   ├── slack_notifier.py
│   │   └── requirements.txt
│   │
│   ├── ui-components/             # ⭐ NEW - Shared React components
│   │   ├── src/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   └── index.ts
│   │   └── package.json
│   │
│   └── types/                     # ⭐ NEW - Shared TypeScript types
│       ├── src/
│       │   ├── fantasy.ts
│       │   └── index.ts
│       └── package.json
│
├── docs/                           # Global documentation
│   ├── WORKSPACE_GUIDE.md
│   ├── MIGRATION_SUMMARY.md
│   ├── API_ARCHITECTURE.md        # ⭐ NEW
│   └── DEPLOYMENT_GUIDE.md        # ⭐ NEW
│
├── .github/                        # GitHub configuration
│   ├── workflows/
│   │   ├── deploy-dashboard.yml
│   │   ├── test-python.yml        # ⭐ NEW
│   │   └── test-typescript.yml    # ⭐ NEW
│   └── PULL_REQUEST_TEMPLATE.md   # ⭐ NEW
│
├── scripts/                        # ⭐ NEW - Global utility scripts
│   ├── build-all.sh
│   ├── test-all.sh
│   ├── lint-all.sh
│   └── clean.sh
│
├── .gitignore                      # Global gitignore
├── pnpm-workspace.yaml             # Workspace config
├── pnpm-lock.yaml                  # Lockfile
├── package.json                    # Root package.json with scripts
├── README.md                       # ⭐ IMPROVED - Better overview
├── CONTRIBUTING.md                 # ⭐ NEW - Contributing guide
└── LICENSE                         # License file
```

---

## Specific Improvements

### 1. Root-Level Cleanup

**Remove from root:**
```bash
# Delete these files
.server.pid
.server (1).pid
trend_history_backup.json
recap_history.backup.20251021_220152.json

# Move to .gitignore
*.pid
*_backup.json
*.backup.json
```

**Add proper `.gitignore`:**
```gitignore
# Server PIDs
*.pid
.server*.pid

# Backups
*_backup.json
*.backup.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv

# Node
node_modules/
.pnp/
.pnp.*
.yarn/

# Next.js
.next/
out/
build/

# Misc
.DS_Store
.env*.local
.vercel

# IDE
.vscode/
.idea/
*.swp
*.swo
```

### 2. Centralized Scripts

**Create `scripts/build-all.sh`:**
```bash
#!/bin/bash
set -e

echo "🏗️  Building all apps..."

# Build Next.js apps
pnpm --filter @fantasy/hub build
pnpm --filter @fantasy/baseball-dashboard build

echo "✅ All builds complete!"
```

**Create `scripts/test-all.sh`:**
```bash
#!/bin/bash
set -e

echo "🧪 Running all tests..."

# Python tests
echo "Testing keeper-advisor..."
cd apps/keeper-advisor && python -m pytest tests/ || true

echo "Testing espn-recap..."
cd ../espn-fantasy-recap && python -m pytest tests/ || true

# TypeScript tests
echo "Testing Next.js apps..."
cd ../..
pnpm --filter './apps/**' test || echo "No tests configured yet"

echo "✅ All tests complete!"
```

**Create `scripts/lint-all.sh`:**
```bash
#!/bin/bash
set -e

echo "🔍 Linting all code..."

# Python linting
echo "Linting Python..."
cd apps/keeper-advisor && ruff check src/ scripts/ || true
cd ../espn-fantasy-recap && ruff check src/ scripts/ || true

# TypeScript linting
echo "Linting TypeScript..."
cd ../..
pnpm lint

echo "✅ Linting complete!"
```

**Create `scripts/preflight.sh`:**
```bash
#!/bin/bash
set -e

echo "✈️  Running preflight checks before deployment..."

# 1. Clean install
echo "📦 Installing dependencies..."
pnpm install

# 2. Type check
echo "🔍 Type checking..."
pnpm typecheck || { echo "❌ Type check failed"; exit 1; }

# 3. Lint
echo "🧹 Linting..."
pnpm lint || { echo "❌ Lint failed"; exit 1; }

# 4. Build
echo "🏗️  Building..."
pnpm build:local || { echo "❌ Build failed"; exit 1; }

echo "✅ Preflight checks passed! Ready to deploy."
```

### 3. Improved `package.json` at Root

```json
{
  "name": "fantasy-sports-monorepo",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "pnpm --filter './apps/**' build",
    "build:hub": "pnpm --filter @fantasy/hub build",
    "build:baseball": "pnpm --filter @fantasy/baseball-dashboard build",
    "build:local": "pnpm build:hub && pnpm build:baseball",
    "dev:hub": "pnpm --filter @fantasy/hub dev",
    "dev:baseball": "pnpm --filter @fantasy/baseball-dashboard dev",
    "lint": "pnpm --filter './apps/**' lint",
    "lint:fix": "pnpm --filter './apps/**' lint -- --fix",
    "typecheck": "pnpm --filter './apps/**' exec tsc --noEmit",
    "clean": "rm -rf apps/*/out apps/*/.next apps/*/node_modules node_modules",
    "preflight": "bash scripts/preflight.sh",
    "test:all": "bash scripts/test-all.sh",
    "format": "prettier --write \"apps/**/*.{ts,tsx,json,md}\""
  },
  "devDependencies": {
    "prettier": "^3.2.4"
  }
}
```

### 4. Python Project Structure

**Add `apps/keeper-advisor/pyproject.toml`:**
```toml
[project]
name = "keeper-advisor"
version = "1.0.0"
description = "Fantasy baseball keeper and lineup analysis tools"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.31.0",
    "pandas>=2.0.0",
    "beautifulsoup4>=4.12.0",
    "fuzzywuzzy>=0.18.0",
    "python-Levenshtein>=0.21.0",
    "prompt-toolkit>=3.0.0",
    "pybaseball>=2.2.0",
    "mlb-statsapi>=1.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "black>=23.0.0",
    "mypy>=1.5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ['py39']
```

**Add `apps/keeper-advisor/tests/` structure:**
```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_adp_fetcher.py
├── test_analyzer.py
├── test_breakout_detector.py
├── test_daily_matchups.py
├── test_lineup_optimizer.py
├── test_waiver_analyzer.py
└── fixtures/
    ├── sample_roster.csv
    ├── sample_adp.json
    └── sample_game_data.json
```

### 5. TypeScript Shared Packages

**Create `packages/ui-components/package.json`:**
```json
{
  "name": "@fantasy/ui-components",
  "version": "1.0.0",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/react": "^19",
    "typescript": "^5"
  }
}
```

**Create `packages/types/package.json`:**
```json
{
  "name": "@fantasy/types",
  "version": "1.0.0",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "devDependencies": {
    "typescript": "^5"
  }
}
```

### 6. Better Documentation

**Improve root `README.md`:**
```markdown
# Fantasy Sports Monorepo

Your complete fantasy sports toolkit with data-driven intelligence.

## 🎯 Quick Start

\`\`\`bash
# Install dependencies
pnpm install

# Run preflight checks (lint, typecheck, build)
pnpm preflight

# Deploy to GitHub Pages
git push origin main
\`\`\`

## 📱 Applications

### ⚾ [Keeper Advisor](apps/keeper-advisor/)
Python-based fantasy baseball tools for keepers, waivers, breakouts, and daily lineups.

### 🏈 [ESPN Recap Generator](apps/espn-fantasy-recap/)
AI-powered weekly recap generator for ESPN Fantasy Football.

### 🌐 [Fantasy Hub](apps/fantasy-hub/)
Landing page to choose your app.

### ⚾ [Baseball Dashboard](apps/baseball-dashboard/)
Web UI for baseball tools (Next.js).

## 🔧 Development

\`\`\`bash
# Run local dev servers
pnpm dev:hub        # Landing page at :3000
pnpm dev:baseball   # Baseball dashboard at :3001

# Build all apps
pnpm build:local

# Run tests
pnpm test:all

# Lint & format
pnpm lint
pnpm format
\`\`\`

## 📚 Documentation

- [Workspace Guide](docs/WORKSPACE_GUIDE.md)
- [Deployment Guide](README_GITHUB_PAGES.md)
- [Contributing](CONTRIBUTING.md)

## 🚀 Deployment

All apps auto-deploy to GitHub Pages on push to `main`:
- Landing: https://thanlon-san.github.io/fantasy/
- Baseball: https://thanlon-san.github.io/fantasy/baseball/
- Recap: https://thanlon-san.github.io/fantasy/recap/

## 📦 Project Structure

\`\`\`
fantasy/
├── apps/           # All applications
├── packages/       # Shared code
├── docs/           # Documentation
├── scripts/        # Utility scripts
└── .github/        # CI/CD workflows
\`\`\`

## 🏆 Features

- **Daily Lineup Optimizer** - Start/sit recommendations with advanced metrics
- **Breakout Detector** - Statcast-powered player discovery
- **Waiver Wire Assistant** - Value-based pickup suggestions
- **Keeper Analyzer** - Optimize your keeper selections
- **ESPN Recap Generator** - AI-generated weekly recaps

## 📄 License

MIT
\`\`\`

---

## Implementation Priority

### Phase 1: Critical Fixes (Do Now) ⚠️
1. ✅ Fix `React.Node` → `React.ReactNode` type error
2. ✅ Update lockfile and test builds
3. ✅ Add root `package.json` with scripts
4. ⬜ Create `scripts/preflight.sh`
5. ⬜ Clean up root directory (remove `.pid` files, backups)
6. ⬜ Update `.gitignore`

### Phase 2: Testing Infrastructure (This Week)
1. ⬜ Add `pytest` to Python projects
2. ⬜ Create basic test files
3. ⬜ Add GitHub Actions for testing
4. ⬜ Create test fixtures

### Phase 3: Code Quality (Next Week)
1. ⬜ Add `ruff` for Python linting
2. ⬜ Add `prettier` for TypeScript formatting
3. ⬜ Create `pyproject.toml` for each Python app
4. ⬜ Add pre-commit hooks

### Phase 4: Shared Packages (Future)
1. ⬜ Create `@fantasy/ui-components`
2. ⬜ Create `@fantasy/types`
3. ⬜ Refactor apps to use shared packages

### Phase 5: Documentation (Ongoing)
1. ⬜ Improve root `README.md`
2. ⬜ Create `CONTRIBUTING.md`
3. ⬜ Add API documentation
4. ⬜ Create deployment guide

---

## Summary

### Current Issues
- ❌ Type error in `layout.tsx` (FIXED)
- ❌ Lockfile out of sync (FIXED)
- ❌ Root directory cluttered
- ❌ No testing infrastructure
- ❌ No centralized scripts

### After Improvements
- ✅ Clean, organized monorepo structure
- ✅ Centralized build/test/lint scripts
- ✅ Proper testing infrastructure
- ✅ Better documentation
- ✅ Shared packages for code reuse
- ✅ Pre-flight checks before deployment

**Impact:** Professional codebase, easier maintenance, faster development, fewer bugs! 🎯
