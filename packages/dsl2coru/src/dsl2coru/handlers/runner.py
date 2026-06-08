"""CORU CLI runner shim — calls coru.cli.main."""

from __future__ import annotations

import contextlib
import subprocess
import sys
from typing import Callable


def _capture_output():
    from io import StringIO

    stdout = StringIO()
    stderr = StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    try:
        yield stdout, stderr
    finally:
        sys.stdout = old_out
        sys.stderr = old_err


def _run_subprocess(argv: list[str], *, error: str | None = None) -> tuple[int, str, str]:
    if error is not None:
        return 1, "", error
    cmd = [sys.executable, "-m", "coru", *argv]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def default_runner(argv: list[str]) -> tuple[int, str, str]:
    """Run CORU command through Python module entrypoint."""
    try:
        from coru import cli as coru_cli
    except Exception as exc:
        return _run_subprocess(argv, error=f"cannot import coru.cli: {exc}")

    with contextlib.contextmanager(_capture_output)() as (stdout, stderr):
        try:
            rc = coru_cli.main(argv)
        except SystemExit as exc:  # pragma: no cover
            rc = int(exc.code) if exc.code is not None else 0
        except Exception as exc:  # pragma: no cover
            return 1, "", f"coru dispatch failed: {exc}"
    return rc, stdout.getvalue(), stderr.getvalue()


Runner = Callable[[list[str]], tuple[int, str, str]]
