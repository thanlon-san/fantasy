"""Builds the prepared context markdown the recap writer reads.

Everything here is deterministic and derived from ``week_data`` -- no LLM, no
invented facts. The writing agent is only allowed to use what this file emits,
so anything it needs (closing line, superlatives, power rankings, GIF) has to be
produced here.
"""

from __future__ import annotations

import json
import os
import random
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.power_rankings import compute_power_rankings, format_rankings_lines
from src.slack_mentions import message_mention

RECAP_HISTORY_FILE = "recap_history.json"
GIF_CONFIG_FILE = "apps/football-recap/config/gifs.json"

# Rotated so no two consecutive weeks share a sign-off. The writer must copy the
# selected line verbatim.
CLOSING_LINES = [
    "The standings don't lie. Your lineup does.",
    "Somewhere, a waiver wire is calling. Answer it.",
    "Sixteen weeks of this. We signed up voluntarily.",
    "The bench is always greener. That's the problem.",
    "Set your lineup. It's the one thing you control.",
    "Every week is a fresh chance to be disappointed by the same players.",
    "Hope is a strategy. A bad one, but a strategy.",
    "See you next Sunday, when none of this will matter and all of it will.",
    "The projections were wrong. They're always wrong. We keep reading them.",
    "Your season is not over. It's just heavily discounted.",
    "Somebody has to finish last. Statistically, it's probably you.",
    "Trust the process. The process is losing, but trust it.",
    "There is no lesson here. There is only next week.",
    "The trade deadline approaches. So does your reckoning.",
    "Fourteen managers. One trophy. Thirteen excuses being drafted right now.",
    "Play your studs. It's not complicated. It is, apparently, difficult.",
    "The waiver wire giveth. Mostly it taketh.",
    "Another week survived. Barely. Loosely. Technically.",
]

# Recurring calendar moments worth a single nod. Keyed by (month, day) window.
# These are fixed observances, not news -- the writer must not extrapolate.
_CALENDAR_HOOKS = [
    ((9, 20), (9, 30), "the last gasp of September"),
    ((10, 1), (10, 15), "peak October, when the standings start meaning something"),
    ((10, 25), (11, 1), "Halloween week"),
    ((11, 20), (11, 30), "Thanksgiving week"),
    ((11, 28), (12, 2), "the Black Friday hangover"),
    ((12, 20), (12, 26), "the Christmas stretch"),
    ((12, 29), (1, 2), "New Year's, and the playoffs waiting on the other side"),
]


def _today() -> date:
    return datetime.now().date()


def get_calendar_hook(when: Optional[date] = None) -> Optional[str]:
    """Return a fixed seasonal hook for today's date, or None.

    Deliberately limited to recurring calendar observances. It never surfaces
    news, politics, or current events -- the writer is told not to invent those
    and this must not smuggle them in.
    """
    when = when or _today()
    for (start_m, start_d), (end_m, end_d), label in _CALENDAR_HOOKS:
        start = date(when.year, start_m, start_d)
        end = date(when.year if end_m >= start_m else when.year + 1, end_m, end_d)
        if start <= when <= end:
            return label
    return None


def get_closing_line(week: int, history_path: str = RECAP_HISTORY_FILE) -> str:
    """Pick a closing line that hasn't been used recently."""
    used: List[str] = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as handle:
                history = json.load(handle)
            for entry in history[-6:]:
                line = (entry.get("context") or {}).get("closing_line")
                if line:
                    used.append(line)
        except (json.JSONDecodeError, OSError, AttributeError, TypeError):
            used = []

    available = [line for line in CLOSING_LINES if line not in used] or CLOSING_LINES
    # Seed by week so a re-run of the same week is reproducible.
    return random.Random(week).choice(available)


def get_gif_of_the_week(week: int, config_path: str = GIF_CONFIG_FILE) -> Optional[str]:
    """Return a Giphy URL for the week, or None if no source is configured.

    Returns None rather than a guessed URL: a dead image in Slack is worse than
    no image, and fabricating a link would violate the no-invention rule.
    """
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            gifs = json.load(handle).get("gifs", [])
    except (json.JSONDecodeError, OSError, AttributeError):
        return None
    if not gifs:
        return None
    return gifs[(week - 1) % len(gifs)]


