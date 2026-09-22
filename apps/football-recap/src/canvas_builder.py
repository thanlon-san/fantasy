"""
Slack Canvas content for the "League HQ" living dashboard.

Unlike the weekly recap (an event, posted once), the Canvas is a persistent
document in #cx-retention-fantasy-football that gets overwritten each week:
current standings, power rankings, and season-long achievements. Built as
plain markdown since that's what ``slack_create_canvas`` /
``slack_update_canvas`` accept.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.constants import DRAFT_ORDER_2026, PRESEASON_MANAGERS_2026

LEAGUE_HQ_CHANNEL_ID = "C05QV3E5J22"
DEFAULT_LEAGUE_NAME = "CX Retention Fantasy Football"

# Same playful categories as season_leaderboard — shown empty in preseason
# so people know what's coming without inventing winners.
PRESEASON_AWARD_PREVIEWS = [
    (
        "🪑 The Bench Whisperer",
        "Most points left on the bench. Your bench is having a season — you just haven't started it yet.",
    ),
    (
        "🧠 Iron Fist Award",
        "Smallest average leftover bench points. Lineup savant energy.",
    ),
    (
        "🎬 Human Highlight Reel",
        "Most Bench Hero of the Week nods — the bench that keeps producing.",
    ),
    (
        "🎲 Giant Slayer",
        "Most Upset of the Week wins. Nobody saw these coming.",
    ),
    (
        "🔨 The Hammer",
        "Most Blowout of the Week wins. Shows no mercy, still a compliment.",
    ),
    (
        "😰 Nail-Biter of the Season",
        "Closest margin all year. Will be a one-point heart attack. Probably.",
    ),
    (
        "💥 Blowout of the Season",
        "Biggest margin all year. Reserved for the week someone forgets they have a kicker.",
    ),
    (
        "💪 Iron Stomach Award",
        "Most weeks with the low score — still showing up every Sunday.",
    ),
]


def _format_standings_table(
    standings: List[Dict[str, Any]], *, placeholder: bool = False
) -> str:
    if not standings:
        return "_No standings yet._"
    lines = ["| Rank | Team | Owner | Record | PF | PA |", "|---|---|---|---|---|---|"]
    if placeholder:
        for t in standings:
            lines.append(
                f"| — | {t.get('team_name', 'TBD')} | {t.get('owner', '')} | — | — | — |"
            )
        return "\n".join(lines)
    for t in sorted(standings, key=lambda x: x.get("rank", 999)):
        record = f"{t.get('wins', 0)}-{t.get('losses', 0)}-{t.get('ties', 0)}"
        lines.append(
            f"| {t.get('rank', '')} | {t.get('team_name', '')} | {t.get('owner', '')} "
            f"| {record} | {t.get('points_for', 0):.1f} | {t.get('points_against', 0):.1f} |"
        )
    return "\n".join(lines)


def _format_power_rankings(
    rankings: List[Dict[str, Any]], *, placeholder: bool = False
) -> str:
    if not rankings:
        return "_No power rankings yet._"
    lines = ["| Rank | Team | Owner | Record | PF |", "|---|---|---|---|---|"]
    if placeholder:
        for r in rankings:
            lines.append(
                f"| — | {r.get('team_name', 'TBD')} | {r.get('owner', '')} | — | — |"
            )
        return "\n".join(lines)
    for r in sorted(rankings, key=lambda x: x.get("rank", 999)):
        record = f"{r.get('wins', 0)}-{r.get('losses', 0)}-{r.get('ties', 0)}"
        movement = r.get("movement", "—")
        lines.append(
            f"| {r.get('rank', '')} {movement} | {r.get('team_name', '')} "
            f"| {r.get('owner', '')} | {record} | {r.get('pf', 0):.1f} |"
        )
    return "\n".join(lines)


def _owner_cell(manager: Dict[str, Any], *, slack_mentions: bool = False) -> str:
    owner = manager.get("owner", "")
    slack_id = manager.get("slack_id") or ""
    if slack_mentions and slack_id:
        return f"![](@{slack_id})"
    return owner


def _team_cell(manager: Dict[str, Any]) -> str:
    # Prefer the 2026 Yahoo name (`team`); last_team is 2025 ESPN history.
    team = (manager.get("team") or manager.get("last_team") or "").strip()
    if team:
        return team
    if manager.get("status") == "open":
        return "TBD — still recruiting"
    return "Team name TBD (new this year)"


def _team_to_manager_map(
    managers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for m in managers or PRESEASON_MANAGERS_2026:
        team = (m.get("team") or m.get("last_team") or "").strip()
        if team:
            out[team] = m
    return out


def _format_draft_order(
    draft_order: Optional[List[str]] = None,
    managers: Optional[List[Dict[str, Any]]] = None,
    *,
    slack_mentions: bool = False,
) -> str:
    order = draft_order if draft_order is not None else DRAFT_ORDER_2026
    by_team = _team_to_manager_map(managers)
    lines = ["| Pick | Team | Manager |", "|---|---|---|"]
    for i, team in enumerate(order, 1):
        mgr = by_team.get(team, {})
        if mgr:
            owner = _owner_cell(mgr, slack_mentions=slack_mentions)
        else:
            owner = team
        lines.append(f"| {i} | {team} | {owner} |")
    return "\n".join(lines)


def _format_preseason_awards() -> str:
    lines = [
        "Nothing to hand out yet — Week 1 is still on the calendar. "
        "These are the trophies that will show up once box scores exist. "
        "All of them are just the numbers being funny on their own.",
        "",
    ]
    for label, desc in PRESEASON_AWARD_PREVIEWS:
        lines.append(f"- {label}: _vacant_\n  _{desc}_")
    return "\n".join(lines)


def preseason_placeholder_rows(
    managers: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Standings-shaped rows for the preseason Canvas (no records yet)."""
    rows = []
    for m in managers or PRESEASON_MANAGERS_2026:
        rows.append(
            {
                "team_name": _team_cell(m),
                "owner": m.get("owner", ""),
            }
        )
    return rows


