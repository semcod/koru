"""Shared ``argv`` for spawning ``python -m koru --queue`` (MCP, scripts, tests).

Keeps one definition of the queue subprocess contract next to
:func:`koru.queue.run_planfile_queue_loop`, which is what ``koru --queue --loop``
uses in-process.
"""

from __future__ import annotations

import sys
from pathlib import Path


def build_koru_queue_argv(
    project: Path,
    *,
    mode: str,
    max_steps: int | None = None,
) -> list[str]:
    """Build argv for a single-shot ``koru --queue`` run (no ``--loop``).

    *mode* ``\"dry\"`` appends ``--dry-run``.  *max_steps*, when set, becomes
    ``--max-iterations`` (same flag the CLI accepts; harmless for non-loop).
    """
    cmd: list[str] = [
        sys.executable,
        "-m",
        "koru",
        "--queue",
        "--project",
        str(project.resolve()),
    ]
    if mode == "dry":
        cmd.append("--dry-run")
    if max_steps:
        cmd.extend(["--max-iterations", str(max_steps)])
    return cmd
