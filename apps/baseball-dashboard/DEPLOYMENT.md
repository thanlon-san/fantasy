# Deployment Guide

## Quick Deploy to Vercel (Recommended)

### 1. Push to GitHub
```bash
git add .
git commit -m "Add baseball dashboard"
git push
```

### 2. Deploy to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your GitHub repo
4. Vercel auto-detects Next.js
5. Click "Deploy"
6. **Done!** Access from anywhere at `your-app.vercel.app`

### Benefits
- ✅ **Free hosting**
- ✅ **Automatic HTTPS**
- ✅ **Global CDN**
- ✅ **Auto-deploys on git push**
- ✅ **Mobile-friendly**
- ✅ **No server management**

---

## Alternative: GitHub Pages (Static)

### 1. Build Static Site
```bash
pnpm build
```

### 2. Push to GitHub Pages Branch
```bash
# Create gh-pages branch
git checkout -b gh-pages
git add out -f
git commit -m "Deploy to GitHub Pages"
git push origin gh-pages
```

### 3. Enable GitHub Pages
1. Go to repo Settings
2. Pages → Source: `gh-pages` branch
3. Wait 1-2 minutes
4. Access at `username.github.io/fantasy`

### Note
Static export means no server-side features, but all client-side features work!

---

## Local Development

```bash
# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Open http://localhost:3001
```

---

## Connect to Python Backend

### Option 1: Local Backend
Keep Python tools running locally:
```bash
cd apps/keeper-advisor
python scripts/server.py  # Create simple Flask API
```

Dashboard calls `http://localhost:5000/api/...`

### Option 2: Deploy Backend
- **Vercel Serverless**: Convert Python to API routes
- **Railway/Render**: Deploy Python FastAPI
- **AWS Lambda**: Serverless Python functions

---

## Environment Variables

Create `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
# or
NEXT_PUBLIC_API_URL=https://your-api.vercel.app
```

---

## Custom Domain (Optional)

In Vercel:
1. Go to Project Settings
2. Domains
3. Add `baseball.yourdomain.com`
4. Update DNS records
5. Done!

---

## Mobile Access

Once deployed to Vercel:
- Add to iPhone home screen
- Works like a native app
- PWA support (offline mode possible)

---

## Recommended: Vercel

**Why Vercel?**
1. Made by Next.js creators
2. Zero config
3. Perfect performance
4. Free for personal use
5. Auto HTTPS + CDN

**Deploy now:**
```bash
pnpm install -g vercel
vercel
```

Follow prompts → Deployed in 60 seconds! 🚀
