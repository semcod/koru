"""Tests for koru sum and koru summary CLI subcommand."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from koru.cli import main
from koru.cli_summary import summary_main


def test_cli_summary_main_markdown(capsys):
    fake_data = {
        "date": "2026-09-26",
        "planfile": {
            "completed_today": [{"repo": "test/repo", "id": "PLF-1", "title": "Done task"}],
            "queue": [{"repo": "test/repo", "id": "PLF-2", "title": "Queued task", "priority": "high", "estimate_minutes": 5}],
            "total_completed_today": 1,
            "total_queued": 1,
            "total_estimate_minutes": 5,
        },
        "prs": {
            "open": [],
            "merged_today": [],
            "total_open": 0,
            "total_merged_today": 0,
        },
    }

    with patch("monag.summary.gather_summary", return_value=fake_data) as mock_gather, \
         patch("monag.summary.format_markdown", return_value="# Fake Summary Output") as mock_format:
        rc = summary_main(["--no-github"])
        assert rc == 0
        mock_gather.assert_called_once()
        mock_format.assert_called_once_with(fake_data)
        out = capsys.readouterr().out
        assert "# Fake Summary Output" in out


def test_cli_summary_main_json(capsys):
    fake_data = {
        "date": "2026-09-26",
        "planfile": {"completed_today": [], "queue": [], "total_completed_today": 0, "total_queued": 0, "total_estimate_minutes": 0},
        "prs": {"open": [], "merged_today": [], "total_open": 0, "total_merged_today": 0},
    }

    with patch("monag.summary.gather_summary", return_value=fake_data):
        rc = summary_main(["--json", "--no-github"])
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["date"] == "2026-09-26"


def test_koru_cli_dispatches_sum(capsys):
    with patch("sys.argv", ["koru", "sum", "--no-github"]), \
         patch("koru.cli_summary.summary_main", return_value=0) as mock_sum:
        rc = main()
        assert rc == 0
        mock_sum.assert_called_once_with(["--no-github"])


def test_koru_cli_dispatches_summary(capsys):
    with patch("sys.argv", ["koru", "summary", "--no-github"]), \
         patch("koru.cli_summary.summary_main", return_value=0) as mock_sum:
        rc = main()
        assert rc == 0
        mock_sum.assert_called_once_with(["--no-github"])
