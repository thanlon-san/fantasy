# Quick Start - Baseball Dashboard

## 🚀 Get Started in 3 Steps

### 1. Install Dependencies
```bash
cd apps/baseball-dashboard

# Clean install (if you had issues)
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### 2. Run Locally
```bash
pnpm dev
```

Open [http://localhost:3001](http://localhost:3001) 🎉

### 3. Deploy to Vercel (Access from anywhere!)
```bash
# Install Vercel CLI
pnpm install -g vercel

# Deploy
vercel

# Follow prompts → Done in 60 seconds!
```

---

## 📱 Access from Your Phone

Once deployed to Vercel:

### iPhone
1. Open dashboard in Safari
2. Tap Share button
3. "Add to Home Screen"
4. Opens like a native app!

### Android  
1. Open dashboard in Chrome
2. Menu → "Add to Home Screen"
3. Works offline!

---

## 🔗 Connect to Python Backend

### Option A: Mock Data (Works Now)
The dashboard works with demo data out of the box.

### Option B: Connect to Your Python Tools

#### Step 1: Create Simple API
Create `apps/keeper-advisor/api/server.py`:

```python
from flask import Flask, jsonify
from flask_cors import CORS
import sys
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Allow dashboard to connect

# Add your keeper-advisor to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lineup_optimizer import LineupOptimizer
from src.importers import CSVImporter

@app.route('/api/lineup')
def get_lineup():
    roster = CSVImporter.import_roster("data/my_roster_from_yahoo.csv")
    optimizer = LineupOptimizer()
    recs = optimizer.get_daily_recommendations(roster)
    
    return jsonify([{
        'player': rec.player.name,
        'recommendation': rec.recommendation.value,
        'confidence': rec.confidence_score,
        'opponent': rec.opponent,
        'reasons': rec.reasons
    } for rec in recs])

@app.route('/api/waivers')
def get_waivers():
    # Similar implementation
    pass

@app.route('/api/breakouts')
def get_breakouts():
    # Similar implementation
    pass

if __name__ == '__main__':
    app.run(port=5000)
```

#### Step 2: Install Flask
```bash
cd apps/keeper-advisor
pip install flask flask-cors
python api/server.py
```

#### Step 3: Connect Dashboard
Create `apps/baseball-dashboard/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Now your dashboard calls real Python backend! 🎉

---

## 🎨 Customize

Edit `app/page.tsx` to change:
- Colors
- Layout
- Features
- Data sources

Tailwind CSS makes styling easy!

---

## 📦 What's Included

- ✅ Modern, mobile-friendly UI
- ✅ Dark mode support  
- ✅ Responsive design (phone/tablet/desktop)
- ✅ Fast loading with Next.js
- ✅ Beautiful components (shadcn/ui style)
- ✅ TypeScript for safety
- ✅ Ready to deploy to Vercel

---

## 🐛 Troubleshooting

### "Cannot find module"
```bash
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### "Port 3001 already in use"
```bash
# Kill existing process
lsof -ti:3001 | xargs kill -9

# Or use different port
pnpm dev --port 3002
```

### "Build failed"
Check `next.config.ts` - make sure `output: "export"` is set for static sites.

---

## 🚀 Next Steps

1. **Run it locally**: `pnpm dev`
2. **Customize it**: Edit `app/page.tsx`
3. **Deploy it**: `vercel`
4. **Use it daily**: Add to phone home screen!

**You now have a web app you can access anywhere, anytime.** 📱💻

No terminal needed. Just open the URL. 🎉
