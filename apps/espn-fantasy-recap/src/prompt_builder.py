"""
Prompt builder for the Fantasy Football columnist.

Instead of keeping one huge markdown file, we split the system prompt into
smaller concern-specific docs (persona, structure, comedy rules, league
context) and stitch them together here for the LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import List


def _read_if_exists(paths: List[Path]) -> str:
    """Return the contents of the first existing path, or an empty string."""
    for p in paths:
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def build_columnist_prompt(use_v2: bool = True, use_v3: bool = False) -> str:
    """
    Build the full system prompt for the columnist by composing smaller files.

    Args:
        use_v2: If True and use_v3 is False, load V2 format.
        use_v3: If True, load the lean V3 format (overrides use_v2).

    V3 (recommended): Single COLUMNIST_PROMPT_V3.md file - lean and focused.
    
    V2/V1 (legacy): Composes from multiple files:
      1) COLUMNIST_PERSONA.md
      2) COLUMNIST_STRUCTURE_V2.md (for V2) or COLUMNIST_STRUCTURE_V1.md (for V1)
      3) COLUMNIST_COMEDY_RULES.md
      4) COLUMNIST_LEAGUE_CONTEXT.md

    If none of these files are found, this function raises FileNotFoundError so
    callers can fall back to the legacy single-file prompt.
    """
    root = Path(__file__).resolve().parent.parent  # project root
    docs = root / "docs"

    # V3: Single lean prompt file (recommended)
    if use_v3:
        v3_text = _read_if_exists(
            [
                docs / "COLUMNIST_PROMPT_V3.md",
                root / "COLUMNIST_PROMPT_V3.md",
            ]
        )
        if v3_text.strip():
            # Also append league lore if it exists
            lore_text = _read_if_exists(
                [
                    docs / "LEAGUE_LORE.md",
                    root / "LEAGUE_LORE.md",
                ]
            )
            if lore_text.strip():
                return v3_text.strip() + "\n\n---\n\n" + lore_text.strip() + "\n"
            return v3_text.strip() + "\n"
        # Fall through to V2 if V3 not found
        use_v2 = True

    # V2/V1: Compose from multiple files (legacy)
    persona_text = _read_if_exists(
        [
            docs / "COLUMNIST_PERSONA.md",
            root / "COLUMNIST_PERSONA.md",
        ]
    )

    if use_v2:
        structure_text = _read_if_exists(
            [
                docs / "COLUMNIST_STRUCTURE_V2.md",
                root / "COLUMNIST_STRUCTURE_V2.md",
            ]
        )
    else:
        structure_text = _read_if_exists(
            [
                docs / "COLUMNIST_STRUCTURE_V1.md",
                root / "COLUMNIST_STRUCTURE_V1.md",
            ]
        )

    comedy_text = _read_if_exists(
        [
            docs / "COLUMNIST_COMEDY_RULES.md",
            root / "COLUMNIST_COMEDY_RULES.md",
        ]
    )

    league_text = _read_if_exists(
        [
            docs / "COLUMNIST_LEAGUE_CONTEXT.md",
            root / "COLUMNIST_LEAGUE_CONTEXT.md",
        ]
    )

    parts = [
        t.strip()
        for t in [persona_text, structure_text, comedy_text, league_text]
        if t.strip()
    ]

    if not parts:
        raise FileNotFoundError(
            "No section files found for columnist prompt "
            "(expected COLUMNIST_PERSONA.md / COLUMNIST_STRUCTURE_*.md / "
            "COLUMNIST_COMEDY_RULES.md / COLUMNIST_LEAGUE_CONTEXT.md)."
        )

    # Use a simple delimiter so the sections stay visually distinct.
    return "\n\n---\n\n".join(parts) + "\n"


# No CLI entrypoint here; this module is used via LLMClient.load_columnist_prompt.
