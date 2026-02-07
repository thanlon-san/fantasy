# Changelog

All notable changes to the Fantasy Sports Hub monorepo.

## [2026-02-06] - Major Repository Cleanup & Reorganization

### 🎯 Overview
Complete audit and reorganization of the monorepo for better maintainability and structure.

### ✅ Added

#### Documentation
- **New comprehensive root README.md** - Complete project overview with quick start guides
- **docs/DEPLOYMENT.md** - Consolidated deployment guide (GitHub Pages, Railway, Vercel)
- **docs/DEVELOPMENT.md** - Complete local development guide with troubleshooting
- **packages/shared/README.md** - Documentation for shared Python utilities
- **packages/shared-config/README.md** - Documentation for shared configuration

#### Packages
- **packages/shared-config/** - New shared configuration package for TypeScript and Tailwind configs
  - `tailwind.config.js` - Base Tailwind configuration
  - `tsconfig.base.json` - Base TypeScript configuration
  - `package.json` - Package manifest with exports

#### Configuration
- **Root requirements.txt** - Consolidated Python dependencies for all apps
- **Enhanced root package.json** - Added metadata, improved scripts:
  - `pnpm preflight` - Run all checks before deployment
  - `pnpm clean:builds` - Clean only build artifacts
  - `pnpm dev` - Default to fantasy-hub
  - Added keywords and description

### 🔄 Changed

#### Documentation Improvements
- **apps/baseball-dashboard/README.md** - Enhanced with tech stack, better quick start
- **apps/keeper-advisor/README.md** - Added documentation links section
- Updated all READMEs to reference centralized docs

#### Repository Structure
- Standardized all app READMEs with consistent format
- Improved .gitignore with better coverage:
  - Added `.env.local` and `.env*.local` patterns
  - Added `**/out/` and `**/.next/` for all apps
  - Added app-specific env files

### 🗑️ Removed

#### Redundant Documentation
- `AUTOMATED_UPDATES.md` → Merged into docs/DEPLOYMENT.md
- `DEPLOY_API.md` → Merged into docs/DEPLOYMENT.md
- `DEPLOYMENT.md` → Moved to docs/DEPLOYMENT.md
- `apps/baseball-dashboard/UI_REDESIGN_SUMMARY.md` - Outdated
- `apps/baseball-dashboard/UI_IMPROVEMENT_PROMPT.md` - Prompt file (not needed in repo)
- `apps/baseball-dashboard/QUICKSTART.md` - Redundant with main docs
- `apps/keeper-advisor/AUDIT_PROMPT.md` - Prompt file (not needed in repo)
- `apps/keeper-advisor/IMPROVEMENTS.md` - Outdated

#### Duplicate Configurations
- `apps/baseball-dashboard/.gitignore` - Using root .gitignore instead
- `apps/fantasy-hub/.gitignore` - Using root .gitignore instead

#### Build Artifacts & Runtime Files
- Cleaned `logs/*` directory (444KB)
- Cleaned `output/*` directory (248KB)
- Removed `.next` build directories from apps
- Removed `out` build directories from apps

#### Backup Files
- `apps/espn-fantasy-recap/recap_history.backup.20251021_220152.json`
- `apps/espn-fantasy-recap/trend_history_backup.json`

#### Git-Tracked Runtime Files (Now Ignored)
- `.server.pid` and `.server (1).pid` - Process ID files
- These files removed from git tracking via `git rm --cached`

### 🔧 Fixed
- **Broken README.md symlink** - Was pointing to non-existent `docs/README.md`
- Now a proper file with complete project documentation

### 📊 Impact

#### Size Reductions
- **~700KB** removed in documentation and backups
- **~700KB** removed in logs/output directories
- Better .gitignore prevents future bloat

#### Organization Improvements
- **21 markdown files** → Consolidated into organized docs/ structure
- **3 deployment docs** → 1 comprehensive guide
- **Duplicate configs** → Shared configuration packages

#### Developer Experience
- Clearer project structure
- Better onboarding with comprehensive docs
- Consistent configuration across apps
- Improved build scripts

### 🚀 Deployment Status
All apps remain fully functional and deployed:
- ✅ Landing Page: https://thanlon-san.github.io/fantasy/
- ✅ Baseball Dashboard: https://thanlon-san.github.io/fantasy/baseball/
- ✅ Recap: https://thanlon-san.github.io/fantasy/recap/
- ✅ Keeper API: Railway (as configured)

### 📚 New Documentation Structure
```
docs/
├── DEPLOYMENT.md      # All deployment guides (Pages, Railway, Vercel)
├── DEVELOPMENT.md     # Complete local dev guide
└── apps/              # App-specific docs (future)
```

### 🎓 Migration Guide

#### For Developers
No breaking changes! All apps work the same way:

```bash
# Install dependencies (same as before)
pnpm install
pip install -r requirements.txt

# Run apps (same as before)
pnpm dev:baseball
pnpm dev:hub
cd apps/keeper-advisor && pnpm lineup
```

#### For CI/CD
No changes required - GitHub Actions workflows remain unchanged.

### 🔜 Future Improvements
- Consider merging fantasy-hub into baseball-dashboard for single Next.js app
- Consolidate Python requirements further
- Add shared React components package
- Add shared TypeScript types package
- Set up automated dependency updates

---

## Previous Releases

See git history for changes prior to 2026-02-06.
