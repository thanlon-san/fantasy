# Web UI Guide - Fantasy Football Recap Generator

A simple, beautiful web interface for generating and managing your weekly fantasy football recaps.

## 🚀 Quick Start

### 1. Start the API Server

```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy
npm run dev
```

### 2. Open Web UI

Visit: **http://localhost:8000**

That's it! The web UI is now running.

## ✨ Features

### Generate Recaps
- Select any week (1-18)
- Click "Generate Recap"
- Wait 30-60 seconds while Claude generates your roast-filled recap
- View, copy, or download the result

### View History
- Browse all previously generated recaps
- Click any recap to view it
- See when each recap was generated

### Copy & Paste to Slack
Since you may not have webhook access, you can easily:
1. Generate a recap in the web UI
2. Click "Copy to Clipboard"
3. Paste directly into your Slack channel

### Download Recaps
- Click "Download" to save any recap as a markdown file
- Files are named `week-X-recap.md`
- Perfect for archiving or sharing via email

## 🖥️ Interface Overview

### Generate Section
```
┌─────────────────────────────────┐
│ Generate New Recap              │
│                                 │
│ Select Week: [6]                │
│                                 │
│ [Generate Recap]                │
└─────────────────────────────────┘
```

### Recap Display
```
┌─────────────────────────────────┐
│ Week 6 Recap                    │
│ [📋 Copy] [💾 Download]         │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ # Week 6: When...           │ │
│ │                             │ │
│ │ [Recap content here]        │ │
│ │                             │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

### History Section
```
┌─────────────────────────────────┐
│ Previous Recaps                 │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Week 6                      │ │
│ │ Oct 15, 2025 9:30 AM        │ │
│ │ "When Projections Go..."    │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Week 5                      │ │
│ │ Oct 8, 2025 9:15 AM         │ │
│ │ "Another Week, Another..."  │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

## 📱 Mobile Friendly

The web UI is fully responsive and works great on:
- Desktop computers
- Tablets
- Mobile phones

## 🔧 Configuration

The web UI uses your existing configuration:

### Required
- **ANTHROPIC_API_KEY** - Set in `.env` file for recap generation
- **API Server** - The FastAPI server must be running

### Optional
- **Slack** - Not required! The web UI gives you copy/paste functionality

## 🎯 Usage Workflow

### For Weekly Recaps

**Option 1: Copy to Slack**
1. Open web UI (http://localhost:8000)
2. Generate recap for current week
3. Click "Copy to Clipboard"
4. Paste into your Slack channel
5. Done! 🎉

**Option 2: Download and Share**
1. Generate recap
2. Click "Download"
3. Share the markdown file via email, Slack upload, etc.

### Viewing Past Recaps
1. Scroll to "Previous Recaps" section
2. Click any recap to view it
3. Copy or download as needed

## 🚨 Troubleshooting

### "Failed to generate recap"

**Check:**
1. Is `ANTHROPIC_API_KEY` set in your `.env` file?
   ```bash
   # In .env file
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

2. Is the API server running?
   ```bash
   # Terminal should show:
   🏈 Fantasy Football API Starting...
   📖 API Documentation: http://localhost:8000/docs
   ```

3. Is your ESPN configuration correct in `config.json`?

### "Connection failed" or Page won't load

**Solution:**
```bash
# Check if server is running
lsof -i :8000

# If not, start it:
python3 src/api.py
```

### Recap generation is slow

**This is normal!** Claude takes 30-60 seconds to:
- Analyze all the matchup data
- Craft personalized roasts
- Format the output beautifully

You'll see a loading indicator while it works.

### Can't copy to clipboard

**Fallback:**
1. Click in the recap content area
2. Select all text (Cmd+A or Ctrl+A)
3. Copy (Cmd+C or Ctrl+C)
4. Paste into Slack

## 🎨 Customization

### Change Port

Edit `src/api.py` or set environment variable:
```bash
PORT=3000 python3 src/api.py
```

### Modify Styling

Edit `static/style.css` to change colors, fonts, spacing, etc.

The UI uses CSS variables for easy customization:
```css
:root {
    --primary-color: #2563eb;  /* Change to your team colors! */
    --card-bg: #ffffff;
    --bg-color: #f8fafc;
}
```

## 📊 API Endpoints (For Advanced Users)

The web UI uses these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serves the web UI |
| `/api/recaps/generate` | POST | Generate new recap |
| `/api/recaps/history` | GET | List all recaps |
| `/api/recaps/{week}` | GET | Get specific recap |

Full API docs: http://localhost:8000/docs

## 💡 Tips & Tricks

### 1. Generate in Advance
Generate your recap Monday night, review it, then post Tuesday morning.

### 2. Keep a Copy
Always download recaps before the season ends. You'll want to revisit these roasts! 😄

### 3. Edit Before Posting
- Copy the recap
- Paste into a text editor
- Make any tweaks
- Then paste into Slack

### 4. Share the Highlights
Copy just the best roasts and post them as teasers, with a link to the full recap.

### 5. Archive Your Season
Download all recaps and compile them into a season highlights document!

## 🔒 Security Note

The web UI runs locally on your computer. Only you can access it at `localhost:8000`.

If you want to make it accessible to others:
1. **Don't expose it publicly** (contains your API keys)
2. Use it locally and copy/paste results to share
3. Or consider deploying with proper authentication

## 🎉 Enjoy!

You now have a beautiful, easy-to-use interface for generating and managing your fantasy football recaps.

No command line required. No Slack webhook setup needed. Just point, click, copy, and paste!

---

**Questions?** Check out:
- [RECAP_USAGE.md](./RECAP_USAGE.md) - General recap guide
- [SLACK_INTEGRATION.md](./SLACK_INTEGRATION.md) - If you later get webhook access
- [API_README.md](./API_README.md) - API documentation

