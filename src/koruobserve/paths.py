"""Filesystem layout for koruobserve runtime state."""

from __future__ import annotations

from pathlib import Path


def runtime_dir(project: Path) -> Path:
    return project.resolve() / ".koru" / "run"


def pidfile(project: Path, name: str) -> Path:
    return runtime_dir(project) / f"{name}.pid"


def logfile(project: Path, name: str) -> Path:
    return runtime_dir(project) / f"{name}.log"


def state_file(project: Path) -> Path:
    return runtime_dir(project) / "observe.json"
