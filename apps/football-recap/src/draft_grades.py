"""
Draft grades context shaping.

We don't compute a statistical "grade" (no reliable ADP/projection source
at draft time), so — consistent with the recap generation philosophy — this
module just shapes the raw draft picks into readable groupings and hands
that to the Cursor Automation agent to *narrate* grades using the columnist
voice. Python's job is structure, not judgment.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def group_picks_by_team(draft_results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Group draft picks by team, in draft order."""
    by_team: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for pick in draft_results.get("picks", []):
        team = pick.get("team_name") or pick.get("team_key") or "Unknown Team"
        by_team[team].append(pick)
    return dict(by_team)


def group_picks_by_round(draft_results: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
    """Group draft picks by round number, in pick order."""
    by_round: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for pick in draft_results.get("picks", []):
        rnd = pick.get("round") or 0
        by_round[rnd].append(pick)
    for rnd in by_round:
        by_round[rnd].sort(key=lambda p: p.get("pick") or 0)
    return dict(by_round)


def position_counts_by_team(
    by_team: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, int]]:
    """Count picks per position for each team — surfaces roster-building bets."""
    out: Dict[str, Dict[str, int]] = {}
    for team, picks in by_team.items():
        counts: Dict[str, int] = defaultdict(int)
        for p in picks:
            pos = p.get("position") or "UNKNOWN"
            counts[pos] += 1
        out[team] = dict(counts)
    return out


def build_draft_grades_context(draft_results: Dict[str, Any], *, league_name: str = "") -> str:
    """
    Build the markdown context bundle for the automation agent to write a
    "Draft Grades" recap from. Pure formatting — no grading opinions here,
    that's the agent's job using the columnist voice.
    """
    by_team = group_picks_by_team(draft_results)
    by_round = group_picks_by_round(draft_results)
    positions = position_counts_by_team(by_team)

    lines = [f"# Draft Results — {league_name or 'League'}", ""]
    lines.append(f"Total picks: {draft_results.get('total_picks', 0)}")
    lines.append("")

    lines.append("## Picks by Team (draft order)")
    lines.append("")
    for team in sorted(by_team.keys()):
        picks = by_team[team]
        owner = picks[0].get("owner", "") if picks else ""
        lines.append(f"### {team} ({owner})")
        for p in picks:
            name = p.get("player_name") or "Unknown Player"
            pos = p.get("position") or "?"
            lines.append(f"- R{p.get('round')}.P{p.get('pick')}: {name} ({pos})")
        pos_summary = ", ".join(
            f"{k}: {v}" for k, v in sorted(positions.get(team, {}).items())
        )
        if pos_summary:
            lines.append(f"  _Position breakdown: {pos_summary}_")
        lines.append("")

    lines.append("## Picks by Round (draft board order)")
    lines.append("")
    for rnd in sorted(by_round.keys()):
        lines.append(f"### Round {rnd}")
        for p in by_round[rnd]:
            name = p.get("player_name") or "Unknown Player"
            pos = p.get("position") or "?"
            lines.append(f"- Pick {p.get('pick')}: {p.get('team_name')} takes {name} ({pos})")
        lines.append("")

    lines.append(
        "## Instructions for the writer\n\n"
        "Write a fun, affectionate 'Draft Grades' recap. For each team: "
        "assign a letter grade (A-F) based on positional balance, value "
        "of top picks relative to draft slot, and any glaring reaches or "
        "steals visible from the pick order above. Keep it playful — this "
        "is a casual league, not a real sports column. No stats beyond what's "
        "given above; do not invent ADP or projections that aren't provided."
    )
    return "\n".join(lines)
