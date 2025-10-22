#!/usr/bin/env python3
"""
FastAPI server for ESPN Fantasy Football Data
Provides REST endpoints for league data, matchups, and statistics
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, List
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv
from src.fetch_league_data import FantasyDataFetcher
from src.logger import get_logger
from src.api_improvements import setup_api_improvements
from src.constants import TEAM_OWNERS

# Load environment variables
load_dotenv()

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

# Mount static files
# Get the project root directory (parent of src/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(project_root, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Static files mounted from {static_dir}")
else:
    logger.warning(f"Static directory not found at {static_dir}")

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
    """Root endpoint - serves the web UI"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(project_root, "static")
    index_path = os.path.join(static_dir, "index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)

    # Fallback to API info if no UI
    return {
        "name": "Fantasy Football API",
        "version": "1.0.0",
        "endpoints": {
            "league_info": "/api/league",
            "standings": "/api/standings",
            "matchups": "/api/matchups/{week}",
            "week_stats": "/api/stats/week/{week}",
            "power_rankings": "/api/power_rankings/{week}",
            "teams": "/api/teams",
            "team_detail": "/api/teams/{team_id}",
            "recap_generate": "/api/recaps/generate",
            "recap_history": "/api/recaps/history",
            "recap_get": "/api/recaps/{week}",
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
            # Look up owner from TEAM_OWNERS constant
            owner = TEAM_OWNERS.get(team.team_name, "Unknown")
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


# ---------------------- Power Rankings (adjPF) Utilities ----------------------
def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _get_season_phase_weights(week: int) -> dict:
    """Return season-phase weights for power ranking score."""
    if week <= 3:
        return {"record": 0.40, "adjpf": 0.40, "recent": 0.15, "coaching": 0.05}
    if week <= 10:
        return {"record": 0.35, "adjpf": 0.40, "recent": 0.20, "coaching": 0.05}
    return {"record": 0.30, "adjpf": 0.45, "recent": 0.20, "coaching": 0.05}


def _compute_adjpf_and_metrics(f, through_week: int):
    """
    Compute opponent-adjusted PF (adjPF), recent adjPF (last 3 weeks), coaching efficiency,
    and records strictly through `through_week`.
    This replays box scores up to `through_week` to avoid using current full-season standings.
    """
    # Basic team metadata
    teams = getattr(f.league, "teams", [])
    team_meta = {t.team_id: {"team_name": t.team_name, "owner": TEAM_OWNERS.get(t.team_name, "Unknown")} for t in teams}

    # Accumulators (through-week)
    team_wins = {tid: 0 for tid in team_meta}
    team_losses = {tid: 0 for tid in team_meta}
    team_ties = {tid: 0 for tid in team_meta}
    team_pf = {tid: 0.0 for tid in team_meta}
    team_pa = {tid: 0.0 for tid in team_meta}
    team_gp = {tid: 0 for tid in team_meta}
    per_game = {tid: [] for tid in team_meta}  # (raw_points, opponent_id)
    team_gaps_by_week = {tid: {} for tid in team_meta}
    team_results = {tid: [] for tid in team_meta}  # per-week results: 'W','L','T'

    for w in range(1, through_week + 1):
        box_scores = f.league.box_scores(w)
        for bs in box_scores:
            home_id = bs.home_team.team_id
            away_id = bs.away_team.team_id
            home_score = float(getattr(bs, "home_score", 0.0))
            away_score = float(getattr(bs, "away_score", 0.0))

            # Tally records
            if home_score > away_score:
                if home_id in team_wins: team_wins[home_id] += 1
                if away_id in team_losses: team_losses[away_id] += 1
                if home_id in team_results: team_results[home_id].append('W')
                if away_id in team_results: team_results[away_id].append('L')
            elif away_score > home_score:
                if away_id in team_wins: team_wins[away_id] += 1
                if home_id in team_losses: team_losses[home_id] += 1
                if away_id in team_results: team_results[away_id].append('W')
                if home_id in team_results: team_results[home_id].append('L')
            else:
                if home_id in team_ties: team_ties[home_id] += 1
                if away_id in team_ties: team_ties[away_id] += 1
                if home_id in team_results: team_results[home_id].append('T')
                if away_id in team_results: team_results[away_id].append('T')

            # PF/PA and games
            if home_id in team_pf:
                team_pf[home_id] += home_score
                team_pa[home_id] += away_score
                team_gp[home_id] += 1
            if away_id in team_pf:
                team_pf[away_id] += away_score
                team_pa[away_id] += home_score
                team_gp[away_id] += 1

            # Save per-game raw for adjPF
            if home_id in per_game:
                per_game[home_id].append((home_score, away_id))
            if away_id in per_game:
                per_game[away_id].append((away_score, home_id))

            # Coaching efficiency: weekly management gap
            try:
                home_opt = calculate_optimal_lineup(bs.home_lineup)
                team_gaps_by_week[home_id][w] = round(home_opt["optimal_score"] - home_score, 2)
            except Exception:
                team_gaps_by_week[home_id][w] = 0.0
            try:
                away_opt = calculate_optimal_lineup(bs.away_lineup)
                team_gaps_by_week[away_id][w] = round(away_opt["optimal_score"] - away_score, 2)
            except Exception:
                team_gaps_by_week[away_id][w] = 0.0

    # Compute league average PA per game and opponent indices (through-week only)
    total_pa = sum(team_pa.values())
    total_gp = sum(max(1, gp) for gp in team_gp.values())
    league_avg_pa_pg = (total_pa / total_gp) if total_gp else 0.0
    pa_pg = {tid: (team_pa[tid] / max(1, team_gp[tid])) for tid in team_meta}

    # Adjusted points per team
    team_adj_points = {tid: [] for tid in team_meta}
    for tid, entries in per_game.items():
        for raw_pts, opp_id in entries:
            opp_pa = pa_pg.get(opp_id, league_avg_pa_pg or 1.0)
            def_index = league_avg_pa_pg / (opp_pa or 1.0)
            def_index = _clamp(def_index, 0.75, 1.25)
            if through_week <= 3:
                ramp = through_week / 3.0
                def_index = 1.0 + (def_index - 1.0) * ramp
            team_adj_points[tid].append(raw_pts * def_index)

    # Build result metrics
    results = {}
    for tid, meta in team_meta.items():
        adj_list = team_adj_points.get(tid, [])
        games = len(adj_list)
        adjpf = (sum(adj_list) / games) if games else 0.0
        recent_adj_list = adj_list[-3:] if games >= 3 else adj_list
        recent_adjpf = (sum(recent_adj_list) / len(recent_adj_list)) if recent_adj_list else 0.0

        gaps = team_gaps_by_week.get(tid, {})
        recent_gap_vals = [gaps[w] for w in sorted(gaps.keys())[-3:]] if gaps else []
        avg_recent_gap = (sum(recent_gap_vals) / len(recent_gap_vals)) if recent_gap_vals else 0.0

        wins = team_wins.get(tid, 0)
        losses = team_losses.get(tid, 0)
        ties = team_ties.get(tid, 0)
        gp_rec = wins + losses
        win_pct = (wins / max(1, gp_rec)) if gp_rec > 0 else 0.0

        # Compute current streak from results
        res_list = team_results.get(tid, [])
        streak_type = 'NONE'
        streak_len = 0
        for r in reversed(res_list):
            if streak_len == 0 and r in ('W','L'):
                streak_type = r
                streak_len = 1
            elif r == streak_type:
                streak_len += 1
            elif r == 'T':
                # ties break win/loss streaks
                break
            else:
                break

        results[tid] = {
            "team_id": tid,
            "team_name": meta["team_name"],
            "owner": meta["owner"],
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "win_pct": round(win_pct, 3),
            "pf": round(team_pf.get(tid, 0.0), 2),
            "adjpf": round(adjpf, 2),
            "recent_adjpf": round(recent_adjpf, 2),
            "coaching_eff": round(-avg_recent_gap, 2),
            "streak_type": streak_type,
            "streak_len": streak_len,
        }

    return results


def _rank_teams(power_metrics: dict, week: int) -> List[dict]:
    weights = _get_season_phase_weights(week)
    scored = []
    vals = {
        k: [v[k] for v in power_metrics.values()]
        for k in ["win_pct", "adjpf", "recent_adjpf", "coaching_eff"]
    }

    def norm(x, arr):
        mn, mx = (min(arr), max(arr))
        return 0.5 if mx == mn else (x - mn) / (mx - mn)

    for tid, m in power_metrics.items():
        score = (
            weights["record"] * norm(m["win_pct"], vals["win_pct"])
            + weights["adjpf"] * norm(m["adjpf"], vals["adjpf"])
            + weights["recent"] * norm(m["recent_adjpf"], vals["recent_adjpf"])
            + weights["coaching"] * norm(m["coaching_eff"], vals["coaching_eff"])
        )
        scored.append({**m, "score": round(float(score), 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    for idx, item in enumerate(scored, 1):
        item["rank"] = idx
    return scored


@app.get("/api/power_rankings/{week}")
def get_power_rankings(week: int):
    """Compute power rankings with opponent-adjusted PF and season-phase weights."""
    try:
        f = get_fetcher()
        week = max(1, int(week))
        metrics_now = _compute_adjpf_and_metrics(f, through_week=week)
        rankings_now = _rank_teams(metrics_now, week)

        prev_rank_map = {}
        if week > 1:
            metrics_prev = _compute_adjpf_and_metrics(f, through_week=week - 1)
            rankings_prev = _rank_teams(metrics_prev, week - 1)
            prev_rank_map = {r["team_id"]: r["rank"] for r in rankings_prev}

        for r in rankings_now:
            prev = prev_rank_map.get(r["team_id"]) if prev_rank_map else None
            r["previous_rank"] = prev
            if prev is None:
                r["movement"] = "—"
            else:
                delta = prev - r["rank"]
                r["movement"] = (
                    f"+{delta}" if delta > 0 else (f"{delta}" if delta < 0 else "—")
                )

        return {"week": week, "rankings": rankings_now}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                    # Note: ESPN API may return -1 for percent_started when data unavailable
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
                    # Note: ESPN API may return -1 for percent_started when data unavailable
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

            # Look up owner names from TEAM_OWNERS constant using team name
            home_owner = TEAM_OWNERS.get(matchup.home_team.team_name, "Unknown")
            away_owner = TEAM_OWNERS.get(matchup.away_team.team_name, "Unknown")

            matchups_data.append(
                {
                    "matchup_id": i,
                    "home_team": {
                        "team_id": matchup.home_team.team_id,
                        "team_name": matchup.home_team.team_name,
                        "owner": home_owner,
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
                        "owner": away_owner,
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
            # Look up owner from TEAM_OWNERS constant
            owner = TEAM_OWNERS.get(team.team_name, "Unknown")

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

        # Look up owner from TEAM_OWNERS constant
        owner = TEAM_OWNERS.get(team.team_name, "Unknown")

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


# Pydantic models for request/response
class GenerateRecapRequest(BaseModel):
    week: int
    use_v2_format: bool = True  # Default to V2 format


# Recap Generation Endpoints
@app.post("/api/recaps/generate")
async def generate_recap(request: GenerateRecapRequest):
    """Generate a new weekly recap using ChatGPT"""
    import asyncio

    week = request.week

    if week < 1 or week > 18:
        raise HTTPException(status_code=400, detail="Week must be between 1 and 18")

    try:
        # Check for Portkey or direct OpenAI configuration
        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        portkey_base_url = os.getenv("PORTKEY_BASE_URL")
        portkey_virtual_key = os.getenv("PORTKEY_OPENAI_VIRTUAL_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        format_type = "V2 (structured)" if request.use_v2_format else "V1 (classic)"

        if portkey_api_key and portkey_base_url:
            # Using Portkey gateway
            api_key = portkey_api_key
            logger.info(
                f"Generating recap for week {week} using Portkey gateway ({format_type})..."
            )
        elif openai_api_key:
            # Direct OpenAI
            api_key = openai_api_key
            logger.info(
                f"Generating recap for week {week} using direct OpenAI ({format_type})..."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Either PORTKEY_API_KEY or OPENAI_API_KEY must be configured in your .env file.",
            )

        # Import here to avoid loading if not needed
        from openai import OpenAI
        from src.recap_generator import RecapGenerator

        # Configure client for Portkey or direct OpenAI
        if portkey_api_key and portkey_base_url:
            # Using Portkey gateway
            logger.info("Configuring OpenAI client for Portkey")
            client = OpenAI(
                api_key=api_key,
                base_url=portkey_base_url,
                default_headers={"x-portkey-virtual-key": portkey_virtual_key}
                if portkey_virtual_key
                else {},
            )
        else:
            # Direct OpenAI connection
            logger.info("Configuring OpenAI client for direct connection")
            client = OpenAI(api_key=api_key)

        generator = RecapGenerator()

        # Run the blocking recap generation in a thread pool to avoid blocking the server
        loop = asyncio.get_event_loop()

        # Use partial to pass all arguments including use_v2_format
        from functools import partial

        generate_func = partial(
            generator.generate_recap_with_openai,
            week=week,
            client=client,
            model="gpt-4o",  # Using GPT-4o (latest model)
            use_v2_format=request.use_v2_format,
        )

        recap_content = await loop.run_in_executor(None, generate_func)

        if not recap_content:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate recap. Check server logs for details.",
            )

        format_label = "V2 (structured)" if request.use_v2_format else "V1 (classic)"
        logger.info(
            f"✅ Recap generated successfully for week {week} using GPT-4o ({format_label})"
        )

        return {
            "success": True,
            "week": week,
            "recap": recap_content,
            "format": format_label,
            "message": f"Recap for week {week} generated successfully using GPT-4o ({format_label})",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recap: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate recap: {str(e)}"
        )


@app.get("/api/recaps/history")
async def get_recap_history():
    """Get list of all generated recaps"""
    try:
        recap_history_file = "recap_history.json"

        if not os.path.exists(recap_history_file):
            return {"recaps": []}

        with open(recap_history_file, "r") as f:
            history = json.load(f)

        # Return just the metadata (week, date) not full content
        recaps_metadata = [
            {
                "week": entry["week"],
                "date": entry["date"],
                "recap": entry["recap"],  # Include full content for now
            }
            for entry in history
        ]

        return {"recaps": recaps_metadata}

    except Exception as e:
        logger.error(f"Error loading recap history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to load recap history: {str(e)}"
        )


@app.get("/api/recaps/{week}")
async def get_recap(week: int):
    """Get a specific recap by week"""
    try:
        # First check recap history
        recap_history_file = "recap_history.json"

        if os.path.exists(recap_history_file):
            with open(recap_history_file, "r") as f:
                history = json.load(f)

            # Find the recap for this week
            for entry in history:
                if entry["week"] == week:
                    return {
                        "week": week,
                        "date": entry["date"],
                        "recap": entry["recap"],
                    }

        # Fallback: Check if file exists in output directory
        recap_file = f"output/week-{week}-recap.md"
        if os.path.exists(recap_file):
            with open(recap_file, "r") as f:
                recap_content = f.read()

            return {"week": week, "recap": recap_content}

        raise HTTPException(
            status_code=404,
            detail=f"Recap for week {week} not found. Generate it first.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading recap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load recap: {str(e)}")


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
