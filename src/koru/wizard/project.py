"""Project / workspace detection for ``koru wizard``.

Given a (possibly running) IDE, we try to figure out which folder the user is
working in. Strategies, in order:

1. The IDE process cmdline often ends with the workspace path (Cursor, VS Code,
   JetBrains launchers, Zed).
2. ``cwd`` of the current shell.
3. Recent project files dropped by the IDE (``~/.config/Cursor/User/globalStorage``,
   ``~/.config/Code/User/workspaceStorage``, ``~/.config/JetBrains/.../recentProjects.xml``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from koru.wizard.ide import DetectedIDE


@dataclass(frozen=True)
class ProjectCandidate:
    """A workspace folder we can offer to the user."""

    path: Path
    source: str

    def label(self) -> str:
        return f"{self.path}  ({self.source})"


def _read_proc_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()


def _read_proc_cwd(pid: int) -> Path | None:
    try:
        target = os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return None
    candidate = Path(target)
    return candidate if candidate.exists() else None


_PATH_LIKE = re.compile(r"(/[^\s\-][\w./@\-+]+)")


def _extract_workspace_from_cmdline(cmdline: str) -> Path | None:
    """Return the last existing path in an IDE cmdline, if any."""
    if not cmdline:
        return None
    matches = list(_PATH_LIKE.finditer(cmdline))
    for m in reversed(matches):
        candidate = Path(m.group(1))
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _candidates_from_running_ide(ide: DetectedIDE) -> list[ProjectCandidate]:
    if not ide.running or ide.pid is None:
        return []
    out: list[ProjectCandidate] = []
    workspace = _extract_workspace_from_cmdline(_read_proc_cmdline(ide.pid))
    if workspace is not None:
        out.append(ProjectCandidate(path=workspace.resolve(), source=f"{ide.label} workspace"))
    cwd = _read_proc_cwd(ide.pid)
    if cwd is not None and (not out or cwd.resolve() != out[0].path):
        out.append(ProjectCandidate(path=cwd.resolve(), source=f"{ide.label} cwd"))
    return out


def _is_project_root(path: Path) -> bool:
    markers = (
        ".git",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        ".planfile",
        "Taskfile.yml",
        "Makefile",
    )
    return any((path / m).exists() for m in markers)


def _walk_up_to_root(start: Path, max_hops: int = 4) -> Path:
    current = start
    for _ in range(max_hops):
        if _is_project_root(current):
            return current
        if current.parent == current:
            return current
        current = current.parent
    return start


def _shell_cwd_candidate() -> ProjectCandidate | None:
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        return None
    return ProjectCandidate(path=_walk_up_to_root(cwd), source="shell cwd")


def _recent_jetbrains_projects() -> list[ProjectCandidate]:
    base = Path("~/.config/JetBrains").expanduser()
    out: list[ProjectCandidate] = []
    if not base.is_dir():
        return out
    pattern = re.compile(r'<option value="\$USER_HOME\$/?([^"]+)"')
    for recents in base.glob("*/options/recentProjects.xml"):
        try:
            text = recents.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in pattern.finditer(text):
            candidate = Path("~").expanduser() / match.group(1)
            if candidate.is_dir():
                out.append(
                    ProjectCandidate(
                        path=candidate.resolve(),
                        source=f"JetBrains recent ({recents.parent.parent.name})",
                    )
                )
        if out:
            break
    return out


def _dedup(items: list[ProjectCandidate]) -> list[ProjectCandidate]:
    seen: set[Path] = set()
    deduped: list[ProjectCandidate] = []
    for item in items:
        if item.path in seen:
            continue
        seen.add(item.path)
        deduped.append(item)
    return deduped


def propose_projects(ides: list[DetectedIDE], *, max_results: int = 8) -> list[ProjectCandidate]:
    """Best-effort ordered list of likely projects to work on."""
    candidates: list[ProjectCandidate] = []
    for ide in ides:
        candidates.extend(_candidates_from_running_ide(ide))

    cwd_candidate = _shell_cwd_candidate()
    if cwd_candidate is not None:
        candidates.append(cwd_candidate)

    candidates.extend(_recent_jetbrains_projects())

    return _dedup(candidates)[:max_results]
