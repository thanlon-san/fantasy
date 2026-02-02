#!/bin/bash

echo "🚀 Deploying Fantasy Sports Hub with 3 apps..."
echo ""

cd /Users/tyler.hanlon/Documents/GitHub/fantasy

echo "📦 Staging all files..."
git add .

echo "💾 Committing changes..."
git commit -m "Deploy fantasy sports hub with baseball dashboard, recap page, and landing page"

echo "⬆️ Pushing to GitHub..."
git push origin main

echo ""
echo "✅ PUSHED TO GITHUB!"
echo ""
echo "📋 Next steps:"
echo "1. Go to: https://github.com/thanlon-san/fantasy/settings/pages"
echo "2. Set Source to: GitHub Actions"
echo "3. Wait 2-3 minutes for build"
echo "4. Visit: https://thanlon-san.github.io/fantasy/"
echo ""
echo "🎉 Your hub will be live with all 3 apps!"
