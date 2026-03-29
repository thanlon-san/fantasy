#!/usr/bin/env python3
"""
Keeper Analysis Script - Quick Start
Shortcut for running keeper analysis with sample data
"""

import sys
import subprocess
from pathlib import Path

# Just run the main CLI with sample flag
app_root = Path(__file__).parent.parent
cli_script = app_root / "scripts" / "keeper_cli.py"

# Run with sample data
sys.exit(subprocess.call([sys.executable, str(cli_script), "--sample", "--scenarios"]))
