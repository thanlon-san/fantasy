"""
Common sys.path setup for football-recap tests.

The football-recap app expects two paths on ``sys.path``:
- ``apps/football-recap`` so ``import src.foo`` resolves
- ``packages`` so ``import shared.bar`` resolves

Tests can either import this module or set the paths themselves. Importing
this module is a single-line, side-effecting setup that keeps every test file
free of boilerplate.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
APP_ROOT = TESTS_DIR.parent
WORKSPACE_ROOT = APP_ROOT.parent.parent
PACKAGES_DIR = WORKSPACE_ROOT / "packages"

for path in (str(APP_ROOT), str(PACKAGES_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)
