#!/usr/bin/env python3
"""
A/B Test Script: Compare Claude Sonnet 4.5, Claude Sonnet 4, and GPT-4o

Usage:
    python scripts/compare_models.py 12                              # Compare week 12 (all models)
    python scripts/compare_models.py 12 --models sonnet-4.5 sonnet-4 # Only compare Claude models

Requires ANTHROPIC_API_KEY and/or OPENAI_API_KEY in your .env file.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Path setup: expose the app root (for `src.*`) and the workspace `packages/`
# dir (for `shared.*`).
_APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_APP_ROOT))
sys.path.insert(0, str(_APP_ROOT.parent.parent / "packages"))

from dotenv import load_dotenv

load_dotenv()

# Model configurations
MODELS = {
    "opus-4.5": {
        "provider": "anthropic",
        "model_id": "claude-opus-4-5",
        "display_name": "Claude Opus 4.5",
        "emoji": "🟡",
        "description": "Most capable, extended thinking, best for nuanced comedy",
    },
    "sonnet-4.5": {
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-5-20250929",
        "display_name": "Claude Sonnet 4.5",
        "emoji": "🟣",
        "description": "Extended thinking, best for complex comedy",
    },
    "sonnet-4": {
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-20250514",
        "display_name": "Claude Sonnet 4",
        "emoji": "🔵",
        "description": "Fast, solid comedy output",
    },
    "gpt-4o": {
        "provider": "openai",
        "model_id": "gpt-4o",
        "display_name": "GPT-4o",
        "emoji": "🟢",
        "description": "OpenAI's flagship model",
    },
}


def compare_models(week: int, model_list: list = None):
    """Generate recaps with multiple models for comparison (one house voice)."""

    from src.recap_generator import RecapGenerator

    # Check API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Determine which models to test
    if model_list:
        models_to_test = [m for m in model_list if m in MODELS]
    else:
        models_to_test = list(MODELS.keys())

    # Filter by available API keys
    available_models = []
    for model_key in models_to_test:
        model_info = MODELS[model_key]
        if model_info["provider"] == "anthropic" and anthropic_key:
            available_models.append(model_key)
        elif model_info["provider"] == "openai" and openai_key:
            available_models.append(model_key)
        else:
            provider = model_info["provider"].upper()
            print(
                f"⚠️  Skipping {model_info['display_name']}: {provider}_API_KEY not set"
            )

    if not available_models:
        print(
            "\n❌ No models available. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY in your .env file."
        )
        return

    generator = RecapGenerator()

    print(f"\n🏈 Model Comparison: Week {week}")
    print("👻 Voice: The Commissioner's Ghost")
    print(
        f"🤖 Models: {', '.join(MODELS[m]['display_name'] for m in available_models)}"
    )
    print("=" * 70)

    # Fetch week data once (reuse for all models)
    print("\n📊 Fetching week data...")
    week_data = generator.fetch_week_data(week)
    if not week_data:
        print("❌ Failed to fetch week data. Is the API server running?")
        return

    data_context = generator.context_builder.build_context(
        week_data, week, use_v2_format=True
    )
    history_context = generator.get_previous_recaps_context()

    results = {}

    # Generate with each model
    for model_key in available_models:
        model_info = MODELS[model_key]
        emoji = model_info["emoji"]
        display_name = model_info["display_name"]

        print(f"\n{emoji} Generating with {display_name}...")

        try:
            if model_info["provider"] == "anthropic":
                from anthropic import Anthropic

                client = Anthropic(api_key=anthropic_key)

                recap = generator.llm_client.generate_with_anthropic(
                    week=week,
                    data_context=data_context,
                    history_context=history_context,
                    client=client,
                    model=model_info["model_id"],
                )
            else:  # openai
                from openai import OpenAI

                client = OpenAI(api_key=openai_key)

                recap = generator.llm_client.generate_with_openai(
                    week=week,
                    data_context=data_context,
                    history_context=history_context,
                    client=client,
                    model=model_info["model_id"],
                )

            results[model_key] = recap
            print(f"   ✅ {display_name} complete")

        except Exception as e:
            print(f"   ❌ {display_name} failed: {e}")
            results[model_key] = None

    # Save outputs
    output_dir = Path("output/comparisons")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n📁 Saving outputs...")
    saved_files = []

    for model_key, recap in results.items():
        if recap:
            model_info = MODELS[model_key]
            filename = f"week-{week}-{model_key}-ghost-{timestamp}.md"
            filepath = output_dir / filename

            with open(filepath, "w") as f:
                f.write(f"# Week {week} - {model_info['display_name']}\n\n")
                f.write(
                    f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write("**Voice:** The Commissioner's Ghost\n")
                f.write(f"**Model:** `{model_info['model_id']}`\n\n")
                f.write("---\n\n")
                f.write(recap)

            saved_files.append((model_key, filepath))
            print(f"   {model_info['emoji']} {filepath.name}")

    # Analysis
    print("\n" + "=" * 70)
    print("📊 COMPARISON ANALYSIS")
    print("=" * 70)

    check_terms = ["churn", "retention", "funnel", "NPS", "CAC", "A/B"]

    for model_key, recap in results.items():
        if recap:
            model_info = MODELS[model_key]
            emoji = model_info["emoji"]

            word_count = len(recap.split())
            jargon_hits = sum(
                1 for term in check_terms if term.lower() in recap.lower()
            )

            has_narrator = "narrator:" in recap.lower()
            has_rhetorical = recap.count("?") > 3
            has_callback = "week" in recap.lower() and any(
                str(w) in recap for w in range(1, week)
            )

            print(f"\n{emoji} **{model_info['display_name']}**")
            print(f"   Words: {word_count}")
            print(f"   CRM jargon hits: {jargon_hits}/{len(check_terms)}")
            print(f"   Narrator device: {'✓' if has_narrator else '✗'}")
            print(f"   Rhetorical questions: {'✓' if has_rhetorical else '✗'}")
            print(f"   Week callbacks: {'✓' if has_callback else '✗'}")

    # Print file paths for easy opening
    print("\n" + "=" * 70)
    print("📂 OUTPUT FILES")
    print("=" * 70)
    for model_key, filepath in saved_files:
        model_info = MODELS[model_key]
        print(f"\n{model_info['emoji']} {model_info['display_name']}:")
        print(f"   {filepath}")

    print("\n💡 Open these files side-by-side to compare:")
    print("   - Which sounds most like The Commissioner's Ghost?")
    print("   - Which has the sharpest, funniest roasts?")
    print("   - Which feels most unique (not generic AI slop)?")
    print("\n🏆 Pick your winner!")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compare AI models for fantasy football recap generation"
    )
    parser.add_argument("week", type=int, help="Week number to generate")
    parser.add_argument(
        "--models",
        "-m",
        nargs="+",
        choices=list(MODELS.keys()),
        default=None,
        help="Specific models to compare (default: all available)",
    )

    args = parser.parse_args()

    if args.week < 1 or args.week > 18:
        print("❌ Week must be between 1 and 18")
        return

    compare_models(args.week, args.models)


if __name__ == "__main__":
    main()
