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
from typing import Literal

TerminalKind = Literal["integrated", "ide_adjacent", "system"]

# Map of IDE id -> (process-name patterns, friendly label).
# Patterns are matched against ``comm`` (basename of the executable)
# as well as the full ``cmdline`` so we catch electron wrappers like
# ``/opt/windsurf/windsurf --type=renderer``.
_IDE_SIGNATURES: dict[str, tuple[tuple[str, ...], str]] = {
    "antigravity": (("antigravity",), "Antigravity"),
    "windsurf": (("windsurf", "devin-desktop"), "Windsurf"),
    "vscode": (("code", "code-insiders"), "VS Code"),
    "vscodium": (("codium", "vscodium", "code-oss"), "VSCodium"),
    "cursor": (("cursor",), "Cursor"),
    "jetbrains": (
        # JetBrains products run as the JVM; the cmdline almost always
        # contains the product name (idea.jar, pycharm, webstorm, ...).
        ("idea", "pycharm", "webstorm", "phpstorm", "goland", "clion", "rubymine"),
        "JetBrains IDE",
    ),
    "zed": (("zed",), "Zed"),
}

_AUTOPILOT_IDE_ORDER = ("auto", *_IDE_SIGNATURES.keys())
_SUPPORTED_AUTOPILOT_IDES = frozenset(_AUTOPILOT_IDE_ORDER)
_VSCODE_EXTENSION_PLUGIN_IDES = frozenset(
    {"antigravity", "windsurf", "vscode", "vscodium", "cursor"}
)
_IDE_ALIASES: dict[str, str] = {
    "code": "vscode",
    "code-insiders": "vscode",
    "vs-code": "vscode",
    "visual-studio-code": "vscode",
    "antigravity": "antigravity",
    "google-antigravity": "antigravity",
    "codium": "vscodium",
    "vscodium": "vscodium",
    "code-oss": "vscodium",
    "code oss": "vscodium",
    "cursor": "cursor",
    "windsurf": "windsurf",
    "devin": "windsurf",
    "devin-desktop": "windsurf",
    "pycharm": "jetbrains",
    "idea": "jetbrains",
    "intellij": "jetbrains",
    "jetbrains": "jetbrains",
    "webstorm": "jetbrains",
    "phpstorm": "jetbrains",
    "goland": "jetbrains",
    "clion": "jetbrains",
    "rubymine": "jetbrains",
    "zed": "zed",
    "zed-editor": "zed",
    "zed-preview": "zed",
}


def normalize_ide_id(raw: str | None) -> str | None:
    """Return Koru's canonical IDE id for common executable/config aliases."""
    token = (raw or "").strip().lower()
    if not token:
        return None
    token = token.rsplit("/", 1)[-1]
    if token.endswith(".desktop"):
        token = token[: -len(".desktop")]
    token = " ".join(token.replace("_", "-").split())
    candidates = (token, token.replace(" - ", "-").replace(" ", "-"))
    for candidate in candidates:
        normalized = _IDE_ALIASES.get(candidate)
        if normalized is not None:
            return normalized
    return token


def supported_autopilot_ide_ids() -> frozenset[str]:
    """Return IDE ids accepted by Koru's autopilot surfaces."""
    return _SUPPORTED_AUTOPILOT_IDES


def autopilot_ide_choices() -> tuple[str, ...]:
    """Return stable CLI choice order for autopilot IDE ids."""
    return _AUTOPILOT_IDE_ORDER


def vscode_extension_plugin_ide_ids() -> frozenset[str]:
    """Return IDE ids supported by the VS Code-extension autopilot plugin."""
    return _VSCODE_EXTENSION_PLUGIN_IDES


def supports_vscode_extension_plugin(ide: str | None) -> bool:
    """True when ``ide`` can run the bundled VS Code-family extension."""
    normalized = normalize_ide_id(ide)
    return bool(normalized and normalized in _VSCODE_EXTENSION_PLUGIN_IDES)


