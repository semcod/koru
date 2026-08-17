"""Command builders for Koru MCP quality-gate adapters."""

from __future__ import annotations

import sys
from pathlib import Path


def vallm_batch_command(path: str | Path = ".") -> list[str]:
    """Build a project-scoped vallm batch validation command."""
    return [
        sys.executable,
        "-m",
        "vallm",
        "batch",
        "-r",
        "--format",
        "json",
        str(path),
    ]


def sumr_scan_command(path: str | Path = ".") -> list[str]:
    """Build a sumr scan via the current interpreter's sumd entry point.

    Bare ``sumr`` shims often point at a different Python than Koru's runtime,
    so invoke ``sumd.cli.main_sumr`` through ``sys.executable``.
    """
    return [
        sys.executable,
        "-c",
        "import sys; from sumd.cli import main_sumr; "
        "sys.argv = ['sumr', *sys.argv[1:]]; raise SystemExit(main_sumr() or 0)",
        str(path),
    ]
