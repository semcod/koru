"""Tests for the dashboard log streaming endpoint and --web flag."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from koruapi.dashboard_logs import (
    _parse_autonomous_log_line,
    _parse_nfo_line,
    read_recent_logs,
    sse_log_stream,
)


class TestParseNfoLine:
    """Tests for _parse_nfo_line."""

    def test_valid_nfo_line(self) -> None:
        line = json.dumps({
            "timestamp": "2026-09-16T07:39:41.000000+00:00",
            "level": "INFO",
            "function_name": "nfo.event",
            "module": "nfo",
            "args": "()",
            "kwargs": "{'event': 'koru.activity', 'category': 'KORUAUTONOMOUS', 'activity_message': 'test message'}",
        })
        entry = _parse_nfo_line(line)
        assert entry is not None
        assert entry["level"] == "INFO"
        assert entry["message"] == "test message"
        assert entry["category"] == "KORUAUTONOMOUS"
        assert entry["source"] == "nfo"

    def test_invalid_json(self) -> None:
        entry = _parse_nfo_line("not json")
        assert entry is None

    def test_empty_line(self) -> None:
        entry = _parse_nfo_line("")
        assert entry is None

    def test_error_level(self) -> None:
        line = json.dumps({
            "timestamp": "2026-09-16T07:39:41.000000+00:00",
            "level": "ERROR",
            "function_name": "nfo.event",
            "kwargs": "{'activity_message': 'something failed'}",
        })
        entry = _parse_nfo_line(line)
        assert entry is not None
        assert entry["level"] == "ERROR"

    def test_missing_message_falls_back_to_function_name(self) -> None:
        line = json.dumps({
            "timestamp": "2026-09-16T07:39:41.000000+00:00",
            "level": "INFO",
            "function_name": "custom.func",
            "kwargs": "{}",
        })
        entry = _parse_nfo_line(line)
        assert entry is not None
        assert "custom.func" in entry["message"]


class TestParseAutonomousLogLine:
    """Tests for _parse_autonomous_log_line."""

    def test_error_line(self) -> None:
        entry = _parse_autonomous_log_line("[ERROR] something went wrong")
        assert entry is not None
        assert entry["level"] == "ERROR"
        assert entry["source"] == "autonomous"

    def test_warning_line(self) -> None:
        entry = _parse_autonomous_log_line("[WARN] be careful")
        assert entry is not None
        assert entry["level"] == "WARNING"

    def test_info_line(self) -> None:
        entry = _parse_autonomous_log_line("cycle #1 started")
        assert entry is not None
        assert entry["level"] == "INFO"

    def test_empty_line(self) -> None:
        assert _parse_autonomous_log_line("") is None
        assert _parse_autonomous_log_line("   ") is None

    def test_cross_mark_error(self) -> None:
        entry = _parse_autonomous_log_line("✗ Quick failed: test")
        assert entry is not None
        assert entry["level"] == "ERROR"


class TestReadRecentLogs:
    """Tests for read_recent_logs."""

    def test_no_log_files(self, tmp_path: Path) -> None:
        entries = read_recent_logs(tmp_path)
        assert entries == []

    def test_reads_nfo_log(self, tmp_path: Path) -> None:
        nfo_path = tmp_path / ".planfile" / ".koru" / "nfo-events.jsonl"
        nfo_path.parent.mkdir(parents=True)
        nfo_path.write_text(json.dumps({
            "timestamp": "2026-09-16T07:39:41.000000+00:00",
            "level": "INFO",
            "function_name": "nfo.event",
            "kwargs": "{'activity_message': 'test entry'}",
        }) + "\n")
        entries = read_recent_logs(tmp_path)
        assert len(entries) == 1
        assert entries[0]["message"] == "test entry"

    def test_reads_autonomous_log(self, tmp_path: Path) -> None:
        auto_path = tmp_path / ".planfile" / ".koru" / "autonomous.log"
        auto_path.parent.mkdir(parents=True)
        auto_path.write_text("[ERROR] failed task\n[WARN] warning msg\n")
        entries = read_recent_logs(tmp_path)
        assert len(entries) == 2
        assert entries[0]["level"] == "ERROR"
        assert entries[1]["level"] == "WARNING"

    def test_limit(self, tmp_path: Path) -> None:
        nfo_path = tmp_path / ".planfile" / ".koru" / "nfo-events.jsonl"
        nfo_path.parent.mkdir(parents=True)
        for i in range(10):
            nfo_path.write_text(
                nfo_path.read_text() if nfo_path.exists() else ""
                + json.dumps({
                    "timestamp": f"2026-09-16T07:39:4{i}.000000+00:00",
                    "level": "INFO",
                    "function_name": "nfo.event",
                    "kwargs": f"{{'activity_message': 'entry {i}'}}",
                }) + "\n",
            )
        entries = read_recent_logs(tmp_path, limit=3)
        assert len(entries) <= 3


class TestSseLogStream:
    """Tests for sse_log_stream generator."""

    def test_yields_sse_format(self, tmp_path: Path) -> None:
        nfo_path = tmp_path / ".planfile" / ".koru" / "nfo-events.jsonl"
        nfo_path.parent.mkdir(parents=True)
        nfo_path.write_text(json.dumps({
            "timestamp": "2026-09-16T07:39:41.000000+00:00",
            "level": "INFO",
            "function_name": "nfo.event",
            "kwargs": "{'activity_message': 'hello'}",
        }) + "\n")
        gen = sse_log_stream(tmp_path, max_events=1, poll_interval=0.01)
        chunks = list(gen)
        data_chunks = [c for c in chunks if c.startswith("data: ")]
        assert len(data_chunks) >= 1
        entry = json.loads(data_chunks[0].replace("data: ", "").strip())
        assert entry["message"] == "hello"

    def test_level_filter(self, tmp_path: Path) -> None:
        nfo_path = tmp_path / ".planfile" / ".koru" / "nfo-events.jsonl"
        nfo_path.parent.mkdir(parents=True)
        nfo_path.write_text(
            json.dumps({
                "timestamp": "2026-09-16T07:39:41.000000+00:00",
                "level": "INFO",
                "function_name": "nfo.event",
                "kwargs": "{'activity_message': 'info msg'}",
            }) + "\n"
            + json.dumps({
                "timestamp": "2026-09-16T07:39:42.000000+00:00",
                "level": "ERROR",
                "function_name": "nfo.event",
                "kwargs": "{'activity_message': 'error msg'}",
            }) + "\n"
        )
        gen = sse_log_stream(tmp_path, levels={"ERROR"}, max_events=1, poll_interval=0.01)
        chunks = list(gen)
        data_chunks = [c for c in chunks if c.startswith("data: ")]
        assert len(data_chunks) == 1
        entry = json.loads(data_chunks[0].replace("data: ", "").strip())
        assert entry["level"] == "ERROR"
        assert entry["message"] == "error msg"


class TestWebFlagParser:
    """Tests for the --web flag consumed before argparse."""

    def test_web_flag_exists(self) -> None:
        from koru.autonomous import _consume_web_flag

        cleaned, web = _consume_web_flag(["up", "--web"])
        assert web is True
        assert cleaned == ["up"]

    def test_no_web_flag(self) -> None:
        from koru.autonomous import _consume_web_flag

        cleaned, web = _consume_web_flag(["up", "--web", "--no-web"])
        assert web is False
        assert cleaned == ["up"]

    def test_web_flag_defaults_false(self) -> None:
        from koru.autonomous import _consume_web_flag

        cleaned, web = _consume_web_flag(["up"])
        assert web is False
        assert cleaned == ["up"]

    def test_web_flag_end_to_end_parse(self) -> None:
        from koru.autonomous import _parse_autonomous_args

        args = _parse_autonomous_args(["up", "--web"], invoked_as_auto=True)
        assert args.web is True

    def test_no_web_flag_end_to_end_parse(self) -> None:
        from koru.autonomous import _parse_autonomous_args

        args = _parse_autonomous_args(["up"], invoked_as_auto=True)
        assert args.web is False
