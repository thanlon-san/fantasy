#!/usr/bin/env python3
"""
Utility to split COLUMNIST_PROMPT.md into modular sections
Run this once to create the prompts/ directory structure
"""

import os
import re


def split_prompt():
    """Split the monolithic prompt into modular files"""

    # Read the current prompt
    with open("COLUMNIST_PROMPT.md", "r") as f:
        content = f.read()

    # Create prompts directory
    os.makedirs("prompts", exist_ok=True)

    # Define sections to extract (based on ## headers)
    sections = {
        "00_core_persona.md": {
            "start": "# The Commissioner's Ghost: Fantasy Football Roast Columnist",
            "end": "## Content Ratio & Structure",
        },
        "01_structure.md": {
            "start": "## Content Ratio & Structure",
            "end": "## Roast Targeting",
        },
        "02_safety_rails.md": {"start": "## Safety Rails", "end": "## Roast Mechanics"},
        "03_data_grounding.md": {
            "start": "## Data Grounding",
            "end": "## Roast Targeting",
        },
        "04_examples.md": {
            "start": "### Running Gags & Callbacks",
            "end": "## Quality Checklist",
        },
        "05_advanced_stats.md": {
            "start": "## Hidden Gems: Advanced Stats",
            "end": "**Benching guidance:**",
        },
        "06_trends.md": {
            "start": "### 📈 Multi-Week Trends",
            "end": "### 💰 Activity Metrics",
        },
        "07_memory.md": {
            "start": "## Memory & Repetition Avoidance",
            "end": "### Running Gags & Callbacks",
        },
        "08_league_context.md": {
            "start": "## League-Specific Context",
            "end": "## Hidden Gems",
        },
        "09_final_reminder.md": {
            "start": "## Final Reminder",
            "end": None,  # End of file
        },
    }

    print("Splitting COLUMNIST_PROMPT.md into modular sections...\n")

    for filename, markers in sections.items():
        start_marker = markers["start"]
        end_marker = markers["end"]

        # Find start position
        start_idx = content.find(start_marker)
        if start_idx == -1:
            print(f"⚠️  Skipping {filename} - start marker not found")
            continue

        # Find end position
        if end_marker:
            end_idx = content.find(end_marker, start_idx + 1)
            if end_idx == -1:
                print(f"⚠️  Skipping {filename} - end marker not found")
                continue
            section_content = content[start_idx:end_idx].strip()
        else:
            section_content = content[start_idx:].strip()

        # Write to file
        filepath = os.path.join("prompts", filename)
        with open(filepath, "w") as f:
            f.write(section_content)

        # Get stats
        lines = len(section_content.splitlines())
        tokens = len(section_content) // 4
        print(f"✅ {filename:30} {lines:4} lines, ~{tokens:5} tokens")

    print(
        f"\n🎉 Done! Created {len(os.listdir('prompts'))} prompt sections in prompts/"
    )
    print("\nYou can now use PromptBuilder to assemble prompts dynamically.")


if __name__ == "__main__":
    split_prompt()
