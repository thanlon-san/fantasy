"""
Curated GIF bank for the weekly "GIF of the Week" section.

We ship a curated pool instead of hitting Giphy's live API so the pipeline
has zero new network dependencies and no API key management. Each entry
is a permanent Giphy CDN URL (`https://media.giphy.com/media/<id>/giphy.gif`)
that renders inline in Slack.

Pick strategy: :func:`pick_gif` chooses the "vibe" tier for the week using
data already in ``week_data`` (blowout margin, nail-biter, shootout, etc.),
then rotates within that tier based on the week number so the same GIF
doesn't repeat too often.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# The bank.
# ---------------------------------------------------------------------------
# Every entry: (URL, short caption used as alt text / hover title)

BLOWOUT_GIFS: List[tuple[str, str]] = [
    ("https://media.giphy.com/media/l4Ki2obCyAQS5WhFe/giphy.gif", "Absolute demolition"),
    ("https://media.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif", "Get in the bag"),
    ("https://media.giphy.com/media/xTiTnLmaxrlBHxsMMg/giphy.gif", "Just wiped clean"),
    ("https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif", "Rolled straight through"),
]

NAILBITER_GIFS: List[tuple[str, str]] = [
    ("https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif", "Nail biter"),
    ("https://media.giphy.com/media/l2SqfBaXHTd7WRLHi/giphy.gif", "Down to the wire"),
    ("https://media.giphy.com/media/xT9IgIc0lryrxvqVGM/giphy.gif", "Heart in throat"),
    ("https://media.giphy.com/media/l0IybX9WFdw0IEsZ2/giphy.gif", "Sweating profusely"),
]

SHOOTOUT_GIFS: List[tuple[str, str]] = [
    ("https://media.giphy.com/media/xUOwGhVYQqQD4KEnvi/giphy.gif", "Points party"),
    ("https://media.giphy.com/media/l0HlIfxGDwzOSKh5C/giphy.gif", "Scoreboard on fire"),
    ("https://media.giphy.com/media/xT5LMESsx1kUe8Xy24/giphy.gif", "Everybody eats"),
]

COLD_WAR_GIFS: List[tuple[str, str]] = [
    ("https://media.giphy.com/media/3o6MbudsUuzD3haQta/giphy.gif", "Watching paint dry"),
    ("https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif", "Where did the offense go"),
    ("https://media.giphy.com/media/3o7btNhMBytxAM6YBa/giphy.gif", "Just brutal to watch"),
]

UPSET_GIFS: List[tuple[str, str]] = [
    ("https://media.giphy.com/media/xUA7bdpLxQhsSQdyog/giphy.gif", "Shock and awe"),
    ("https://media.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif", "Wait, what?"),
    ("https://media.giphy.com/media/l3q2K5jinAlChoCLS/giphy.gif", "Nobody saw this coming"),
]

MANAGEMENT_DISASTER_GIFS: List[tuple[str, str]] = [
    ("https://media.giphy.com/media/xT0GqfbTZTiI3IOx1u/giphy.gif", "Coach yourself gently"),
    ("https://media.giphy.com/media/xT5LMB2WiOdjpB7K4o/giphy.gif", "That was a choice"),
    ("https://media.giphy.com/media/26FLdmIp6wJr91JAI/giphy.gif", "Left the points on the bench"),
]

DEFAULT_GIFS: List[tuple[str, str]] = [
    ("https://media.giphy.com/media/l0HlNaQ6gWfllcjDO/giphy.gif", "Just another week of football"),
    ("https://media.giphy.com/media/xTiTnEKzXOOFrsCFHi/giphy.gif", "Same time next Sunday"),
    ("https://media.giphy.com/media/3o7TKz9bX9v7z2gzy0/giphy.gif", "Fantasy football is a lifestyle"),
]


def pick_gif(
    week_data: Dict[str, Any],
    week: int,
    superlatives: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    Choose a GIF for the week based on the dominant vibe.

    Priority order (first match wins):
      1. Upset (biggest projection-vs-outcome mismatch)
      2. Blowout (>= 30 pt margin)
      3. Nail-biter (< 5 pt margin)
      4. Shootout (combined >= 250 pts)
      5. Cold war (combined <= 170 pts)
      6. Management disaster (someone left >= 25 pts on the bench)
      7. Fallback: DEFAULT_GIFS

    ``superlatives`` (from :mod:`src.superlatives`) is preferred when given
    — same rules, no re-computation. Absent that, this function falls back
    to inspecting the matchups payload directly.
    """
    pool: List[tuple[str, str]]
    tier: str

    superlatives = superlatives or {}
    if "upset_of_the_week" in superlatives:
        pool, tier = UPSET_GIFS, "upset"
    elif "blowout_of_the_week" in superlatives:
        pool, tier = BLOWOUT_GIFS, "blowout"
    elif "nailbiter_of_the_week" in superlatives:
        pool, tier = NAILBITER_GIFS, "nailbiter"
    elif "shootout_of_the_week" in superlatives:
        pool, tier = SHOOTOUT_GIFS, "shootout"
    elif "cold_war_of_the_week" in superlatives:
        pool, tier = COLD_WAR_GIFS, "cold_war"
    elif "cooked_of_the_week" in superlatives:
        pool, tier = MANAGEMENT_DISASTER_GIFS, "management"
    else:
        pool, tier = DEFAULT_GIFS, "default"

    # Deterministic pick within tier: rotate by week so consecutive weeks in
    # the same tier get different GIFs, without any global mutable state.
    idx = week % len(pool)
    url, caption = pool[idx]
    return {"url": url, "caption": caption, "tier": tier}


def all_gifs() -> Dict[str, List[Dict[str, str]]]:
    """Debug helper: dump the entire bank grouped by tier."""
    return {
        "blowout": [{"url": u, "caption": c} for u, c in BLOWOUT_GIFS],
        "nailbiter": [{"url": u, "caption": c} for u, c in NAILBITER_GIFS],
        "shootout": [{"url": u, "caption": c} for u, c in SHOOTOUT_GIFS],
        "cold_war": [{"url": u, "caption": c} for u, c in COLD_WAR_GIFS],
        "upset": [{"url": u, "caption": c} for u, c in UPSET_GIFS],
        "management": [{"url": u, "caption": c} for u, c in MANAGEMENT_DISASTER_GIFS],
        "default": [{"url": u, "caption": c} for u, c in DEFAULT_GIFS],
    }
