"""Automatic broad project discovery via ``code2llm`` when the queue is idle.

When ``koru auto`` finds an empty planfile queue, instead of asking an IDE
operator to run ``code2llm`` manually we attempt to:

1. Detect a working ``code2llm`` binary on ``PATH``.
2. Generate fresh analysis artifacts (``analysis.toon.yaml``, ``map.toon.yaml``,
   ``planfile-tickets.yaml`` etc.) under ``./project/``.
3. Apply the planfile-tickets directly through ``planfile ticket create``.

Each step is best-effort: any failure is reported as a structured outcome so
the caller can fall back to the legacy "create operator ticket" flow.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

DEFAULT_OUTPUT_SUBDIR = "project"
DEFAULT_FORMATS = "all"
DEFAULT_EXCLUDES = ("*.md",)
DEFAULT_STALE_MINUTES = 60.0
DEFAULT_SOURCE = "koru-project-discovery"


@dataclass
class DiscoveryOutcome:
    """Result of an automatic ``code2llm`` discovery cycle."""

    ran: bool = False
    skipped_reason: str | None = None
    code2llm_path: str | None = None
    code2llm_returncode: int | None = None
    code2llm_duration_s: float | None = None
    artifacts_dir: str | None = None
    applied_titles: list[str] = field(default_factory=list)
    skipped_titles: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "skipped_reason": self.skipped_reason,
            "code2llm_path": self.code2llm_path,
            "code2llm_returncode": self.code2llm_returncode,
            "code2llm_duration_s": self.code2llm_duration_s,
            "artifacts_dir": self.artifacts_dir,
            "applied": list(self.applied_titles),
            "skipped": list(self.skipped_titles),
            "error": self.error,
        }


def _default_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )


def _artifacts_fresh(artifacts_dir: Path, *, stale_minutes: float) -> bool:
    analysis = artifacts_dir / "analysis.toon.yaml"
    if not analysis.is_file():
        return False
    age_s = max(0.0, time.time() - analysis.stat().st_mtime)
    return age_s < stale_minutes * 60.0


def _code2llm_executable() -> str | None:
    return shutil.which("code2llm")


def _build_code2llm_cmd(
    binary: str,
    *,
    project: Path,
    output_dir: Path,
    formats: str,
    excludes: Sequence[str],
    apply_planfile: bool,
    planfile_source: str,
    planfile_sprint: str,
    planfile_limit: int | None,
) -> list[str]:
    cmd = [
        binary,
        str(project),
        "-f",
        formats,
        "-o",
        str(output_dir),
        "--no-chunk",
    ]
    for pattern in excludes:
        cmd.extend(["--exclude", pattern])
    if apply_planfile:
        cmd.append("--planfile-apply")
        cmd.extend(["--planfile-source", planfile_source])
        cmd.extend(["--planfile-sprint", planfile_sprint])
        cmd.extend(["--planfile-project", str(project)])
        if planfile_limit is not None and planfile_limit > 0:
            cmd.extend(["--planfile-limit", str(planfile_limit)])
    return cmd


def _read_planfile_tickets_output(artifacts_dir: Path) -> tuple[list[str], list[str]]:
    """Parse ``planfile-tickets.yaml`` for the applied/skipped lists."""
    path = artifacts_dir / "planfile-tickets.yaml"
    if not path.is_file():
        return [], []
    try:
        import yaml  # local import; yaml is already a runtime dep of koru

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 — best-effort
        return [], []
    if not isinstance(data, dict):
        return [], []
    applied = [str(item) for item in (data.get("applied") or []) if isinstance(item, str)]
    skipped = [str(item) for item in (data.get("skipped") or []) if isinstance(item, str)]
    return applied, skipped


def run_code2llm_discovery(
    project: Path,
    *,
    output_subdir: str = DEFAULT_OUTPUT_SUBDIR,
    formats: str = DEFAULT_FORMATS,
    excludes: Sequence[str] = DEFAULT_EXCLUDES,
    apply_planfile: bool = True,
    planfile_source: str = DEFAULT_SOURCE,
    planfile_sprint: str = "current",
    planfile_limit: int | None = 20,
    stale_minutes: float = DEFAULT_STALE_MINUTES,
    force: bool = False,
    runner: Runner = _default_runner,
) -> DiscoveryOutcome:
    """Run ``code2llm`` to refresh project artifacts and apply planfile tickets.

    Returns a structured :class:`DiscoveryOutcome` so callers can branch on the
    result without parsing logs.
    """
    project = project.resolve()
    artifacts_dir = (project / output_subdir).resolve()
    outcome = DiscoveryOutcome(artifacts_dir=str(artifacts_dir))

    binary = _code2llm_executable()
    if binary is None:
        outcome.skipped_reason = "code2llm not on PATH"
        return outcome
    outcome.code2llm_path = binary

    if not force and _artifacts_fresh(artifacts_dir, stale_minutes=stale_minutes):
        outcome.skipped_reason = (
            f"artifacts younger than {stale_minutes:.0f}m in {artifacts_dir}"
        )
        # Still apply planfile tickets if a fresh ticket file is present.
        applied, skipped = _read_planfile_tickets_output(artifacts_dir)
        outcome.applied_titles = applied
        outcome.skipped_titles = skipped
        return outcome

    cmd = _build_code2llm_cmd(
        binary,
        project=project,
        output_dir=artifacts_dir,
        formats=formats,
        excludes=excludes,
        apply_planfile=apply_planfile,
        planfile_source=planfile_source,
        planfile_sprint=planfile_sprint,
        planfile_limit=planfile_limit,
    )
    start = time.monotonic()
    try:
        result = runner(cmd, project)
    except subprocess.TimeoutExpired as exc:
        outcome.error = f"code2llm timed out after {exc.timeout}s"
        outcome.code2llm_duration_s = time.monotonic() - start
        return outcome
    except (OSError, ValueError) as exc:
        outcome.error = f"code2llm exec failed: {exc}"
        outcome.code2llm_duration_s = time.monotonic() - start
        return outcome
    outcome.code2llm_duration_s = time.monotonic() - start
    outcome.code2llm_returncode = result.returncode
    outcome.ran = True
    if result.returncode != 0:
        outcome.error = (result.stderr or result.stdout or "").strip().splitlines()[-1:] or [
            f"code2llm rc={result.returncode}",
        ]
        outcome.error = outcome.error[0] if outcome.error else f"rc={result.returncode}"
        return outcome

    applied, skipped = _read_planfile_tickets_output(artifacts_dir)
    outcome.applied_titles = applied
    outcome.skipped_titles = skipped
    return outcome


def format_discovery_summary(outcome: DiscoveryOutcome) -> str:
    """One-line summary suitable for the koru activity log."""
    if outcome.skipped_reason and not outcome.ran:
        return f"code2llm discovery skipped: {outcome.skipped_reason}"
    if outcome.error:
        return f"code2llm discovery error: {outcome.error}"
    pieces: list[str] = []
    if outcome.code2llm_duration_s is not None:
        pieces.append(f"code2llm {outcome.code2llm_duration_s:.1f}s")
    pieces.append(f"applied={len(outcome.applied_titles)}")
    pieces.append(f"skipped={len(outcome.skipped_titles)}")
    if outcome.artifacts_dir:
        pieces.append(f"artifacts={outcome.artifacts_dir}")
    return "code2llm discovery: " + " ".join(pieces)


__all__ = [
    "DiscoveryOutcome",
    "Runner",
    "format_discovery_summary",
    "run_code2llm_discovery",
]
