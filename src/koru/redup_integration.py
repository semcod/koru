"""Command builders for Koru's reDUP integration."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

DEFAULT_MIN_LINES = 10
DEFAULT_BASE_REF = "HEAD"
DEFAULT_CHANGED_REPORT = Path(".redup/wup-changed.json")


def redup_scan_command(path: str | Path = ".", *, min_lines: int = DEFAULT_MIN_LINES) -> list[str]:
    """Build a full reDUP scan command."""
    return ["redup", "scan", str(path), "--min-lines", str(min_lines)]


def redup_check_command(path: str | Path = ".", *, min_lines: int = DEFAULT_MIN_LINES) -> list[str]:
    """Build a reDUP budget-check command."""
    return ["redup", "check", str(path), "--min-lines", str(min_lines)]


def redup_changed_scan_command(
    path: str | Path = ".",
    *,
    base_ref: str = DEFAULT_BASE_REF,
    output: str | Path = DEFAULT_CHANGED_REPORT,
    min_lines: int = DEFAULT_MIN_LINES,
) -> list[str]:
    """Build an incremental changed-file scan for WUP/on-change workflows."""
    return [
        "redup",
        "scan",
        str(path),
        "--changed-only",
        "--base-ref",
        base_ref,
        "--include-untracked",
        "--incremental",
        "--format",
        "json",
        "--output",
        str(output),
        "--min-lines",
        str(min_lines),
    ]


def redup_changed_scan_runner_command(
    *,
    base_ref: str = DEFAULT_BASE_REF,
    output: str | Path = DEFAULT_CHANGED_REPORT,
    min_lines: int = DEFAULT_MIN_LINES,
) -> list[str]:
    """Build the Koru wrapper command for version-tolerant changed scans."""
    return [
        "python3",
        "-m",
        "koru.redup_integration",
        "changed-scan",
        "--base-ref",
        base_ref,
        "--output",
        str(output),
        "--min-lines",
        str(min_lines),
    ]


def _redup_scan_supports(option: str) -> bool:
    result = subprocess.run(
        ["redup", "scan", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    return option in f"{result.stdout}\n{result.stderr}"


def _redup_json_scan_command(
    path: str | Path = ".",
    *,
    output: str | Path = DEFAULT_CHANGED_REPORT,
    min_lines: int = DEFAULT_MIN_LINES,
) -> list[str]:
    return [
        "redup",
        "scan",
        str(path),
        "--format",
        "json",
        "--output",
        str(output),
        "--min-lines",
        str(min_lines),
    ]


def run_changed_scan(
    *,
    base_ref: str = DEFAULT_BASE_REF,
    output: str | Path = DEFAULT_CHANGED_REPORT,
    min_lines: int = DEFAULT_MIN_LINES,
) -> int:
    """Run a changed-file scan when supported, with a full JSON scan fallback."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if _redup_scan_supports("--changed-only"):
        command = redup_changed_scan_command(
            base_ref=base_ref,
            output=output,
            min_lines=min_lines,
        )
    else:
        print("[redup] installed CLI lacks --changed-only; falling back to full JSON scan")
        command = _redup_json_scan_command(output=output, min_lines=min_lines)
    return subprocess.run(command, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Koru helpers for reDUP integration.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    changed = subparsers.add_parser("changed-scan")
    changed.add_argument("--base-ref", default=DEFAULT_BASE_REF)
    changed.add_argument("--output", default=str(DEFAULT_CHANGED_REPORT))
    changed.add_argument("--min-lines", type=int, default=DEFAULT_MIN_LINES)

    args = parser.parse_args(argv)
    if args.command == "changed-scan":
        return run_changed_scan(
            base_ref=args.base_ref,
            output=args.output,
            min_lines=args.min_lines,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
