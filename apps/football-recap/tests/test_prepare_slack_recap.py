"""Tests for week resolution in ``scripts/prepare_slack_recap.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests import _bootstrap  # noqa: F401


def _load_prepare_slack_recap_module():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "prepare_slack_recap.py"
    spec = importlib.util.spec_from_file_location("prepare_slack_recap", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareSlackRecapWeekTests(unittest.TestCase):

    def test_default_week_uses_yahoo_league_info(self):
        mod = _load_prepare_slack_recap_module()
        fetcher = MagicMock()
        fetcher.league_info.return_value = {"current_week": 6}

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mod, "OUTPUT_DIR", tmp):
                with patch.object(mod, "RecapGenerator") as gen_cls:
                    gen = gen_cls.return_value
                    gen.fetcher = fetcher
                    gen.recap_history = []
                    gen.fetch_week_data.return_value = {
                        "league": {"league_name": "Test", "current_week": 6},
                        "matchups": {"matchups": []},
                        "power_rankings": {"rankings": []},
                        "week_stats": {},
                    }
                    with patch.object(sys, "argv", ["prepare_slack_recap.py"]):
                        rc = mod.main()
        self.assertEqual(rc, 0)
        gen.fetch_week_data.assert_called_once_with(6)

    def test_no_fetch_uses_yahoo_from_cache(self):
        mod = _load_prepare_slack_recap_module()
        week_data = {
            "league": {"league_name": "Test", "current_week": 6},
            "matchups": {"matchups": []},
            "power_rankings": {"rankings": []},
            "week_stats": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "week-6-weekdata.json"
            cache.write_text(json.dumps(week_data), encoding="utf-8")
            with patch.object(mod, "OUTPUT_DIR", tmp):
                with patch.object(mod, "RecapGenerator") as gen_cls:
                    gen = gen_cls.return_value
                    gen.recap_history = []
                    with patch.object(sys, "argv", ["prepare_slack_recap.py", "--no-fetch"]):
                        rc = mod.main()
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
