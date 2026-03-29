# Slack Integration Guide

This guide will help you set up automatic Slack notifications for your fantasy football weekly recaps.

## Table of Contents
- [Overview](#overview)
- [Setup Methods](#setup-methods)
  - [Method 1: Incoming Webhook (Recommended)](#method-1-incoming-webhook-recommended)
  - [Method 2: Slack Bot Token](#method-2-slack-bot-token)
- [Configuration](#configuration)
- [Testing the Integration](#testing-the-integration)
- [Automated Scheduling](#automated-scheduling)
- [Troubleshooting](#troubleshooting)

## Overview

The Slack integration allows you to:
- ✅ Automatically post weekly recaps to a Slack channel
- ✅ Format recaps with nice Slack formatting and emojis
- ✅ Schedule automatic posting on a regular cadence (e.g., every Tuesday)
- ✅ Manually send recaps on demand

## Setup Methods

You can choose between two methods. **Method 1 (Webhook)** is easier and recommended for most users.

### Method 1: Incoming Webhook (Recommended)

This is the easiest method and requires minimal setup.

#### Step 1: Create an Incoming Webhook

1. Go to [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
2. Click "Create your Slack app" or go to [Your Apps](https://api.slack.com/apps)
3. Click "Create New App" → "From scratch"
4. Name your app (e.g., "Fantasy Football Recap Bot")
5. Select your workspace
6. Click "Incoming Webhooks" in the sidebar
7. Toggle "Activate Incoming Webhooks" to **On**
8. Click "Add New Webhook to Workspace"
9. Select the channel where you want recaps posted
10. Click "Allow"
11. Copy the Webhook URL (starts with `https://hooks.slack.com/services/...`)

#### Step 2: Add to Your .env File

Open your `.env` file and add:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

That's it! The webhook method is now configured.

### Method 2: Slack Bot Token

This method provides more features but requires more setup steps.

#### Step 1: Create a Slack App

1. Go to [Your Apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Fantasy Football Recap Bot")
4. Select your workspace
5. Click "OAuth & Permissions" in the sidebar

#### Step 2: Add Bot Token Scopes

Scroll to "Scopes" → "Bot Token Scopes" and add:
- `chat:write` - Post messages
- `chat:write.public` - Post to public channels without joining

#### Step 3: Install App to Workspace

1. Scroll to top of "OAuth & Permissions" page
2. Click "Install to Workspace"
3. Review permissions and click "Allow"
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

#### Step 4: Add to Your .env File

Open your `.env` file and add:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL=#fantasy-football
```

Replace `#fantasy-football` with your channel name.

## Configuration

Your `.env` file should look like this:

```bash
# Required: Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Choose ONE Slack method:

# Method 1: Webhook (Recommended)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# OR Method 2: Bot Token
# SLACK_BOT_TOKEN=xoxb-your-bot-token-here
# SLACK_CHANNEL=#fantasy-football
```

## Testing the Integration

### Test the Connection

Run this command to send a test message:

```bash
python -m src.slack_notifier --test
```

You should see:
```
🧪 Testing Slack connection...
✅ Test message sent successfully!
```

And receive a message in your Slack channel confirming the connection.

### Send an Existing Recap

If you have already generated a recap (e.g., Week 6), you can test sending it:

```bash
python -m src.slack_notifier --week 6
```

This will send the recap from `output/week-6-recap.md` to your Slack channel.

## Automated Scheduling

You can schedule recaps to be generated and sent automatically.

### Manual Execution

Generate and send a recap for the current week:

```bash
python scripts/scheduled_recap.py
```

Generate and send for a specific week:

```bash
python scripts/scheduled_recap.py --week 7
```

### Scheduling with Cron (Linux/Mac)

Set up automatic weekly recaps using cron:

#### Step 1: Edit Crontab

```bash
crontab -e
```

#### Step 2: Add Cron Entry

Add one of these lines depending on when you want recaps sent:

```bash
# Every Tuesday at 9:00 AM
0 9 * * 2 cd /Users/tyler.hanlon/Documents/GitHub/fantasy && /usr/bin/python3 scripts/scheduled_recap.py >> logs/scheduler.log 2>&1

# Every Wednesday at 10:00 AM
0 10 * * 3 cd /Users/tyler.hanlon/Documents/GitHub/fantasy && /usr/bin/python3 scripts/scheduled_recap.py >> logs/scheduler.log 2>&1
```

**Important:** Replace the path with your actual project path!

#### Step 3: Find Your Python Path

If you're not sure of your Python path:

```bash
which python3
```

Use that path in the cron entry.

#### Cron Time Format

```
* * * * *
│ │ │ │ │
│ │ │ │ └── Day of week (0-7, Sunday=0 or 7)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)
```

Examples:
- `0 9 * * 2` - Every Tuesday at 9:00 AM
- `30 10 * * 3` - Every Wednesday at 10:30 AM
- `0 20 * * 5` - Every Friday at 8:00 PM

### Scheduling with launchd (Mac - Alternative to Cron)

On macOS, you can use `launchd` for more reliable scheduling:

#### Step 1: Create Launch Agent

Create file `~/Library/LaunchAgents/com.fantasy.recap.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fantasy.recap</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/tyler.hanlon/Documents/GitHub/fantasy/scripts/scheduled_recap.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>2</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/Users/tyler.hanlon/Documents/GitHub/fantasy</string>
    <key>StandardOutPath</key>
    <string>/Users/tyler.hanlon/Documents/GitHub/fantasy/logs/scheduler.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/tyler.hanlon/Documents/GitHub/fantasy/logs/scheduler.log</string>
</dict>
</plist>
```

**Note:** Update paths to match your system!

#### Step 2: Load the Launch Agent

```bash
launchctl load ~/Library/LaunchAgents/com.fantasy.recap.plist
```

#### Step 3: Verify It's Loaded

```bash
launchctl list | grep fantasy
```

#### Step 4: Unload (if needed)

```bash
launchctl unload ~/Library/LaunchAgents/com.fantasy.recap.plist
```

### Scheduling on Windows

Use Windows Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. Name it "Fantasy Football Recap"
4. Trigger: Weekly, select day and time
5. Action: Start a program
   - Program: `C:\Python\python.exe` (your Python path)
   - Arguments: `scripts/scheduled_recap.py`
   - Start in: `C:\path\to\fantasy` (your project path)
6. Finish

## Command Reference

### Slack Notifier Module

```bash
# Test Slack connection
python -m src.slack_notifier --test

# Send existing recap to Slack
python -m src.slack_notifier --week 6
```

### Scheduled Recap Script

```bash
# Generate and send recap (auto-detects current week)
python scripts/scheduled_recap.py

# Generate and send for specific week
python scripts/scheduled_recap.py --week 7

# Generate but don't send (dry run)
python scripts/scheduled_recap.py --dry-run

# Send existing recap without regenerating
python scripts/scheduled_recap.py --week 6 --send-only
```

## Troubleshooting

### "SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN must be provided"

**Solution:** Make sure you have added the Slack credentials to your `.env` file:

```bash
# Copy example file if you haven't already
cp config/env.example .env

# Edit .env and add your credentials
```

### "SLACK_CHANNEL must be provided when using SLACK_BOT_TOKEN"

**Solution:** If using bot token method, you must specify a channel:

```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#fantasy-football
```

### "Slack webhook error: 404"

**Solution:** Your webhook URL is invalid. Create a new webhook following the steps above.

### "Slack API error: channel_not_found"

**Solution:** 
1. Make sure the channel name is correct (include the `#`)
2. If using a bot token, invite the bot to the channel:
   - Go to the channel in Slack
   - Type `/invite @Fantasy Football Recap Bot`

### "Slack API error: not_in_channel"

**Solution:** Invite the bot to your channel (see above).

### Messages Not Formatting Properly

The integration converts standard Markdown to Slack's format automatically. If you see formatting issues, it's likely due to Slack's markdown limitations. This is normal.

### Cron Job Not Running

**Check these:**

1. Is cron running?
   ```bash
   # Mac
   sudo launchctl list | grep cron
   
   # Linux
   service cron status
   ```

2. Check the log file:
   ```bash
   tail -f logs/scheduler.log
   ```

3. Test the script manually:
   ```bash
   cd /path/to/fantasy
   python3 scripts/scheduled_recap.py
   ```

4. Verify Python path:
   ```bash
   which python3
   ```

5. Make sure `.env` file is in the project root

### Week Auto-Detection Is Wrong

The script estimates the NFL week based on the current date (assuming season starts ~September 5th). If it's wrong, specify the week manually:

```bash
python scripts/scheduled_recap.py --week 7
```

You can also modify the `get_current_nfl_week()` function in `scripts/scheduled_recap.py` to match your league's schedule.

## Next Steps

Once set up, your system will:
1. ✅ Automatically fetch data from your API
2. ✅ Generate a roast-filled recap using Claude
3. ✅ Post it to Slack with nice formatting
4. ✅ Save it to `output/` for your records

Enjoy your automated fantasy football roasts! 🏈🔥

