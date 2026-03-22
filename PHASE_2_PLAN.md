# Fantasy Baseball Dashboard — Phase 2 Build Plan

This document is a complete, self-contained specification for the next phase of development. It assumes no prior context. Read every section before writing any code.

---

## 1. What This Project Is

A personal fantasy baseball intelligence system for a single user (Tyler, team "2balls") in the California Palm League — a 12-team, Yahoo Fantasy, H2H categories, 24-round snake keeper league.

**Tech stack:**
- **Frontend**: Next.js 15 / React 19, Tailwind CSS, Radix UI, deployed to GitHub Pages as a static site
- **Python backend**: FastAPI server (`draft_server.py`) that runs locally during draft/in-season; serves the frontend via REST API
- **Data pipeline**: Python scripts that fetch from Yahoo Fantasy API, MLB Stats API, Baseball Savant (Statcast) → write static JSON files → Next.js reads those JSON files at build time

**Monorepo layout (pnpm workspaces):**
```
fantasy/
  apps/
    baseball-dashboard/     ← Next.js frontend (the main app)
      app/                  ← Next.js App Router pages
        page.tsx            ← Main dashboard (daily lineup, waiver wire, breakouts, keepers)
        draft/page.tsx      ← Pre-draft keeper board
        draft/live/page.tsx ← Live draft UI (requires Python server)
        matchup/page.tsx    ← H2H week matchup (requires Python server)
        standings/page.tsx  ← Category standings (requires Python server)
        closers/page.tsx    ← Closer monitor (requires Python server)
      public/api/           ← Static JSON files served by GitHub Pages
        daily_lineup.json
        waiver_wire.json
        breakouts.json
        keepers.json
        league_keepers.json
    keeper-advisor/         ← Python data engine
      src/                  ← Core Python modules
        yahoo_client.py     ← Yahoo Fantasy API wrapper
        yahoo_oauth_manual.py ← OAuth2 implementation
        stats_fetcher.py    ← MLB Stats API (statsapi.mlb.com/api/v1)
        statcast_client.py  ← Baseball Savant via pybaseball
        lineup_optimizer.py ← Daily lineup scoring engine
        waiver_analyzer.py  ← Waiver wire ranking engine
        breakout_detector.py ← Statcast breakout signal detection
        breakout_tracker.py ← Prediction accuracy tracking
        analyzer.py         ← Keeper value analysis
        adp_fetcher.py      ← FantasyPros ADP scraper
        importers.py        ← CSV/JSON roster import
        models.py           ← Player, Roster dataclasses
        daily_matchups.py   ← MLB schedule + probable pitchers
        cache_manager.py    ← File-based cache with TTL
      scripts/
        export_dashboard_data.py  ← Master pipeline: generates all 4 JSON files
        draft_assistant.py        ← Terminal draft tool
        draft_server.py           ← FastAPI server (port 8001)
        fetch_roster_with_draft.py
        fetch_yahoo_roster.py
      config/
        league_settings.json ← League config (scoring cats, roster slots, etc.)
        oauth2.json          ← Yahoo OAuth credentials (NOT committed to repo)
      data/
        my_roster_from_yahoo.csv  ← Your current roster (NOT committed to repo)
  .github/workflows/
    update-data.yml   ← Daily cron: runs export_dashboard_data.py, commits JSON
    deploy-dashboard.yml ← On push to main: builds Next.js, deploys to GitHub Pages
```

---

## 2. League Configuration

**Scoring categories (H2H, 12 categories):**
- Batting (6): R, H, HR, RBI, SB, OPS
- Pitching (6): SV, HR (allowed), K, ERA, WHIP, QS

**Yahoo stat IDs (confirmed from league settings API):**
```
Batting:  R=7  H=8  HR=12  RBI=13  SB=16  OPS=55
Pitching: SV=32  HR_allowed=38  K=42  ERA=26  WHIP=27  QS=83
Display:  H/AB=60  IP=50  (non-scoring, shown in UI but not counted)
```

