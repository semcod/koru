"""Install the koru autopilot IDE plugin for the active editor.

The current shipped plugin targets the VS Code extension API, which is shared
by VS Code, Windsurf and Cursor. Installation is best-effort and intentionally
non-privileged: we call the editor's own ``--install-extension`` CLI when the
matching command is available. When the extension is already installed,
``--install-extension <id>`` is run again by default (helps Windsurf/Cursor
recover from a disabled extension); set ``KORU_AUTOPILOT_REASSERT_INSTALL=0``
to skip that step.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from koruide.ide import detect_focused_ide_id, detect_running_ides

SUPPORTED_IDES = frozenset({"windsurf", "vscode", "cursor"})
EXTENSION_ID = "semcod.koru-autopilot-vscode"
SOCKET_SETTING_KEY = "koruAutopilot.socketPath"

_IDE_COMMANDS: dict[str, tuple[str, ...]] = {
    "windsurf": ("windsurf",),
    "cursor": ("cursor",),
    "vscode": ("code", "code-insiders", "codium", "code-oss"),
}


@dataclass(frozen=True)
class PluginInstallResult:
    ide: str
    status: str
    message: str
    command: list[str] | None = None
    vsix: str | None = None
    settings_path: str | None = None
    socket_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "ide": self.ide,
            "status": self.status,
            "message": self.message,
        }
        if self.command is not None:
            out["command"] = self.command
        if self.vsix is not None:
            out["vsix"] = self.vsix
        if self.settings_path is not None:
            out["settings_path"] = self.settings_path
        if self.socket_path is not None:
            out["socket_path"] = self.socket_path
        return out


def _valid_ide(raw: str | None) -> str | None:
    if raw is None:
        return None
    ide = raw.strip().lower()
    return ide if ide in {"auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"} else None


def _ide_from_terminal_env() -> str | None:
    """Best-effort IDE hint from an integrated terminal environment."""
    term_program = os.environ.get("TERM_PROGRAM", "").strip().lower()
    if term_program in ("vscode", "code"):
        return "vscode"
    if term_program in SUPPORTED_IDES:
        return term_program
    if os.environ.get("VSCODE_PID"):
        return "vscode"
    return None


def _terminal_vscode_flavor() -> str | None:
    """Return the VS Code-family CLI/config flavor for the current integrated terminal."""
    hints = " ".join(
        os.environ.get(key, "")
        for key in (
            "VSCODE_NLS_CONFIG",
            "VSCODE_CODE_CACHE_PATH",
            "VSCODE_IPC_HOOK",
            "SNAP_NAME",
        )
    ).lower()
    if "codium" in hints or "vscodium" in hints:
        return "vscodium"
    if os.environ.get("VSCODE_PID"):
        return "vscode"
    return None


def resolve_target_ide(requested: str = "auto") -> str | None:
    """Resolve the IDE that should receive the plugin install."""
    explicit = _valid_ide(requested)
    if explicit and explicit != "auto":
        return explicit

    env_ide = _valid_ide(os.environ.get("KORU_AUTOPILOT_IDE"))
    if env_ide and env_ide != "auto":
        return env_ide

    terminal_ide = _ide_from_terminal_env()
    if terminal_ide is not None:
        return terminal_ide

    focused = detect_focused_ide_id()
    if focused:
        return focused

    detected = detect_running_ides()
    for ide in detected:
        if ide.id in SUPPORTED_IDES:
            return ide.id
    return detected[0].id if detected else None


def resolve_extension_vsix() -> Path | None:
    """Find the bundled VS Code-family extension package."""
    env_path = os.environ.get("KORU_AUTOPILOT_VSIX", "").strip()
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path).expanduser())

    here = Path(__file__).resolve()
    repo_root = here.parents[3] if len(here.parents) > 3 else None
    if repo_root is not None:
        candidates.extend((repo_root / "plugins" / "koru-autopilot-vscode").glob("*.vsix"))

    cwd_plugin = Path.cwd() / "plugins" / "koru-autopilot-vscode"
    candidates.extend(cwd_plugin.glob("*.vsix"))

    candidates = sorted(
        {candidate.resolve() for candidate in candidates if candidate.is_file()},
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _resolve_ide_command(ide: str) -> str | None:
    if ide == "vscode" and _terminal_vscode_flavor() == "vscodium":
        for name in ("codium", "vscodium"):
            resolved = shutil.which(name)
            if resolved:
                return resolved
    for name in _IDE_COMMANDS.get(ide, ()):
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return None


def _settings_path_for_ide(ide: str) -> Path | None:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    dirname = {
        "windsurf": "Windsurf",
        "cursor": "Cursor",
        "vscode": "VSCodium" if _terminal_vscode_flavor() == "vscodium" else "Code",
    }.get(ide)
    if dirname is None:
        return None
    return config_home / dirname / "User" / "settings.json"


def _configure_socket_path(ide: str, socket_path: Path | None) -> Path | None:
    if socket_path is None:
        return None
    settings_path = _settings_path_for_ide(ide)
    if settings_path is None:
        return None
    try:
        if settings_path.exists():
            raw = settings_path.read_text(encoding="utf-8").strip()
            settings = json.loads(raw) if raw else {}
        else:
            settings = {}
        if not isinstance(settings, dict):
            return None
        wanted = str(socket_path.resolve())
        if settings.get(SOCKET_SETTING_KEY) == wanted:
            return settings_path
        settings[SOCKET_SETTING_KEY] = wanted
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(settings, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return settings_path
    except (OSError, json.JSONDecodeError):
        return None


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(cmd: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _env_reassert_extension_install() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_REASSERT_INSTALL", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _extension_is_installed(command: str, runner: Runner) -> bool | None:
    try:
        proc = runner([command, "--list-extensions"])
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    installed = {line.strip().lower() for line in proc.stdout.splitlines()}
    return EXTENSION_ID.lower() in installed


def install_plugin_for_ide(
    *,
    ide: str = "auto",
    dry_run: bool = False,
    socket_path: Path | None = None,
    runner: Runner = _run,
) -> PluginInstallResult:
    """Install the koru plugin for ``ide`` or the currently detected IDE."""
    target = resolve_target_ide(ide) or "auto"
    if target not in SUPPORTED_IDES:
        return PluginInstallResult(
            ide=target,
            status="unsupported",
            message=(
                "no installable koru plugin for this IDE yet (supported: windsurf, cursor, vscode)"
            ),
        )

    command = _resolve_ide_command(target)
    if command is None:
        return PluginInstallResult(
            ide=target,
            status="missing_cli",
            message=f"{target} CLI is not in PATH; cannot install the extension automatically",
        )

    settings_path = None if dry_run else _configure_socket_path(target, socket_path)
    socket_path_str = str(socket_path.resolve()) if socket_path is not None else None

    already_installed = _extension_is_installed(command, runner)
    if already_installed is True:
        last_cmd: list[str] = [command, "--list-extensions"]
        extra = ""
        if not dry_run and _env_reassert_extension_install():
            vsix = resolve_extension_vsix()
            reassert_cmd = (
                [command, "--install-extension", str(vsix), "--force"]
                if vsix is not None
                else [command, "--install-extension", EXTENSION_ID]
            )
            try:
                proc = runner(reassert_cmd, timeout=90.0)
            except (OSError, subprocess.SubprocessError) as exc:
                extra = f"; reassert failed: {exc}"
            else:
                last_cmd = reassert_cmd
                extra = f"; reassert rc={proc.returncode}"
                if proc.returncode != 0:
                    hint = (proc.stderr or proc.stdout or "").strip()
                    if hint:
                        extra += f" ({hint[:240]})"
        return PluginInstallResult(
            ide=target,
            status="already_installed",
            message=(
                f"{EXTENSION_ID} is already installed for {target}{extra}; "
                "reload the IDE window or run `koru: Connect autopilot daemon` if it is already open"
            ),
            command=last_cmd,
            settings_path=str(settings_path) if settings_path is not None else None,
            socket_path=socket_path_str,
        )

    vsix = resolve_extension_vsix()
    if vsix is None:
        return PluginInstallResult(
            ide=target,
            status="missing_vsix",
            message=(
                "cannot find koru autopilot VSIX; set KORU_AUTOPILOT_VSIX "
                "or run from a koru source checkout"
            ),
            settings_path=str(settings_path) if settings_path is not None else None,
            socket_path=socket_path_str,
        )

    cmd = [command, "--install-extension", str(vsix)]
    if dry_run:
        return PluginInstallResult(
            ide=target,
            status="dry_run",
            message="would install koru autopilot IDE extension",
            command=cmd,
            vsix=str(vsix),
            socket_path=socket_path_str,
        )

    try:
        proc = runner(cmd, timeout=120.0)
    except (OSError, subprocess.SubprocessError) as exc:
        return PluginInstallResult(
            ide=target,
            status="failed",
            message=f"failed to run extension installer: {exc}",
            command=cmd,
            vsix=str(vsix),
            settings_path=str(settings_path) if settings_path is not None else None,
            socket_path=socket_path_str,
        )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return PluginInstallResult(
            ide=target,
            status="failed",
            message=detail or f"extension installer exited {proc.returncode}",
            command=cmd,
            vsix=str(vsix),
            settings_path=str(settings_path) if settings_path is not None else None,
            socket_path=socket_path_str,
        )
    return PluginInstallResult(
        ide=target,
        status="installed",
        message=f"installed {EXTENSION_ID}; reload/restart {target} if it is already open",
        command=cmd,
        vsix=str(vsix),
        settings_path=str(settings_path) if settings_path is not None else None,
        socket_path=socket_path_str,
    )


def format_plugin_install_result(result: PluginInstallResult) -> str:
    """Human-friendly single-line status for autonomous startup."""
    suffix = f" ({' '.join(result.command)})" if result.command else ""
    return f"koru autopilot plugin: {result.status} ide={result.ide}: {result.message}{suffix}"


__all__ = [
    "EXTENSION_ID",
    "PluginInstallResult",
    "format_plugin_install_result",
    "install_plugin_for_ide",
    "resolve_extension_vsix",
    "resolve_target_ide",
]
