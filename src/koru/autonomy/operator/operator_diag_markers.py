"""Flat filesystem paths for autonomous diagnostic ticket markers."""

from __future__ import annotations

from pathlib import Path


def diagnostic_marker_path(state_dir: Path, check_id: str) -> Path:
    """Map a logical check_id to a flat marker file under *state_dir*.

    WUP service names may contain path separators (e.g. ``src/koru``). Using
    them raw in ``{check_id}.failed`` would treat slashes as directories and
    crash on ``write_text`` when parents were never created.
    """
    safe = check_id.replace("/", "_").replace("\\", "_")
    return state_dir / f"{safe}.failed"