def build_superlatives(week_data: Dict[str, Any]) -> List[str]:
    """Derive award-style callouts straight from the week's numbers."""
    stats = week_data.get("week_stats", {})
    matchups = week_data.get("matchups", {}).get("matchups", [])
    out: List[str] = []

    rosters = week_data.get("rosters")
    if rosters:
        from src.bench_stats import pick_bench_hero, summarize_all_rosters

        teams = week_data.get("standings", {}).get("standings", [])
        team_lookup = {t["team_key"]: t for t in teams if t.get("team_key")}
        hero = pick_bench_hero(summarize_all_rosters(rosters), team_lookup)
        if hero:
            out.append(
                f"**Bench Hero of the Week** — "
                f"{message_mention(hero['owner'], team_key=hero['team_key'])} left "
                f"{hero['player_name']} ({hero['points']:.1f} pts) on the bench"
            )

    high = stats.get("highest_score")
    if high:
        out.append(
            f"**Highest Score** — "
            f"{message_mention(high['owner'], team_key=high.get('team_key'))} "
            f"({high['team']}), {high['points']:.1f} points"
        )

    low = stats.get("lowest_score")
    if low:
        out.append(
            f"**Lowest Score** — "
            f"{message_mention(low['owner'], team_key=low.get('team_key'))} "
            f"({low['team']}), {low['points']:.1f} points"
        )

    blowout = stats.get("biggest_blowout")
    if blowout:
        out.append(
            f"**Biggest Blowout** — {blowout['winner']} over {blowout['loser']} "
            f"by {blowout['margin']:.1f}"
        )

    upset = stats.get("biggest_upset")
    if upset:
        out.append(
            f"**Biggest Upset** — "
            f"{message_mention(upset['winner_owner'], team_key=upset.get('winner_team_key'))}'s "
            f"{upset['winner']} was projected for {upset['winner_projected']:.1f} vs. "
            f"{upset['loser']}'s {upset['loser_projected']:.1f}, and won anyway"
        )

    closest = stats.get("closest_game")
    if closest:
        out.append(
            f"**Closest Game** — {closest['team1']} vs {closest['team2']}, "
            f"decided by {closest['margin']:.1f}"
        )

    if stats.get("average_score") is not None:
        out.append(f"**League Average** — {stats['average_score']:.1f} points")

    # Anyone who won while scoring below the league average got away with one.
    average = stats.get("average_score")
    if average:
        for matchup in matchups:
            for key in ("home_team", "away_team"):
                side = matchup[key]
                if matchup.get("winner") == side["team_name"] and (
                    side["score"] < average
                ):
                    out.append(
                        f"**Luckiest Win** — "
                        f"{message_mention(side['owner'], team_key=side.get('team_key'))} "
                        f"won with {side['score']:.1f}, below the {average:.1f} "
                        "league average"
                    )
                    break
            else:
                continue
            break

    return out


def pick_bit_of_the_week(week_data: Dict[str, Any]) -> Optional[str]:
    """Choose the single game worth opening on: the tightest decided matchup."""
    matchups = [
        m for m in week_data.get("matchups", {}).get("matchups", []) if m.get("winner")
    ]
    if not matchups:
        return None
    game = min(matchups, key=lambda m: m["margin"])
    home, away = game["home_team"], game["away_team"]
    home_mention = message_mention(home["owner"], team_key=home.get("team_key"))
    away_mention = message_mention(away["owner"], team_key=away.get("team_key"))
    return (
        f"{home_mention}'s {home['team_name']} ({home['score']:.1f}) vs "
        f"{away_mention}'s {away['team_name']} ({away['score']:.1f}) — "
        f"decided by {game['margin']:.1f}"
    )


def _matchup_line(matchup: Dict[str, Any]) -> str:
    home, away = matchup["home_team"], matchup["away_team"]
    home_mention = message_mention(home["owner"], team_key=home.get("team_key"))
    away_mention = message_mention(away["owner"], team_key=away.get("team_key"))
    if matchup.get("winner") == home["team_name"]:
        winner, loser = home, away
        winner_mention, loser_mention = home_mention, away_mention
    elif matchup.get("winner") == away["team_name"]:
        winner, loser = away, home
        winner_mention, loser_mention = away_mention, home_mention
    else:
        return (
            f"- {home_mention}'s {home['team_name']} ({home['score']:.1f}) "
            f"TIED {away_mention}'s {away['team_name']} ({away['score']:.1f})"
        )
    return (
        f"- {winner_mention}'s {winner['team_name']} ({winner['score']:.1f}) "
        f"def. {loser_mention}'s {loser['team_name']} ({loser['score']:.1f}) "
        f"— margin {matchup['margin']:.1f}"
    )


