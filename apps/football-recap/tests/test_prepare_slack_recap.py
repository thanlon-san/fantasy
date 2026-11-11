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
        fetcher.week_matchups.return_value = {
            "matchups": [{"status": "postevent", "home_team": {"score": 90.0}, "away_team": {"score": 80.0}}]
        }

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
        base = {
            "league": {"league_name": "Test", "current_week": 7},
            "matchups": {"matchups": []},
            "power_rankings": {"rankings": []},
            "week_stats": {},
        }
        upcoming = dict(base, matchups={"matchups": [{"status": "preevent", "home_team": {"score": 0}, "away_team": {"score": 0}}]})
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "week-6-weekdata.json").write_text(json.dumps(base), encoding="utf-8")
            (Path(tmp) / "week-7-weekdata.json").write_text(json.dumps(upcoming), encoding="utf-8")
            with patch.object(mod, "OUTPUT_DIR", tmp):
                with patch.object(mod, "RecapGenerator") as gen_cls:
                    gen = gen_cls.return_value
                    gen.recap_history = []
                    with patch.object(sys, "argv", ["prepare_slack_recap.py", "--no-fetch"]):
                        rc = mod.main()
        self.assertEqual(rc, 0)

    def test_default_week_steps_back_when_current_week_preevent(self):
        mod = _load_prepare_slack_recap_module()
        fetcher = MagicMock()
        fetcher.league_info.return_value = {"current_week": 10}
        fetcher.week_matchups.return_value = {
            "matchups": [{"status": "preevent", "home_team": {"score": 0}, "away_team": {"score": 0}}]
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mod, "OUTPUT_DIR", tmp):
                with patch.object(mod, "RecapGenerator") as gen_cls:
                    gen = gen_cls.return_value
                    gen.fetcher = fetcher
                    gen.recap_history = []
                    gen.fetch_week_data.return_value = {
                        "league": {"league_name": "Test", "current_week": 10},
                        "matchups": {"matchups": []},
                        "power_rankings": {"rankings": []},
                        "week_stats": {},
                    }
                    with patch.object(sys, "argv", ["prepare_slack_recap.py"]):
                        mod.main()
        gen.fetch_week_data.assert_called_once_with(9)


if __name__ == "__main__":
    unittest.main()
