# Baseball Dashboard

Modern Next.js dashboard for fantasy baseball keeper league analysis.

## Features

- 🎯 **Daily Lineup Optimizer** - Smart lineup recommendations with confidence scores
- 🔍 **Waiver Wire Scanner** - Find hidden gems on the wire
- ⚡ **Breakout Detection** - Statcast-powered breakout alerts
- 💎 **Keeper Analysis** - Calculate keeper value and surplus

## Quick Start

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev  # http://localhost:3001

# Build for production
pnpm build
```

## Configuration

Create `.env.local` for dynamic API mode:

```bash
NEXT_PUBLIC_USE_API=true
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Or leave unset to use static JSON data (default).

## Tech Stack

- Next.js 15 (App Router)
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui components
- Radix UI primitives

## Deployment

Auto-deploys to GitHub Pages: **https://thanlon-san.github.io/fantasy/baseball/**

See [Deployment Guide](../../docs/DEPLOYMENT.md) for details.

## Documentation

- [Development Guide](../../docs/DEVELOPMENT.md)
- [Deployment Guide](../../docs/DEPLOYMENT.md)
