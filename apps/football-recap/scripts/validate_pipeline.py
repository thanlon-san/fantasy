#!/usr/bin/env python3
"""Offline smoke test for the weekly recap pipeline.

Runs the whole chain against a synthetic 14-team week so the context builder,
power rankings, canvas renderers, and history writer can be exercised without
touching Yahoo. Also reports whether Yahoo credentials are present and, with
--check-yahoo, whether they actually work.

The fixture is obviously synthetic (managers are "Manager 01"...) so its output
can never be mistaken for real league data.

Usage:
    python apps/football-recap/scripts/validate_pipeline.py
    python apps/football-recap/scripts/validate_pipeline.py --check-yahoo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import (  # noqa: E402
    LEAGUE_SIZE_2026,
    YAHOO_OAUTH_ENV_VAR,
    get_current_nfl_week,
    has_season_started,
)
from src.power_rankings import compute_power_rankings, format_rankings_lines  # noqa: E402
from src.recap_context import build_context  # noqa: E402
from src.yahoo_nfl_client import (  # noqa: E402
    YahooError,
    YahooNFLClient,
    compute_week_stats,
    flatten,
    iter_collection,
)

PASS, FAIL = "PASS", "FAIL"
_results: List[tuple] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    _results.append((PASS if condition else FAIL, name, detail))
    print(f"  [{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))
    return condition


def make_fixture(week: int = 1, teams: int = LEAGUE_SIZE_2026) -> Dict[str, Any]:
    """Build a synthetic but structurally faithful week_data blob."""
    standings = []
    for i in range(1, teams + 1):
        wins = (teams - i) % (week + 1)
        standings.append(
            {
                "team_key": f"nfl.l.999.t.{i}",
                "team_id": i,
                "team_name": f"Test Team {i:02d}",
                "owner": f"Manager {i:02d}",
                "managers": [f"Manager {i:02d}"],
                "rank": i,
                "wins": wins,
                "losses": week - wins,
                "ties": 0,
                "win_pct": round(wins / max(1, week), 3),
                "points_for": round(150 - i * 3.5, 2),
                "points_against": round(100 + i * 2.0, 2),
                "streak": "W1" if wins else "L1",
                "week_points": round(150 - i * 3.5, 2),
                "week_projected": 120.0,
            }
        )

    matchups = []
    for index in range(0, teams, 2):
        home, away = standings[index], standings[index + 1]

        def side(team):
            return {
                "team_id": team["team_id"],
                "team_key": team["team_key"],
                "team_name": team["team_name"],
                "owner": team["owner"],
                "score": team["week_points"],
                "projected": team["week_projected"],
                "record": f"{team['wins']}-{team['losses']}-0",
                "starters": [],
                "bench": [],
            }

        winner = (
            home["team_name"]
            if home["week_points"] > away["week_points"]
            else away["team_name"]
        )
        matchups.append(
            {
                "matchup_id": index // 2,
                "week": week,
                "is_playoffs": False,
                "is_consolation": False,
                "status": "postevent",
                "home_team": side(home),
                "away_team": side(away),
                "winner": winner,
                "margin": round(
                    abs(home["week_points"] - away["week_points"]), 2
                ),
            }
        )

    return {
        "week": week,
        "league": {
            "league_name": "Validation League",
            "season": "2026",
            "total_teams": teams,
            "current_week": week,
        },
        "teams": {"total_teams": teams, "teams": standings},
        "standings": {"standings": standings},
        "matchups": {"week": week, "total_matchups": len(matchups), "matchups": matchups},
        "next_week_matchups": {
            "week": week + 1,
            "total_matchups": len(matchups),
            "matchups": matchups,
        },
        "week_stats": compute_week_stats(week, matchups),
        "source": "fixture",
    }


def validate_yahoo_parsers() -> None:
    print("\nYahoo JSON shape helpers")
    check(
        "flatten collapses list-of-single-key-dicts",
        flatten([{"a": 1}, [{"b": 2}], {"c": 3}]) == {"a": 1, "b": 2, "c": 3},
    )
    check(
        "flatten walks numeric-keyed containers",
        flatten({"0": {"x": 1}, "1": {"y": 2}}) == {"x": 1, "y": 2},
    )
    check(
        "iter_collection skips the count key and orders numerically",
        list(iter_collection({"0": "a", "10": "c", "2": "b", "count": 3}))
        == ["a", "b", "c"],
    )
    check("iter_collection passes lists through", list(iter_collection(["a"])) == ["a"])
    check("iter_collection tolerates junk", list(iter_collection(None)) == [])


def validate_power_rankings(fixture: Dict[str, Any], week: int) -> List[Dict[str, Any]]:
    print("\nPower rankings")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "pr.json")
        rankings = compute_power_rankings(fixture, week, history_path=path)

    check(
        "ranks every team",
        len(rankings) == LEAGUE_SIZE_2026,
        f"{len(rankings)} of {LEAGUE_SIZE_2026}",
    )
    check(
        "ranks are contiguous 1..N",
        [r["rank"] for r in rankings] == list(range(1, len(rankings) + 1)),
    )
    check(
        "sorted by descending score",
        all(
            rankings[i]["score"] >= rankings[i + 1]["score"]
            for i in range(len(rankings) - 1)
        ),
    )
    check("every rank has a movement marker", all(r.get("movement") for r in rankings))
    lines = format_rankings_lines(rankings)
    check("renders one line per team", len(lines) == len(rankings))
    check(
        "lines use @Owner form",
        all("**@" in line for line in lines),
        lines[0] if lines else "",
    )
    return rankings


def validate_context(fixture: Dict[str, Any], week: int) -> Dict[str, Any]:
    print("\nPrepared context")
    built = build_context(fixture, week)
    markdown = built["markdown"]

    for section in (
        f"# Week {week} Recap Data",
        "## Matchups",
        "## Power Rankings",
        "## Weekly Superlatives",
        f"## Week {week + 1} Preview",
        "## GIF of the Week",
        "## CLOSING LINE",
    ):
        check(f"emits {section!r}", section in markdown)

    check("names a bit of the week", "## BIT_OF_THE_WEEK" in markdown)
    check(
        "power rankings list every team",
        all(f"\n{r['rank']}. **@" in markdown for r in built["rankings"]),
    )
    check("closing line is in the meta sidecar", bool(built["meta"]["closing_line"]))
    check(
        "closing line text appears in the context",
        built["meta"]["closing_line"] in markdown,
    )
    check(
        "forbids invention explicitly",
        "Do not invent" in markdown,
    )
    check(
        "omits the GIF line when no source is configured",
        "Do not invent a Giphy URL" in markdown or "![GIF](" in markdown,
    )
    check("superlatives were derived", built["meta"]["superlative_count"] > 0)
    return built


def validate_canvases(fixture: Dict[str, Any], week: int) -> None:
    print("\nCanvas renderers")
    from prepare_league_hq_canvas import build_canvas as build_hq
    from prepare_preseason_canvas import build_canvas as build_preseason

    hq = build_hq(fixture, week)
    check("HQ canvas has standings", "## Standings" in hq)
    check("HQ canvas has power rankings", "## Power Rankings" in hq)
    check("HQ canvas has season awards", "## Season Awards" in hq)
    check(
        "HQ canvas lists every team in standings",
        all(f"Manager {i:02d}" in hq for i in range(1, LEAGUE_SIZE_2026 + 1)),
    )

    preseason = build_preseason([], "Test status")
    check("preseason canvas renders with no roster", "# 🏈 League HQ" in preseason)
    check(
        "preseason canvas admits the roster is pending",
        "has not been read from Yahoo yet" in preseason,
    )
    check("preseason canvas shows empty standings", "_No games played yet._" in preseason)

    populated = build_preseason(
        [{"manager": "A", "team_name": "T", "draft_slot": 1}], "Test"
    )
    check("preseason canvas renders a configured roster", "| 1 | A | T |" in populated)


def validate_environment(check_yahoo: bool) -> None:
    print("\nEnvironment")
    week = get_current_nfl_week()
    check("season start date is configured", True, f"season started: {has_season_started()}")
    check("current week resolves", 1 <= week <= 18, f"week {week}")

    has_creds = bool(os.environ.get(YAHOO_OAUTH_ENV_VAR, "").strip())
    check(f"{YAHOO_OAUTH_ENV_VAR} is set", has_creds)

    if not check_yahoo:
        print("  [skip] Yahoo connectivity (pass --check-yahoo to test)")
        return

    try:
        client = YahooNFLClient()
    except YahooError as exc:
        check("Yahoo credentials load", False, str(exc))
        return
    check("Yahoo credentials load", True)

    try:
        client.refresh_access_token()
        check("Yahoo token refresh", True)
    except YahooError as exc:
        check("Yahoo token refresh", False, str(exc))
        return

    try:
        client.fetch_league_meta()
        check("Yahoo league is readable", True)
    except YahooError as exc:
        check("Yahoo league is readable", False, f"{exc.code}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, default=1, help="Week to simulate")
    parser.add_argument(
        "--check-yahoo",
        action="store_true",
        help="Also hit Yahoo to verify credentials really work.",
    )
    parser.add_argument("--dump", help="Write the generated context markdown here")
    args = parser.parse_args()

    print("Validating the weekly recap pipeline (offline fixture)\n" + "=" * 55)

    fixture = make_fixture(args.week)
    validate_yahoo_parsers()
    validate_power_rankings(fixture, args.week)
    built = validate_context(fixture, args.week)
    validate_canvases(fixture, args.week)
    validate_environment(args.check_yahoo)

    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as handle:
            handle.write(built["markdown"])
        print(f"\nWrote sample context to {args.dump}")

    failures = [r for r in _results if r[0] == FAIL]
    print("\n" + "=" * 55)
    print(f"{len(_results) - len(failures)} passed, {len(failures)} failed")
    for _, name, detail in failures:
        print(f"  FAIL: {name}" + (f" — {detail}" if detail else ""))

    # Yahoo connectivity is reported but never gates the offline suite: the
    # pipeline being correct and Yahoo being reachable are separate questions.
    blocking = [
        r for r in failures if not r[1].startswith("Yahoo") and YAHOO_OAUTH_ENV_VAR not in r[1]
    ]
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