**Roster slots:** C×1, 1B×1, 2B×1, 3B×1, SS×1, OF×3, Util×2, SP×6, RP×3, P×1 (flex pitcher), BN×4

**League key:** `469.l.25136`  
**My team:** `2balls`, team ID 2, team key `469.l.25136.t.2`  
**Season:** 2026, week 1 starts 2026-03-25

**Keeper rules:** Max 3 keepers. Cost = `draft_round - years_kept - 1`. Undrafted FAs start at round 12. Rounds 13+ treated as round 12.

**Pitching strategy:** The user stacks closers to dominate ERA, WHIP, SV, HR Allowed (4 of 6 pitching cats). Has Garrett Crochet (ace SP) + Mason Miller (elite closer) as keepers. This informs all recommendations — relievers get priority in late draft rounds and waiver wire pitching adds.

---

## 3. Authentication

Yahoo OAuth2 is implemented in `src/yahoo_oauth_manual.py`. Tokens are in `apps/keeper-advisor/config/oauth2.json` (this file is NOT committed to the repo — it exists locally on the developer's machine).

**Loading the client:**
```python
import sys
from pathlib import Path
APP_ROOT = Path("apps/keeper-advisor")  # adjust relative to your working dir
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(Path("packages")))

from src.yahoo_oauth_manual import YahooOAuth2

oauth = YahooOAuth2.load_from_file("apps/keeper-advisor/config/oauth2.json")
# Token may be expired — always attempt a refresh before use:
oauth.refresh_access_token()
oauth.save_to_file("apps/keeper-advisor/config/oauth2.json")
```

**Making API calls:**
```python
import requests
session = requests.Session()
session.headers["Authorization"] = f"Bearer {oauth.access_token}"
url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/469.l.25136/teams?format=json"
resp = session.get(url, timeout=15)
data = resp.json()["fantasy_content"]
```

**Using the existing YahooDraft client** (from `draft_server.py` / `draft_assistant.py`):
```python
from scripts.draft_assistant import YahooDraft  # or inline the class
yahoo = YahooDraft()  # loads oauth2.json automatically
data = yahoo._get("/league/469.l.25136/scoreboard")  # handles token refresh
```

---

## 4. The Data Pipeline (how daily data flows)

```
GitHub Actions (8am ET daily)
  → export_dashboard_data.py
    → loads my_roster_from_yahoo.csv (BROKEN — see Task 1)
    → LineupOptimizer → daily_lineup.json
    → WaiverAnalyzer (hardcoded 10 FAs — BROKEN — see Task 2)
      → WaiverAnalyzer → waiver_wire.json
    → BreakoutDetector → breakouts.json
    → KeeperAnalyzer → keepers.json
  → commits JSON files to repo
  → deploy-dashboard.yml triggers on push
  → GitHub Pages serves updated static files
```

**The frontend reads static JSON** from `public/api/*.json`. When `NEXT_PUBLIC_USE_API=true` (local dev only), it hits `http://localhost:8000` instead.

---

## 5. What's Currently Broken (fix these first)

### 5A. The daily pipeline fails silently in GitHub Actions

`export_dashboard_data.py` immediately calls:
```python
roster = CSVImporter.import_roster(
    app_root / "data" / "my_roster_from_yahoo.csv",
    team_name="2balls"
)
```
The file `data/my_roster_from_yahoo.csv` is not committed to the repo (it's local-only). The workflow runs successfully but the exception handler writes empty JSON files. The dashboard says "Auto-updates daily at 8am ET" but hasn't been generating real data since setup.

**The existing Yahoo client already has the roster fetch method** — `get_team_roster()` in `src/yahoo_client.py`. The fix is to replace the CSV load with a live Yahoo API call at the top of `export_dashboard_data.py`.

### 5B. The waiver wire analyzes the wrong players

```python
# apps/keeper-advisor/scripts/export_dashboard_data.py, line ~172
sample_free_agents = [
    {'name': 'Yoshinobu Yamamoto', ...},  # 95% rostered — not a free agent
    ...
]
```
This is a hardcoded list of players, not real free agents from the league. Yoshinobu Yamamoto is explicitly labeled with `rostered_pct: 95%` in the output — he's already owned by someone. The `YahooFantasyClient.get_free_agents()` method in `src/yahoo_client.py` already exists and works.

---

## 6. Phase 2 Tasks (prioritized)

---

### TASK 1: Fix the daily pipeline — fetch roster from Yahoo at runtime

**File to modify:** `apps/keeper-advisor/scripts/export_dashboard_data.py`

**What to do:** Replace the CSV roster load at the top of the script with a live Yahoo API fetch. The result must produce a `Roster` object identical to what `CSVImporter.import_roster()` returns (same `Roster` dataclass from `src/models.py`).

**Existing working method:**
```python
# src/yahoo_client.py — get_team_roster(team_key) already works
# Returns list of dicts: [{name, player_key, position, eligible_positions, editorial_team_abbr, ...}]
```

**Implementation:**

Replace this block at the top of `export_dashboard_data.py`:
```python
# REMOVE:
from src.importers import CSVImporter
roster = CSVImporter.import_roster(
    app_root / "data" / "my_roster_from_yahoo.csv",
    team_name="2balls"
)
```

With:
```python
from src.yahoo_oauth_manual import YahooOAuth2
from src.yahoo_client import YahooFantasyClient
from src.models import Player, Roster

def fetch_roster_from_yahoo() -> Roster:
    """Fetch current roster from Yahoo Fantasy API."""
    config_path = app_root / "config" / "oauth2.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Yahoo OAuth config not found: {config_path}")
    
    oauth = YahooOAuth2.load_from_file(str(config_path))
    oauth.refresh_access_token()
    oauth.save_to_file(str(config_path))
    
    client = YahooFantasyClient(oauth)
    LEAGUE_KEY = "469.l.25136"
    MY_TEAM_KEY = "469.l.25136.t.2"
    
    # Also need ADP for each player — use ADPFetcher
    from src.adp_fetcher import ADPFetcher
    adp_fetcher = ADPFetcher()
    
    raw_players = client.get_team_roster(MY_TEAM_KEY)
    
    roster = Roster(team_name="2balls", league_name="California Palm League", year=2026)
    for p in raw_players:
        name = p.get("name", "")
        if not name:
            continue
        
        position = p.get("display_position", p.get("eligible_positions", ["UTIL"])[0] if p.get("eligible_positions") else "UTIL")
        team = p.get("editorial_team_abbr", "FA")
        adp = adp_fetcher.get_player_adp(name) or 300.0
        
        player = Player(
            name=name,
            position=position,
            team=team,
            draft_round=12,       # Unknown for current season; use 12 as default
            draft_year=2025,      # Assume drafted last year
            years_kept=0,
            adp=adp,
            is_undrafted_fa=False,
        )
        roster.add_player(player)
    
    return roster

roster = fetch_roster_from_yahoo()
print(f"✅ Loaded {len(roster.players)} players from Yahoo API")
```

**Also add to GitHub Actions workflow** (`update-data.yml`) — the oauth2.json file needs to be available. Add it as a GitHub Actions secret:
- Add a repository secret named `YAHOO_OAUTH_JSON` containing the full contents of `oauth2.json`
- Add a step in the workflow before `Run data export`:
```yaml
- name: Set up Yahoo OAuth credentials
  run: |
    mkdir -p apps/keeper-advisor/config
    echo '${{ secrets.YAHOO_OAUTH_JSON }}' > apps/keeper-advisor/config/oauth2.json
```

**Success criteria:** Running `python scripts/export_dashboard_data.py` locally (with `oauth2.json` present) produces a `daily_lineup.json` with real roster players, not from a CSV file. The GitHub Actions workflow produces non-empty JSON files.

---

### TASK 2: Fix the waiver wire — use real Yahoo free agents

**File to modify:** `apps/keeper-advisor/scripts/export_dashboard_data.py`

**What to do:** Replace the hardcoded `sample_free_agents` list with a live fetch of actual available free agents from Yahoo.

**Existing working method:**
```python
# src/yahoo_client.py
client.get_free_agents(league_key, count=50)
# Returns list of dicts with keys: name, player_key, eligible_positions, editorial_team_abbr
# Already in the exact format that waiver_analyzer.analyze_free_agents() expects
```

**Implementation:**

In the "Waiver Wire Analysis" section of `export_dashboard_data.py`, replace:
```python
# REMOVE this block:
sample_free_agents = [
    {'name': 'Yoshinobu Yamamoto', ...},
    ...  # all 10 hardcoded entries
]
```

With:
```python
# Fetch real free agents from Yahoo
try:
    print("  Fetching free agents from Yahoo...")
    # Reuse the oauth/client initialized in fetch_roster_from_yahoo()
    # You'll need to store client/LEAGUE_KEY at module scope or re-init here
    free_agents_raw = client.get_free_agents(LEAGUE_KEY, count=75)
    
    # Adapter: get_free_agents returns {name, player_key, eligible_positions, editorial_team_abbr}
    # WaiverAnalyzer expects {name, eligible_positions, editorial_team_abbr}
    sample_free_agents = [
        {
            "name": fa["name"],
            "eligible_positions": fa.get("eligible_positions", []),
            "editorial_team_abbr": fa.get("editorial_team_abbr", "FA"),
        }
        for fa in free_agents_raw
        if fa.get("name")
    ]
    print(f"  Got {len(sample_free_agents)} real free agents from Yahoo")
except Exception as e:
    print(f"  ⚠️  Yahoo FA fetch failed: {e}. Using fallback list.")
    sample_free_agents = []  # WaiverAnalyzer handles empty list gracefully
```

**Refactor needed:** Move the `client` and `LEAGUE_KEY` variables to module scope so they're accessible in the waiver section. The cleanest approach is to initialize OAuth/client once at the top of the script (after the roster fetch) and reuse them throughout.

**Success criteria:** `waiver_wire.json` contains players who are actually available as free agents in the league (0% rostered or low rostered_pct), not already-rostered stars.

---

### TASK 3: Matchup-aware lineup suggestions

**What to build:** Connect the matchup page's swing category data to the lineup optimizer so that on days when the draft server is running, the main dashboard shows a "Focus this week:" callout that surfaces which players on your roster specifically help flip your swing categories.

**New endpoint to add to `draft_server.py`:**
```python
@app.get("/season/lineup-focus")
def get_lineup_focus():
    """
    Returns players on my roster who most help with this week's swing categories.
    Combines matchup data (which categories are close) with roster data (who helps there).
    """
```

**Logic:**
1. Call `get_matchup()` internally (reuse the function, don't make another HTTP request)
2. Identify swing categories: `status in ("close_win", "close_loss")`
3. For each swing category, identify which roster players contribute to it:
   - Batting swing cats (R, H, HR, RBI, SB, OPS): return batters sorted by projected contribution (use their ADP as a proxy for overall quality; better players contribute more)
   - Pitching swing cats (K, ERA, WHIP, SV, HR_allowed): return pitchers sorted by relevance
4. For `close_loss` categories specifically, flag the top 1-2 waiver adds that would help

**Response shape:**
```json
{
  "week": 1,
  "swing_categories": [
    {
      "stat_name": "HR",
      "stat_id": "12", 
      "status": "close_loss",
      "my_value": 8,
      "opp_value": 10,
      "focus_players": ["Aaron Judge", "Jose Ramirez"],
      "waiver_suggestion": "Consider streaming a power hitter if available"
    }
  ],
  "season_started": false
}
```

**Frontend change:** In `apps/baseball-dashboard/app/page.tsx`, add a banner below the header (when `NEXT_PUBLIC_DRAFT_API_URL` is set and reachable) that polls `/season/lineup-focus` every 60 seconds. Show a compact "This week: focus on HR (–2) and SB (–4) — start your best hitters with these skills." Only show when `swing_categories.length > 0` and season has started.

---

### TASK 4: Category trajectory tracker

**What to build:** A new page at `/trajectory` that shows your rank in each of the 12 scoring categories across the current season, week by week.

**New endpoint to add to `draft_server.py`:**
```python
@app.get("/season/trajectory")
def get_trajectory():
    """
    Returns weekly category rank history for my team.
    Fetches league scoreboard for each past week and computes my rank per category.
    """
```

**Logic:**
1. Get `current_week` from `GET /league/{key}/scoreboard` metadata
2. For weeks 1 through `current_week - 1`, fetch `/league/{key}/scoreboard;week={w}`
3. For each past week's matchup involving my team: record my stats in each category
4. For each category, compute my rank that week by comparing against all other teams
5. Cache the full result for 1 hour (this is expensive — 12+ API calls for a full season)

**Response shape:**
```json
{
  "current_week": 5,
  "categories": {
    "7": {
      "name": "R",
      "label": "Runs",
      "group": "batting",
      "better": "high",
      "weekly_ranks": [3, 2, 4, 1, null],
      "weekly_values": [42, 38, 45, 51, null],
      "trend": "improving",
      "avg_rank": 2.5
    }
  }
}
```

**Frontend (`app/trajectory/page.tsx`):** A page with 12 mini sparkline charts (one per category), each showing your weekly rank. Color the line green if rank ≤ 4, yellow if 5–8, red if ≥ 9. Show the 4-week trend arrow. Add a summary at the top: "Dominating: ERA, WHIP, SV | Struggling: K, QS | Improving: HR".

**Navigation:** Add `<Link href="/trajectory"><Button>Trajectory</Button></Link>` to the dashboard header nav in `app/page.tsx`.

---

### TASK 5: Opponent scouting card

**What to build:** Before each weekly matchup, show a scouting report on your opponent — their strengths, weaknesses, and a specific game plan.

**New endpoint to add to `draft_server.py`:**
```python
@app.get("/season/opponent")
def get_opponent_scouting():
    """
    Returns scouting report on this week's opponent.
    """
```

**Logic:**
1. Get this week's matchup to identify the opponent's team key
2. Fetch their roster: `GET /team/{opp_team_key}/roster`
3. Fetch their season stats: `GET /team/{opp_team_key}/stats`
4. Fetch league standings to see their category rankings
5. Build the scouting report:
   - Their **strengths**: categories where they rank 1–4 in the league
   - Their **weaknesses**: categories where they rank 9–12
   - **Your advantages**: categories where you outrank them in season standings
   - **Threat categories**: categories where they outrank you + it's currently close

**Response shape:**
```json
{
  "opponent_name": "sallywithacrouton",
  "their_strengths": ["ERA", "WHIP"],
  "their_weaknesses": ["SB", "HR"],
  "your_advantages": ["SV", "OPS"],
  "threat_categories": ["K"],
  "game_plan": "They dominate pitching rate stats — you should match them there. Focus lineup on SB and HR hitters to exploit their weaknesses. K is a battleground — stream a high-K SP if available.",
  "week": 1
}
```

**The `game_plan` string** should be generated from a simple template based on the category analysis — no LLM needed for v1.

**Frontend change:** Add an "Opponent Scout" section to `/matchup/page.tsx` below the swing categories callout. Show their strengths as red badges, weaknesses as green badges, and the game plan text.

---

### TASK 6: Deploy the API server (remove local-only dependency)

**What to do:** Deploy `draft_server.py` to Railway (the `railway.json` already exists in `apps/keeper-api/`). This makes `/matchup`, `/standings`, `/closers`, `/trajectory`, and `/opponent` work from anywhere — including the deployed GitHub Pages site — without needing to run a local Python server.

**Files involved:**
- `apps/keeper-advisor/scripts/draft_server.py` — the server to deploy
- `apps/keeper-api/railway.json` — Railway config already present

**Steps:**
1. Create a `Procfile` or update `railway.json` to point at `draft_server.py`:
```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": { "startCommand": "python apps/keeper-advisor/scripts/draft_server.py --host 0.0.0.0 --port $PORT" }
}
```
2. Set Railway environment variables: `YAHOO_OAUTH_JSON` (the full contents of `oauth2.json` as a secret)
3. Update `draft_server.py` to load OAuth from an env var when `oauth2.json` doesn't exist as a file:
```python
import os, json, tempfile

OAUTH_CONFIG = APP_ROOT / "config" / "oauth2.json"
if not OAUTH_CONFIG.exists():
    # Running in Railway/CI — load from environment variable
    oauth_json = os.environ.get("YAHOO_OAUTH_JSON")
    if oauth_json:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write(oauth_json)
        tmp.close()
        OAUTH_CONFIG = Path(tmp.name)
```
4. Update `apps/baseball-dashboard/.env.example`:
```
NEXT_PUBLIC_DRAFT_API_URL=https://your-railway-app.up.railway.app
```
5. Set `NEXT_PUBLIC_DRAFT_API_URL` in GitHub repository secrets so the build uses the deployed URL
6. Update `deploy-dashboard.yml` to pass the env var during the Next.js build:
```yaml
- name: Build baseball dashboard
  working-directory: apps/baseball-dashboard
  run: pnpm build
  env:
    NODE_ENV: production
    NEXT_PUBLIC_DRAFT_API_URL: ${{ secrets.DRAFT_API_URL }}
```

**Success criteria:** Visiting `https://thanlon-san.github.io/fantasy/baseball/matchup` (no local server running) shows live matchup data.

---

## 7. Key Technical Patterns

### Yahoo API response structure
Yahoo wraps everything in `fantasy_content` and uses mixed array/object structures:
```python
# The outer wrapper
data = resp.json()["fantasy_content"]

# League data is always: data["league"] = [meta_dict, content_dict]
meta = data["league"][0]    # {league_key, name, current_week, ...}
content = data["league"][1] # {scoreboard: {...}} or {standings: {...}} etc.

# Teams are in numbered dicts with a "count" key:
teams_dict = content["standings"][0]["teams"]
for k, v in teams_dict.items():
    if k == "count": continue
    team_arr = v["team"]  # [[{props...}], {standings}]
    props = team_arr[0]   # list of property dicts
    name = next((p["name"] for p in props if isinstance(p, dict) and "name" in p), "?")
```

### Stat parsing pattern
```python
def _parse_stats(stats_list: list) -> dict:
    """Parse [{stat: {stat_id, value}}, ...] → {stat_id: float}"""
    result = {}
    for entry in stats_list:
        s = entry.get("stat", {})
        sid = str(s.get("stat_id", ""))
        val = s.get("value", "")
        if sid in SCORING_STAT_IDS:
            try:
                result[sid] = float(val) if val not in ("", "-", None) else None
            except (ValueError, TypeError):
                result[sid] = None
    return result
```

### The `_yahoo_get` helper (already in `draft_server.py`)
```python
def _yahoo_get(path: str):
    """Makes authenticated Yahoo API call; returns fantasy_content or None."""
    if _yahoo is None:
        return None
    return _yahoo._get(f"https://fantasysports.yahooapis.com/fantasy/v2{path}")
```

### Frontend polling pattern (used in all season pages)
```typescript
const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

const fetch_ = useCallback(async () => {
  const res = await fetch(`${API_BASE}/season/your-endpoint`, { cache: "no-store" })
  if (!res.ok) throw new Error(`API ${res.status}`)
  setData(await res.json())
}, [])

useEffect(() => {
  fetch_()
  const t = setInterval(() => fetch_(), 60_000)  // poll every 60s
  return () => clearInterval(t)
}, [fetch_])
```

### Adding navigation links to the dashboard header
In `apps/baseball-dashboard/app/page.tsx`, the nav buttons are in the header section (around line 270). Follow the exact same pattern as the existing buttons:
```tsx
import { YourIcon } from "lucide-react"

<Link href="/your-page">
  <Button variant="outline" size="sm" className="gap-1.5">
    <YourIcon className="h-4 w-4" />
    Your Page
  </Button>
</Link>
```

---

## 8. Code Style Conventions

**Python:**
- All new Python files go in `apps/keeper-advisor/scripts/` (scripts) or `apps/keeper-advisor/src/` (reusable modules)
- Path setup at the top of every script:
```python
import sys
from pathlib import Path
APP_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "packages"))
```
- File-based caching uses `src/cache_manager.py`: `cache = get_cache(); cache.get(key, max_age_hours=6); cache.set(key, data)`
- All new FastAPI endpoints go in `apps/keeper-advisor/scripts/draft_server.py` under the existing `# ─── Season endpoints ─────────────────────────────────────────────` section

**TypeScript/React:**
- All new pages go in `apps/baseball-dashboard/app/{route}/page.tsx`
- Use `"use client"` directive on all interactive pages
- Dark theme: background is `slate-950`, cards are `slate-900/60`, borders are `slate-700/60`
- Import UI components from `@/components/ui/` (Button, Badge, etc. — all Radix-based)
- Icons from `lucide-react` only
- `NEXT_PUBLIC_DRAFT_API_URL` env var for all API calls, defaulting to `"http://localhost:8001"`
- No inline styles — Tailwind classes only
- ESLint is strict: no unused variables, no unescaped entities in JSX (`'` → `&apos;`)

---

## 9. Build Order

Complete these in order. Each task is independently deployable.

1. **Task 1** (roster from Yahoo) — unblocks the daily pipeline. Do this before anything else.
2. **Task 2** (real free agents) — depends on Task 1 (reuses the Yahoo client init).
3. **Task 3** (matchup-aware suggestions) — builds on existing `/season/matchup` endpoint.
4. **Task 4** (trajectory tracker) — standalone, no dependencies on Tasks 1–3.
5. **Task 5** (opponent scouting) — builds on standings data from Task 4's API calls.
6. **Task 6** (deploy server) — do this last; it makes all season features work on the deployed site.

---

## 10. Testing Each Task

**Task 1:** Run `python apps/keeper-advisor/scripts/export_dashboard_data.py` locally. Check that `daily_lineup.json` has ≥20 players with real MLB team abbreviations (not all "FA").

**Task 2:** Same run. Check that `waiver_wire.json` has 0 players with `rostered_pct > 50`. All players should be genuine free agents.

**Task 3:** With `python apps/keeper-advisor/scripts/draft_server.py` running, call `curl http://localhost:8001/season/lineup-focus`. Response should have `swing_categories` array (may be empty pre-season — that's fine). Open `http://localhost:3001` and verify the banner appears or gracefully hides if no swing categories.

**Task 4:** Call `curl http://localhost:8001/season/trajectory`. Response should have `categories` dict with 12 entries. Pre-season, `weekly_ranks` arrays will be all-null — that's correct. Open `http://localhost:3001/trajectory` and verify the page loads (sparklines will be empty pre-season).

**Task 5:** Call `curl http://localhost:8001/season/opponent`. Response should identify the opponent from this week's matchup and return scouting data. Open `/matchup` and verify the scouting section renders.

**Task 6:** After Railway deployment, update `.env.local` in `baseball-dashboard` to point at the Railway URL and confirm all season pages load without running the local Python server.

---

## 11. Do Not Touch

- `apps/keeper-advisor/config/oauth2.json` — contains live credentials, never commit
- `apps/baseball-dashboard/.env.local` — never overwrite
- `apps/keeper-advisor/data/my_roster_from_yahoo.csv` — being replaced by Task 1
- The `espn-fantasy-recap` app — not part of this project
- The `keeper-api` FastAPI app — separate from `draft_server.py`, not used currently
- Push to `main` branch only when explicitly asked by the user
