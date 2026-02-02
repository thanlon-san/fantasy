# Automated Dashboard Updates

**Automated data updates via GitHub Actions - 100% free forever!**

## How It Works

```
┌─────────────────────────────────────────────┐
│  Scheduled Update (Daily at 8am ET)         │
│  OR Manual Trigger (Refresh Button)         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ GitHub Actions │
         │   Workflow     │
         └────────┬───────┘
                  │
                  ├─ Install Python deps
                  ├─ Run export_dashboard_data.py
                  ├─ Commit updated JSON files
                  └─ Push to repo
                  │
                  ▼
         ┌────────────────┐
         │ GitHub Pages   │
         │  Auto-Deploy   │
         └────────────────┘
```

## Features

- ✅ **Auto-updates daily** at 8am ET
- ✅ **Manual trigger** from GitHub Actions tab
- ✅ **100% free** (GitHub Actions free tier: 2000 min/month)
- ✅ **Fast** static JSON files on CDN
- ✅ **Simple** no backend hosting needed

---

## Setup

**No setup required!** The workflow is already configured and will start running automatically.

### Test Manual Trigger

1. Go to your repo: https://github.com/thanlon-san/fantasy
2. Click "Actions" tab
3. Select "Update Dashboard Data" workflow
4. Click "Run workflow" → "Run workflow"
5. Watch it run (~2-3 minutes)
6. Visit your dashboard to see updated data

---

## Scheduled Updates

The workflow runs automatically:
- **Time**: 8:00 AM ET (12:00 PM UTC)
- **Frequency**: Daily
- **Days**: Every day (including weekends)

To change the schedule, edit `.github/workflows/update-data.yml`:
```yaml
schedule:
  - cron: '0 12 * * *'  # 12pm UTC = 8am ET
```

Common schedules:
- `'0 12 * * *'` - Daily at 8am ET
- `'0 12 * * 1-5'` - Weekdays only at 8am ET
- `'0 12,18 * * *'` - Twice daily: 8am and 2pm ET

---

## Usage

### For End Users (Dashboard)

**Daily Use:**
1. Data automatically refreshes at 8am ET
2. Just visit the dashboard - data is always fresh

**Manual Refresh:**
1. Go to GitHub → Actions tab
2. Run "Update Dashboard Data" workflow
3. Wait 2-3 minutes
4. Reload dashboard

### For Developers

**Test locally:**
```bash
cd apps/keeper-advisor
python scripts/export_dashboard_data.py
```

**View workflow logs:**
1. Go to repo → Actions tab
2. Click latest workflow run
3. View logs for debugging

---

## Cost

**100% FREE:**
- GitHub Actions: 2000 free minutes/month
- Your usage: ~5 minutes/day = 150 min/month
- Plenty of headroom for manual refreshes

---

## Troubleshooting

### Workflow fails

**Check workflow logs:**
1. Go to repo → Actions tab
2. Click failed run
3. Check which step failed

**Common failures:**

**"Module not found":**
- Check requirements.txt has all dependencies
- Verify Python version (should be 3.11)

**"No changes to commit":**
- Normal! Means data hasn't changed since last run
- Not an error

**"Permission denied":**
- Check GitHub token has `contents: write` permission
- Workflow has `permissions: contents: write` in YAML

### Data not updating on site

**Clear cache:**
- Hard refresh: Ctrl+Shift+R (PC) or Cmd+Shift+R (Mac)
- Or wait 5 minutes for CDN to update

**Check if workflow ran:**
1. GitHub → Actions tab
2. Verify latest run succeeded
3. Check commit was pushed

---

## Monitoring

### Check last update time

**From dashboard JSON:**
```bash
curl https://thanlon-san.github.io/fantasy/baseball/api/daily_lineup.json | jq .generated_at
```

**From GitHub:**
1. Go to repo
2. Check latest commit message
3. Should see: "🤖 Auto-update dashboard data"

### GitHub Actions notifications

Enable email notifications:
1. GitHub → Settings → Notifications
2. Check "Actions" under "Watching"
3. Get emailed when workflows fail

---

## Advanced Configuration

### Run only during baseball season

Edit `.github/workflows/update-data.yml`:
```yaml
# Add this step before "Run data export"
- name: Check if baseball season
  run: |
    month=$(date +%m)
    if [ $month -lt 03 ] || [ $month -gt 10 ]; then
      echo "Off-season, skipping update"
      exit 0
    fi
```

### Add Yahoo API integration

To enable live waiver/breakout scanning:

1. Add secrets to GitHub:
   - `YAHOO_CLIENT_ID`
   - `YAHOO_CLIENT_SECRET`
   - `YAHOO_ACCESS_TOKEN`
   - `YAHOO_REFRESH_TOKEN`

2. Update workflow to use secrets:
```yaml
- name: Run data export
  env:
    YAHOO_CLIENT_ID: ${{ secrets.YAHOO_CLIENT_ID }}
    YAHOO_CLIENT_SECRET: ${{ secrets.YAHOO_CLIENT_SECRET }}
  working-directory: apps/keeper-advisor
  run: |
    python scripts/export_dashboard_data.py
```

---

## Security

### Token Security

**DO NOT:**
- ❌ Commit tokens to repo
- ❌ Share tokens publicly
- ❌ Use personal tokens for production

**DO:**
- ✅ Use environment variables
- ✅ Rotate tokens annually
- ✅ Use minimal scopes needed
- ✅ Use GitHub secrets in workflows

### Rate Limits

GitHub API limits:
- **Authenticated**: 5000 requests/hour
- **Your usage**: ~1 request per manual refresh
- **No risk** of hitting limits

---

## Maintenance

### Yearly tasks

1. **Rotate GitHub token** (if set to expire)
2. **Review workflow logs** for any issues
3. **Update dependencies** in requirements.txt
4. **Check GitHub Actions minutes** (should be well under 2000/month)

### Updates

The workflow automatically:
- ✅ Updates roster data
- ✅ Updates lineup recommendations
- ✅ Updates keeper analysis
- ✅ Commits changes
- ✅ Deploys to site

No manual maintenance needed!

---

## Alternative: Vercel Cron Jobs

If you deploy to Vercel, you can also use Vercel Cron:

```typescript
// vercel.json
{
  "crons": [{
    "path": "/api/update-data",
    "schedule": "0 12 * * *"
  }]
}
```

**Pros:**
- Simpler (no GitHub token needed)
- Integrated with Vercel

**Cons:**
- Vercel Pro required ($20/month)
- Not free

**Stick with GitHub Actions** for free solution!

---

## Summary

✅ **Setup**: 10 minutes (create token, add to Vercel)
✅ **Cost**: $0 forever
✅ **Updates**: Automatic daily + manual refresh
✅ **Maintenance**: None needed
✅ **Speed**: Fast (static files on CDN)

**You now have a fully automated, free, production-ready system!** 🎉
