"""
Extract Commissioner's Ghost prose from ``week-N-recap.md`` for Slack paste.

The long recap is LLM-written (Cursor automation or API). This module pulls
League Pulse, Stat of the Week, and Matchups — not Python template blurbs.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# V3 section headers (markdown bold with emoji)
_RE_LEAGUE_PULSE = re.compile(
    r"^\*\*:heart-8bit:\s*League Pulse\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_STAT = re.compile(
    r"^\*\*:confused-math-lady:\s*Stat of the Week\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_MATCHUPS = re.compile(
    r"^\*\*:right-facing_fist:\s*Matchups\b.*\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_POWER = re.compile(
    r"^\*\*:power-up:\s*Power Rankings\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_GIF_LINE = re.compile(
    r"^!\[.*?\]\(https?://media\.giphy\.com/[^\)]+\)\s*$",
    re.MULTILINE,
)


def _section_slice(
    text: str,
    start_pat: re.Pattern[str],
    end_pat: Optional[re.Pattern[str]],
) -> Optional[str]:
    """Body between ``start_pat`` line and the next ``end_pat`` line (or EOF)."""
    m = start_pat.search(text)
    if not m:
        return None
    start = m.end()
    if end_pat:
        end_m = end_pat.search(text, start)
        end = end_m.start() if end_m else len(text)
    else:
        end = len(text)
    body = text[start:end].strip()
    return body or None


def _slackify_markdown_for_paste(text: str) -> str:
    """
    Light cleanup for Slack composer paste.

    Recaps use ``**bold**``; Slack mrkdwn prefers ``*bold*``. Mention tokens
    are left as ``<@U…>`` here; :func:`build_slack_recap` resolves them for paste.
    """
    lines: List[str] = []
    for line in text.splitlines():
        if _RE_GIF_LINE.match(line.strip()):
            continue
        # Avoid mangling lines that are only emoji section markers
        if line.strip().startswith("**:") and line.strip().endswith("**"):
            inner = line.strip()[2:-2]
            lines.append(f"*{inner}*")
            continue
        lines.append(re.sub(r"\*\*([^*]+)\*\*", r"*\1*", line))
    return "\n".join(lines).strip()


def extract_recap_slack_sections(recap_markdown: str) -> Optional[str]:
    """
    Return League Pulse + Stat + Matchups from a V3 recap, or None if not found.
    """
    if not recap_markdown or not recap_markdown.strip():
        return None

    pulse = _section_slice(recap_markdown, _RE_LEAGUE_PULSE, _RE_STAT)
    stat = _section_slice(recap_markdown, _RE_STAT, _RE_MATCHUPS)
    matchups = _section_slice(recap_markdown, _RE_MATCHUPS, _RE_POWER)

    if not matchups:
        return None

    parts: List[str] = []
    if pulse:
        parts.append("*:heart-8bit: League Pulse*\n" + pulse)
    if stat:
        parts.append("*:confused-math-lady: Stat of the Week*\n" + stat)
    parts.append("*:right-facing_fist: Matchups :left-facing_fist:*\n" + matchups)

    return _slackify_markdown_for_paste("\n\n".join(parts))


def load_recap_excerpt_from_file(recap_path: str) -> Tuple[Optional[str], bool]:
    """
    Read ``recap_path`` and extract Slack excerpt.

    Returns ``(excerpt, file_was_readable)``.
    """
    try:
        with open(recap_path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return None, False
    excerpt = extract_recap_slack_sections(raw)
    return excerpt, True
