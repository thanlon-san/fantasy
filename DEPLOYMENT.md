# Deployment Guide

Your Fantasy Sports Hub deploys to **GitHub Pages** for free hosting.

## 🌐 Live URLs

```
Landing Page:  https://thanlon-san.github.io/fantasy/
Baseball:      https://thanlon-san.github.io/fantasy/baseball/
Recap:         https://thanlon-san.github.io/fantasy/recap/
```

---

## ⚡ Quick Deploy

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

4. **Visit your site!**
   - https://thanlon-san.github.io/fantasy/

---

## 🔄 Updates (Automatic)

Every push to `main` triggers auto-deployment:

```bash
# Make changes
git add .
git commit -m "Update dashboard"
git push

# GitHub automatically rebuilds and deploys
# Live in ~3 minutes!
```

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

## 🧪 Test Before Deploying

Run preflight checks locally:

```bash
# Full test
pnpm preflight

# Or manual steps
pnpm install
pnpm typecheck
pnpm lint
pnpm build:local
```

If all pass, you're ready to push!

---

## 🐛 Troubleshooting

### Build Fails
- Check GitHub Actions tab: `/actions`
- Look for error logs in failed workflow
- Test build locally first: `pnpm build:local`

### Site Shows 404
- Verify Pages enabled (Settings → Pages)
- Check Actions completed (green checkmark)
- Hard refresh: Cmd+Shift+R
- Wait 2-3 minutes for CDN cache

### Old Version Showing
- Hard refresh browser
- Clear cache
- Wait for CDN propagation (~2 min)

---

## 📊 Build Details

GitHub Actions workflow (`.github/workflows/deploy-dashboard.yml`):
1. Checks out code
2. Installs pnpm
3. Builds fantasy-hub (landing page)
4. Builds baseball-dashboard
5. Copies espn-recap-web (static)
6. Combines all into `_site/`
7. Deploys to GitHub Pages

**Total time:** ~3-4 minutes

---

## 🎯 Summary

- **Cost:** FREE (GitHub Pages)
- **Updates:** Automatic on push
- **HTTPS:** Automatic
- **CDN:** Global, fast
- **Mobile:** Fully responsive

Just push to deploy! 🚀
