# 🚀 Multi-App GitHub Pages Deployment

Your Fantasy Sports Hub now hosts **THREE apps** on one URL!

## 🌐 Live URLs (after deployment)

### Landing Page
```
https://thanlon-san.github.io/fantasy/
```
Choose which app to use from a beautiful landing page

### Baseball Dashboard
```
https://thanlon-san.github.io/fantasy/baseball/
```
Daily lineup optimizer, waiver wire, breakouts, keepers

### ESPN Recap Generator
```
https://thanlon-san.github.io/fantasy/recap/
```
Information page about the recap tool with setup instructions

---

## ⚡ Deploy All Three Apps (3 Steps)

### Step 1: Push to GitHub
```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy

git add .
git commit -m "Add multi-app fantasy sports hub"
git push origin main
```

### Step 2: Enable GitHub Pages
1. Go to: **https://github.com/thanlon-san/fantasy/settings/pages**
2. Under "Build and deployment"
3. **Source:** Select **"GitHub Actions"**
4. Save ✅

### Step 3: Wait for Build (~3 minutes)
- Watch: **https://github.com/thanlon-san/fantasy/actions**
- When green checkmark appears, visit:

```
🌐 https://thanlon-san.github.io/fantasy/
```

**All three apps are LIVE!** 🎉

---

## 📱 What You Get

### 1. Landing Page (`/fantasy/`)
- Beautiful homepage
- Links to both apps
- Feature descriptions
- Mobile-friendly design

### 2. Baseball Dashboard (`/fantasy/baseball/`)
- Full Next.js app
- Daily lineup recommendations
- Waiver wire analysis
- Breakout detector
- Keeper optimizer
- Works on mobile
- Add to home screen

### 3. ESPN Recap (`/fantasy/recap/`)
- Info page about the tool
- Setup instructions
- GitHub links
- Documentation

---

## 🔄 How Updates Work

### Update Any App
```bash
# Make changes to any app
cd apps/baseball-dashboard
# or
cd apps/fantasy-hub
# or
cd apps/espn-recap-web

# Push changes
git add .
git commit -m "Update app"
git push
```

**GitHub Actions automatically:**
1. Builds all apps
2. Combines them into one site
3. Deploys everything
4. **Live in ~3 minutes**

---

## 📂 App Structure

```
fantasy/
├── apps/
│   ├── fantasy-hub/           → Landing page (/)
│   │   └── out/               → Built files
│   │
│   ├── baseball-dashboard/    → Baseball tools (/baseball)
│   │   └── out/               → Built files
│   │
│   └── espn-recap-web/        → Recap info (/recap)
│       └── index.html         → Static page
│
└── .github/workflows/
    └── deploy-dashboard.yml   → Builds & deploys all
```

**GitHub Pages serves:**
```
_site/
├── index.html              → Hub landing page
├── baseball/
│   └── index.html          → Baseball dashboard
└── recap/
    └── index.html          → Recap info page
```

---

## 🎨 Customization

### Update Landing Page
Edit `apps/fantasy-hub/app/page.tsx`

### Update Baseball Dashboard
Edit `apps/baseball-dashboard/app/page.tsx`

### Update Recap Page
Edit `apps/espn-recap-web/index.html`

Then just `git push` → Auto-deploys! ✨

---

## 📱 Mobile Use

### Add Hub to Home Screen
1. Open `https://thanlon-san.github.io/fantasy/`
2. Add to Home Screen
3. Tap icon → Choose app

### Add Baseball Dashboard Directly
1. Open `https://thanlon-san.github.io/fantasy/baseball/`
2. Add to Home Screen
3. Opens like native app!

---

## 🎯 Navigation Flow

```
User visits: thanlon-san.github.io/fantasy
           ↓
     Landing Page
    /            \
   /              \
Baseball Dashboard  ESPN Recap
  /baseball/         /recap/
```

### Features:
- ✅ Single GitHub repo
- ✅ One GitHub Pages site
- ✅ Three distinct apps
- ✅ Independent routing
- ✅ All free forever
- ✅ Auto-deploy on push

---

## 🐛 Troubleshooting

### "404 on /baseball/"
- Check GitHub Actions completed successfully
- Hard refresh (Cmd+Shift+R)
- Wait 2-3 minutes for CDN

### "Landing page works, sub-apps don't"
- Verify base paths in next.config.ts
- Check GitHub Actions logs
- Ensure all apps built successfully

### Test Locally
```bash
# Test hub
cd apps/fantasy-hub
pnpm dev

# Test baseball dashboard
cd apps/baseball-dashboard
pnpm dev

# Both should work without errors
```

---

## 🎊 What You Now Have

✅ **Landing page** - Professional hub  
✅ **Baseball dashboard** - Full-featured app  
✅ **ESPN recap info** - Documentation page  
✅ **Single URL** - One domain for all  
✅ **Auto-deploy** - Push to update  
✅ **Mobile-friendly** - All responsive  
✅ **FREE hosting** - GitHub Pages  

---

## 🚀 Ready to Deploy?

```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy

git add .
git commit -m "Add fantasy sports hub with 3 apps"
git push origin main

# Then enable GitHub Pages in repo settings
# Visit: https://thanlon-san.github.io/fantasy/
```

**Three apps. One URL. Zero cost.** 🏆

---

## 📊 Summary

| App | URL | Tech | Purpose |
|-----|-----|------|---------|
| **Hub** | `/fantasy/` | Next.js | Landing page |
| **Baseball** | `/fantasy/baseball/` | Next.js | Full dashboard |
| **Recap** | `/fantasy/recap/` | HTML | Info page |

**All hosted on GitHub Pages. All free. All mobile-friendly.** 📱⚾🏈
