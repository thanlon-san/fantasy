"""
Fantasy Baseball API
FastAPI service that wraps the keeper-advisor Python tools
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sys
from pathlib import Path

# Add keeper-advisor to path
advisor_path = Path(__file__).parent.parent / "keeper-advisor"
sys.path.insert(0, str(advisor_path))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))

from src.importers import CSVImporter
from src.lineup_optimizer import LineupOptimizer
from src.waiver_analyzer import WaiverAnalyzer
from src.analyzer import KeeperAnalyzer

app = FastAPI(title="Fantasy Baseball API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load roster once at startup
ROSTER = None

@app.on_event("startup")
async def startup_event():
    """Load roster on startup"""
    global ROSTER
    roster_file = advisor_path / "data" / "my_roster_from_yahoo.csv"
    ROSTER = CSVImporter.import_roster(roster_file, team_name="2balls")
    print(f"✅ Loaded {len(ROSTER.players)} players")


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Fantasy Baseball API",
        "roster_size": len(ROSTER.players) if ROSTER else 0,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/lineup")
async def get_daily_lineup():
    """
    Get daily lineup recommendations
    Returns: Lineup recommendations with all tiers
    """
    try:
        optimizer = LineupOptimizer(use_breakout_signals=False)  # Fast mode
        recommendations = optimizer.get_daily_recommendations(ROSTER, show_all_players=True)
        
        # Separate into tiers
        playing = [r for r in recommendations if r.opponent != "No game"]
        not_playing = [r for r in recommendations if r.opponent == "No game"]
        
        must_start = [r for r in playing if r.confidence_score >= 80]
        start = [r for r in playing if 65 <= r.confidence_score < 80]
        flex = [r for r in playing if 50 <= r.confidence_score < 65]
        bench = [r for r in playing if r.confidence_score < 50]
        
        def format_rec(r):
            return {
                "player": r.player.name,
                "position": r.player.position,
                "team": r.player.team,
                "opponent": f"{r.home_away.upper()[0]} {r.opponent}" if r.home_away else r.opponent,
                "opponent_pitcher": r.opponent_pitcher or "TBD",
                "game_time": r.game_time or "TBD",
                "confidence": int(r.confidence_score),
                "matchup": int(r.matchup_score),
                "parkFactor": int(r.park_score),
                "platoon": int(r.platoon_score),
                "form": int(r.form_score),
                "breakout": int(r.breakout_boost),
                "reasons": r.reasons
            }
        
        return {
            "generated_at": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "must_start": [format_rec(r) for r in must_start],
            "start": [format_rec(r) for r in start],
            "flex": [format_rec(r) for r in flex],
            "bench": [format_rec(r) for r in bench],
            "not_playing": [
                {
                    "player": r.player.name,
                    "position": r.player.position,
                    "team": r.player.team,
                    "adp": int(r.player.adp) if r.player.adp else None
                }
                for r in not_playing
            ],
            "summary": {
                "total_roster": len(recommendations),
                "playing_today": len(playing),
                "not_playing": len(not_playing),
                "must_start_count": len(must_start),
                "start_count": len(start),
                "flex_count": len(flex),
                "bench_count": len(bench)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keepers")
async def get_keepers():
    """
    Get keeper recommendations
    Returns: Top keeper candidates with value analysis
    """
    try:
        analyzer = KeeperAnalyzer(ROSTER)
        analyses = analyzer.analyze_all_players()
        top_keepers = analyzer.get_recommended_keepers(3)
        
        return {
            "generated_at": datetime.now().isoformat(),
            "keepers": [
                {
                    "player": k.player.name,
                    "position": k.player.position,
                    "round": k.adjusted_keeper_round or k.keeper_round,
                    "adp": int(k.player.adp) if k.player.adp else 0,
                    "surplus": f"+{int(k.surplus_value)}" if k.surplus_value else "N/A",
                    "value": k.recommendation,
                    "years_remaining": k.years_remaining,
                    "reason": k.recommendation_reason
                }
                for k in top_keepers
            ],
            "summary": {
                "total_eligible": len([a for a in analyses if a.is_eligible]),
                "recommended": len([a for a in analyses if a.recommendation == "Keep"])
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/waivers")
async def get_waivers():
    """
    Get waiver wire recommendations
    Returns: Top pickup targets (demo mode - needs Yahoo API integration)
    """
    return {
        "generated_at": datetime.now().isoformat(),
        "note": "Waiver scanning requires Yahoo API integration",
        "targets": []
    }


@app.get("/api/breakouts")
async def get_breakouts():
    """
    Get breakout candidates
    Returns: Players showing breakout signals (demo mode - needs free agent data)
    """
    return {
        "generated_at": datetime.now().isoformat(),
        "note": "Breakout scanning requires free agent data",
        "alerts": []
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