def canonical_autopilot_ide_id(raw: str) -> str:
    """Map lane/instance slugs (e.g. ``cursor-main``) to canonical IDE ids."""
    normalized = normalize_ide_id(raw) or (raw or "").strip().lower()
    if normalized in _SUPPORTED_AUTOPILOT_IDES and normalized != "auto":
        return normalized
    for ide_id in _AUTOPILOT_IDE_ORDER:
        if ide_id == "auto":
            continue
        if normalized == ide_id or normalized.startswith(f"{ide_id}-"):
            return ide_id
    return normalized


@dataclass(frozen=True)
class RunningIDE:
    """A single IDE process discovered on the system."""

    id: str
    label: str
    pid: int
    exe: str

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "label": self.label, "pid": self.pid, "exe": self.exe}


TerminalKind = Literal["integrated", "ide_adjacent", "system"]


@dataclass(frozen=True)
class TerminalHostContext:
    """Resolved host context for the terminal running Koru/Coru."""

    ide: str | None
    source: str
    kind: TerminalKind = "system"

    @property
    def integrated(self) -> bool:
        """True only for IDE integrated terminals (env markers), not external shells."""
        return self.kind == "integrated"


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
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""


def _read_cmdline(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
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


_CANONICAL_COMM: dict[str, tuple[str, ...]] = {
    "antigravity": ("antigravity",),
    "windsurf": ("windsurf",),
    "vscode": ("code", "code-insiders"),
    "vscodium": ("codium", "vscodium", "code-oss"),
    "cursor": ("cursor",),
    "zed": ("zed",),
}


def _score_comm_name(ide_id: str, comm: str) -> int:
    canonical = _CANONICAL_COMM.get(ide_id, ())
    return 100 if comm.lower() in canonical else 0


_PRIMARY_EXE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "antigravity": ("/antigravity",),
    "vscode": ("/code", "/code-insiders"),
    "vscodium": ("/codium", "/vscodium", "/code-oss"),
    "cursor": ("/cursor",),
}


def _score_windsurf_exe_path(exe_l: str) -> int:
    if exe_l.endswith("/windsurf") and "/extensions/" not in exe_l:
        return 120
    if "/extensions/" in exe_l or "/devin/" in exe_l:
        return -80
    return 0


def _score_primary_exe_path(ide_id: str, exe_l: str) -> int:
    suffixes = _PRIMARY_EXE_SUFFIXES.get(ide_id, ())
    return 120 if exe_l.endswith(suffixes) else 0


def _score_exe_path(ide_id: str, exe: str) -> int:
    exe_l = exe.lower()
    if not exe_l:
        return 0
    if ide_id == "windsurf":
        return _score_windsurf_exe_path(exe_l)
    return _score_primary_exe_path(ide_id, exe_l)


def _score_cmdline_flags(cmdline: str) -> int:
    cmd_l = cmdline.lower()
    score = 0
    if "--type=renderer" in cmd_l or "--type=utility" in cmd_l:
        score -= 20
    if "--type=browser" in cmd_l:
        score += 10
    return score


def _candidate_score(ide_id: str, pid: int, comm: str, cmdline: str, exe: str) -> int:
    """Rank multiple process matches for the same IDE.

    Higher score means "more likely the primary IDE process".
    """
    return (
        _score_comm_name(ide_id, comm)
        + _score_exe_path(ide_id, exe)
        + _score_cmdline_flags(cmdline)
        - pid // 100000
    )


def detect_running_ides(*, _pids: list[int] | None = None) -> list[RunningIDE]:
    """Return a deduplicated list of IDEs visible in ``/proc``.

    The ``_pids`` hook is used by tests to inject a fixed snapshot.
    """
    import sys
    if _pids is None and ("pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST")):
        return []
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


def detect_focused_ide_id(
    *, _active_pid: int | None = None, _log: Callable[[str], None] | None = None
) -> str | None:
    """Detect which IDE currently owns desktop focus.

    On X11 this maps active-window PID to one of our known IDE ids.
    On unsupported environments this returns ``None``.
    """
    import sys
    if _active_pid is None and ("pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST")):
        return None
    pid = _active_pid if _active_pid is not None else _active_window_pid_x11()
    if pid is None:
        if _log:
            _log("focused_ide: no active window detected")
        return None
    ide = _ide_id_from_process(pid)
    if _log:
        _log(f"focused_ide: detected={ide or 'none'} (pid={pid})")
    return ide