def build_context(week_data: Dict[str, Any], week: int) -> Dict[str, Any]:
    """Build the context markdown plus the metadata sidecar.

    Returns ``{"markdown": str, "meta": dict, "rankings": list}``.
    """
    league = week_data.get("league", {})
    matchups = week_data.get("matchups", {}).get("matchups", [])
    next_matchups = week_data.get("next_week_matchups", {}).get("matchups", [])
    rankings = compute_power_rankings(week_data, week)
    superlatives = build_superlatives(week_data)
    closing_line = get_closing_line(week)
    calendar_hook = get_calendar_hook()
    bit = pick_bit_of_the_week(week_data)
    gif = get_gif_of_the_week(week)

    parts: List[str] = []
    parts.append(f"# Week {week} Recap Data")
    parts.append(
        f"League: {league.get('league_name', 'Unknown')} "
        f"({league.get('total_teams', len(rankings))} teams) — "
        f"season {league.get('season', '')}"
    )
    parts.append(
        "\n> Use ONLY the data in this file. Do not invent scores, owners, "
        "matchups, rankings, news, politics, or world events."
    )

    if bit:
        parts.append("\n## BIT_OF_THE_WEEK")
        parts.append(f"Open League Pulse on this game:\n\n{bit}")

    if calendar_hook:
        parts.append("\n## CALENDAR_HOOK")
        parts.append(
            f"You may nod to this once, lightly: {calendar_hook}. "
            "Do not build the recap around it."
        )

    parts.append(f"\n## Matchups ({len(matchups)} total — cover ALL of them)")
    if matchups:
        # Drama order: closest games first.
        for matchup in sorted(matchups, key=lambda m: m["margin"]):
            parts.append(_matchup_line(matchup))
    else:
        parts.append("- No matchups returned for this week.")

    parts.append(f"\n## Power Rankings (ALL {len(rankings)} teams — copy 1:1, do not reorder)")
    if rankings:
        parts.extend(format_rankings_lines(rankings))
    else:
        parts.append("- No standings returned for this week.")

    if superlatives:
        parts.append("\n## Weekly Superlatives (weave in 2–3 as callouts)")
        for item in superlatives:
            parts.append(f"- {item}")

    parts.append(f"\n## Week {week + 1} Preview (ACTUAL matchups — use these)")
    if next_matchups:
        for matchup in next_matchups:
            home, away = matchup["home_team"], matchup["away_team"]
            home_mention = message_mention(home["owner"], team_key=home.get("team_key"))
            away_mention = message_mention(away["owner"], team_key=away.get("team_key"))
            parts.append(
                f"- {home_mention}'s {home['team_name']} vs "
                f"{away_mention}'s {away['team_name']}"
            )
    else:
        parts.append("- Next week's schedule is not available yet. Keep the preview general.")

    parts.append("\n## GIF of the Week")
    if gif:
        parts.append(f"Include this line verbatim so Slack renders it inline:\n\n![GIF]({gif})")
    else:
        parts.append(
            "No GIF source configured — OMIT the GIF line entirely. "
            "Do not invent a Giphy URL."
        )

    parts.append("\n## CLOSING LINE (use this exact line)")
    parts.append(f'> "{closing_line}"')

    meta = {
        "week": week,
        "generated_at": datetime.now().isoformat(),
        "league_name": league.get("league_name"),
        "team_count": len(rankings),
        "matchup_count": len(matchups),
        "closing_line": closing_line,
        "calendar_hook": calendar_hook,
        "bit_of_the_week": bit,
        "gif_url": gif,
        "superlative_count": len(superlatives),
        "source": week_data.get("source", "yahoo"),
    }

    return {"markdown": "\n".join(parts) + "\n", "meta": meta, "rankings": rankings}
