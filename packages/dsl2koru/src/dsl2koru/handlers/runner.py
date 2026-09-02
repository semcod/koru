"""Compatibility runner that calls ``coru.cli.main``."""

from __future__ import annotations

import contextlib
import subprocess
import sys
from collections.abc import Callable, Iterator
from io import StringIO

Runner = Callable[[list[str]], tuple[int, str, str]]


@contextlib.contextmanager
def _capture_output() -> Iterator[tuple[StringIO, StringIO]]:
    stdout = StringIO()
    stderr = StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        yield stdout, stderr


def _run_subprocess(argv: list[str], *, error: str | None = None) -> tuple[int, str, str]:
    if error is not None:
        return 1, "", error
    proc = subprocess.run(
        [sys.executable, "-m", "coru", *argv],
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def default_runner(argv: list[str]) -> tuple[int, str, str]:
    """Run a Coru command through its Python module entry point."""
    try:
        from coru import cli as coru_cli
    except Exception as exc:
        return _run_subprocess(argv, error=f"cannot import coru.cli: {exc}")

    with _capture_output() as (stdout, stderr):
        try:
            rc = coru_cli.main(argv)
        except SystemExit as exc:  # pragma: no cover
            rc = int(exc.code) if exc.code is not None else 0
        except Exception as exc:  # pragma: no cover
            return 1, "", f"coru dispatch failed: {exc}"
    return rc, stdout.getvalue(), stderr.getvalue()