_VSCODE_FAMILY_ENV_KEYS = (
    "VSCODE_PID",
    "VSCODE_NLS_CONFIG",
    "VSCODE_IPC_HOOK",
    "VSCODE_CODE_CACHE_PATH",
    "VSCODE_CWD",
    "CHROME_DESKTOP",
    "GIO_LAUNCHED_DESKTOP_FILE",
)

# Env values that carry brand identity for a VS Code-family editor. These are
# scanned (in addition to the IPC/cache vars above) because forks encode their
# provider name in the desktop-entry / version string even when ``TERM_PROGRAM``
# is the generic ``vscode``.
_VSCODE_BRAND_ENV_KEYS = (
    "VSCODE_CODE_CACHE_PATH",
    "VSCODE_IPC_HOOK",
    "VSCODE_NLS_CONFIG",
    "VSCODE_CWD",
    "CHROME_DESKTOP",
    "GIO_LAUNCHED_DESKTOP_FILE",
    "TERM_PROGRAM_VERSION",
)

# Provider/brand tokens for VS Code forks, matched BEFORE the generic ``vscode``
# fallback so editors are recognised by their provider name first (Windsurf,
# now shipped as Devin, Cursor, Antigravity, VSCodium...). Add a new fork here
# in ONE place; ``vscode`` is deliberately absent so it stays the last resort.
_VSCODE_FORK_BRAND_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cursor", ("cursor",)),
    ("antigravity", ("antigravity",)),
    ("windsurf", ("windsurf", "devin")),
    ("vscodium", ("vscodium", "codium", "code-oss", "code - oss")),
)


_SOURCE_VSCODE_ENV = "env:VSCODE_*"


def _vscode_fork_brand_from_text(*values: str) -> str | None:
    """Return the provider/brand IDE id for any VS Code fork token in ``values``.

    Generic VS Code is intentionally NOT matched here so callers can treat it
    as the last-resort fallback once brand detection fails.
    """
    blob = " ".join(value for value in values if value).lower()
    if not blob:
        return None
    for ide_id, tokens in _VSCODE_FORK_BRAND_TOKENS:
        if any(token in blob for token in tokens):
            return ide_id
    return None


def _vscode_family_env_present() -> bool:
    return any((os.environ.get(key) or "").strip() for key in _VSCODE_FAMILY_ENV_KEYS)


def _vscode_family_flavor_from_env() -> str | None:
    """Resolve a VS Code-family editor by provider name, else generic vscode."""
    values = [os.environ.get(key, "") for key in _VSCODE_BRAND_ENV_KEYS]
    brand = _vscode_fork_brand_from_text(*values)
    if brand is not None:
        return brand
    if any(value.strip() for value in values):
        return "vscode"
    return None


def _cursor_terminal_env_hint(chrome_ide: str | None) -> bool:
    return chrome_ide == "cursor" or bool(
        os.environ.get("CURSOR_AGENT") or os.environ.get("CURSOR_CLI")
    )


def _windsurf_primary_terminal_env_hint(chrome_ide: str | None) -> bool:
    term_program_version = os.environ.get("TERM_PROGRAM_VERSION", "").strip().lower()
    return (
        "windsurf" in term_program_version
        or bool(os.environ.get("WINDSURF_CASCADE_TERMINAL"))
        or chrome_ide == "windsurf"
        or "windsurf" in os.environ.get("GIO_LAUNCHED_DESKTOP_FILE", "").lower()
    )


def _vscode_family_terminal_hint(term_program: str) -> str | None:
    if term_program in {"vscode", "code"} and _vscode_family_env_present():
        return _vscode_family_flavor_from_env()
    return None


def _jetbrains_terminal_env_hint() -> bool:
    terminal_emulator = os.environ.get("TERMINAL_EMULATOR", "").strip().lower()
    return bool(
        "jetbrains" in terminal_emulator
        or "jediterm" in terminal_emulator
        or os.environ.get("IDEA_INITIAL_DIRECTORY")
        or os.environ.get("PYCHARM_HOSTED")
        or os.environ.get("JETBRAINS_IDE")
    )


