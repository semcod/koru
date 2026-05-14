"""Tests for :func:`koru.queue.build_koru_queue_argv`."""

from __future__ import annotations

import sys
from pathlib import Path

from koru.queue import build_koru_queue_argv


def test_build_queue_argv_apply_minimal(tmp_path: Path) -> None:
    argv = build_koru_queue_argv(tmp_path, mode="apply", max_steps=None)
    assert argv[:4] == [sys.executable, "-m", "koru", "--queue"]
    assert "--project" in argv
    assert str(tmp_path.resolve()) in argv
    assert "--dry-run" not in argv
    assert "--max-iterations" not in argv


def test_build_queue_argv_dry_and_max_steps(tmp_path: Path) -> None:
    argv = build_koru_queue_argv(tmp_path, mode="dry", max_steps=3)
    assert "--dry-run" in argv
    assert argv[argv.index("--max-iterations") + 1] == "3"
