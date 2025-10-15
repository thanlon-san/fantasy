#!/usr/bin/env python3
"""
FastAPI server for ESPN Fantasy Football Data
Provides REST endpoints for league data, matchups, and statistics
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Dict, List
import json
import os
from src.fetch_league_data import FantasyDataFetcher
from src.logger import get_logger
from src.api_improvements import setup_api_improvements

logger = get_logger(__name__)

# Load configuration
config_path = "config.json"
if not os.path.exists(config_path):
    config_path = "config.example.json"
    logger.warning("config.json not found, using config.example.json")

try:
    with open(config_path, "r") as f:
        config = json.load(f)
    logger.info(f"Configuration loaded from {config_path}")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

# Initialize FastAPI app
app = FastAPI(
    title="Fantasy Football API",
    description="ESPN Fantasy Football data API - Get league stats, matchups, and standings",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize fetcher (will be connected on first request)
fetcher = None


def get_fetcher() -> FantasyDataFetcher:
    """Get or create the data fetcher instance"""
    global fetcher
    if fetcher is None:
        logger.info("Initializing ESPN data fetcher...")
        league_id = config.get("league_id")
        year = config.get("year")
        espn_s2 = config.get("espn_s2", "")
        swid = config.get("swid", "")

        try:
            if espn_s2 and swid:
                fetcher = FantasyDataFetcher(league_id, year, espn_s2, swid)
            else:
                fetcher = FantasyDataFetcher(league_id, year)

            league = fetcher.connect()
            if not league:
                logger.error("Failed to connect to ESPN API")
                raise HTTPException(
                    status_code=500, detail="Failed to connect to ESPN API"
                )

            logger.info(f"Connected to league {league_id} for year {year}")
        except Exception as e:
            logger.error(f"Failed to initialize fetcher: {e}", exc_info=True)
            raise

    return fetcher


@app.get("/")
def read_root():
    """Root endpoint with API information"""
    return {
        "name": "Fantasy Football API",
        "version": "1.0.0",
        "endpoints": {
            "league_info": "/api/league",
            "standings": "/api/standings",
            "matchups": "/api/matchups/{week}",
            "week_stats": "/api/stats/week/{week}",
            "teams": "/api/teams",
            "team_detail": "/api/teams/{team_id}",
        },
    }


@app.get("/api/league")
def get_league_info():
    """Get basic league information"""
    try:
        f = get_fetcher()
        league = f.league

        return {
            "league_id": f.league_id,
            "year": f.year,
            "league_name": league.settings.name
            if hasattr(league, "settings")
            else "Unknown",
            "current_week": league.current_week
            if hasattr(league, "current_week")
            else config.get("current_week", 1),
            "total_teams": len(league.teams) if hasattr(league, "teams") else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/standings")
def get_standings():
    """Get current league standings"""
    try:
        f = get_fetcher()
        standings = f.league.standings()

        teams_data = []
        for i, team in enumerate(standings, 1):
            owner = (
                team.owner.split()[0]
                if hasattr(team, "owner") and team.owner
                else "Unknown"
            )
            pct = (
                team.wins / (team.wins + team.losses)
                if (team.wins + team.losses) > 0
                else 0
            )
            streak = getattr(team, "streak_type", "W") + str(
                getattr(team, "streak_length", 0)
            )

            teams_data.append(
                {
                    "rank": i,
                    "team_id": team.team_id,
                    "team_name": team.team_name,
                    "owner": owner,
                    "wins": team.wins,
                    "losses": team.losses,
                    "ties": team.ties,
                    "win_pct": round(pct, 3),
                    "points_for": round(team.points_for, 2),
                    "points_against": round(team.points_against, 2),
                    "point_differential": round(
                        team.points_for - team.points_against, 2
                    ),
                    "streak": streak,
                }
            )

        return {
            "standings": teams_data,
            "leaders": {
                "most_points": max(teams_data, key=lambda x: x["points_for"]),
                "fewest_points_against": min(
                    teams_data, key=lambda x: x["points_against"]
                ),
                "best_differential": max(
                    teams_data, key=lambda x: x["point_differential"]
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_player_stats(player) -> dict:
    """Extract detailed stats from player breakdown"""
    stats = {}
    if hasattr(player, "points_breakdown") and player.points_breakdown:
        breakdown = player.points_breakdown

        # Passing stats
        stats["passing_yards"] = int(breakdown.get("passingYards", 0))
        stats["passing_tds"] = int(breakdown.get("passingTouchdowns", 0))
        stats["passing_ints"] = int(breakdown.get("passingInterceptions", 0))
        stats["passing_attempts"] = int(breakdown.get("passingAttempts", 0))
        stats["passing_completions"] = int(breakdown.get("passingCompletions", 0))

        # Rushing stats
        stats["rushing_yards"] = int(breakdown.get("rushingYards", 0))
        stats["rushing_tds"] = int(breakdown.get("rushingTouchdowns", 0))
        stats["rushing_attempts"] = int(breakdown.get("rushingAttempts", 0))

        # Receiving stats
        stats["receiving_yards"] = int(breakdown.get("receivingYards", 0))
        stats["receiving_tds"] = int(breakdown.get("receivingTouchdowns", 0))
        stats["receiving_receptions"] = int(breakdown.get("receivingReceptions", 0))
        stats["receiving_targets"] = int(breakdown.get("receivingTargets", 0))

    return stats


def calculate_position_aggregates(lineup) -> dict:
    """Calculate total points by position"""
    aggregates = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "K": 0, "D/ST": 0, "FLEX": 0}

    for player in lineup:
        if player.slot_position not in ["BE", "IR"]:  # Only count starters
            position = player.position
            points = getattr(player, "points", 0)

            if position in aggregates:
                aggregates[position] += points

    return {k: round(v, 2) for k, v in aggregates.items()}


def calculate_optimal_lineup(lineup) -> dict:
    """Calculate best possible score with optimal lineup"""
    # Group players by position
    qbs = [p for p in lineup if p.position == "QB" and p.slot_position != "IR"]
    rbs = [p for p in lineup if p.position == "RB" and p.slot_position != "IR"]
    wrs = [p for p in lineup if p.position == "WR" and p.slot_position != "IR"]
    tes = [p for p in lineup if p.position == "TE" and p.slot_position != "IR"]
    ks = [p for p in lineup if p.position == "K" and p.slot_position != "IR"]
    dsts = [p for p in lineup if p.position == "D/ST" and p.slot_position != "IR"]

    # Sort by points
    qbs.sort(key=lambda x: getattr(x, "points", 0), reverse=True)
    rbs.sort(key=lambda x: getattr(x, "points", 0), reverse=True)
    wrs.sort(key=lambda x: getattr(x, "points", 0), reverse=True)
    tes.sort(key=lambda x: getattr(x, "points", 0), reverse=True)
    ks.sort(key=lambda x: getattr(x, "points", 0), reverse=True)
    dsts.sort(key=lambda x: getattr(x, "points", 0), reverse=True)

    optimal_score = 0
    optimal_players = []

    # Standard lineup: 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX, 1 K, 1 D/ST
    if qbs:
        optimal_score += getattr(qbs[0], "points", 0)
        optimal_players.append(
            {
                "name": qbs[0].name,
                "position": "QB",
                "points": getattr(qbs[0], "points", 0),
            }
        )

    for i in range(min(2, len(rbs))):
        optimal_score += getattr(rbs[i], "points", 0)
        optimal_players.append(
            {
                "name": rbs[i].name,
                "position": "RB",
                "points": getattr(rbs[i], "points", 0),
            }
        )

    for i in range(min(2, len(wrs))):
        optimal_score += getattr(wrs[i], "points", 0)
        optimal_players.append(
            {
                "name": wrs[i].name,
                "position": "WR",
                "points": getattr(wrs[i], "points", 0),
            }
        )

    if tes:
        optimal_score += getattr(tes[0], "points", 0)
        optimal_players.append(
            {
                "name": tes[0].name,
                "position": "TE",
                "points": getattr(tes[0], "points", 0),
            }
        )

    # FLEX (best remaining RB/WR/TE)
    flex_options = (
        (rbs[2:] if len(rbs) > 2 else [])
        + (wrs[2:] if len(wrs) > 2 else [])
        + (tes[1:] if len(tes) > 1 else [])
    )
    if flex_options:
        best_flex = max(flex_options, key=lambda x: getattr(x, "points", 0))
        optimal_score += getattr(best_flex, "points", 0)
        optimal_players.append(
            {
                "name": best_flex.name,
                "position": f"FLEX ({best_flex.position})",
                "points": getattr(best_flex, "points", 0),
            }
        )

    if ks:
        optimal_score += getattr(ks[0], "points", 0)
        optimal_players.append(
            {"name": ks[0].name, "position": "K", "points": getattr(ks[0], "points", 0)}
        )

    if dsts:
        optimal_score += getattr(dsts[0], "points", 0)
        optimal_players.append(
            {
                "name": dsts[0].name,
                "position": "D/ST",
                "points": getattr(dsts[0], "points", 0),
            }
        )

    return {
        "optimal_score": round(optimal_score, 2),
        "optimal_players": optimal_players,
    }


@app.get("/api/matchups/{week}")
def get_matchups(week: int):
    """Get all matchups for a specific week"""
    try:
        f = get_fetcher()
        matchups = f.league.box_scores(week)

        matchups_data = []
        for i, matchup in enumerate(matchups, 1):
            # Process home team lineup
            home_starters = []
            home_bench = []
            for player in matchup.home_lineup:
                player_data = {
                    "name": player.name,
                    "position": player.position,
                    "slot": player.slot_position,
                    "projected_points": round(
                        getattr(player, "projected_points", 0), 2
                    ),
                    "actual_points": round(getattr(player, "points", 0), 2),
                    "pro_team": getattr(player, "proTeam", "FA"),
                    "percent_started": getattr(player, "percent_started", 0),
                    "stats": extract_player_stats(player),
                }

                if player.slot_position in ["BE", "IR"]:
                    home_bench.append(player_data)
                else:
                    home_starters.append(player_data)

            # Process away team lineup
            away_starters = []
            away_bench = []
            for player in matchup.away_lineup:
                player_data = {
                    "name": player.name,
                    "position": player.position,
                    "slot": player.slot_position,
                    "projected_points": round(
                        getattr(player, "projected_points", 0), 2
                    ),
                    "actual_points": round(getattr(player, "points", 0), 2),
                    "pro_team": getattr(player, "proTeam", "FA"),
                    "percent_started": getattr(player, "percent_started", 0),
                    "stats": extract_player_stats(player),
                }

                if player.slot_position in ["BE", "IR"]:
                    away_bench.append(player_data)
                else:
                    away_starters.append(player_data)

            # Calculate analytics for both teams
            home_position_aggregates = calculate_position_aggregates(
                matchup.home_lineup
            )
            home_optimal = calculate_optimal_lineup(matchup.home_lineup)
            home_management_gap = round(
                home_optimal["optimal_score"] - matchup.home_score, 2
            )

            away_position_aggregates = calculate_position_aggregates(
                matchup.away_lineup
            )
            away_optimal = calculate_optimal_lineup(matchup.away_lineup)
            away_management_gap = round(
                away_optimal["optimal_score"] - matchup.away_score, 2
            )

            matchups_data.append(
                {
                    "matchup_id": i,
                    "home_team": {
                        "team_id": matchup.home_team.team_id,
                        "team_name": matchup.home_team.team_name,
                        "score": round(matchup.home_score, 2),
                        "record": f"{matchup.home_team.wins}-{matchup.home_team.losses}-{matchup.home_team.ties}",
                        "starters": home_starters,
                        "bench": home_bench,
                        "position_aggregates": home_position_aggregates,
                        "optimal_lineup": home_optimal,
                        "management_gap": home_management_gap,
                    },
                    "away_team": {
                        "team_id": matchup.away_team.team_id,
                        "team_name": matchup.away_team.team_name,
                        "score": round(matchup.away_score, 2),
                        "record": f"{matchup.away_team.wins}-{matchup.away_team.losses}-{matchup.away_team.ties}",
                        "starters": away_starters,
                        "bench": away_bench,
                        "position_aggregates": away_position_aggregates,
                        "optimal_lineup": away_optimal,
                        "management_gap": away_management_gap,
                    },
                    "winner": matchup.home_team.team_name
                    if matchup.home_score > matchup.away_score
                    else matchup.away_team.team_name,
                    "margin": round(abs(matchup.home_score - matchup.away_score), 2),
                }
            )

        return {
            "week": week,
            "total_matchups": len(matchups_data),
            "matchups": matchups_data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/week/{week}")
def get_week_stats(week: int):
    """Get statistical analysis for a specific week"""
    try:
        f = get_fetcher()
        # Note: calculate_week_stats uses league.box_scores internally via fetch_league_data.py
        stats = f.calculate_week_stats(week)

        return {
            "week": week,
            "highest_score": {
                "team": stats["highest_score"][0],
                "points": round(stats["highest_score"][1], 2),
            }
            if stats.get("highest_score")
            else None,
            "lowest_score": {
                "team": stats["lowest_score"][0],
                "points": round(stats["lowest_score"][1], 2),
            }
            if stats.get("lowest_score")
            else None,
            "biggest_blowout": {
                "winner": stats["biggest_blowout"]["winner"],
                "loser": stats["biggest_blowout"]["loser"],
                "margin": round(stats["biggest_blowout"]["margin"], 2),
            }
            if stats.get("biggest_blowout")
            else None,
            "closest_game": {
                "team1": stats["closest_game"]["team1"],
                "team2": stats["closest_game"]["team2"],
                "margin": round(stats["closest_game"]["margin"], 2),
            }
            if stats.get("closest_game")
            else None,
            "most_bench_points": {
                "team": stats["most_bench_points"]["team"],
                "points": round(stats["most_bench_points"]["points"], 2),
            }
            if stats.get("most_bench_points")
            else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams")
def get_teams():
    """Get list of all teams in the league"""
    try:
        f = get_fetcher()
        teams = f.league.teams

        teams_data = []
        for team in teams:
            owner = (
                team.owner.split()[0]
                if hasattr(team, "owner") and team.owner
                else "Unknown"
            )

            teams_data.append(
                {
                    "team_id": team.team_id,
                    "team_name": team.team_name,
                    "owner": owner,
                    "wins": team.wins,
                    "losses": team.losses,
                    "ties": team.ties,
                    "points_for": round(team.points_for, 2),
                    "points_against": round(team.points_against, 2),
                    "acquisitions": getattr(team, "acquisitions", 0),
                    "drops": getattr(team, "drops", 0),
                    "trades": getattr(team, "trades", 0),
                    "faab_spent": getattr(team, "acquisition_budget_spent", 0),
                    "streak_type": getattr(team, "streak_type", "NONE"),
                    "streak_length": getattr(team, "streak_length", 0),
                    "standing": getattr(team, "standing", 0),
                }
            )

        return {"total_teams": len(teams_data), "teams": teams_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams/{team_id}")
def get_team_detail(team_id: int):
    """Get detailed information about a specific team"""
    try:
        f = get_fetcher()
        teams = f.league.teams

        team = next((t for t in teams if t.team_id == team_id), None)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        owner = (
            team.owner.split()[0]
            if hasattr(team, "owner") and team.owner
            else "Unknown"
        )

        # Get current roster
        roster = []
        if hasattr(team, "roster"):
            for player in team.roster:
                roster.append(
                    {
                        "name": player.name,
                        "position": player.position,
                        "pro_team": getattr(player, "proTeam", "FA"),
                        "projected_total": round(
                            getattr(player, "projected_total_points", 0), 2
                        ),
                        "total_points": round(getattr(player, "total_points", 0), 2),
                    }
                )

        return {
            "team_id": team.team_id,
            "team_name": team.team_name,
            "owner": owner,
            "record": {"wins": team.wins, "losses": team.losses, "ties": team.ties},
            "points": {
                "for": round(team.points_for, 2),
                "against": round(team.points_against, 2),
                "differential": round(team.points_for - team.points_against, 2),
            },
            "streak": {
                "type": getattr(team, "streak_type", "W"),
                "length": getattr(team, "streak_length", 0),
            },
            "roster": roster,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Setup API improvements after all endpoints are defined
setup_api_improvements(app, get_fetcher, enable_rate_limit=True)
logger.info("✅ API improvements activated: health checks, logging, rate limiting")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Fantasy Football API on port {port}...")
    print(f"\n🏈 Fantasy Football API Starting...")
    print(f"📖 API Documentation: http://localhost:{port}/docs")
    print(f"🔍 Health Check: http://localhost:{port}/health")
    print(f"📊 API Info: http://localhost:{port}/")
    print(f"📝 Logs: logs/{os.popen('date +%Y%m%d').read().strip()}.log\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