def _format_season_awards(awards: Dict[str, Any]) -> str:
    if not awards:
        return "_Season awards will appear here once a few weeks are in the books._"
    lines = []
    for entry in awards.values():
        label = entry.get("label", "Award")
        desc = entry.get("description", "")
        team = entry.get("team") or entry.get("winner") or entry.get("team1")
        owner = entry.get("owner") or entry.get("winner_owner")
        detail_bits = []
        if team:
            detail_bits.append(f"**{team}**" + (f" ({owner})" if owner else ""))
        for key in ("count", "total_points_left", "avg_points_left", "margin"):
            if key in entry:
                detail_bits.append(f"{key.replace('_', ' ')}: {entry[key]}")
        detail = " — ".join(detail_bits)
        lines.append(f"- {label}: {detail}\n  _{desc}_")
    return "\n".join(lines)


def build_league_hq_canvas_markdown(
    week_data: Dict[str, Any],
    season_awards: Dict[str, Any],
    *,
    week: Optional[int] = None,
) -> str:
    """
    Build the full Canvas markdown for "League HQ".

    ``week_data`` is the latest week's fetched bundle (for standings +
    power rankings); ``season_awards`` comes from
    :func:`src.season_leaderboard.compute_season_awards`.

    Team names come from live Yahoo ``week_data`` (``team_name`` on
    standings / power rankings). PRESEASON_MANAGERS_2026 is not used here.
    """
    league = week_data.get("league", {})
    league_name = league.get("league_name", "Fantasy Football League")
    standings = week_data.get("standings", {}).get("standings", [])
    rankings = week_data.get("power_rankings", {}).get("rankings", [])
    awards = season_awards.get("awards", {})
    weeks_played = season_awards.get("weeks_played", 0)

    week_label = f"Week {week}" if week is not None else "Latest Week"
    updated = datetime.now().strftime("%B %d, %Y")

    parts = [
        f"# 🏈 {league_name} — League HQ",
        f"_Last updated after {week_label} · {updated}_",
        "",
        "This is the living dashboard for the league — standings, power "
        "rankings, and season-long bragging rights, updated automatically "
        "each week. The weekly recap is the story; this is the scoreboard.",
        "",
        "## 📊 Standings",
        "",
        _format_standings_table(standings),
        "",
        "## ⚡ Power Rankings",
        "",
        _format_power_rankings(rankings),
        "",
        f"## 🏆 Season Awards (through {weeks_played} weeks)",
        "",
        _format_season_awards(awards),
        "",
        "---",
        "_Awards are computed automatically from box scores — nothing here "
        "is a personal judgment, just the numbers being funny on their own._",
    ]
    return "\n".join(parts)


def build_preseason_league_hq_canvas_markdown(
    *,
    managers: Optional[List[Dict[str, Any]]] = None,
    draft_order: Optional[List[str]] = None,
    league_name: str = DEFAULT_LEAGUE_NAME,
    slack_mentions: bool = False,
) -> str:
    """
    Preseason / preview Canvas: real managers we know, empty standings
    and awards, plus a banner that Yahoo stats are placeholders.

    Omit the H1 title — Slack uses the canvas ``title`` field for that.
    """
    roster = list(managers if managers is not None else PRESEASON_MANAGERS_2026)
    locked = sum(1 for m in roster if m.get("status") == "locked")
    open_slots = sum(1 for m in roster if m.get("status") == "open")
    total = len(roster)
    rows = preseason_placeholder_rows(roster)
    updated = datetime.now().strftime("%B %d, %Y")

    if open_slots:
        roster_status = (
            f"{locked} of {total} managers are locked; "
            f"{open_slots} slot{'s' if open_slots != 1 else ''} still recruiting."
        )
    else:
        roster_status = f"All {locked} managers are locked."

    parts = [
        "::: {.callout}",
        "**Preseason preview — not live standings.** "
        "Yahoo Fantasy API access is still gated, so power rankings and "
        "records are empty placeholders until that comes back. "
        f"{roster_status} "
        "Draft order is set (randomized in Yahoo). "
        "Draft is ![](slack_date:2026-09-08). "
        "Kickoff is ![](slack_date:2026-09-09).",
        ":::",
        "",
        f"_Last updated {updated} · living dashboard for ![](#{LEAGUE_HQ_CHANNEL_ID})_",
        "",
        "The weekly recap is the story. This Canvas is the scoreboard — "
        "standings, power rankings, and season-long bragging rights, "
        "updated after each recap once games exist.",
        "",
        "## 🎯 Draft Order",
        "",
        "Randomized in Yahoo — 14-team snake draft, picks 1–14. "
        "Full draft board lives here until Week 1 standings take over.",
        "",
        _format_draft_order(
            draft_order, roster, slack_mentions=slack_mentions
        ),
        "",
        "## 📊 Standings",
        "",
        "_Placeholders until Yahoo box scores exist._",
        "",
        _format_standings_table(rows, placeholder=True),
        "",
        "## ⚡ Power Rankings",
        "",
        "_Everyone is undefeated in August. That will not last._",
        "",
        _format_power_rankings(rows, placeholder=True),
        "",
        "## 🏆 Season Awards (through 0 weeks)",
        "",
        _format_preseason_awards(),
        "",
        "---",
        "_Awards are computed automatically from box scores — nothing here "
        "is a personal judgment, just the numbers being funny on their own. "
        "Reaction-triggered roasts are on hold._",
    ]
    return "\n".join(parts)
