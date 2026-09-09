#!/usr/bin/env python3
"""Shape the draft board into prepared context for draft grades.

Same split as the weekly recap: this does the arithmetic, the writer does the
voice. Everything here is derived from the board -- no opinions, no invented
players.

Writes ``output/draft-<season>-context.md``.

Usage:
    python apps/football-recap/scripts/prepare_draft_context.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import OUTPUT_DIR  # noqa: E402

DEFAULT_BOARD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "draft-2026.json",
)

# Yahoo default starting lineup for a 14-team league.
STARTER_NEEDS = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "K": 1, "DST": 1}
# Rounds at or after which taking a K/DST is normal rather than a reach.
SENSIBLE_K_DST_ROUND = 13


def load_board(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def analyze_team(team: Dict[str, Any], rounds: int) -> Dict[str, Any]:
    picks = [
        {"round": p[0], "player": p[1], "nfl": p[2], "pos": p[3]}
        for p in team["picks"]
    ]
    by_pos = Counter(p["pos"] for p in picks)

    first_at = {}
    for pos in ("QB", "RB", "WR", "TE", "K", "DST"):
        hits = [p["round"] for p in picks if p["pos"] == pos]
        first_at[pos] = min(hits) if hits else None

    # Positions where the roster cannot even field a legal starting lineup.
    unfilled = [
        pos for pos, need in STARTER_NEEDS.items() if by_pos.get(pos, 0) < need
    ]

    # Kickers and defenses taken earlier than they need to be.
    early_k_dst = [
        p
        for p in picks
        if p["pos"] in ("K", "DST") and p["round"] < SENSIBLE_K_DST_ROUND
    ]

    # Depth beyond what a lineup can use.
    hoarded = {
        pos: count
        for pos, count in by_pos.items()
        if pos in ("QB", "TE", "K", "DST") and count > STARTER_NEEDS[pos] + 1
    }

    core = [p for p in picks if p["round"] <= 3]
    bench_flex = by_pos.get("RB", 0) + by_pos.get("WR", 0)

    return {
        "team_name": team["team_name"],
        "draft_slot": team["draft_slot"],
        "picks": picks,
        "by_pos": dict(by_pos),
        "first_at": first_at,
        "unfilled_starters": unfilled,
        "early_k_dst": early_k_dst,
        "hoarded": hoarded,
        "core": core,
        "rb_wr_count": bench_flex,
    }


def build_markdown(board: Dict[str, Any], teams: List[Dict[str, Any]]) -> str:
    rounds = board.get("rounds", 15)
    parts: List[str] = []
    parts.append(f"# {board['season']} Draft Board — prepared context")
    parts.append(
        f"{len(teams)}-team snake, {rounds} rounds, drafted "
        f"{board.get('draft_date', 'unknown date')}."
    )
    parts.append(
        "\n> Grade only what is on this board. Do not invent picks, players, "
        "projections, or ADP. Every team gets a grade; nobody is skipped."
    )
    parts.append(
        f"\nStarting lineup assumed: "
        + ", ".join(f"{n}{p}" for p, n in STARTER_NEEDS.items())
        + f". A K or DST before round {SENSIBLE_K_DST_ROUND} is early."
    )

    # League-wide context so the grades can be comparative.
    parts.append("\n## League-wide")
    all_first_qb = [t["first_at"]["QB"] for t in teams if t["first_at"]["QB"]]
    all_first_te = [t["first_at"]["TE"] for t in teams if t["first_at"]["TE"]]
    parts.append(
        f"- First QB taken by a team: earliest round {min(all_first_qb)}, "
        f"latest round {max(all_first_qb)}"
    )
    parts.append(
        f"- First TE taken by a team: earliest round {min(all_first_te)}, "
        f"latest round {max(all_first_te)}"
    )
    reachers = [t for t in teams if t["early_k_dst"]]
    parts.append(
        f"- Teams that spent a pick on K/DST before round "
        f"{SENSIBLE_K_DST_ROUND}: {len(reachers)}"
    )
    broken = [t for t in teams if t["unfilled_starters"]]
    parts.append(f"- Teams that cannot field a full legal starting lineup: {len(broken)}")

    parts.append("\n## Teams")
    for team in sorted(teams, key=lambda t: t["draft_slot"]):
        parts.append(f"\n### {team['draft_slot']}. {team['team_name']}")

        counts = ", ".join(
            f"{pos} {team['by_pos'].get(pos, 0)}"
            for pos in ("QB", "RB", "WR", "TE", "K", "DST")
        )
        parts.append(f"Roster shape: {counts}")

        core = ", ".join(f"{p['player']} ({p['pos']})" for p in team["core"])
        parts.append(f"First three rounds: {core}")

        firsts = ", ".join(
            f"{pos} R{rnd}" for pos, rnd in team["first_at"].items() if rnd
        )
        parts.append(f"First taken at each position: {firsts}")

        if team["unfilled_starters"]:
            parts.append(
                f"⚠️ Cannot start a legal lineup — short at: "
                f"{', '.join(team['unfilled_starters'])}"
            )
        if team["early_k_dst"]:
            early = ", ".join(
                f"{p['player']} ({p['pos']}, R{p['round']})"
                for p in team["early_k_dst"]
            )
            parts.append(f"⚠️ Early K/DST: {early}")
        if team["hoarded"]:
            hoard = ", ".join(f"{n} {pos}s" for pos, n in team["hoarded"].items())
            parts.append(f"⚠️ Roster clog: {hoard}")

        full = "; ".join(
            f"R{p['round']} {p['player']} ({p['nfl']} {p['pos']})"
            for p in team["picks"]
        )
        parts.append(f"Full board: {full}")

    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", default=DEFAULT_BOARD, help="Draft board JSON")
    parser.add_argument("--out", default=None, help="Where to write the context")
    args = parser.parse_args()

    if not os.path.exists(args.board):
        print(f"No draft board at {args.board}", file=sys.stderr)
        return 1

    board = load_board(args.board)
    teams = [analyze_team(t, board.get("rounds", 15)) for t in board["teams"]]

    out = args.out or os.path.join(
        OUTPUT_DIR, f"draft-{board['season']}-context.md"
    )
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(build_markdown(board, teams))

    total = sum(len(t["picks"]) for t in teams)
    print(f"Wrote {out}")
    print(f"{len(teams)} teams, {total} picks analyzed")
    for team in sorted(teams, key=lambda t: t["draft_slot"]):
        flags = []
        if team["unfilled_starters"]:
            flags.append(f"short {'/'.join(team['unfilled_starters'])}")
        if team["early_k_dst"]:
            flags.append(f"{len(team['early_k_dst'])} early K/DST")
        if team["hoarded"]:
            flags.append("clogged")
        print(
            f"  {team['draft_slot']:>2}. {team['team_name']:<24}"
            + (f" [{', '.join(flags)}]" if flags else "")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
