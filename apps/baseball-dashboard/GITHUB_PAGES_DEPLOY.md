# Deploy to GitHub Pages - EASY MODE 🚀

## ✅ One-Time Setup (2 minutes)

### 1. Enable GitHub Pages

Go to your repo settings:
```
https://github.com/thanlon-san/fantasy/settings/pages
```

**Configure:**
- **Source:** GitHub Actions
- That's it! ✅

### 2. Push Your Code

```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy

# Add all dashboard files
git add apps/baseball-dashboard/
git add .github/workflows/deploy-dashboard.yml

# Commit
git commit -m "Add baseball dashboard with auto-deploy"

# Push to GitHub
git push origin main
```

### 3. Wait ~2 Minutes

GitHub Actions will:
1. Install dependencies
2. Build your dashboard
3. Deploy to GitHub Pages

**Watch progress:**
```
https://github.com/thanlon-san/fantasy/actions
```

### 4. Access Your Dashboard

**Live URL:**
```
https://thanlon-san.github.io/fantasy
```

**That's it!** 🎉

---

## 📱 Add to Your Phone

### iPhone
1. Open `https://thanlon-san.github.io/fantasy` in Safari
2. Tap Share → "Add to Home Screen"
3. Now you have an app icon! 📱

### Android
1. Open in Chrome
2. Menu → "Add to Home Screen"
3. Done!

---

## 🔄 Updates (Automatic)

Every time you push changes to `apps/baseball-dashboard/`:

```bash
git add apps/baseball-dashboard/
git commit -m "Update dashboard"
git push
```

**GitHub automatically:**
1. Rebuilds your dashboard
2. Deploys new version
3. Live in ~2 minutes

No manual deploy needed! 🚀

---

## 🧪 Test Locally First

```bash
cd apps/baseball-dashboard

# Start dev server
pnpm dev

# Opens at http://localhost:3001
# Make changes, see them instantly

# When ready, commit & push
# Auto-deploys to GitHub Pages!
```

---

## 🎯 Summary

| Step | Command | Time |
|------|---------|------|
| **1. Enable Pages** | Go to repo settings | 30 sec |
| **2. Push code** | `git push` | 30 sec |
| **3. Wait for build** | GitHub Actions | ~2 min |
| **4. Access** | `thanlon-san.github.io/fantasy` | Done! |

**Total:** 3 minutes to live dashboard! 🎉

---

## 📊 Your Dashboard Features

✅ Daily lineup recommendations  
✅ Waiver wire analysis  
✅ Breakout player detection  
✅ Keeper value calculator  
✅ Mobile-friendly design  
✅ Dark mode support  
✅ **FREE hosting forever**  

---

## 🆘 Troubleshooting

### "404 Not Found"
- Check repo settings → Pages → Source is "GitHub Actions"
- Wait 2-3 minutes after first deploy
- Check Actions tab for build status

### "Build Failed"
```bash
# Test build locally
cd apps/baseball-dashboard
pnpm build

# If it works locally, push again
git push
```

### "Old version showing"
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Clear browser cache
- Wait 1-2 minutes for CDN to update

---

## 🎊 What You Get

✅ **Free hosting** (GitHub Pages)  
✅ **Auto-deploy** (on every push)  
✅ **HTTPS** (automatic)  
✅ **CDN** (fast worldwide)  
✅ **No server** (static site)  
✅ **Mobile app** (add to home screen)  

**All from your existing GitHub repo!**

---

## 🚀 Ready to Deploy?

```bash
# 1. Push code
git add .
git commit -m "Add baseball dashboard"
git push

# 2. Enable Pages in repo settings

# 3. Open URL
https://thanlon-san.github.io/fantasy

# 4. Add to phone home screen

# 5. Use daily!
```

**No Vercel. No extra accounts. Just GitHub.** 🎉

Your dashboard will be live at:
# 🌐 https://thanlon-san.github.io/fantasy

**Clean. Simple. FREE.** 📱⚾🏆
