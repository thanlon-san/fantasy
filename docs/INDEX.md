# Documentation Index 📚

**Welcome to the Fantasy Football Recap Generator documentation!**

This index will help you find the right documentation for your needs.

---

## 🚀 Getting Started (Start Here!)

New to this project? Start with these:

1. **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in 5 minutes
   - Install dependencies
   - Configure your league
   - Start the server
   - Generate your first recap

2. **[README.md](README.md)** - Project overview and features
   - What this project does
   - Feature list
   - Quick command reference

---

## 🎨 Using the Web UI (Easiest Method)

The web interface is the easiest way to generate recaps:

- **[WEB_UI_QUICKSTART.md](WEB_UI_QUICKSTART.md)** - 2-minute setup
- **[WEB_UI_GUIDE.md](WEB_UI_GUIDE.md)** - Complete web UI guide
- **[WEBAPP_README.md](WEBAPP_README.md)** - Alternative web UI readme

**Quick Start:**
```bash
npm run dev
# Visit http://localhost:8000
```

---

## 📡 API Documentation

Using the REST API programmatically:

- **[API_README.md](API_README.md)** - Complete API reference
  - All endpoints
  - Request/response examples
  - Error codes
  - Rate limiting

**Quick Reference:**
- `GET /api/league` - League info
- `GET /api/standings` - Current standings
- `GET /api/matchups/{week}` - Week matchups
- `GET /api/recaps/generate` - Generate recap

---

## 😈 Generating AI Recaps

Learn how to create AI-powered roast recaps:

- **[RECAP_USAGE.md](RECAP_USAGE.md)** - Complete recap generation guide
  - LLM integration (OpenAI/Anthropic)
  - Context generation
  - Customization options
  - Troubleshooting

- **[COLUMNIST_PROMPT.md](COLUMNIST_PROMPT.md)** - The AI columnist's brain
  - Voice and style guide
  - Roasting rules
  - CRM jargon easter eggs
  - Safety guidelines

---

## 📲 Slack Integration

Post recaps automatically to Slack:

- **[SLACK_INTEGRATION.md](SLACK_INTEGRATION.md)** - Complete Slack setup
  - Webhook configuration
  - Bot token setup
  - Automated scheduling (cron/launchd)
  - Manual posting

- **[SLACK_FORMATTING.md](SLACK_FORMATTING.md)** - How Slack formatting works
  - Before/after examples
  - Emoji mappings
  - Markdown conversions

---

## 🏗️ Project Structure & Development

Understanding the codebase:

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Directory organization
  - File purposes
  - Import patterns
  - How to add new features

---

## 🔧 Server Management

Managing the API server:

### Start/Stop Commands
```bash
npm run dev      # Start server in background
npm run stop     # Stop server
npm run restart  # Restart server
npm status       # Check server status
npm run logs     # View logs
```

### Configuration
- **[ENV_SETUP.md](ENV_SETUP.md)** - Environment variables
- **config.json** - League configuration
- **.env** - API keys and secrets

---

## 📖 Additional Documentation

### Status & Audit Documents
- **[DOCUMENTATION_AUDIT.md](DOCUMENTATION_AUDIT.md)** - This audit (Nov 2025)
- **[FINAL_STATUS.md](FINAL_STATUS.md)** - Project audit (Oct 2025)
- **[SUMMARY.md](SUMMARY.md)** - Project summary

### Specialized Topics
- **[PROMPT_ARCHITECTURE.md](PROMPT_ARCHITECTURE.md)** - Modular prompt system
- **[V2_FORMAT_GUIDE.md](V2_FORMAT_GUIDE.md)** - Format guidelines
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Integration patterns
- **[API_INTEGRATIONS.md](API_INTEGRATIONS.md)** - API integration details

### Historical/Reference
- **[PROJECT_AUDIT.md](PROJECT_AUDIT.md)** - Historical audit
- **[SLACK_FORMAT_UPDATE.md](SLACK_FORMAT_UPDATE.md)** - Slack feature announcement
- **[FOOTBALL_STATS_APIS.md](FOOTBALL_STATS_APIS.md)** - Stats API research

---

## 🎯 Quick Command Reference

### Server Management
```bash
npm run dev      # Start server
npm run stop     # Stop server
npm run restart  # Restart server
npm status       # Check status
npm run logs     # View logs
```

### Common Tasks
```bash
# Start server and open web UI
npm run dev
# Visit http://localhost:8000

# Check server health
curl http://localhost:8000/health

# View API docs
# Visit http://localhost:8000/docs
```

---

## 🗺️ Documentation Roadmap

### By User Type

**First-Time User:**
1. QUICKSTART.md
2. WEB_UI_QUICKSTART.md
3. Try generating a recap!

**Regular User:**
1. WEB_UI_GUIDE.md
2. RECAP_USAGE.md
3. COLUMNIST_PROMPT.md (to customize)

**Developer/Integrator:**
1. API_README.md
2. PROJECT_STRUCTURE.md
3. INTEGRATION_GUIDE.md

**Slack Admin:**
1. SLACK_INTEGRATION.md
2. SLACK_FORMATTING.md

---

## 🆘 Troubleshooting

### Server won't start
```bash
npm run stop
npm run dev
```

### Port already in use
```bash
npm run stop  # Stops any existing server
npm run dev   # Start fresh
```

### Can't generate recaps
1. Check `.env` has your ANTHROPIC_API_KEY
2. Verify server is running: `npm status`
3. Check logs: `npm run logs:api`

### Documentation seems outdated
- Check [DOCUMENTATION_AUDIT.md](DOCUMENTATION_AUDIT.md) for latest status
- All commands updated to use npm scripts as of Nov 2025

---

## 📝 Documentation Standards

All documentation follows these standards:

- ✅ Uses `npm run dev` (not `python3 api.py`)
- ✅ Uses `npm run stop` (not `kill -9`)
- ✅ Current as of November 2025
- ✅ Includes examples and code snippets
- ✅ Has troubleshooting sections

---

## 🤝 Contributing to Docs

Found an error or want to improve the docs?

1. Check if the doc is in the "Core" category (see DOCUMENTATION_AUDIT.md)
2. Update the specific doc file
3. Update this INDEX.md if you add/remove docs
4. Follow existing formatting and style

---

## 📬 Need Help?

1. Check the relevant documentation above
2. Look at troubleshooting sections
3. Review [QUICKSTART.md](QUICKSTART.md) for common issues
4. Check server logs: `npm run logs:api`

---

**Last Updated:** November 5, 2025  
**Documentation Version:** 2.0 (npm commands update)

