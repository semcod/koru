"""Tests for koru sum and koru summary CLI subcommand and terminal markdown rendering."""

from __future__ import annotations

import io
import json
import os
from unittest.mock import MagicMock, patch

from koru.cli import main
from koru.cli_summary import summary_main
from koru.terminal_render import is_interactive_terminal, render_markdown, strip_markdown


def test_cli_summary_main_pipe_markdown(capsys):
    """When stdout is a pipe/redirect (non-TTY), raw markdown is output."""
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
         patch("monag.summary.format_markdown", return_value="# Fake Summary Output\n- **Done**: `test`") as mock_format:
        rc = summary_main(["--no-github"])
        assert rc == 0
        mock_gather.assert_called_once()
        mock_format.assert_called_once_with(fake_data)
        out = capsys.readouterr().out
        assert "# Fake Summary Output" in out
        assert "- **Done**: `test`" in out


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


def test_cli_summary_main_raw_flag(capsys):
    fake_data = {
        "date": "2026-09-26",
        "planfile": {"completed_today": [], "queue": [], "total_completed_today": 0, "total_queued": 0, "total_estimate_minutes": 0},
        "prs": {"open": [], "merged_today": [], "total_open": 0, "total_merged_today": 0},
    }

    with patch("monag.summary.gather_summary", return_value=fake_data), \
         patch("monag.summary.format_markdown", return_value="# Raw Title\n- **Item**"):
        rc = summary_main(["--raw", "--no-github"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "# Raw Title" in out
        assert "- **Item**" in out


def test_cli_summary_main_plain_flag(capsys):
    fake_data = {
        "date": "2026-09-26",
        "planfile": {"completed_today": [], "queue": [], "total_completed_today": 0, "total_queued": 0, "total_estimate_minutes": 0},
        "prs": {"open": [], "merged_today": [], "total_open": 0, "total_merged_today": 0},
    }

    with patch("monag.summary.gather_summary", return_value=fake_data), \
         patch("monag.summary.format_markdown", return_value="# Plain Title\n- **Item**: `value`"):
        rc = summary_main(["--plain", "--no-github"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "# Plain Title" not in out
        assert "Plain Title" in out
        assert "**Item**" not in out
        assert "`value`" not in out
        assert "Item: value" in out


def test_terminal_render_interactive_rich():
    """In interactive TTY, rich formats markdown."""
    md = "# Hello Title\n- **Key**: `val`"
    buf = io.StringIO()
    buf.isatty = lambda: True

    with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
        render_markdown(md, stream=buf)
    out = buf.getvalue()
    # Headers in rich are formatted without leading '#'
    assert "# Hello Title" not in out
    assert "Hello Title" in out


def test_terminal_render_dumb_term():
    """TERM=dumb bypasses rich interactive mode and outputs raw markdown."""
    md = "# Dumb Title\n- Item"
    buf = io.StringIO()
    buf.isatty = lambda: True

    with patch.dict(os.environ, {"TERM": "dumb"}):
        assert not is_interactive_terminal(buf)
        render_markdown(md, stream=buf)
    out = buf.getvalue()
    assert "# Dumb Title" in out


def test_strip_markdown():
    text = (
        "# Main Heading\n"
        "## Sub Heading\n"
        "- **Status**: `ok`\n"
        "Some *italic* and **bold** text."
    )
    stripped = strip_markdown(text)
    assert "#" not in stripped
    assert "**" not in stripped
    assert "`" not in stripped
    assert "Main Heading" in stripped
    assert "Sub Heading" in stripped
    assert "Status: ok" in stripped
    assert "Some italic and bold text." in stripped


def test_koru_cli_dispatches_sum():
    with patch("sys.argv", ["koru", "sum", "--no-github"]), \
         patch("koru.cli_summary.summary_main", return_value=0) as mock_sum:
        rc = main()
        assert rc == 0
        mock_sum.assert_called_once_with(["--no-github"])


def test_koru_cli_dispatches_summary():
    with patch("sys.argv", ["koru", "summary", "--no-github"]), \
         patch("koru.cli_summary.summary_main", return_value=0) as mock_sum:
        rc = main()
        assert rc == 0
        mock_sum.assert_called_once_with(["--no-github"])
