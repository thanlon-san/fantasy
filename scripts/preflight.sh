#!/bin/bash
set -e

echo "✈️  Running preflight checks before deployment..."
echo ""

# 1. Clean install
echo "📦 Installing dependencies..."
pnpm install --no-frozen-lockfile
echo "✅ Dependencies installed"
echo ""

# 2. Type check
echo "🔍 Type checking..."
cd apps/fantasy-hub && npx tsc --noEmit && cd ../..
cd apps/baseball-dashboard && npx tsc --noEmit && cd ../..
echo "✅ Type check passed"
echo ""

# 3. Lint
echo "🧹 Linting..."
cd apps/fantasy-hub && npm run lint && cd ../..
cd apps/baseball-dashboard && npm run lint && cd ../..
echo "✅ Lint passed"
echo ""

# 4. Build
echo "🏗️  Building all apps..."
cd apps/fantasy-hub && pnpm build && cd ../..
cd apps/baseball-dashboard && pnpm build && cd ../..
echo "✅ Build complete"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Preflight checks PASSED! Ready to deploy."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next step: git push origin main"