def _ide_from_vscode_pid() -> str | None:
    pid = (os.environ.get("VSCODE_PID") or "").strip()
    if not pid.isdigit():
        return None
    exe_path = Path(f"/proc/{pid}/exe")
    try:
        target = str(exe_path.resolve()).lower()
    except OSError:
        return None
    brand = _vscode_fork_brand_from_text(target)
    if brand is not None:
        return brand
    if "code" in target or "vscode" in target:
        return "vscode"
    return None


def _known_terminal_ide_hint(term_ide: str | None, chrome_ide: str | None) -> str | None:
    if term_ide in _IDE_SIGNATURES:
        return term_ide
    if chrome_ide in _IDE_SIGNATURES:
        return chrome_ide
    return None


def _legacy_windsurf_terminal_env_hint(chrome: str) -> bool:
    return bool(os.environ.get("WINDSURF_VERSION")) or (
        bool(os.environ.get("WINDSURF_CSRF_TOKEN")) and "cursor" not in chrome
    )


def _terminal_ide_env_candidates(
    chrome: str,
    chrome_ide: str | None,
    term_program: str,
    term_ide: str | None,
) -> tuple[str | None, ...]:
    return (
        "antigravity"
        if "antigravity" in os.environ.get("GIO_LAUNCHED_DESKTOP_FILE", "").lower()
        else None,
        "cursor" if _cursor_terminal_env_hint(chrome_ide) else None,
        "windsurf" if _windsurf_primary_terminal_env_hint(chrome_ide) else None,
        _vscode_family_terminal_hint(term_program),
        _known_terminal_ide_hint(term_ide, chrome_ide),
        _vscode_family_flavor_from_env() if _vscode_family_env_present() else None,
        "windsurf" if _legacy_windsurf_terminal_env_hint(chrome) else None,
    )


def _vscode_family_terminal_ide(chrome_ide: str | None) -> tuple[str | None, str | None]:
    """Resolve a VS Code-family integrated terminal, provider/brand name first.

    VS Code forks all export ``TERM_PROGRAM=vscode``; this returns plain
    ``vscode`` only as the last-resort fallback after brand detection fails.
    """
    # 1) The actual running editor binary is the most authoritative signal.
    if (os.environ.get("VSCODE_PID") or "").strip():
        via_pid = _ide_from_vscode_pid()
        if via_pid is not None:
            return via_pid, "env:VSCODE_PID.exe"
    # 2) Provider/brand tokens carried in VS Code env values.
    brand = _vscode_fork_brand_from_text(
        *(os.environ.get(key, "") for key in _VSCODE_BRAND_ENV_KEYS)
    )
    if brand is not None:
        return brand, _SOURCE_VSCODE_ENV
    # 3) Brand-specific env markers (Cursor / Windsurf cascade).
    if _cursor_terminal_env_hint(chrome_ide):
        return "cursor", "env:CURSOR_*"
    if _windsurf_primary_terminal_env_hint(chrome_ide):
        return "windsurf", "env:WINDSURF_*"
    # 4) Last resort: a generic VS Code integrated terminal.
    if _vscode_family_env_present():
        return "vscode", _SOURCE_VSCODE_ENV
    return None, None


