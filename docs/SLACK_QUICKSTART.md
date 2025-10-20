# Slack Integration - Quick Start

Get your weekly fantasy football recaps automatically posted to Slack in just a few minutes!

## 🚀 Quick Setup (5 minutes)

### 1. Get a Slack Webhook URL

1. Visit: https://api.slack.com/messaging/webhooks
2. Click **"Create your Slack app"** or go to https://api.slack.com/apps
3. Click **"Create New App"** → **"From scratch"**
4. Name it: `Fantasy Football Recap Bot`
5. Select your workspace
6. Click **"Incoming Webhooks"** in sidebar
7. Toggle **"Activate Incoming Webhooks"** to **ON**
8. Click **"Add New Webhook to Workspace"**
9. Select your channel (e.g., `#fantasy-football`)
10. Copy the Webhook URL (starts with `https://hooks.slack.com/services/...`)

### 2. Add to Your .env File

Open (or create) `.env` in your project root:

```bash
# If .env doesn't exist, copy from example
cp config/env.example .env
```

Add your webhook URL:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. Test It!

```bash
python -m src.slack_notifier --test
```

You should see:
```
🧪 Testing Slack connection...
✅ Test message sent successfully!
```

And receive a test message in your Slack channel! 🎉

### 4. Generate and Send a Recap

```bash
# Generate recap for week 6 and send to Slack
python scripts/scheduled_recap.py --week 6
```

**That's it!** You've successfully integrated Slack! 🎊

## 📅 Automate Weekly Posting

### Option 1: Cron (Linux/Mac)

Edit your crontab:
```bash
crontab -e
```

Add this line (sends every Tuesday at 9 AM):
```
0 9 * * 2 cd /Users/tyler.hanlon/Documents/GitHub/fantasy && /usr/bin/python3 scripts/scheduled_recap.py >> logs/scheduler.log 2>&1
```

**Important:** Update the path to match your project location!

Find your Python path:
```bash
which python3
```

### Option 2: Manual (Run When Ready)

Just run this whenever you want to generate and send:
```bash
python scripts/scheduled_recap.py
```

It will auto-detect the current NFL week!

## 🔧 Useful Commands

```bash
# Test Slack connection
python -m src.slack_notifier --test

# Generate and send (auto-detects week)
python scripts/scheduled_recap.py

# Generate and send specific week
python scripts/scheduled_recap.py --week 7

# Generate but don't send (preview)
python scripts/scheduled_recap.py --dry-run

# Send existing recap without regenerating
python -m src.slack_notifier --week 6
```

## ❓ Troubleshooting

### "SLACK_WEBHOOK_URL not found"
→ Make sure you added it to your `.env` file (not `config/env.example`)

### "Webhook error: 404"
→ Your webhook URL is invalid. Create a new one following step 1 above.

### "Recap file not found"
→ Generate the recap first:
```bash
python scripts/example_generate_recap.py
```

### Still stuck?
→ Check the full guide: [SLACK_INTEGRATION.md](./SLACK_INTEGRATION.md)

## 🎯 What You Get

- ✅ Automatic weekly recaps posted to Slack
- ✅ Beautiful formatting with emojis and headers
- ✅ Scheduled posting on a regular cadence
- ✅ Long recaps automatically split into multiple messages
- ✅ Timestamps showing when recap was generated

## 📖 Next Steps

- **Full documentation:** [SLACK_INTEGRATION.md](./SLACK_INTEGRATION.md)
- **Customize the columnist:** [COLUMNIST_PROMPT.md](./COLUMNIST_PROMPT.md)
- **Advanced scheduling:** See the full guide for launchd (Mac) or Windows Task Scheduler

---

**Happy roasting!** 🏈🔥

