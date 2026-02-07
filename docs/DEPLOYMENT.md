# Deployment Guide

Complete guide for deploying all Fantasy Sports Hub apps to production.

---

## 🌐 Live URLs

```
Landing Page:  https://thanlon-san.github.io/fantasy/
Baseball:      https://thanlon-san.github.io/fantasy/baseball/
Recap:         https://thanlon-san.github.io/fantasy/recap/
API:           https://your-app.railway.app/
```

---

## 📱 GitHub Pages Deployment (Static Sites)

### One-Time Setup (2 minutes)

1. **Enable GitHub Pages**
   - Go to: https://github.com/thanlon-san/fantasy/settings/pages
   - **Source:** Select "GitHub Actions"
   - Save ✅

2. **Push your code**
   ```bash
   git add .
   git commit -m "Deploy fantasy hub"
   git push origin main
   ```

3. **Wait 3-4 minutes** for GitHub Actions to build

4. **Visit your site:** https://thanlon-san.github.io/fantasy/

### Automatic Updates

Every push to `main` triggers auto-deployment:

```bash
# Make changes
git add .
git commit -m "Update dashboard"
git push

# GitHub automatically rebuilds and deploys
# Live in ~3 minutes!
```

### Build Details

GitHub Actions workflow (`.github/workflows/deploy-dashboard.yml`):
1. Installs dependencies
2. Builds fantasy-hub (landing page)
3. Builds baseball-dashboard
4. Copies espn-recap-web (static)
5. Combines all into `_site/`
6. Deploys to GitHub Pages

**Build time:** ~3-4 minutes

### Troubleshooting

**Build Fails:**
- Check GitHub Actions tab: `/actions`
- Look for error logs in failed workflow
- Test build locally first: `pnpm build:local`

**Site Shows 404:**
- Verify Pages enabled (Settings → Pages)
- Check Actions completed (green checkmark)
- Hard refresh: Cmd+Shift+R
- Wait 2-3 minutes for CDN cache

**Old Version Showing:**
- Hard refresh browser
- Clear cache
- Wait for CDN propagation (~2 min)

---

## 🤖 Automated Data Updates

**100% free automated updates via GitHub Actions!**

### How It Works

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

### Features

- ✅ **Auto-updates daily** at 8am ET
- ✅ **Manual trigger** from GitHub Actions tab
- ✅ **100% free** (GitHub Actions free tier: 2000 min/month)
- ✅ **Fast** static JSON files on CDN

### Manual Trigger

1. Go to your repo → Actions tab
2. Select "Update Dashboard Data" workflow
3. Click "Run workflow" → "Run workflow"
4. Wait ~2-3 minutes
5. Visit dashboard to see updated data

### Scheduled Updates

The workflow runs automatically:
- **Time**: 8:00 AM ET (12:00 PM UTC)
- **Frequency**: Daily
- **Days**: Every day (including weekends)

To change schedule, edit `.github/workflows/update-data.yml`:
```yaml
schedule:
  - cron: '0 12 * * *'  # 12pm UTC = 8am ET
```

Common schedules:
- `'0 12 * * *'` - Daily at 8am ET
- `'0 12 * * 1-5'` - Weekdays only at 8am ET
- `'0 12,18 * * *'` - Twice daily: 8am and 2pm ET

### Cost: 100% FREE

- GitHub Actions: 2000 free minutes/month
- Your usage: ~5 minutes/day = 150 min/month
- Plenty of headroom for manual refreshes

---

## 🚂 Railway Deployment (API Backend)

### Deploy Keeper API to Railway (5 minutes)

#### 1. Sign Up for Railway
- Go to https://railway.app
- Click "Login with GitHub"
- Authorize Railway

#### 2. Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `fantasy` repository
4. Click "Deploy"

#### 3. Configure Service
1. Click on your service
2. Go to "Settings" tab
3. Set **Root Directory**: `apps/keeper-api`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click "Deploy"

#### 4. Get Your API URL
1. Go to "Settings" tab
2. Click "Generate Domain"
3. Copy the URL (e.g., `https://keeper-api-production.up.railway.app`)

**✅ Your API is now live!**

Test it:
```bash
curl https://your-api.railway.app/
curl https://your-api.railway.app/api/lineup
curl https://your-api.railway.app/api/keepers
```

