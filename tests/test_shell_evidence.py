from __future__ import annotations

import json

from koru.queue.shell_evidence import SHELL_RUN_NOTE_TAG, format_shell_run_note


def test_format_shell_run_note_includes_meta_and_streams() -> None:
    text = format_shell_run_note(
        run_id="abc123",
        exit_code=0,
        stdout="hello\n",
        stderr="warn",
    )
    first, _, rest = text.partition("\n")
    assert first.startswith(SHELL_RUN_NOTE_TAG + " ")
    meta = json.loads(first.removeprefix(SHELL_RUN_NOTE_TAG + " "))
    assert meta["run_id"] == "abc123"
    assert meta["exit_code"] == 0
    assert meta["truncated"] is False
    assert "hello" in rest
    assert "warn" in rest


def test_format_shell_run_note_truncates_long_stdout() -> None:
    big = "x" * 9000
    text = format_shell_run_note(
        run_id="r1",
        exit_code=0,
        stdout=big,
        stderr="",
        max_stream_chars=100,
    )
    first, _, rest = text.partition("\n")
    meta = json.loads(first.removeprefix(SHELL_RUN_NOTE_TAG + " "))
    assert meta["truncated"] is True
    assert len(rest) < len(big)
    assert "xxx" in rest


def test_format_shell_run_note_hard_total_cap() -> None:
    text = format_shell_run_note(
        run_id="r2",
        exit_code=0,
        stdout="y" * 5000,
        stderr="z" * 5000,
        max_stream_chars=4000,
        max_total_chars=500,
    )
    assert len(text) <= 500
