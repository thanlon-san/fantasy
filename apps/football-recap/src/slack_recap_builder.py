"""
Compact Slack-native weekly digest from ``week_data``.

Produces scannable markdown (emoji headers, ``<@U…>`` mentions, inline GIF)
for draft/paste into Slack — separate from the long Commissioner's Ghost recap.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.constants import format_slack_mention
from src.gif_bank import pick_gif
from src.season_leaderboard import SLACK_SEASON_TROPHY_KEY, compute_season_awards
from src.superlatives import compute_superlatives

TIER_LABELS = ("S", "A", "B", "C", "D", "F")
RECAP_HISTORY_FILE = "recap_history.json"
OUTPUT_DIR = "output"


def tier_for_rank(rank: int, total: int) -> str:
    """Map power rank (1 = best) to an S–F bucket, proportional to league size."""
    if total <= 0:
        return "F"
    if total == 1:
        return "S"
    idx = min(5, int((rank - 1) * 6 / total))
    return TIER_LABELS[idx]


def _team_week_snapshot(
    week_data: Dict[str, Any], team_name: str
) -> Dict[str, Any]:
    for team in _all_matchup_teams(week_data):
        if team.get("team_name") == team_name:
            return team
    return {}


def _all_matchup_teams(week_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in week_data.get("matchups", {}).get("matchups", []) or []:
        for side in ("home_team", "away_team"):
            t = m.get(side)
            if t:
                out.append(t)
    return out


def snark_line_for_team(
    row: Dict[str, Any],
    week_data: Dict[str, Any],
    *,
    tier: str,
) -> str:
    """One deterministic quip per team (max one line)."""
    heat = (row.get("heat") or "steady").lower()
    movement = str(row.get("movement") or "—")
    team_name = row.get("team_name") or ""
    snap = _team_week_snapshot(week_data, team_name)
    gap = float(snap.get("management_gap") or 0)
    score = float(snap.get("score") or 0)

    if tier == "S":
        if movement.startswith("▲"):
            return "Top dog and still climbing — annoying."
        return "The rest of the league is cosplaying contenders."
    if tier == "F":
        if gap >= 20:
            return "Last place with a full bench of regrets."
        return "Mathematically still in it, spiritually not."
    if heat == "surging":
        return "Three-week heater — don't get comfortable."
    if heat == "sliding":
        return "Cooling off like a waiver wire after Tuesday."
    if movement.startswith("▼"):
        return "Dropped a tier in the power ranks — ouch."
    if movement.startswith("▲"):
        return "Up in the ranks on vibes and points."
    if gap >= 15:
        return f"Left {gap:.0f} on the bench and lived to tell nobody."
    if score > 0 and score < 80:
        return f"Scored {score:.0f} — the matchup was not impressed."
    return "Steady Eddie — no headline, no mercy."


def _load_history(path: str = RECAP_HISTORY_FILE) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _headline_superlative(
    superlatives: Dict[str, Dict[str, Any]],
) -> Optional[Tuple[str, str]]:
    """Pick the punchiest award for the TL;DR highlight."""
    priority = (
        "upset_of_the_week",
        "blowout_of_the_week",
        "nailbiter_of_the_week",
        "cooked_of_the_week",
        "coach_of_the_week",
        "bench_hero_of_the_week",
        "shootout_of_the_week",
        "cold_war_of_the_week",
    )
    for key in priority:
        entry = superlatives.get(key)
        if not entry:
            continue
        label = entry.get("label") or key.replace("_", " ").title()
        if key == "upset_of_the_week":
            detail = (
                f"{entry.get('winner')} over {entry.get('loser')} "
                f"(proj gap {entry.get('projection_gap')})"
            )
        elif key == "blowout_of_the_week":
            detail = (
                f"{entry.get('team')} by {entry.get('margin')} over "
                f"{entry.get('opponent')}"
            )
        elif key == "nailbiter_of_the_week":
            detail = (
                f"{entry.get('team1')} vs {entry.get('team2')} — "
                f"{entry.get('margin')} pts"
            )
        elif key == "cooked_of_the_week":
            detail = (
                f"{entry.get('team')} left {entry.get('management_gap')} on the bench"
            )
        elif key == "coach_of_the_week":
            detail = f"{entry.get('team')} (gap {entry.get('management_gap')})"
        elif key == "bench_hero_of_the_week":
            detail = (
                f"{entry.get('player')} ({entry.get('points')} pts) on "
                f"{entry.get('team')}'s bench"
            )
        else:
            detail = str(entry)
        return label, detail
    return None


def _season_trophy_line(
    history: Sequence[Dict[str, Any]],
) -> Optional[str]:
    payload = compute_season_awards(list(history))
    award = (payload.get("awards") or {}).get(SLACK_SEASON_TROPHY_KEY)
    if not award:
        return None
    mention = format_slack_mention(
        team_name=award.get("team", ""),
        owner_name=award.get("owner") or "",
    )
    pts = award.get("total_points_left")
    stat = f"{pts:.1f} pts left on benches" if pts is not None else award.get("description", "")
    return f"🏆 *Season · {award.get('label', 'Trophy')}:* {mention} — {stat}"


def _tldr_line(
    week: int,
    week_data: Dict[str, Any],
    superlatives: Dict[str, Dict[str, Any]],
    gif: Dict[str, str],
) -> str:
    stats = week_data.get("week_stats") or {}
    high = stats.get("highest_score") or {}
    parts: List[str] = [f"*TL;DR · Week {week}*"]
    if high.get("team"):
        pts = high.get("points")
        pts_fmt = f"{pts:.1f}" if isinstance(pts, (int, float)) else str(pts)
        parts.append(f"Top score: *{high.get('team')}* ({pts_fmt}).")
    headline = _headline_superlative(superlatives)
    if headline:
        parts.append(f"*{headline[0]}:* {headline[1]}.")
    parts.append(f"GIF vibe: _{gif.get('caption', '')}_")
    return " ".join(parts)


def _format_tier_block(
    rankings: List[Dict[str, Any]],
    week_data: Dict[str, Any],
) -> List[str]:
    if not rankings:
        return ["*Power tiers* — (no rankings this week)"]

    by_tier: Dict[str, List[Dict[str, Any]]] = {t: [] for t in TIER_LABELS}
    total = len(rankings)
    for row in rankings:
        tier = tier_for_rank(int(row.get("rank") or total), total)
        by_tier[tier].append(row)

    lines = ["*⚡ Power tiers* _(S → F, one line each)_"]
    for tier in TIER_LABELS:
        rows = by_tier[tier]
        if not rows:
            continue
        lines.append(f"*{tier}-tier*")
        for row in rows:
            mention = format_slack_mention(
                team_name=row.get("team_name", ""),
                owner_name=row.get("owner") or "",
            )
            record = f"{row.get('wins', 0)}–{row.get('losses', 0)}"
            snark = snark_line_for_team(row, week_data, tier=tier)
            lines.append(f"• {mention} ({record}, PF {row.get('pf', 0)}) — {snark}")
    return lines


def build_slack_recap(
    week: int,
    week_data: Dict[str, Any],
    *,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    full_recap_path: Optional[str] = None,
) -> str:
    """
    Build Slack-friendly markdown for week ``week``.

    ``full_recap_path`` — if the long recap file exists, link text is included.
    """
    history = list(history) if history is not None else _load_history()
    superlatives = week_data.get("superlatives") or compute_superlatives(week_data)
    gif = week_data.get("gif_of_the_week") or pick_gif(
        week_data, week, superlatives=superlatives
    )

    league = week_data.get("league") or {}
    league_name = league.get("league_name") or "Fantasy Football"

    lines: List[str] = [
        f"🏈 *Week {week} · {league_name}*",
    ]

    trophy = _season_trophy_line(history)
    if trophy:
        lines.append(trophy)

    lines.append("")
    lines.append(_tldr_line(week, week_data, superlatives, gif))
    lines.append("")
    lines.append(f"![GIF]({gif['url']})")
    lines.append("")

    rankings = (week_data.get("power_rankings") or {}).get("rankings") or []
    lines.extend(_format_tier_block(rankings, week_data))

    recap_path = full_recap_path or os.path.join(OUTPUT_DIR, f"week-{week}-recap.md")
    if recap_path and os.path.isfile(recap_path):
        lines.append("")
        lines.append(
            f"📖 *Full Commissioner's Ghost recap:* attach `{os.path.basename(recap_path)}` "
            f"or paste from `{recap_path}`"
        )

    body = "\n".join(lines).strip() + "\n"
    if body.count("\n") > 45:
        # Soft guard — callers can trim; tests assert reasonable default size.
        pass
    return body


def save_slack_recap(
    week: int,
    week_data: Dict[str, Any],
    *,
    output_dir: str = OUTPUT_DIR,
    history: Optional[Sequence[Dict[str, Any]]] = None,
) -> str:
    """Write ``output/week-N-slack.md`` and return the path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    recap_path = str(out / f"week-{week}-recap.md")
    markdown = build_slack_recap(
        week,
        week_data,
        history=history,
        full_recap_path=recap_path if os.path.isfile(recap_path) else None,
    )
    path = out / f"week-{week}-slack.md"
    path.write_text(markdown, encoding="utf-8")
    return str(path)
