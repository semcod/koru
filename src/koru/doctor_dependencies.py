"""Opt-in dependency freshness checks for ``koru doctor``."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from koru.doctor_constants import PASS, SKIP, WARN


def check_uv_lock_freshness(
    project: Path,
    *,
    subprocess_run: Callable[..., object] = subprocess.run,
) -> tuple[str, str]:
    """Report whether resolving the lockfile against current indexes changes it.

    This is intentionally opt-in because it contacts configured package indexes.
    ``--dry-run`` guarantees that neither ``uv.lock`` nor the environment changes.
    """
    if not (project / "pyproject.toml").is_file() or not (project / "uv.lock").is_file():
        return SKIP, "no uv project lockfile"
    uv = shutil.which("uv")
    if not uv:
        return SKIP, "uv is not on PATH"
    try:
        result = subprocess_run(
            [uv, "lock", "--upgrade", "--dry-run"],
            cwd=str(project.resolve()),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return WARN, f"could not check lock freshness: {exc}"

    output = f"{getattr(result, 'stdout', '') or ''}\n{getattr(result, 'stderr', '') or ''}"
    if getattr(result, "returncode", 1) != 0:
        return WARN, f"uv lock freshness check failed: {output.strip()[-500:]}"
    changes = [
        line.strip()
        for line in output.splitlines()
        if line.startswith("Update ") or line.startswith("Add ")
    ]
    if not changes:
        return PASS, "uv.lock is current against configured indexes"
    preview = "; ".join(changes[:3])
    remainder = f"; +{len(changes) - 3} more" if len(changes) > 3 else ""
    return WARN, f"uv.lock has {len(changes)} available change(s): {preview}{remainder}"
