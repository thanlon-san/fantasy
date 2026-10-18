"""
Compact Slack-native weekly digest from ``week_data``.

Produces scannable markdown (emoji headers, ``<@U…>`` mentions, inline GIF)
for draft/paste into Slack — separate from the long Commissioner's Ghost recap.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.constants import format_slack_mention
from src.gif_bank import pick_gif
from src.ownership_stats import compute_start_sit_swaps
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


def week_scores_unfinalized(week: int, week_data: Dict[str, Any]) -> bool:
    """
    True when Yahoo has not finalized this week's matchup scores yet.

    Uses ``league.current_week`` when present, else treats all-zero scores as
    not ready for matchup superlatives / TL;DR highlights.
    """
    league = week_data.get("league") or {}
    yahoo_week = league.get("current_week")
    teams = _all_matchup_teams(week_data)
    scores = [float(t.get("score") or 0) for t in teams]
    all_zero = bool(scores) and all(s == 0.0 for s in scores)

    if yahoo_week is not None:
        try:
            cw = int(yahoo_week)
        except (TypeError, ValueError):
            cw = None
        if cw is not None:
            if week > cw:
                return True
            if week == cw and all_zero:
                return True
            if week < cw:
                return False

    return all_zero


def unfinalized_week_banner(week: int, week_data: Dict[str, Any]) -> str:
    league = week_data.get("league") or {}
    yahoo_week = league.get("current_week")
    yw = f" (Yahoo current_week={yahoo_week})" if yahoo_week is not None else ""
    return (
        f"⚠️ *Week {week} not finalized on Yahoo yet{yw}* — "
        "matchup scores may be 0. Regenerate without `--week` once games finish."
    )


def _all_matchup_teams(week_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in week_data.get("matchups", {}).get("matchups", []) or []:
        for side in ("home_team", "away_team"):
            t = m.get(side)
            if t:
                out.append(t)
    return out


def _pick_snark(team_name: str, bucket: str, options: Sequence[str]) -> str:
    """Deterministic line per team so reruns match but peers in a tier differ."""
    if not options:
        return ""
    if len(options) == 1:
        return options[0]
    digest = hashlib.md5(f"{team_name}:{bucket}".encode()).hexdigest()
    return options[int(digest, 16) % len(options)]


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
        if movement.startswith("▲") or movement.startswith("+") or "▲" in movement:
            return _pick_snark(
                team_name,
                "S-climb",
                (
                    "Top dog and still climbing — annoying.",
                    "No. 1 and rising — the group chat hates you.",
                    "Crown getting heavier; keep whining anyway.",
                ),
            )
        return _pick_snark(
            team_name,
            "S-hold",
            (
                "The rest of the league is cosplaying contenders.",
                "S-tier rent is due; everyone else is subletting hope.",
                "Built different — or at least scored different.",
            ),
        )
    if tier == "F":
        if gap >= 20:
            return _pick_snark(
                team_name,
                "F-gap",
                (
                    "Last place with a full bench of regrets.",
                    "Cellar dweller with a stocked bench — tragic.",
                    "Bottom of the ranks, top of the 'what if' list.",
                ),
            )
        return _pick_snark(
            team_name,
            "F-base",
            (
                "Mathematically still in it, spiritually not.",
                "Playoff math exists; vibes do not.",
                "The tank is subtle but the record isn't.",
            ),
        )
    if heat == "surging":
        return _pick_snark(
            team_name,
            "surging",
            (
                "Three-week heater — don't get comfortable.",
                "On a run — schedule hasn't noticed yet.",
                "Trending up; humility optional.",
            ),
        )
    if heat == "sliding":
        return _pick_snark(
            team_name,
            "sliding",
            (
                "Cooling off like a waiver wire after Tuesday.",
                "Momentum left the chat.",
                "Peaked early; the bye can't come soon enough.",
            ),
        )
    if movement.startswith("▼") or movement.startswith("-") or "▼" in movement:
        return _pick_snark(
            team_name,
            "drop",
            (
                "Dropped a tier in the power ranks — ouch.",
                "Took the elevator down — skipped the lobby.",
                "Rank slide — blame the flex, always the flex.",
            ),
        )
    if movement.startswith("▲") or movement.startswith("+") or "▲" in movement:
        return _pick_snark(
            team_name,
            "rise",
            (
                "Up in the ranks on vibes and points.",
                "Climbing — one more win and it's a personality.",
                "Moved up; don't mention last month's lineup.",
            ),
        )
    if gap >= 15:
        return _pick_snark(
            team_name,
            f"gap-{int(gap)}",
            (
                f"Left {gap:.0f} on the bench and lived to tell nobody.",
                f"{gap:.0f} rotting on the pine — chef's kiss.",
                f"Bench held {gap:.0f}; starters held a funeral.",
            ),
        )
    if score > 0 and score < 80:
        return _pick_snark(
            team_name,
            f"low-{int(score)}",
            (
                f"Scored {score:.0f} — the matchup was not impressed.",
                f"{score:.0f} points — tough crowd, tougher schedule.",
                f"Put up {score:.0f}; opponent sent a thank-you note.",
            ),
        )
    return _pick_snark(
        team_name,
        "steady",
        (
            "Steady Eddie — no headline, no mercy.",
            "Middle of the pack — dangerously average.",
            "No drama, no glory — perfect fantasy purgatory.",
        ),
    )


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


def _season_trophy_leader_changed(
    history: Sequence[Dict[str, Any]],
    week: int,
) -> Optional[str]:
    """Return a TL;DR bullet when the Slack season trophy holder changed this week."""
    through_week = [
        e
        for e in history
        if isinstance(e.get("week"), int) and int(e["week"]) <= week
    ]
    before_week = [
        e for e in through_week if isinstance(e.get("week"), int) and int(e["week"]) < week
    ]
    if not before_week or not through_week:
        return None
    before = compute_season_awards(before_week)
    after = compute_season_awards(through_week)
    prev = (before.get("awards") or {}).get(SLACK_SEASON_TROPHY_KEY)
    curr = (after.get("awards") or {}).get(SLACK_SEASON_TROPHY_KEY)
    if not prev or not curr or prev.get("team") == curr.get("team"):
        return None
    mention = format_slack_mention(
        team_name=curr.get("team", ""),
        owner_name=curr.get("owner") or "",
    )
    return f"🪑 *Bench Whisperer* crown: {mention} (was {prev.get('team')})."


def _biggest_power_mover_line(week_data: Dict[str, Any]) -> Optional[str]:
    rankings = (week_data.get("power_rankings") or {}).get("rankings") or []
    best_delta = 0
    best_row: Optional[Dict[str, Any]] = None
    for row in rankings:
        movement = str(row.get("movement") or "—")
        match = re.fullmatch(r"([▲▼])(\d+)", movement.strip())
        if not match:
            continue
        steps = int(match.group(2))
        signed = steps if match.group(1) == "▲" else -steps
        if abs(signed) > abs(best_delta):
            best_delta = signed
            best_row = row
    if not best_row or best_delta == 0:
        return None
    mention = format_slack_mention(
        team_name=best_row.get("team_name", ""),
        owner_name=best_row.get("owner") or "",
    )
    arrow = "▲" if best_delta > 0 else "▼"
    return f"⚡ Biggest power move: {mention} ({arrow}{abs(best_delta)})."


def _roastable_swap_line(week_data: Dict[str, Any]) -> Optional[str]:
    best_margin = 0.0
    best_team = ""
    best_swap: Optional[Dict[str, Any]] = None
    for team in _all_matchup_teams(week_data):
        for swap in compute_start_sit_swaps(team):
            if not swap.get("roastable"):
                continue
            margin = float(swap["benched_points"]) - float(swap["started_points"])
            if margin > best_margin:
                best_margin = margin
                best_team = team.get("team_name") or ""
                best_swap = swap
    if not best_swap or best_margin <= 0:
        return None
    owner = ""
    for team in _all_matchup_teams(week_data):
        if team.get("team_name") == best_team:
            owner = team.get("owner") or ""
            break
    mention = format_slack_mention(team_name=best_team, owner_name=owner)
    return (
        f"🔥 Roastable swap: {mention} benched *{best_swap['benched_name']}* "
        f"({best_swap['benched_points']:.1f}) over "
        f"*{best_swap['started_name']}* ({best_swap['started_points']:.1f})."
    )


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


def _tldr_block(
    week: int,
    week_data: Dict[str, Any],
    superlatives: Dict[str, Dict[str, Any]],
    gif: Dict[str, str],
    *,
    history: Sequence[Dict[str, Any]],
    scores_unfinalized: bool,
) -> List[str]:
    lines: List[str] = [f"*TL;DR · Week {week}*"]
    stats = week_data.get("week_stats") or {}
    high = stats.get("highest_score") or {}
    pts = high.get("points")
    has_real_scores = (
        isinstance(pts, (int, float)) and float(pts) > 0 and not scores_unfinalized
    )
    if high.get("team") and has_real_scores:
        pts_fmt = f"{pts:.1f}" if isinstance(pts, (int, float)) else str(pts)
        lines.append(f"• Top score: *{high.get('team')}* ({pts_fmt}).")
    elif scores_unfinalized:
        lines.append("• Matchups still in progress — scores not in yet.")

    extras: List[str] = []
    if not scores_unfinalized:
        swap_line = _roastable_swap_line(week_data)
        if swap_line:
            extras.append(swap_line)
        trophy_change = _season_trophy_leader_changed(history, week)
        if trophy_change:
            extras.append(f"• {trophy_change}")
        mover = _biggest_power_mover_line(week_data)
        if mover:
            extras.append(f"• {mover}")
        headline = _headline_superlative(superlatives)
        if headline and len(extras) < 3:
            extras.append(f"• *{headline[0]}:* {headline[1]}.")
    for bullet in extras[:3]:
        if not bullet.startswith("•"):
            lines.append(f"• {bullet}")
        else:
            lines.append(bullet)

    lines.append(f"• GIF vibe: _{gif.get('caption', '')}_")
    return lines


def _format_gif_for_slack(gif: Dict[str, str]) -> str:
    """Bare URL on its own line so Slack unfurls the GIF (not markdown image syntax)."""
    return gif.get("url", "")


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
    scores_unfinalized = week_scores_unfinalized(week, week_data)

    lines: List[str] = [
        f"🏈 *Week {week} · {league_name}*",
    ]

    if scores_unfinalized:
        lines.append(unfinalized_week_banner(week, week_data))

    trophy = _season_trophy_line(history)
    if trophy:
        lines.append(trophy)

    lines.append("")
    lines.extend(
        _tldr_block(
            week,
            week_data,
            superlatives,
            gif,
            history=history,
            scores_unfinalized=scores_unfinalized,
        )
    )
    lines.append("")
    lines.append(_format_gif_for_slack(gif))
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