def _terminal_ide_from_env_with_source() -> tuple[str | None, str | None]:
    chrome = os.environ.get("CHROME_DESKTOP", "").strip().lower()
    chrome_ide = normalize_ide_id(chrome)
    term_program = os.environ.get("TERM_PROGRAM", "").strip().lower()
    term_ide = normalize_ide_id(term_program)

    if _jetbrains_terminal_env_hint():
        return "jetbrains", "env:TERMINAL_EMULATOR"

    if term_program in {"vscode", "code"}:
        ide, source = _vscode_family_terminal_ide(chrome_ide)
        if ide is not None:
            return ide, source

    if "antigravity" in os.environ.get("GIO_LAUNCHED_DESKTOP_FILE", "").lower():
        return "antigravity", "env:GIO_LAUNCHED_DESKTOP_FILE"
    # Explicit TERM_PROGRAM / CHROME_DESKTOP beats stale secondary markers
    # (e.g. WINDSURF_CASCADE_TERMINAL leaking into a Cursor integrated terminal).
    known = _known_terminal_ide_hint(term_ide, chrome_ide)
    if known is not None:
        return known, "env:TERM_PROGRAM/CHROME_DESKTOP"
    if _cursor_terminal_env_hint(chrome_ide):
        return "cursor", "env:CURSOR_*"
    if _windsurf_primary_terminal_env_hint(chrome_ide):
        return "windsurf", "env:WINDSURF_*"
    if _vscode_family_env_present():
        flavor = _vscode_family_flavor_from_env()
        if flavor is not None:
            return flavor, _SOURCE_VSCODE_ENV
    if _legacy_windsurf_terminal_env_hint(chrome):
        return "windsurf", "env:WINDSURF_LEGACY"
    return None, None


def _terminal_ide_from_env() -> str | None:
    ide, _source = _terminal_ide_from_env_with_source()
    return ide


def _terminal_ide_from_parent_chain(start_pid: int) -> str | None:
    pid = start_pid
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
    for preferred in (
        "antigravity",
        "cursor",
        "windsurf",
        "vscodium",
        "vscode",
        "zed",
        "jetbrains",
    ):
        if preferred in chain:
            return preferred
    return chain[0]


def detect_terminal_host_ide_id(
    *, _start_pid: int | None = None, _log: Callable[[str], None] | None = None
) -> str | None:
    """IDE that owns the shell running this command (integrated terminal).

    Uses editor-specific env vars first (works on Wayland), then walks
    ``/proc`` parents. Cursor must be checked before generic ``VSCODE_*``
    because Cursor also sets ``VSCODE_PID``.
    """
    from_env, source = _terminal_ide_from_env_with_source()
    if from_env is not None:
        if _log:
            _log(f"terminal_host_ide: detected={from_env} ({source or 'env'})")
        return from_env
    import sys
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return None
    start = _start_pid if _start_pid is not None else os.getpid()
    ide = _terminal_ide_from_parent_chain(start)
    if _log:
        _log(f"terminal_host_ide: detected={ide or 'none'} (parent chain from pid={start})")
    return ide


def detect_terminal_host_context(
    *, _start_pid: int | None = None, _log: Callable[[str], None] | None = None
) -> TerminalHostContext:
    """Return terminal host IDE plus source and integrated/system classification."""

    from_env, source = _terminal_ide_from_env_with_source()
    if from_env is not None:
        if _log:
            _log(f"terminal_host_context: ide={from_env} source={source or 'env'} kind=integrated")
        return TerminalHostContext(ide=from_env, source=source or "env", kind="integrated")

    start = _start_pid if _start_pid is not None else os.getpid()
    ide = _terminal_ide_from_parent_chain(start)
    if ide is not None:
        if _log:
            _log(
                f"terminal_host_context: ide={ide} "
                f"source=parent_chain(pid={start}) kind=ide_adjacent"
            )
        return TerminalHostContext(
            ide=ide,
            source=f"parent_chain(pid={start})",
            kind="ide_adjacent",
        )

    if _log:
        _log("terminal_host_context: ide=none source=none kind=system")
    return TerminalHostContext(ide=None, source="none", kind="system")


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


def _find_ide_by_id(detected: list[RunningIDE], ide_id: str | None) -> RunningIDE | None:
    if not ide_id:
        return None
    for ide in detected:
        if ide.id == ide_id:
            return ide
    return None


