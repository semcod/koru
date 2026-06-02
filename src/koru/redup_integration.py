"""Command builders for Koru's reDUP integration."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_MIN_LINES = 10
DEFAULT_BASE_REF = "HEAD"
DEFAULT_CHANGED_REPORT = Path(".redup/wup-changed.json")
FULL_SCAN_FALLBACK_ENV = "KORU_REDUP_FULL_SCAN_FALLBACK"


def _redup_module_command() -> list[str]:
    return [sys.executable, "-m", "redup"]


def redup_scan_command(path: str | Path = ".", *, min_lines: int = DEFAULT_MIN_LINES) -> list[str]:
    """Build a full reDUP scan command."""
    return [*_redup_module_command(), "scan", str(path), "--min-lines", str(min_lines)]


def redup_check_command(path: str | Path = ".", *, min_lines: int = DEFAULT_MIN_LINES) -> list[str]:
    """Build a reDUP budget-check command."""
    return [*_redup_module_command(), "check", str(path), "--min-lines", str(min_lines)]


def redup_changed_scan_command(
    path: str | Path = ".",
    *,
    base_ref: str = DEFAULT_BASE_REF,
    output: str | Path = DEFAULT_CHANGED_REPORT,
    min_lines: int = DEFAULT_MIN_LINES,
) -> list[str]:
    """Build an incremental changed-file scan for WUP/on-change workflows."""
    return [
        *_redup_module_command(),
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
        sys.executable,
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
        [*_redup_module_command(), "scan", "--help"],
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
        *_redup_module_command(),
        "scan",
        str(path),
        "--format",
        "json",
        "--output",
        str(output),
        "--min-lines",
        str(min_lines),
    ]


from koru.env_flags import env_truthy as _env_bool


def _write_skipped_changed_report(output: str | Path, *, reason: str) -> None:
    report = {
        "project_path": str(Path.cwd()),
        "stats": {
            "files_scanned": 0,
            "total_lines": 0,
            "total_blocks": 0,
            "scan_time_ms": 0.0,
        },
        "summary": {
            "total_groups": 0,
            "total_fragments": 0,
            "total_saved_lines": 0,
        },
        "groups": [],
        "refactor_suggestions": [],
        "meta": {
            "changed_only": True,
            "skipped": True,
            "reason": reason,
        },
    }
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")


def run_changed_scan(
    *,
    base_ref: str = DEFAULT_BASE_REF,
    output: str | Path = DEFAULT_CHANGED_REPORT,
    min_lines: int = DEFAULT_MIN_LINES,
) -> int:
    """Run a changed-file scan without silently falling back to full-repo work."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if _redup_scan_supports("--changed-only"):
        command = redup_changed_scan_command(
            base_ref=base_ref,
            output=output,
            min_lines=min_lines,
        )
        return subprocess.run(command, check=False).returncode

    reason = "installed redup CLI lacks --changed-only"
    if _env_bool(FULL_SCAN_FALLBACK_ENV):
        print(
            "[redup] installed CLI lacks --changed-only; "
            f"{FULL_SCAN_FALLBACK_ENV}=1 so falling back to full JSON scan"
        )
        command = _redup_json_scan_command(output=output, min_lines=min_lines)
        return subprocess.run(command, check=False).returncode

    print(
        "[redup] installed CLI lacks --changed-only; skipping full-repo fallback "
        f"(set {FULL_SCAN_FALLBACK_ENV}=1 to opt in)"
    )
    _write_skipped_changed_report(output, reason=reason)
    return 0


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
