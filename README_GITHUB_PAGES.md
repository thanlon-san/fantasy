# 🎉 FANTASY SPORTS HUB - THREE APPS, ONE URL!

## 🌐 Your Live URLs (after deploy)

```
🏠 Landing Page:        https://thanlon-san.github.io/fantasy/
⚾ Baseball Dashboard:  https://thanlon-san.github.io/fantasy/baseball/
🏈 ESPN Recap:          https://thanlon-san.github.io/fantasy/recap/
```

---

## ✨ What You Get

### 1. **Landing Page** (`/fantasy/`)
Beautiful hub to choose which app to use:
- Modern gradient design
- Links to both apps
- Feature highlights
- Mobile-friendly

### 2. **Baseball Dashboard** (`/fantasy/baseball/`)
Full Next.js app with:
- ⚾ Daily lineup optimizer
- 🎯 Waiver wire analysis
- 🔬 Breakout detector (Statcast)
- ⭐ Keeper value calculator
- 📱 Add to home screen
- 🌙 Dark mode support

### 3. **ESPN Recap Info** (`/fantasy/recap/`)
Information page with:
- 🏈 Feature overview
- 📚 Setup instructions
- 🔗 GitHub links
- 📖 Documentation

---

## 🚀 DEPLOY NOW (One Command!)

### Option 1: Run the Script
```bash
./DEPLOY_MULTI_APP.sh
```

### Option 2: Manual Deploy
```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy

git add .
git commit -m "Deploy fantasy sports hub with 3 apps"
git push origin main
```

### Then Enable GitHub Pages:
1. Go to: https://github.com/thanlon-san/fantasy/settings/pages
2. **Source:** Select **"GitHub Actions"**
3. Save ✅
4. Wait ~3 minutes
5. Visit: https://thanlon-san.github.io/fantasy/

**DONE!** 🎉

---

## 📱 Use on Mobile

### Add to iPhone Home Screen:
1. Open `https://thanlon-san.github.io/fantasy/baseball/`
2. Safari → Share → "Add to Home Screen"
3. Tap icon → Full-screen app!

### Add to Android:
1. Open in Chrome
2. Menu → "Add to Home Screen"
3. Works like native app!

---

## 🎯 How It Works

### Site Structure:
```
thanlon-san.github.io/fantasy/
├── /                   → Landing page (choose app)
├── /baseball/          → Full baseball dashboard
└── /recap/             → ESPN recap info page
```

### Build Process:
```yaml
GitHub Actions:
1. Builds fantasy-hub → Landing page
2. Builds baseball-dashboard → Baseball tools
3. Copies espn-recap-web → Recap info
4. Combines all → Single site
5. Deploys to GitHub Pages
```

### Navigation:
```
User visits hub → Sees beautiful landing page
                → Clicks "Baseball Dashboard"
                → Goes to /fantasy/baseball/
                → Full app loads instantly!
```

---

## 🔄 Update Any App

```bash
# Edit any app
cd apps/baseball-dashboard
# Make changes...

# Push to GitHub
git add .
git commit -m "Update baseball dashboard"
git push

# GitHub Actions auto-rebuilds ALL apps
# Live in ~3 minutes! ✨
```

---

## 📂 Project Structure

```
fantasy/
├── apps/
│   ├── fantasy-hub/           # Landing page
│   │   ├── app/page.tsx       # Edit homepage here
│   │   └── next.config.ts     # Base: /fantasy
│   │
│   ├── baseball-dashboard/    # Baseball tools
│   │   ├── app/page.tsx       # Edit dashboard here
│   │   └── next.config.ts     # Base: /fantasy/baseball
│   │
│   └── espn-recap-web/        # Recap info
│       └── index.html         # Edit page here
│
├── .github/workflows/
│   └── deploy-dashboard.yml   # Builds & deploys all 3
│
├── DEPLOY_MULTI_APP.sh        # One-command deploy
└── MULTI_APP_DEPLOY.md        # Full docs
```

---

## 🎨 Customize

### Landing Page:
```typescript
// apps/fantasy-hub/app/page.tsx
export default function Home() {
  return (
    // Edit this React component
  );
}
```

### Baseball Dashboard:
```typescript
// apps/baseball-dashboard/app/page.tsx
export default function Home() {
  return (
    // Edit dashboard layout
  );
}
```

### Recap Page:
```html
<!-- apps/espn-recap-web/index.html -->
<!-- Edit HTML directly -->
```

**Push changes → Auto-deploys!**

---

## ✅ Features

| Feature | Status |
|---------|--------|
| **Free Hosting** | ✅ GitHub Pages |
| **Custom Domain** | ✅ Can add later |
| **HTTPS** | ✅ Automatic |
| **CDN** | ✅ Global, fast |
| **Mobile Support** | ✅ Responsive |
| **Add to Home** | ✅ PWA-ready |
| **Auto Deploy** | ✅ On git push |
| **Zero Config** | ✅ Just enable |

---

## 🐛 Troubleshooting

### "404 Not Found"
- Check Actions completed (green checkmark)
- Hard refresh: Cmd+Shift+R
- Wait 2-3 minutes for CDN

### "Landing works, /baseball/ doesn't"
- Check build logs in Actions tab
- Verify base paths in next.config.ts
- Ensure all apps built successfully

### Test Locally First:
```bash
# Test landing page
cd apps/fantasy-hub && pnpm dev

# Test baseball dashboard  
cd apps/baseball-dashboard && pnpm dev

# Both should work without errors
```

---

## 📊 Deployment Checklist

- [ ] Run `./DEPLOY_MULTI_APP.sh` OR `git push`
- [ ] Go to repo settings → Pages
- [ ] Set Source to "GitHub Actions"
- [ ] Wait for Actions to complete (~3 min)
- [ ] Visit `https://thanlon-san.github.io/fantasy/`
- [ ] Test all three routes work
- [ ] Add baseball dashboard to phone
- [ ] Share with league!

---

## 🎊 What This Means

### Before:
- Terminal commands only
- One computer access
- Manual processes

### After:
- ✅ Beautiful web apps
- ✅ Access from anywhere
- ✅ Use on phone/tablet
- ✅ Share with friends
- ✅ Professional presentation
- ✅ Auto-deploy on update
- ✅ **All FREE forever**

---

## 🏆 Your Complete Toolkit

```
📱 Landing Page
   ↓
   ├─→ ⚾ Baseball Dashboard
   │      ├─ Daily lineups
   │      ├─ Waiver wire
   │      ├─ Breakouts
   │      └─ Keepers
   │
   └─→ 🏈 ESPN Recap
          ├─ Tool info
          ├─ Setup guide
          └─ Documentation
```

**All hosted on GitHub Pages. All free. All mobile-friendly.** 📱🏆

---

## 🚀 READY? DEPLOY NOW!

```bash
./DEPLOY_MULTI_APP.sh
```

**Then enable GitHub Pages in repo settings.**

**Live in 3 minutes!** ⚡

---

**Your league-mates won't know what hit them.** 🎯💪
