"""Shared todo2code configuration and process construction.

This module belongs to the lower queue layer so queue verification and the
higher autonomy workflow can reuse the same deterministic command contract.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def _dotenv_value(project: Path | None, name: str) -> str:
    if project is None:
        return ""
    try:
        text = (project / ".env").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip().strip("'\"") if match else ""


def config_value(name: str, project: Path | None = None) -> str:
    """Resolve a todo2code setting from the process or target ``.env``."""
    return (os.environ.get(name) or "").strip() or _dotenv_value(project, name)


def t2c_executable(project: Path | None = None) -> str | None:
    """Resolve the configured or installed todo2code executable."""
    override = config_value("KORU_TODO2CODE_BIN", project)
    if override:
        path = Path(override).expanduser()
        return str(path) if path.is_file() else None
    found = shutil.which("t2c")
    if found:
        return found
    sibling = Path.home() / "github" / "semcod" / "todo2code" / "dist" / "src" / "cli.js"
    return str(sibling) if sibling.is_file() else None


def _resolve_t2c_cli_js(binary: str) -> str | None:
    """Resolve a t2c launcher or symlink to its JavaScript entrypoint."""
    path = Path(binary)
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    if resolved.is_file() and resolved.suffix == ".js":
        return str(resolved)
    if path.is_file() and path.suffix == ".js":
        return str(path)
    return None


def _optional_input(project: Path, *candidates: str) -> Path | None:
    for name in candidates:
        path = project / name
        if path.is_file():
            return path
    return None


def build_pipeline_cmd(binary: str, project: Path, *, out_dir: Path) -> list[str]:
    """Build the deterministic todo2code pipeline command."""
    cli_js = _resolve_t2c_cli_js(binary)
    if cli_js is not None:
        cmd = ["node", cli_js, "pipeline", str(project)]
    else:
        cmd = [binary, "pipeline", str(project)]

    cmd.extend(
        [
            "--nl-mode",
            "deterministic",
            "--markdown-mode",
            "deterministic",
            "--communication-mode",
            "deterministic",
            "--project-dir",
            "project",
            "--no-docs-llm",
            "--no-summary-llm",
            "--out",
            str(out_dir),
        ]
    )
    for flag, candidates in (
        ("--todo", ("TODO.md", "todo.md", "TODO.txt", "todo.txt")),
        ("--changelog", ("CHANGELOG.md", "changelog.md")),
        ("--task", ("TASK.md", "task.md", "TASKS.md")),
    ):
        path = _optional_input(project, *candidates)
        if path is not None:
            cmd.extend([flag, str(path)])
    return cmd
