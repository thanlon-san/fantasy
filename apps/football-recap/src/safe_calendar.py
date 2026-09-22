"""
Allowlist calendar for recap current-events.

Returns at most one holiday / NFL-milestone note for the 2026 season.
If nothing fits, returns None. Never invents news.

Hooks are boring on purpose: Thanksgiving slate, Christmas, kickoff week.
The Ghost may nod once. Same voice. No costume.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union

from src.constants import NFL_REGULAR_SEASON_WEEKS, NFL_SEASON_START_DATE

DateLike = Union[date, datetime]

# (name, note) — notes stay calendar-only. No politics, tragedy, or celebrity.
_HOOKS = {
    "labor_day": (
        "Labor Day / kickoff week. Opening-weekend energy is fair game. "
        "Do not invent other news."
    ),
    "thanksgiving": (
        "Thanksgiving week. The Thursday NFL slate is on the calendar. "
        "A turkey-day nod is fine. Do not invent other news."
    ),
    "christmas": (
        "Christmas week. A holiday-slate nod is fine. "
        "Do not invent other news."
    ),
    "new_year": (
        "New Year week. A calendar-flip nod is fine. "
        "Do not invent other news."
    ),
    "super_bowl": (
        "Super Bowl week. Championship-Sunday energy is fair game. "
        "Do not invent other news."
    ),
    "draft_preseason": (
        "Draft / preseason week. Roster-building and camp vibes are fair game. "
        "Do not invent other news."
    ),
}


def _as_date(when: Optional[DateLike]) -> date:
    if when is None:
        return date.today()
    if isinstance(when, datetime):
        return when.date()
    return when


def week_for_date(when: DateLike) -> Optional[int]:
    """
    Map a date onto the 2026 fantasy week (1–18).

    Returns None before kickoff week and after the regular season.
    """
    d = _as_date(when)
    start = NFL_SEASON_START_DATE.date()
    if d < start:
        return None
    week = (d - start).days // 7 + 1
    if week < 1 or week > NFL_REGULAR_SEASON_WEEKS:
        return None
    return week


def _hook_for_week(week: int) -> Optional[str]:
    # 2026 kickoff Thu Sep 3 → Week 1 includes Labor Day (Mon Sep 7).
    if week == 1:
        return _HOOKS["labor_day"]
    # Thanksgiving 2026 is Thu Nov 26 → Week 13 (Nov 26–Dec 2).
    if week == 13:
        return _HOOKS["thanksgiving"]
    # Christmas 2026 is Fri Dec 25 → Week 17 (Dec 24–30).
    # Week 16 (Dec 17–23) is the recap written on Christmas week itself.
    if week in (16, 17):
        return _HOOKS["christmas"]
    # New Year 2027 is Fri Jan 1 → Week 18 (Dec 31–Jan 6).
    if week == 18:
        return _HOOKS["new_year"]
    return None


def _hook_for_date(when: date) -> Optional[str]:
    """
    Off-season / adjacent windows that are not a regular-season week.
    In-season dates are handled via week number so we never double-fire.
    """
    # Preseason / draft window for the 2026 season (Aug through day before kickoff).
    if date(2026, 8, 1) <= when < NFL_SEASON_START_DATE.date():
        return _HOOKS["draft_preseason"]
    # Super Bowl LXI week (first Sunday of Feb 2027 is Feb 7).
    if date(2027, 2, 1) <= when <= date(2027, 2, 8):
        return _HOOKS["super_bowl"]
    return None


def calendar_hook(
    week: Optional[int] = None,
    when: Optional[DateLike] = None,
) -> Optional[str]:
    """
    Return 0–1 calendar notes for the 2026 season.

    Prefers an explicit ``week`` (the recap week). Falls back to ``when``
    (default today) for preseason / Super Bowl windows.

    Returns None when nothing on the allowlist fits.
    """
    if week is not None:
        note = _hook_for_week(int(week))
        if note:
            return note
        # Recap week is in-season but not a holiday week — skip.
        # Don't also fire a date-based hook and invent a second event.
        return None

    d = _as_date(when)
    mapped = week_for_date(d)
    if mapped is not None:
        return _hook_for_week(mapped)
    return _hook_for_date(d)