### Cost Breakdown (FREE)

**Railway:**
- **Free Tier**: $5 credit/month
- **Your Usage**: ~$0.50/month
- **Limits**: 
  - 500 hours/month (plenty)
  - No sleep (always fast)
  - 8GB RAM (you use ~150MB)

**Total Cost: $0/month** ✅

### Troubleshooting Railway

**"Application failed to respond":**
- Check Railway logs: Click service → "Deployments" → Latest deploy → "View Logs"
- Common issue: Wrong root directory (should be `apps/keeper-api`)

**"Module not found":**
- Check Railway is using correct root directory
- Railway should auto-install from `requirements.txt`

---

## ▲ Vercel Deployment (Next.js Apps)

### Deploy Baseball Dashboard to Vercel

#### 1. Sign Up for Vercel
- Go to https://vercel.com
- Sign in with GitHub

#### 2. Import Project
1. Click "Add New..." → "Project"
2. Import your `fantasy` repository
3. **Framework Preset**: Next.js
4. **Root Directory**: `apps/baseball-dashboard`
5. Add environment variables:
   - `NEXT_PUBLIC_USE_API` = `true`
   - `NEXT_PUBLIC_API_URL` = `https://your-api.railway.app`
6. Click "Deploy"

#### 3. Get Your Dashboard URL
Vercel provides: `https://fantasy-baseball-dashboard.vercel.app`

**✅ Done!** Your dashboard now fetches live data.

### Vercel Free Tier

- **Free Tier**: Unlimited personal projects
- **Limits**:
  - 100GB bandwidth/month
  - 100 build minutes/month
  - Perfect for personal projects

### Update Dashboard Environment Variables

For **Vercel** deployment:
1. Go to https://vercel.com/dashboard
2. Select your `baseball-dashboard` project
3. Go to "Settings" → "Environment Variables"
4. Add:
   - `NEXT_PUBLIC_USE_API` = `true`
   - `NEXT_PUBLIC_API_URL` = `https://your-api.railway.app`
5. Click "Save"
6. Go to "Deployments" → Click "⋯" → "Redeploy"

For **Local Development:**
```bash
cd apps/baseball-dashboard

# Create .env.local
cat > .env.local << EOF
NEXT_PUBLIC_USE_API=true
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

# Test locally
pnpm dev
# Visit http://localhost:3001
```

### Troubleshooting Vercel

**Dashboard shows old data:**
- Clear browser cache
- Check environment variables in Vercel
- Make sure `NEXT_PUBLIC_USE_API=true`

**CORS errors:**
- Check Railway logs for errors
- Verify API URL in dashboard env vars (no trailing slash)

---

## 🧪 Test Before Deploying

Run preflight checks locally:

```bash
# Full test
pnpm install
pnpm typecheck
pnpm lint
pnpm build:local

# Or all at once
pnpm test:build
```

If all pass, you're ready to deploy!

---

## 📱 Mobile Access

### Add to Home Screen:

**iPhone:**
1. Open site in Safari
2. Share → "Add to Home Screen"
3. Opens like native app!

**Android:**
1. Open in Chrome
2. Menu → "Add to Home Screen"

---

## 🔄 Switching Between Static & Dynamic Data

### Use Static JSON (GitHub Pages):
```bash
# In baseball-dashboard/.env.local
NEXT_PUBLIC_USE_API=false
```

### Use Dynamic API (Railway):
```bash
# In baseball-dashboard/.env.local
NEXT_PUBLIC_USE_API=true
NEXT_PUBLIC_API_URL=https://your-api.railway.app
```

The dashboard checks this flag and fetches from either static JSON files or the live API.

---

## 🎯 Deployment Summary

| Service | Platform | Cost | URL |
|---------|----------|------|-----|
| Landing Page | GitHub Pages | FREE | `thanlon-san.github.io/fantasy/` |
| Baseball Dashboard | GitHub Pages | FREE | `thanlon-san.github.io/fantasy/baseball/` |
| Keeper API | Railway | FREE | `your-app.railway.app` |
| ESPN Recap | Self-hosted | FREE | Local only |

**Total Cost: $0/month** 🎉

Just push to deploy! 🚀
