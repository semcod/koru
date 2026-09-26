"""Configuration knobs and ``nxdo`` resolution for idle-time ticket generation.

Every knob is looked up in ``os.environ`` first, then in the project's
``.env`` file — ``koru auto`` does not load ``.env`` into the process
environment, so the fallback keeps configuration in the repo:

- ``KORU_NXDO_ENABLE``: ``0``/``false`` disables the generator (default on).
- ``KORU_NXDO_BIN``: explicit path to the ``nxdo`` executable. Fallbacks:
  ``PATH`` lookup, then ``~/.venv/bin/nxdo`` (the shared semcod venv).
- ``KORU_NXDO_REPOS``: ``:``/``,``-separated extra repos (globs allowed,
  e.g. ``/home/tom/github/semcod/*``) to plan for after the project itself.
  Only directories containing ``.git`` qualify.
- ``KORU_NXDO_TIMEOUT_SECONDS``: subprocess timeout (default 300).
"""

from __future__ import annotations

import glob as _glob
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

DEFAULT_TIMEOUT_SECONDS = 300.0


def _default_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=_env_float("KORU_NXDO_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )


def _dotenv_value(project: Path | None, name: str) -> str:
    """Read ``name`` from ``<project>/.env`` (simple ``KEY=VALUE`` lines)."""
    if project is None:
        return ""
    try:
        text = (project / ".env").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip().strip("'\"") if match else ""


def _config_value(name: str, project: Path | None = None) -> str:
    return (os.environ.get(name) or "").strip() or _dotenv_value(project, name)


def _env_flag(name: str, default: bool, project: Path | None = None) -> bool:
    raw = _config_value(name, project).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, project: Path | None = None) -> float:
    try:
        return float(_config_value(name, project) or default)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, project: Path | None = None) -> int:
    try:
        return int(_config_value(name, project) or default)
    except (TypeError, ValueError):
        return default


def nxdo_enabled(project: Path | None = None) -> bool:
    return _env_flag("KORU_NXDO_ENABLE", True, project)


def _nxdo_executable(project: Path | None = None) -> str | None:
    override = _config_value("KORU_NXDO_BIN", project)
    if override:
        return override if Path(override).is_file() else None
    found = shutil.which("nxdo")
    if found:
        return found
    fallback = Path.home() / ".venv" / "bin" / "nxdo"
    return str(fallback) if fallback.is_file() else None


def _api_key_available(project: Path) -> bool:
    for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if (os.environ.get(key) or "").strip():
            return True
    env_file = project / ".env"
    try:
        text = env_file.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(re.search(r"^\s*(OPENROUTER_API_KEY|OPENAI_API_KEY)\s*=\s*\S", text, re.M))


def nxdo_target_repos(project: Path) -> list[Path]:
    """The project itself plus ``KORU_NXDO_REPOS`` extras (globs expanded)."""
    project = project.resolve()
    repos: list[Path] = [project]
    raw = _config_value("KORU_NXDO_REPOS", project)
    if not raw:
        return repos
    for spec in re.split(r"[:,]", raw):
        spec = os.path.expanduser(spec.strip())
        if not spec:
            continue
        for hit in sorted(_glob.glob(spec)):
            path = Path(hit).resolve()
            if path == project or path in repos:
                continue
            if path.is_dir() and (path / ".git").exists():
                repos.append(path)
    return repos
