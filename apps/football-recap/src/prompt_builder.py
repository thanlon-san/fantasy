"""
Load the single house-voice columnist prompt.

V3 is the only source. No modular costume files. No V1/V2 fallbacks.
"""

from __future__ import annotations

from pathlib import Path


def build_columnist_prompt() -> str:
    """
    Load ``docs/COLUMNIST_PROMPT_V3.md``.

    Optionally appends ``LEAGUE_LORE.md`` if that file exists.
    """
    root = Path(__file__).resolve().parent.parent
    docs = root / "docs"

    v3_paths = [
        docs / "COLUMNIST_PROMPT_V3.md",
        root / "COLUMNIST_PROMPT_V3.md",
    ]
    v3_text = ""
    for path in v3_paths:
        if path.exists():
            v3_text = path.read_text(encoding="utf-8")
            break

    if not v3_text.strip():
        raise FileNotFoundError(
            "Could not find docs/COLUMNIST_PROMPT_V3.md — that file is the "
            "only columnist prompt source."
        )

    lore_paths = [
        docs / "LEAGUE_LORE.md",
        root / "LEAGUE_LORE.md",
    ]
    lore_text = ""
    for path in lore_paths:
        if path.exists():
            lore_text = path.read_text(encoding="utf-8")
            break

    if lore_text.strip():
        return v3_text.strip() + "\n\n---\n\n" + lore_text.strip() + "\n"
    return v3_text.strip() + "\n"
