#!/usr/bin/env python3
"""
End-to-end pipeline validation without touching the Yahoo network.

Runs the exact code path a recap uses (fetcher output -> ContextBuilder ->
formatted LLM context) against a realistic synthetic ``week_data`` dict.
Fails loud if anything downstream of the fetcher regresses.

Also asserts that the fetcher's OAuth loader rejects a missing token with a
clean, actionable error (rather than crashing partway through Yahoo calls).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_APP_ROOT))
sys.path.insert(0, str(_APP_ROOT.parent.parent / "packages"))

from src.context_builder import ContextBuilder
from src.ownership_stats import OwnershipStats
from src.recap_generator import RecapGenerator
from src.trend_tracker import TrendTracker


def synthetic_week_data(week: int = 5) -> dict:
    """
    A realistic ``week_data`` dict shaped like what
    ``YahooLeagueFetcher.fetch_all_for_week`` returns. Values are just enough
    to exercise every consumer branch in ContextBuilder.
    """
    def make_team(team_id, team_name, owner, score, starters, bench,
                  wins=3, losses=2, standing=None):
        return {
            "team_id": team_id,
            "team_key": f"461.l.1324751.t.{team_id}",
            "team_name": team_name,
            "owner": owner,
            "score": score,
            "record": f"{wins}-{losses}-0",
            "starters": starters,
            "bench": bench,
            "position_aggregates": {"QB": 20, "RB": 30, "WR": 25, "TE": 10, "K": 8, "D/ST": 6, "FLEX": 12},
            "optimal_lineup": {"optimal_score": score + 12.0, "optimal_players": []},
            "management_gap": 12.0,
        }

    def make_player(name, position, slot, actual):
        return {
            "name": name,
            "position": position,
            "slot": slot,
            "projected_points": max(0.0, actual - 3),
            "actual_points": actual,
            "pro_team": "TB",
            "percent_started": -1,
            "stats": {},
        }

    home = make_team(
        1, "Beacon", "Han",
        score=118.4,
        starters=[
            make_player("QB One", "QB", "QB", 26.2),
            make_player("RB One", "RB", "RB", 21.5),
            make_player("RB Two", "RB", "RB", 12.0),
            make_player("WR One", "WR", "WR", 19.4),
            make_player("WR Two", "WR", "WR", 11.1),
            make_player("TE One", "TE", "TE", 8.9),
            make_player("FLEX One", "WR", "W/R/T", 10.2),
            make_player("Kicker", "K", "K", 6.0),
            make_player("Defense", "DEF", "DEF", 3.1),
        ],
        bench=[
            make_player("Bench Stud", "WR", "BN", 22.8),
            make_player("Bench QB", "QB", "BN", 4.0),
        ],
        wins=4, losses=1, standing=1,
    )

    away = make_team(
        2, "Purdy Boys", "tyler",
        score=94.1,
        starters=[
            make_player("QB Two", "QB", "QB", 17.5),
            make_player("RB Three", "RB", "RB", 15.9),
            make_player("RB Four", "RB", "RB", 8.4),
            make_player("WR Three", "WR", "WR", 13.6),
            make_player("WR Four", "WR", "WR", 9.0),
            make_player("TE Two", "TE", "TE", 6.5),
            make_player("FLEX Two", "RB", "W/R/T", 7.2),
            make_player("Kicker Two", "K", "K", 8.0),
            make_player("Defense Two", "DEF", "DEF", 8.0),
        ],
        bench=[
            make_player("Bench Bust", "RB", "BN", 1.2),
        ],
        wins=2, losses=3, standing=6,
    )

    matchups_payload = {
        "week": week,
        "total_matchups": 1,
        "matchups": [
            {
                "matchup_id": 1,
                "home_team": home,
                "away_team": away,
                "winner": home["team_name"],
                "margin": round(home["score"] - away["score"], 2),
                "is_playoffs": False,
            }
        ],
    }

    standings_payload = {
        "standings": [
            {
                "rank": 1, "team_id": 1, "team_name": "Beacon", "owner": "Han",
                "wins": 4, "losses": 1, "ties": 0, "win_pct": 0.8,
                "points_for": 612.0, "points_against": 480.0, "point_differential": 132.0,
                "streak": "W3",
            },
            {
                "rank": 2, "team_id": 2, "team_name": "Purdy Boys", "owner": "tyler",
                "wins": 2, "losses": 3, "ties": 0, "win_pct": 0.4,
                "points_for": 480.0, "points_against": 520.0, "point_differential": -40.0,
                "streak": "L1",
            },
        ],
        "leaders": {},
    }

    teams_payload = {
        "total_teams": 2,
        "teams": [
            {**standings_payload["standings"][0], "streak_type": "W", "streak_length": 3, "standing": 1,
             "acquisitions": None, "drops": None, "trades": None, "faab_spent": None},
            {**standings_payload["standings"][1], "streak_type": "L", "streak_length": 1, "standing": 2,
             "acquisitions": None, "drops": None, "trades": None, "faab_spent": None},
        ],
    }

    data = {
        "league": {
            "league_id": 1324751,
            "year": 2026,
            "season_year": 2026,
            "league_name": "CX Retention Fantasy Football",
            "current_week": week,
            "total_teams": 2,
            "league_key": "461.l.1324751",
        },
        "teams": teams_payload,
        "standings": standings_payload,
        "matchups": matchups_payload,
        "week_stats": {
            "highest_score": {"team": home["team_name"], "points": home["score"]},
            "lowest_score": {"team": away["team_name"], "points": away["score"]},
            "biggest_blowout": {"winner": home["team_name"], "loser": away["team_name"], "margin": 24.3},
            "closest_game": {"team1": home["team_name"], "team2": away["team_name"], "margin": 24.3},
            "most_bench_points": {"team": home["team_name"], "points": 26.8},
        },
        "power_rankings": {
            "week": week,
            "rankings": [
                {"rank": 1, "team_id": 1, "team_name": "Beacon", "owner": "Han",
                 "wins": 4, "losses": 1, "ties": 0, "pf": 612.0, "movement": "+1"},
                {"rank": 2, "team_id": 2, "team_name": "Purdy Boys", "owner": "tyler",
                 "wins": 2, "losses": 3, "ties": 0, "pf": 480.0, "movement": "-1"},
            ],
        },
        "next_week_matchups": {
            "week": week + 1,
            "total_matchups": 1,
            "matchups": [
                {
                    "matchup_id": 1,
                    "home_team": {"team_name": "Beacon", "record": "4-1-0"},
                    "away_team": {"team_name": "Purdy Boys", "record": "2-3-0"},
                    "winner": None,
                    "margin": 0.0,
                }
            ],
        },
    }
    # Layer in the engagement features exactly the way YahooLeagueFetcher does.
    from src.gif_bank import pick_gif
    from src.superlatives import compute_superlatives
    data["superlatives"] = compute_superlatives(data)
    data["gif_of_the_week"] = pick_gif(data, week, superlatives=data["superlatives"])
    return data


def check(label: str, cond: bool, detail: str = "") -> None:
    marker = "✅" if cond else "❌"
    suffix = f" — {detail}" if detail else ""
    print(f"  {marker} {label}{suffix}")
    if not cond:
        raise SystemExit(1)


def test_context_builder_end_to_end() -> None:
    print("• context builder end-to-end")
    trend = TrendTracker()
    ownership = OwnershipStats()
    builder = ContextBuilder(trend, ownership)
    week_data = synthetic_week_data(week=5)
    ctx = builder.build_context(week_data, week=5, use_v2_format=True)

    check("returns non-empty context", isinstance(ctx, str) and len(ctx) > 500,
          f"len={len(ctx) if isinstance(ctx, str) else 'n/a'}")
    for expected in (
        "# Week 5 Recap Data",
        "CX Retention Fantasy Football",
        "Week Winner",
        "Beacon",
        "Purdy Boys",
        "Power Rankings",
        "Week 6 Preview",
        "Bench MVP",
        "Weekly Superlatives",
        "Bench Hero of the Week",
        "GIF of the Week",
        "media.giphy.com",
    ):
        check(f"contains {expected!r}", expected in ctx)


def test_recap_generator_context_delegation() -> None:
    print("• RecapGenerator.build_context delegates through ContextBuilder")
    # Instantiate WITHOUT a real fetcher; we're only exercising context path.
    gen = RecapGenerator(fetcher=object())  # sentinel so fetcher never lazy-loads
    ctx = gen.build_context(synthetic_week_data(week=7), week=7)
    check("non-empty context via generator", isinstance(ctx, str) and len(ctx) > 500)
    check("week 7 header present", "# Week 7 Recap Data" in ctx)


def test_oauth_loader_error_message() -> None:
    print("• OAuth loader fails cleanly when no token is available")
    # Ensure env var is not present for this check
    prev = os.environ.pop("YAHOO_OAUTH_JSON", None)
    try:
        from src.yahoo_fetcher import load_yahoo_oauth
        # Point at a non-existent explicit path so the default search misses too.
        try:
            load_yahoo_oauth(explicit_path=Path("/tmp/does-not-exist-oauth.json"))
            raise SystemExit("Expected RuntimeError, none raised")
        except RuntimeError as exc:
            msg = str(exc)
            check("error mentions oauth2.json path", "oauth2.json" in msg)
            check("error mentions env var fallback", "YAHOO_OAUTH_JSON" in msg)
    finally:
        if prev is not None:
            os.environ["YAHOO_OAUTH_JSON"] = prev


def main() -> None:
    print("🏈 Football Recap pipeline validation\n")
    test_context_builder_end_to_end()
    test_recap_generator_context_delegation()
    test_oauth_loader_error_message()
    print("\n🎉 Pipeline validation passed — every non-network path is wired end-to-end.")
    print("   To validate against real Yahoo data, drop oauth2.json into")
    print("   apps/football-recap/config/ (or apps/baseball-engine/config/),")
    print("   then run:  python3 apps/football-recap/scripts/prepare_recap_context.py --week 1")


if __name__ == "__main__":
    main()