def _env_preferred_ide_id() -> str | None:
    env_prefer = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_IDE"))
    return env_prefer if env_prefer and env_prefer != "auto" else None


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
    3. Focused IDE window (X11 active window, when detectable).
    4. Integrated-terminal host IDE (``CURSOR_*``, ``VSCODE_PID``, parent walk).
    5. The first IDE in :data:`_IDE_SIGNATURES` order.
    """
    prefer = normalize_ide_id(prefer)
    if prefer:
        return _find_ide_by_id(detected, prefer)
    env_preferred = _find_ide_by_id(detected, _env_preferred_ide_id())
    if env_preferred is not None:
        return env_preferred
    focused = focused_ide(detected, focused_id=focused_id)
    if focused is not None:
        return focused
    terminal = _find_ide_by_id(detected, detect_terminal_host_ide_id())
    if terminal is not None:
        return terminal
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
    import gillm.injection.os_injector as oi

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


def _resolve_explicit_drive_target(
    prefer: str,
    target: RunningIDE | None,
    *,
    project: Path | None,
    profile_check: Callable[[str, Path | None], bool],
) -> tuple[str, str, str]:
    keyboard = prefer or "default"
    if target is None and prefer:
        return keyboard, keyboard, f"explicit-missing:{keyboard}"
    keyboard = target.id if target is not None else keyboard
    if profile_check(keyboard, project):
        return keyboard, keyboard, f"explicit-profile:{keyboard}"
    return keyboard, keyboard, f"explicit:{keyboard}"


def _resolve_auto_drive_target(
    detected: list[RunningIDE],
    target: RunningIDE | None,
    *,
    project: Path | None,
    profile_check: Callable[[str, Path | None], bool],
) -> tuple[str, str, str]:
    terminal = detect_terminal_host_ide_id()
    running_ids = {ide.id for ide in detected}
    if terminal and terminal in running_ids:
        suffix = "profile" if profile_check(terminal, project) else "no-profile"
        return terminal, terminal, f"auto:terminal-{suffix}"

    for ide_id in _auto_profile_candidate_ids(detected):
        if not profile_check(ide_id, project):
            continue
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


def _log_drive_target_result(
    result: tuple[str, str, str],
    log: Callable[[str], None] | None,
) -> tuple[str, str, str]:
    if log:
        log(f"resolve_drive_target: {result}")
    return result


def _resolve_profile_override(
    stripped_profile: str,
    target: RunningIDE | None,
    prefer: str | None,
) -> tuple[str, str, str]:
    keyboard = target.id if target is not None else (prefer or "default")
    return keyboard, stripped_profile, f"os-profile:{stripped_profile}"


def resolve_drive_target(
    ide_arg: str,
    os_profile: str | None,
    *,
    project: Path | None = None,
    has_profile: Callable[[str, Path | None], bool] | None = None,
    _log: Callable[[str], None] | None = None,
) -> tuple[str, str, str]:
    """Resolve ``(keyboard_ide, profile_tool_id, selection_reason)`` for ``drive``.

    When ``ide_arg`` is ``auto`` (default), pick the first running/focused IDE that
    has a saved OS-injector profile (``ide-os-injector.json``). Otherwise use
    :func:`pick_target` for keyboard fallback only.
    """
    profile_check = has_profile or _has_os_injector_profile
    stripped_profile = (os_profile or "").strip()
    raw = (ide_arg or "").strip()
    normalized = normalize_ide_id(raw)
    is_auto = not raw or normalized == "auto"
    prefer = None if is_auto else (normalized or raw.lower())
    detected = detect_running_ides()
    target = pick_target(detected, prefer=prefer)

    if stripped_profile:
        result = _resolve_profile_override(stripped_profile, target, prefer)
        return _log_drive_target_result(result, _log)

    if not is_auto:
        result = _resolve_explicit_drive_target(
            prefer or "default", target, project=project, profile_check=profile_check
        )
        return _log_drive_target_result(result, _log)

    result = _resolve_auto_drive_target(
        detected, target, project=project, profile_check=profile_check
    )
    return _log_drive_target_result(result, _log)


__all__ = [
    "RunningIDE",
    "TerminalHostContext",
    "TerminalKind",
    "autopilot_ide_choices",
    "canonical_autopilot_ide_id",
    "detect_running_ides",
    "detect_running_ides_cached",
    "detect_focused_ide_id",
    "detect_terminal_host_context",
    "detect_terminal_host_ide_id",
    "clear_detect_cache",
    "focused_ide",
    "normalize_ide_id",
    "pick_target",
    "resolve_drive_target",
    "is_linux",
    "supported_autopilot_ide_ids",
    "supports_vscode_extension_plugin",
    "vscode_extension_plugin_ide_ids",
]
