# Deploy Dynamic API Architecture

**Goal:** Make your dashboard fetch live data instead of static JSON files.

## Architecture

```
┌─────────────────┐      API Calls      ┌──────────────────┐
│  Next.js        │ ──────────────────> │  FastAPI Backend │
│  Dashboard      │                     │  (Railway.app)   │
│  (Vercel)       │ <────────────────── │                  │
└─────────────────┘    JSON Response    └──────────────────┘
                                               │
                                               │ Uses
                                               ▼
                                        ┌──────────────────┐
                                        │  Python Tools    │
                                        │  (keeper-advisor)│
                                        └──────────────────┘
```

## Step 1: Deploy API to Railway (5 minutes)

### 1.1 Sign Up for Railway
- Go to https://railway.app
- Click "Login with GitHub"
- Authorize Railway

### 1.2 Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose: `thanlon-san/fantasy`
4. Click "Add variables" (skip for now)
5. Click "Deploy"

### 1.3 Configure Root Directory
Railway might try to deploy the whole repo. Fix this:
1. Click on your service
2. Go to "Settings" tab
3. Scroll to "Service Settings"
4. Set **Root Directory**: `apps/keeper-api`
5. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Click "Deploy"

### 1.4 Get Your API URL
1. Go to "Settings" tab
2. Click "Generate Domain"
3. Copy the URL (e.g., `https://keeper-api-production.up.railway.app`)

**✅ Your API is now live!**

Test it:
```bash
curl https://your-api.railway.app/
curl https://your-api.railway.app/api/lineup
```

---

## Step 2: Update Dashboard to Use API (2 minutes)

### 2.1 Configure Environment Variables

For **Vercel** deployment:
1. Go to https://vercel.com/dashboard
2. Select your `baseball-dashboard` project
3. Go to "Settings" → "Environment Variables"
4. Add:
   - `NEXT_PUBLIC_USE_API` = `true`
   - `NEXT_PUBLIC_API_URL` = `https://your-api.railway.app`
5. Click "Save"
6. Go to "Deployments" → Click "⋯" → "Redeploy"

For **GitHub Pages** (current setup):
The dashboard will still use static JSON files. To switch to API:
1. Add environment variables to GitHub Actions workflow
2. Or migrate to Vercel (recommended for dynamic data)

### 2.2 For Local Development
```bash
cd apps/baseball-dashboard

# Create .env.local
cat > .env.local << EOF
NEXT_PUBLIC_USE_API=true
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

# Test locally
npm run dev
# Visit http://localhost:3001
```

---

## Step 3: Deploy Dashboard to Vercel (Optional)

If you want to switch from GitHub Pages to Vercel:

### 3.1 Sign Up for Vercel
- Go to https://vercel.com
- Sign in with GitHub

### 3.2 Import Project
1. Click "Add New..." → "Project"
2. Import `thanlon-san/fantasy`
3. **Framework Preset**: Next.js
4. **Root Directory**: `apps/baseball-dashboard`
5. Add environment variables:
   - `NEXT_PUBLIC_USE_API` = `true`
   - `NEXT_PUBLIC_API_URL` = `https://your-api.railway.app`
6. Click "Deploy"

### 3.3 Get Your Dashboard URL
Vercel provides: `https://fantasy-baseball-dashboard.vercel.app`

**✅ Done!** Your dashboard now fetches live data.

---

## Cost Breakdown (100% Free)

### Railway (API Backend)
- **Free Tier**: $5 credit/month
- **Your Usage**: ~$0.50/month
- **Limits**: 
  - 500 hours/month (plenty)
  - No sleep (always fast)
  - 8GB RAM (you use ~150MB)

### Vercel (Dashboard)
- **Free Tier**: Unlimited
- **Limits**:
  - 100GB bandwidth/month
  - 100 build minutes/month
  - Perfect for personal projects

**Total Cost: $0/month** ✅

---

## Testing Your Setup

### Test API
```bash
# Health check
curl https://your-api.railway.app/

# Get lineup (should return your 24 players)
curl https://your-api.railway.app/api/lineup

# Get keepers
curl https://your-api.railway.app/api/keepers
```

### Test Dashboard
1. Visit your dashboard URL
2. Open browser DevTools (F12)
3. Go to "Network" tab
4. Refresh page
5. You should see requests to your Railway API (not `.json` files)

---

## Troubleshooting

### API shows "Application failed to respond"
- Check Railway logs: Click service → "Deployments" → Latest deploy → "View Logs"
- Common issue: Wrong root directory (should be `apps/keeper-api`)

### Dashboard shows old data
- Clear browser cache
- Check environment variables in Vercel
- Make sure `NEXT_PUBLIC_USE_API=true`

### CORS errors
- Check Railway logs for errors
- Verify API URL in dashboard env vars (no trailing slash)

### "Module not found" in Railway
- Check that Railway is using correct root directory: `apps/keeper-advisor`
- Railway should auto-install from `requirements.txt`

---

## Next Steps

Once deployed:

1. **Add Real-Time Waiver Scanning**
   - Integrate Yahoo API in the backend
   - Update `/api/waivers` endpoint

2. **Add Breakout Detection**
   - Run Statcast queries in background
   - Cache results for fast responses

3. **Add Authentication**
   - Protect your API with API keys
   - Add user login to dashboard

4. **Add Caching**
   - Use Redis to cache API responses
   - Refresh every 30 minutes during season

---

## Reverting to Static (if needed)

If you want to go back to static JSON files:

### On Vercel:
1. Settings → Environment Variables
2. Set `NEXT_PUBLIC_USE_API` = `false`
3. Redeploy

### Keep Railway API:
The API will still be there if you want to use it later!

---

## Support

- Railway: https://railway.app/help
- Vercel: https://vercel.com/docs
- API Issues: Check Railway logs
- Dashboard Issues: Check browser console (F12)
