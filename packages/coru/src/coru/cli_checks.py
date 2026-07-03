"""Lightweight check/utility helpers extracted from cli.py.

Contains:
- OQL trace utilities (_trace_enabled, _trace)
- Project normalisation (_coru_*)
- Lane status checks (_status_has_*)
- Readiness/plan helpers
"""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from coru.cli import Plan


def _trace_enabled() -> bool:
    return os.environ.get("CORU_TRACE", "").strip().lower() in {"1", "true", "yes", "oql"}


def _trace(step: str, **kv: Any) -> None:
    """Emit an OQL-style RESOLVE trace line to stderr.

    Format:  RESOLVE step  key=value key=value ...
    Enabled by CORU_TRACE=1 (or CORU_TRACE=oql).
    """
    if not _trace_enabled():
        return
    parts = [f"RESOLVE {step}"]
    for k, v in kv.items():
        parts.append(f"{k}={v}")
    print(" ".join(parts), file=sys.stderr)


def _coru_normalize_project(path: Path | str | None) -> Path | None:
    if path is None:
        return None
    try:
        from koru.autonomous_runtime import normalize_project_root

        return normalize_project_root(path)
    except Exception:
        pass
    try:
        current = Path(path).expanduser().resolve()
    except OSError:
        return None
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / ".git").exists():
            return candidate
    return current


def _coru_projects_equivalent(left: Path | str | None, right: Path | str | None) -> bool:
    try:
        from koru.autonomous_runtime import projects_equivalent

        return projects_equivalent(left, right)
    except Exception:
        left_norm = _coru_normalize_project(left)
        right_norm = _coru_normalize_project(right)
        if left_norm is None or right_norm is None:
            return False
        return left_norm == right_norm


def _coru_readiness_strict() -> bool:
    return os.environ.get("CORU_READINESS_STRICT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _status_has_target_plugin(status: dict[str, Any], *, ide: str, project: Path) -> bool:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False
    project_resolved = str(project.resolve())
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if plugin_ide != ide:
            continue
        folders = plugin.get("workspaceFolders")
        if not isinstance(folders, list):
            return True
        for folder in folders:
            try:
                if str(Path(str(folder)).expanduser().resolve()) == project_resolved:
                    return True
            except Exception:
                if str(folder) == str(project):
                    return True
    return False


def _status_has_plugin_for_ide(status: Mapping[str, Any], ide: str) -> bool:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False
    wanted = ide.strip().lower()
    for plugin in plugins:
        if not isinstance(plugin, Mapping):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if wanted in {"", "auto"} or plugin_ide == wanted:
            return True
    return False


def _status_has_keyboard_backend(status: Mapping[str, Any]) -> bool:
    if str(status.get("selected_backend") or "").strip():
        return True
    backends = status.get("backends")
    if not isinstance(backends, list):
        return False
    return any(isinstance(item, Mapping) and bool(item.get("available")) for item in backends)


def _status_failure_ok_to_continue(plans: Sequence[Plan], index: int) -> bool:  # type: ignore[type-arg]
    """Allow auto/setup chains to proceed when daemon is down; koru auto starts it."""
    return any(p.action == "auto" for p in plans[index + 1 :])
