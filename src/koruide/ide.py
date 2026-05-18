"""Detect IDEs currently running on the user's desktop.

We rely on ``/proc/<pid>/comm`` and ``/proc/<pid>/cmdline`` so this
module has zero third-party dependencies. On non-Linux platforms the
detection silently degrades to "no IDEs found", which is OK because
the rest of autopilot is Linux-only anyway.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable
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


def _read_exe(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return ""


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


def _candidate_score(ide_id: str, pid: int, comm: str, cmdline: str, exe: str) -> int:
    """Rank multiple process matches for the same IDE.

    Higher score means "more likely the primary IDE process".
    """
    score = 0
    comm_l = comm.lower()
    cmd_l = cmdline.lower()
    exe_l = exe.lower()
    # Prefer canonical process names.
    canonical_comm = {
        "windsurf": ("windsurf",),
        "vscode": ("code", "code-insiders", "code-oss", "codium", "vscodium"),
        "cursor": ("cursor",),
        "zed": ("zed",),
    }
    if ide_id in canonical_comm and comm_l in canonical_comm[ide_id]:
        score += 100
    # Prefer main executable path if available.
    if exe_l:
        if ide_id == "windsurf":
            if exe_l.endswith("/windsurf") and "/extensions/" not in exe_l:
                score += 120
            if "/extensions/" in exe_l or "/devin/" in exe_l:
                score -= 80
        elif ide_id == "vscode":
            if exe_l.endswith("/code") or exe_l.endswith("/code-insiders"):
                score += 120
        elif ide_id == "cursor":
            if exe_l.endswith("/cursor"):
                score += 120
    # Renderer / utility processes are worse than browser/main.
    if "--type=renderer" in cmd_l or "--type=utility" in cmd_l:
        score -= 20
    if "--type=browser" in cmd_l:
        score += 10
    # Deterministic tie-breaker: prefer lower pid (usually older/main proc).
    score -= pid // 100000
    return score


def detect_running_ides(*, _pids: list[int] | None = None) -> list[RunningIDE]:
    """Return a deduplicated list of IDEs visible in ``/proc``.

    The ``_pids`` hook is used by tests to inject a fixed snapshot.
    """
    pids = _pids if _pids is not None else _iter_proc_pids()
    seen: dict[str, tuple[RunningIDE, int]] = {}
    for pid in pids:
        comm = _read_comm(pid)
        cmdline = _read_cmdline(pid)
        exe_link = _read_exe(pid)
        if not comm and not cmdline:
            continue
        for ide_id, (patterns, label) in _IDE_SIGNATURES.items():
            if _matches(comm, cmdline, patterns):
                exe = exe_link or (cmdline.split(" ", 1)[0] if cmdline else comm)
                row = RunningIDE(id=ide_id, label=label, pid=pid, exe=exe)
                score = _candidate_score(ide_id, pid, comm, cmdline, exe)
                prev = seen.get(ide_id)
                if prev is None or score > prev[1]:
                    seen[ide_id] = (row, score)
                break
    # Stable order: declared order in _IDE_SIGNATURES.
    return [seen[k][0] for k in _IDE_SIGNATURES if k in seen]


def _active_window_pid_x11() -> int | None:
    """Return PID of the active X11 window, if available.

    Uses ``xdotool getactivewindow getwindowpid``. Returns ``None`` on
    Wayland, when xdotool is unavailable, or on parsing/runtime errors.
    """
    if not os.environ.get("DISPLAY"):
        return None
    if not shutil.which("xdotool"):
        return None
    try:
        proc = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowpid"],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw.isdigit():
        return None
    pid = int(raw)
    return pid if pid > 0 else None


def _ide_id_from_process(pid: int) -> str | None:
    """Map a single process to a known IDE id, if any."""
    comm = _read_comm(pid)
    cmdline = _read_cmdline(pid)
    if not comm and not cmdline:
        return None
    for ide_id, (patterns, _label) in _IDE_SIGNATURES.items():
        if _matches(comm, cmdline, patterns):
            return ide_id
    return None


def detect_focused_ide_id(*, _active_pid: int | None = None) -> str | None:
    """Detect which IDE currently owns desktop focus.

    On X11 this maps active-window PID to one of our known IDE ids.
    On unsupported environments this returns ``None``.
    """
    pid = _active_pid if _active_pid is not None else _active_window_pid_x11()
    if pid is None:
        return None
    return _ide_id_from_process(pid)


_VSCODE_FAMILY_ENV_KEYS = (
    "VSCODE_PID",
    "VSCODE_NLS_CONFIG",
    "VSCODE_IPC_HOOK",
    "VSCODE_CODE_CACHE_PATH",
    "VSCODE_CWD",
)


def _vscode_family_env_present() -> bool:
    return any((os.environ.get(key) or "").strip() for key in _VSCODE_FAMILY_ENV_KEYS)


def _vscode_family_flavor_from_env() -> str | None:
    """Distinguish Cursor / VS Code / Codium from integrated-terminal env."""
    blob = " ".join(
        os.environ.get(key, "")
        for key in (
            "VSCODE_CODE_CACHE_PATH",
            "VSCODE_IPC_HOOK",
            "VSCODE_NLS_CONFIG",
            "VSCODE_CWD",
            "CHROME_DESKTOP",
        )
    ).lower()
    if "cursor" in blob:
        return "cursor"
    if "windsurf" in blob:
        return "windsurf"
    if "codium" in blob or "vscodium" in blob:
        return "vscode"
    if blob.strip():
        return "vscode"
    return None


def detect_terminal_host_ide_id(*, _start_pid: int | None = None) -> str | None:
    """IDE that owns the shell running this command (integrated terminal).

    Uses editor-specific env vars first (works on Wayland), then walks
    ``/proc`` parents. Cursor must be checked before generic ``VSCODE_*``
    because Cursor also sets ``VSCODE_PID``.
    """
    chrome = os.environ.get("CHROME_DESKTOP", "").strip().lower()
    if chrome == "cursor.desktop" or os.environ.get("CURSOR_AGENT") or os.environ.get("CURSOR_CLI"):
        return "cursor"

    term_program = os.environ.get("TERM_PROGRAM", "").strip().lower()
    if term_program in _IDE_SIGNATURES:
        return term_program

    # Before stale WINDSURF_CSRF_TOKEN: VS Code / Cursor / Windsurf set VSCODE_* in the shell.
    if _vscode_family_env_present():
        flavor = _vscode_family_flavor_from_env()
        if flavor is not None:
            return flavor

    if os.environ.get("WINDSURF_VERSION") or (
        os.environ.get("WINDSURF_CSRF_TOKEN") and "cursor" not in chrome
    ):
        return "windsurf"

    pid = _start_pid if _start_pid is not None else os.getpid()
    seen: set[int] = set()
    chain: list[str] = []
    for _ in range(40):
        if pid in seen or pid <= 0:
            break
        seen.add(pid)
        found = _ide_id_from_process(pid)
        if found is not None and found not in chain:
            chain.append(found)
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
            ppid = int(stat.split()[3])
        except (OSError, ValueError, IndexError):
            break
        if ppid == pid:
            break
        pid = ppid
    if not chain:
        return None
    for preferred in ("cursor", "windsurf", "vscode", "zed"):
        if preferred in chain:
            return preferred
    return chain[0]


def focused_ide(
    detected: list[RunningIDE],
    *,
    focused_id: str | None = None,
) -> RunningIDE | None:
    """Return the focused IDE from ``detected`` if one can be identified."""
    if not detected:
        return None
    wanted = focused_id if focused_id is not None else detect_focused_ide_id()
    if wanted is None:
        return None
    for ide in detected:
        if ide.id == wanted:
            return ide
    return None


def pick_target(
    detected: list[RunningIDE],
    *,
    prefer: str | None = None,
    focused_id: str | None = None,
) -> RunningIDE | None:
    """Choose which detected IDE should receive the injection.

    Priority:

    1. ``prefer`` (the user's explicit ``--ide`` flag), if running.
    2. ``KORU_AUTOPILOT_IDE`` (when set and not ``auto``), if running.
    3. Integrated-terminal host IDE (``CURSOR_*``, ``VSCODE_PID``, parent walk).
    4. Focused IDE window (X11 active window, when detectable).
    5. The first IDE in :data:`_IDE_SIGNATURES` order.
    """
    if prefer:
        for ide in detected:
            if ide.id == prefer:
                return ide
        return None
    env_prefer = os.environ.get("KORU_AUTOPILOT_IDE", "").strip().lower()
    if env_prefer and env_prefer != "auto":
        for ide in detected:
            if ide.id == env_prefer:
                return ide
    terminal = detect_terminal_host_ide_id()
    if terminal is not None:
        for ide in detected:
            if ide.id == terminal:
                return ide
    focused = focused_ide(detected, focused_id=focused_id)
    if focused is not None:
        return focused
    return detected[0] if detected else None


def is_linux() -> bool:
    return os.name == "posix" and Path("/proc").is_dir()


# R5: cache ``detect_running_ides`` to avoid scanning ``/proc`` on every
# ``drive`` and every ``status``. TTL is short (default 2 s) because the
# scan is mostly used to decide which IDE to drive — a stale answer for
# ~2 s is fine, and the cache pays off when tests / loops call us
# rapidly.
_DETECT_TTL_DEFAULT = 2.0
_detect_cache: tuple[float, list[RunningIDE]] | None = None


def detect_running_ides_cached(*, ttl: float = _DETECT_TTL_DEFAULT) -> list[RunningIDE]:
    """Return :func:`detect_running_ides` results, cached for ``ttl`` seconds.

    Pass ``ttl=0`` to force a fresh scan. The cache is keyed only on
    time, not on arguments, because there are no arguments that affect
    the result.
    """
    global _detect_cache
    now = time.monotonic()
    if ttl > 0 and _detect_cache is not None and (now - _detect_cache[0]) < ttl:
        return _detect_cache[1]
    fresh = detect_running_ides()
    _detect_cache = (now, fresh)
    return fresh


def clear_detect_cache() -> None:
    """Drop the cached scan. Used by tests and ``koru autopilot doctor``."""
    global _detect_cache
    _detect_cache = None


def _has_os_injector_profile(tool_id: str, project: Path | None) -> bool:
    from koruide import os_injector as oi

    if oi.os_injector_env_disabled():
        return False
    return oi.try_load_profile(tool_id, project=project) is not None


def _auto_profile_candidate_ids(detected: list[RunningIDE]) -> list[str]:
    """IDE ids to try for OS-injector profile autodetection (priority order)."""
    terminal = detect_terminal_host_ide_id()
    focused = detect_focused_ide_id()
    target = pick_target(detected, prefer=None)
    order: list[str] = []
    seen: set[str] = set()

    def add(ide_id: str | None) -> None:
        if ide_id and ide_id not in seen:
            seen.add(ide_id)
            order.append(ide_id)

    add(terminal)
    add(focused)
    if target is not None:
        add(target.id)
    for ide in detected:
        add(ide.id)
    return order


def resolve_drive_target(
    ide_arg: str,
    os_profile: str | None,
    *,
    project: Path | None = None,
    has_profile: Callable[[str, Path | None], bool] | None = None,
) -> tuple[str, str, str]:
    """Resolve ``(keyboard_ide, profile_tool_id, selection_reason)`` for ``drive``.

  When ``ide_arg`` is ``auto`` (default), pick the first running/focused IDE that
  has a saved OS-injector profile (``ide-os-injector.json``). Otherwise use
  :func:`pick_target` for keyboard fallback only.
    """
    profile_check = has_profile or _has_os_injector_profile
    stripped_profile = (os_profile or "").strip()
    raw = (ide_arg or "").strip()
    is_auto = not raw or raw.lower() == "auto"
    prefer = None if is_auto else raw
    detected = detect_running_ides()
    target = pick_target(detected, prefer=prefer)

    if stripped_profile:
        keyboard = target.id if target is not None else (prefer or "default")
        return keyboard, stripped_profile, f"os-profile:{stripped_profile}"

    if not is_auto:
        keyboard = prefer or "default"
        if target is None and prefer:
            return keyboard, keyboard, f"explicit-missing:{keyboard}"
        keyboard = target.id if target is not None else keyboard
        if profile_check(keyboard, project):
            return keyboard, keyboard, f"explicit-profile:{keyboard}"
        return keyboard, keyboard, f"explicit:{keyboard}"

    terminal = detect_terminal_host_ide_id()
    running_ids = {ide.id for ide in detected}
    # Integrated terminal: never inject another IDE's calibrated coordinates.
    if terminal and terminal in running_ids:
        if profile_check(terminal, project):
            return terminal, terminal, "auto:terminal-profile"
        return terminal, terminal, "auto:terminal-no-profile"

    for ide_id in _auto_profile_candidate_ids(detected):
        if profile_check(ide_id, project):
            focused = detect_focused_ide_id()
            if ide_id == focused:
                reason = "auto:focused-profile"
            elif target is not None and ide_id == target.id:
                reason = "auto:running-profile"
            else:
                reason = "auto:profile"
            return ide_id, ide_id, reason

    keyboard = target.id if target is not None else "default"
    focused = detect_focused_ide_id()
    if focused and focused != keyboard:
        return keyboard, keyboard, f"auto:focused-no-profile:{focused}"
    return keyboard, keyboard, "auto:no-profile"


__all__ = [
    "RunningIDE",
    "detect_running_ides",
    "detect_running_ides_cached",
    "detect_focused_ide_id",
    "detect_terminal_host_ide_id",
    "clear_detect_cache",
    "focused_ide",
    "pick_target",
    "resolve_drive_target",
    "is_linux",
]
