"""Per-repo cooldown stamps — the cost control for paid LLM planning runs.

Each ``nxdo`` planning run is a paid LLM call, so every repo (the project
plus the ``KORU_NXDO_REPOS`` extras) is stamped with its last run;
``KORU_NXDO_COOLDOWN_SECONDS`` (default 3600) must elapse before the repo
is eligible again. A failing run is stamped too — a failing repo must not
burn an LLM call every idle cycle. Stamps live in
``<project>/.planfile/.koru/nxdo-discovery.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from koru.autonomy.nxdo_config import _env_float, nxdo_target_repos

DEFAULT_COOLDOWN_SECONDS = 3600.0
STAMP_RELPATH = Path(".planfile") / ".koru" / "nxdo-discovery.json"


def _stamp_path(project: Path) -> Path:
    return project / STAMP_RELPATH


def _load_stamps(project: Path) -> dict[str, float]:
    try:
        data = json.loads(_stamp_path(project).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}


def _save_stamps(project: Path, stamps: dict[str, float]) -> None:
    path = _stamp_path(project)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stamps, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


class _CooldownSelection(NamedTuple):
    """Result of cooldown-based target-repo selection."""

    repo: Path | None
    remaining: float


def _select_target_repo(project: Path, *, now: float) -> _CooldownSelection:
    """First repo whose per-repo cooldown has expired (project first)."""
    cooldown = _env_float("KORU_NXDO_COOLDOWN_SECONDS", DEFAULT_COOLDOWN_SECONDS, project)
    stamps = _load_stamps(project)
    best_remaining = float("inf")
    for repo in nxdo_target_repos(project):
        last = stamps.get(str(repo), 0.0)
        remaining = cooldown - (now - last)
        if remaining <= 0:
            return _CooldownSelection(repo, 0.0)
        best_remaining = min(best_remaining, remaining)
    return _CooldownSelection(None, best_remaining)
