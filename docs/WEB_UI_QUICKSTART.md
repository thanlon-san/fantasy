# Web UI - Quick Start Guide

Get your fantasy football recap generator up and running in 2 minutes!

## 🚀 Start the Server

```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy
python3 -m src.api
```

You should see:
```
🏈 Fantasy Football API Starting...
📖 API Documentation: http://localhost:8000/docs
```

## 🌐 Open the Web UI

Open your browser and visit:

**http://localhost:8000**

## 📝 Generate Your First Recap

1. **Enter a week number** (e.g., 6)
2. **Click "Generate Recap"**
3. **Wait 30-60 seconds** ⏳ (Claude is thinking hard!)
4. **View your roast-filled recap!** 🔥

## 💬 Copy to Slack (Now with Fun Formatting!)

1. Click the **"💬 Copy for Slack"** button (purple, with Slack colors!)
2. Go to your Slack channel
3. Paste (Cmd+V or Ctrl+V)
4. Send! 🎉

Your recap is automatically converted to Slack-friendly format with:
- ✨ Proper Slack formatting (bold, italic, etc.)
- 🎉 Contextual emojis (🔥 for roasts, 📊 for stats, 🏆 for winners)
- 📱 Better visual separation
- 🎭 Way more fun to read!

## 💾 Download for Later

Click the **"💾 Download"** button to save the recap as a markdown file.

## 📚 View Previous Recaps

Scroll down to the "Previous Recaps" section to see all your past roasts!

## 🛑 Stop the Server

When you're done:

```bash
# Find the server process
lsof -i :8000

# Kill it
kill <PID>
```

Or just press **Ctrl+C** in the terminal where the server is running.

## 💡 Pro Tips

### 1. Keep it Running
Leave the server running in the background and generate recaps whenever you need them!

### 2. Generate in Advance
Generate Monday night, review Tuesday morning, post Tuesday afternoon.

### 3. Mobile Access
The web UI works on your phone! Just make sure you're on the same network as your computer.

### 4. Bookmark It
Add http://localhost:8000 to your bookmarks for quick access!

## ⚠️ Troubleshooting

### Port Already in Use

```bash
# Kill any process on port 8000
lsof -ti :8000 | xargs kill -9

# Then start again
python3 -m src.api
```

### "Connection Refused"

Make sure the server is running:
```bash
lsof -i :8000
```

If nothing shows up, start the server again.

### "ANTHROPIC_API_KEY not configured"

Add your API key to `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

### Generation Failed

1. Check your internet connection
2. Verify your API key is valid
3. Check that your ESPN config is correct
4. Look at the server logs for details

## 🎉 That's It!

You're all set! Generate recaps, copy to Slack, and watch your league mates cry-laugh at the roasts.

---

**Need more help?** Check out:
- [Full Web UI Guide](./WEB_UI_GUIDE.md)
- [Recap Usage Guide](./RECAP_USAGE.md)

