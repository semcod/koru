"""Detect IDEs currently running on the user's desktop.

We rely on ``/proc/<pid>/comm`` and ``/proc/<pid>/cmdline`` so this
module has zero third-party dependencies. On non-Linux platforms the
detection silently degrades to "no IDEs found", which is OK because
the rest of autopilot is Linux-only anyway.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Map of IDE id -> (process-name patterns, friendly label).
# Patterns are matched against ``comm`` (basename of the executable)
# as well as the full ``cmdline`` so we catch electron wrappers like
# ``/opt/windsurf/windsurf --type=renderer``.
_IDE_SIGNATURES: dict[str, tuple[tuple[str, ...], str]] = {
    "windsurf": (("windsurf",), "Windsurf"),
    "vscode": (("code", "code-oss", "vscodium"), "VS Code"),
    "cursor": (("cursor",), "Cursor"),
    "jetbrains": (
        # JetBrains products run as the JVM; the cmdline almost always
        # contains the product name (idea.jar, pycharm, webstorm, ...).
        ("idea", "pycharm", "webstorm", "phpstorm", "goland", "clion", "rubymine"),
        "JetBrains IDE",
    ),
    "zed": (("zed",), "Zed"),
}


@dataclass(frozen=True)
class RunningIDE:
    """A single IDE process discovered on the system."""

    id: str
    label: str
    pid: int
    exe: str

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "label": self.label, "pid": self.pid, "exe": self.exe}


def _iter_proc_pids() -> list[int]:
    proc = Path("/proc")
    if not proc.is_dir():
        return []
    pids: list[int] = []
    for entry in proc.iterdir():
        name = entry.name
        if name.isdigit():
            pids.append(int(name))
    return pids


def _read_comm(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    # cmdline is NUL-separated; join with spaces for substring matches.
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()


def _matches(comm: str, cmdline: str, patterns: tuple[str, ...]) -> bool:
    comm_l = comm.lower()
    cmd_l = cmdline.lower()
    for pat in patterns:
        # Exact comm match wins (avoids matching ``code`` inside random
        # paths).
        if comm_l == pat:
            return True
        # Token match against cmdline split on spaces.
        tokens = cmd_l.split()
        if pat in tokens:
            return True
        # Path-style and jar-style matches: ``/opt/windsurf/windsurf``,
        # ``/opt/idea/lib/idea.jar``, ``-Didea.paths.selector=...``.
        # We check ``/<pat>``, ``/<pat>/``, ``/<pat>.``, ``<pat>.jar`` —
        # those rule out false positives like ``coderef`` while catching
        # both electron wrappers and JVM-launched IDEs.
        needles = (f"/{pat} ", f"/{pat}/", f"/{pat}.", f"{pat}.jar", f"{pat}64.jar")
        if any(n in cmd_l for n in needles):
            return True
        if cmd_l.endswith(f"/{pat}"):
            return True
    return False


def detect_running_ides(*, _pids: list[int] | None = None) -> list[RunningIDE]:
    """Return a deduplicated list of IDEs visible in ``/proc``.

    The ``_pids`` hook is used by tests to inject a fixed snapshot.
    """
    pids = _pids if _pids is not None else _iter_proc_pids()
    seen: dict[str, RunningIDE] = {}
    for pid in pids:
        comm = _read_comm(pid)
        cmdline = _read_cmdline(pid)
        if not comm and not cmdline:
            continue
        for ide_id, (patterns, label) in _IDE_SIGNATURES.items():
            if ide_id in seen:
                continue
            if _matches(comm, cmdline, patterns):
                exe = cmdline.split(" ", 1)[0] if cmdline else comm
                seen[ide_id] = RunningIDE(id=ide_id, label=label, pid=pid, exe=exe)
                break
    # Stable order: declared order in _IDE_SIGNATURES.
    return [seen[k] for k in _IDE_SIGNATURES if k in seen]


def pick_target(
    detected: list[RunningIDE],
    *,
    prefer: str | None = None,
) -> RunningIDE | None:
    """Choose which detected IDE should receive the injection.

    Priority:

    1. ``prefer`` (the user's explicit ``--ide`` flag), if running.
    2. The first IDE in :data:`_IDE_SIGNATURES` order — that order
       matches our backend reliability ranking (Windsurf has the
       richest extension API for chat, JetBrains the least).
    """
    if prefer:
        for ide in detected:
            if ide.id == prefer:
                return ide
        return None
    return detected[0] if detected else None


def is_linux() -> bool:
    return os.name == "posix" and Path("/proc").is_dir()


__all__ = ["RunningIDE", "detect_running_ides", "pick_target", "is_linux"]
