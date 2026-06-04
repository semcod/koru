"""Install the koru autopilot IDE plugin for the active editor.

Each IDE (Cursor, VS Code, VSCodium, Windsurf, Antigravity) ships its own
VSIX with a distinct extension ID so a regression in one plugin cannot
leak into another. Installation is best-effort and non-privileged: we call
the editor's ``--install-extension`` CLI when available.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from koruide.ide import (
    detect_focused_ide_id,
    detect_running_ides,
    detect_terminal_host_ide_id,
    normalize_ide_id,
    supported_autopilot_ide_ids,
    vscode_extension_plugin_ide_ids,
)

SUPPORTED_IDES = vscode_extension_plugin_ide_ids()

# Each per-IDE VSIX has its own extension ID. Cursor moved to a
# dedicated ``koru-autopilot-cursor`` package so a regression in the
# Cursor pipeline cannot leak into the umbrella VS Code-family plugin.
# Sibling IDEs (vscode/vscodium/windsurf/antigravity) still share the
# legacy ``koru-autopilot-vscode`` VSIX while they are extracted in
# follow-up iterations.
EXTENSION_ID = "semcod.koru-autopilot-vscode"
_EXTENSION_IDS: dict[str, str] = {
    "cursor": "semcod.koru-autopilot-cursor",
    "vscode": EXTENSION_ID,
    "vscodium": "semcod.koru-autopilot-vscodium",
    "windsurf": "semcod.koru-autopilot-windsurf",
    "antigravity": "semcod.koru-autopilot-antigravity",
}

# Per-IDE plugin source directories under ``plugins/``.
_PLUGIN_DIR_NAMES: dict[str, tuple[str, ...]] = {
    "cursor": ("koru-autopilot-cursor",),
    "vscode": ("koru-autopilot-vscode",),
    "vscodium": ("koru-autopilot-vscodium",),
    "windsurf": ("koru-autopilot-windsurf",),
    "antigravity": ("koru-autopilot-antigravity",),
}

SOCKET_SETTING_KEY = "koruAutopilot.socketPath"
AUTO_CONNECT_SETTING_KEY = "koruAutopilot.autoConnect"

_IDE_COMMANDS: dict[str, tuple[str, ...]] = {
    "antigravity": ("antigravity",),
    "windsurf": ("windsurf",),
    "cursor": ("cursor",),
    "vscode": ("code", "code-insiders"),
    "vscodium": ("codium", "vscodium", "code-oss"),
}


def extension_id_for_ide(ide_id: str | None) -> str:
    """Return the VSIX extension ID for ``ide_id``.

    Unknown IDE falls back to the umbrella VS Code-family ID so legacy
    callers that pass ``None`` keep their previous behaviour.
    """

    if not ide_id:
        return EXTENSION_ID
    return _EXTENSION_IDS.get(ide_id.lower(), EXTENSION_ID)


def plugin_dir_names_for_ide(ide_id: str | None) -> tuple[str, ...]:
    """Return candidate ``plugins/<name>`` directory names for ``ide_id``.

    Cursor returns its dedicated dir first; if the matching VSIX has not
    been built yet (development checkout), callers can fall back to the
    umbrella VS Code plugin dir.
    """

    if not ide_id:
        return _PLUGIN_DIR_NAMES["vscode"]
    return _PLUGIN_DIR_NAMES.get(ide_id.lower(), _PLUGIN_DIR_NAMES["vscode"])


@dataclass(frozen=True)
class PluginInstallResult:
    ide: str
    status: str
    message: str
    command: list[str] | None = None
    vsix: str | None = None
    settings_path: str | None = None
    socket_path: str | None = None
    conflicts_removed: tuple[str, ...] = ()
    stale_extension_dirs_moved: tuple[str, ...] = ()

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
        if self.conflicts_removed:
            out["conflicts_removed"] = list(self.conflicts_removed)
        if self.stale_extension_dirs_moved:
            out["stale_extension_dirs_moved"] = list(self.stale_extension_dirs_moved)
        return out


@dataclass(frozen=True)
class ExtensionMetadataAdapter:
    """IDE-specific adapter for extension metadata location."""

    ide: str
    metadata_path: Path


@dataclass(frozen=True)
class ReassertDecision:
    """Pure reassert policy output used by install/reassert orchestration."""

    should_reassert: bool
    skip_message: str = ""


def _valid_ide(raw: str | None) -> str | None:
    ide = normalize_ide_id(raw)
    return ide if ide in supported_autopilot_ide_ids() else None


def _ide_from_terminal_env() -> str | None:
    """Best-effort IDE hint from an integrated terminal environment."""
    return detect_terminal_host_ide_id()


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
    if "antigravity" in hints:
        return "antigravity"
    if "codium" in hints or "vscodium" in hints:
        return "vscodium"
    if os.environ.get("VSCODE_PID"):
        return "vscode"
    return None


def _repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (
            parent / "plugins" / "koru-autopilot-vscode"
        ).is_dir():
            return parent
    return None


def _plugin_package_version(plugin_dir: Path) -> str | None:
    try:
        data = json.loads((plugin_dir / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return str(version) if version else None


def _plugin_package_name(plugin_dir: Path) -> str | None:
    try:
        data = json.loads((plugin_dir / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    name = data.get("name") if isinstance(data, dict) else None
    return str(name) if name else None


def _versioned_vsix_candidates(plugin_dir: Path) -> list[Path]:
    version = _plugin_package_version(plugin_dir)
    if not version:
        return []
    name = _plugin_package_name(plugin_dir) or "koru-autopilot"
    return [
        plugin_dir / f"{name}-{version}.vsix",
        plugin_dir / f"koru-autopilot-{version}.vsix",
        plugin_dir / f"koru-autopilot-vscode-{version}.vsix",
    ]


def _bundled_vsix_candidates(plugin_dir_name: str = "koru-autopilot-vscode") -> list[Path]:
    try:
        root = resources.files("koru").joinpath("assets", plugin_dir_name)
    except (ModuleNotFoundError, AttributeError):
        return []
    try:
        candidates = [
            Path(str(candidate)) for candidate in root.iterdir() if candidate.name.endswith(".vsix")
        ]
    except (FileNotFoundError, NotADirectoryError, OSError):
        return []
    return sorted(
        [candidate for candidate in candidates if candidate.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _fallback_vsix_candidates(
    anchor: Path | None = None,
    *,
    plugin_dir_names: tuple[str, ...] = ("koru-autopilot-vscode",),
) -> list[Path]:
    candidates: list[Path] = []
    if anchor is not None:
        try:
            candidates.extend(
                sorted(
                    anchor.parent.glob("*.vsix"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                ),
            )
        except OSError:
            pass

    repo_root = _repo_root()
    for dir_name in plugin_dir_names:
        if repo_root is not None:
            plugin_dir = repo_root / "plugins" / dir_name
            try:
                candidates.extend(
                    sorted(
                        plugin_dir.glob("*.vsix"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    ),
                )
            except OSError:
                pass
        cwd_plugin = Path.cwd() / "plugins" / dir_name
        try:
            candidates.extend(
                sorted(
                    cwd_plugin.glob("*.vsix"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                ),
            )
        except OSError:
            pass

    out: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not resolved.is_file() or resolved in seen:
            continue
        seen.add(resolved)
        out.append(resolved)
    return out


def _running_vscode_flavor() -> str | None:
    """Return VS Code-family flavor from the actually running editor process."""
    for ide in detect_running_ides():
        if getattr(ide, "id", None) == "antigravity":
            return "antigravity"
        if getattr(ide, "id", None) != "vscode":
            continue
        exe = str(getattr(ide, "exe", "") or "").lower()
        if "antigravity" in exe:
            return "antigravity"
        if "codium" in exe or "vscodium" in exe:
            return "vscodium"
        if "code" in exe:
            return "vscode"
    return None


def _vscode_flavor() -> str | None:
    return _running_vscode_flavor() or _terminal_vscode_flavor()


def resolve_target_ide(requested: str = "auto") -> str | None:
    """Resolve the IDE that should receive the plugin install."""
    explicit = _valid_ide(requested)
    # Return explicit IDE even if not in SUPPORTED_IDES - let caller handle unsupported
    if explicit and explicit != "auto":
        return explicit

    env_ide = _valid_ide(os.environ.get("KORU_AUTOPILOT_IDE"))
    if env_ide and env_ide != "auto":
        return env_ide

    terminal_ide = normalize_ide_id(_ide_from_terminal_env())
    if terminal_ide in SUPPORTED_IDES:
        return terminal_ide

    focused = normalize_ide_id(detect_focused_ide_id())
    if focused:
        return focused

    detected = detect_running_ides()
    for ide in detected:
        if ide.id in SUPPORTED_IDES:
            return ide.id
    return detected[0].id if detected else None


def resolve_extension_vsix(target_ide: str | None = None) -> Path | None:
    """Find the bundled VSIX package matching ``target_ide``.

    When ``target_ide`` is ``"cursor"`` the dedicated
    ``plugins/koru-autopilot-cursor`` build wins; falling back to the
    umbrella ``koru-autopilot-vscode`` package only when no Cursor VSIX
    is present (development checkout before the first build).
    """
    env_path = os.environ.get("KORU_AUTOPILOT_VSIX", "").strip()
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path).expanduser())

    dir_names = plugin_dir_names_for_ide(target_ide)
    if local_vsix := _first_local_extension_vsix(dir_names):
        return local_vsix

    for dir_name in dir_names:
        candidates.extend(_bundled_vsix_candidates(dir_name))

    return _newest_existing_vsix(candidates)


def _first_local_extension_vsix(dir_names: Sequence[str]) -> Path | None:
    roots = [root for root in (_repo_root(), Path.cwd()) if root is not None]
    for dir_name in dir_names:
        for root in roots:
            if match := _newest_plugin_dir_vsix(root / "plugins" / dir_name):
                return match
    return None


def _newest_plugin_dir_vsix(plugin_dir: Path) -> Path | None:
    for candidate in _versioned_vsix_candidates(plugin_dir):
        if candidate.is_file():
            return candidate.resolve()
    return _newest_existing_vsix(plugin_dir.glob("*.vsix"))


def _newest_existing_vsix(candidates: Iterable[Path]) -> Path | None:
    try:
        matches = sorted(
            {candidate.resolve() for candidate in candidates if candidate.is_file()},
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    return matches[0] if matches else None


def _resolve_ide_command(ide: str) -> str | None:
    try:
        from koru.autopilot.install_plugin_cli import resolve_plugin_editor_bin

        return resolve_plugin_editor_bin(ide)
    except RuntimeError:
        return None
    except Exception:  # noqa: BLE001 - install path may run without full koru tree
        pass
    for name in _IDE_COMMANDS.get(ide, ()):
        resolved = shutil.which(name)
        if not resolved:
            continue
        try:
            from koru.autopilot.install_plugin_cli import _editor_bin_usable_for_cli_install

            if _editor_bin_usable_for_cli_install(resolved):
                return resolved
        except Exception:  # noqa: BLE001
            return resolved
    return None


def _settings_path_for_ide(ide: str) -> Path | None:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    dirname = {
        "antigravity": "Antigravity",
        "windsurf": "Windsurf",
        "cursor": "Cursor",
        "vscode": "Code",
        "vscodium": "VSCodium",
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
        changed = False
        if settings.get(SOCKET_SETTING_KEY) != wanted:
            settings[SOCKET_SETTING_KEY] = wanted
            changed = True
        if settings.get(AUTO_CONNECT_SETTING_KEY) is not True:
            settings[AUTO_CONNECT_SETTING_KEY] = True
            changed = True
        if not changed:
            return settings_path
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(settings, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return settings_path
    except (OSError, json.JSONDecodeError):
        return None


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(
    cmd: list[str],
    *,
    timeout: float = 30.0,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )


def _env_reassert_extension_install() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_REASSERT_INSTALL", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _env_force_reassert_extension_install() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_FORCE_REASSERT_INSTALL", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_build_local_vsix() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_BUILD_LOCAL_VSIX", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _local_plugin_dir(target_ide: str | None) -> Path | None:
    root = _repo_root()
    if root is None:
        return None
    for dir_name in plugin_dir_names_for_ide(target_ide):
        plugin_dir = root / "plugins" / dir_name
        if (plugin_dir / "package.json").is_file():
            return plugin_dir
    return None


def _package_build_sha(package_json: Path) -> str | None:
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    build_info = data.get("koruAutopilotBuild") if isinstance(data, dict) else None
    if isinstance(build_info, dict) and isinstance(build_info.get("sha"), str):
        return build_info["sha"]
    return None


def _vsix_build_sha(vsix: Path) -> str | None:
    try:
        with zipfile.ZipFile(vsix) as archive:
            with archive.open("extension/package.json") as package_file:
                data = json.loads(package_file.read().decode("utf-8"))
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError):
        return None
    build_info = data.get("koruAutopilotBuild") if isinstance(data, dict) else None
    if isinstance(build_info, dict) and isinstance(build_info.get("sha"), str):
        return build_info["sha"]
    return None


def _latest_plugin_source_mtime(plugin_dir: Path) -> float:
    repo_root = _repo_root()
    roots = [plugin_dir / "src", plugin_dir / "package.json", plugin_dir / "tsconfig.json"]
    if repo_root is not None:
        roots.append(repo_root / "plugins" / "koru-autopilot-shared" / "src")
    latest = 0.0
    for root in roots:
        if root.is_file():
            latest = max(latest, root.stat().st_mtime)
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {"node_modules", "out", ".git"} for part in path.parts):
                continue
            latest = max(latest, path.stat().st_mtime)
    return latest


def _local_vsix_needs_build(plugin_dir: Path, vsix: Path | None) -> bool:
    if vsix is None or not vsix.is_file():
        return True
    expected_build = _package_build_sha(plugin_dir / "package.json")
    vsix_build = _vsix_build_sha(vsix)
    if expected_build and vsix_build != expected_build:
        return True
    try:
        return _latest_plugin_source_mtime(plugin_dir) > vsix.stat().st_mtime
    except OSError:
        return True


def _ensure_local_extension_vsix(
    target_ide: str,
    *,
    dry_run: bool,
    runner: Runner,
) -> None:
    if dry_run or not _env_reassert_extension_install() or not _env_build_local_vsix():
        return
    plugin_dir = _local_plugin_dir(target_ide)
    if plugin_dir is None or not (plugin_dir / "package.json").is_file():
        return
    existing = _newest_plugin_dir_vsix(plugin_dir)
    resolved = resolve_extension_vsix(target_ide)
    if existing is not None and resolved is not None:
        try:
            if not resolved.resolve().is_relative_to(plugin_dir.resolve()):
                return
        except OSError:
            return
    if not _local_vsix_needs_build(plugin_dir, existing):
        return
    try:
        proc = runner(["npm", "run", "package"], timeout=180.0, cwd=str(plugin_dir))
    except (OSError, subprocess.SubprocessError):
        return
    if proc.returncode != 0:
        return


def _extension_is_installed(
    command: str,
    runner: Runner,
    *,
    extension_id: str = EXTENSION_ID,
) -> bool | None:
    try:
        proc = runner([command, "--list-extensions"])
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    installed = {line.strip().lower() for line in proc.stdout.splitlines()}
    return extension_id.lower() in installed


def _installed_extension_ids(command: str, runner: Runner) -> set[str] | None:
    try:
        proc = runner([command, "--list-extensions"])
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return {line.strip().lower() for line in proc.stdout.splitlines() if line.strip()}


def _conflicting_extension_ids(target_ide: str) -> tuple[str, ...]:
    expected = extension_id_for_ide(target_ide).lower()
    candidates = sorted({ext_id.lower() for ext_id in _EXTENSION_IDS.values()})
    return tuple(ext_id for ext_id in candidates if ext_id != expected)


def _remove_conflicting_extensions(
    command: str,
    runner: Runner,
    *,
    target_ide: str,
    dry_run: bool,
) -> tuple[str, ...]:
    installed = _installed_extension_ids(command, runner)
    if not installed:
        return ()
    conflicts = tuple(
        ext_id for ext_id in _conflicting_extension_ids(target_ide) if ext_id in installed
    )
    if dry_run:
        return conflicts
    removed: list[str] = []
    for ext_id in conflicts:
        try:
            proc = runner([command, "--uninstall-extension", ext_id], timeout=120.0)
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            removed.append(ext_id)
    return tuple(removed)


def _extensions_metadata_path_for_ide(ide: str) -> Path | None:
    return _metadata_adapter_for_ide(ide).metadata_path if _metadata_adapter_for_ide(ide) else None


def _metadata_adapter_for_ide(ide: str) -> ExtensionMetadataAdapter | None:
    relative_paths = {
        "antigravity": Path(".antigravity") / "extensions" / "extensions.json",
        "cursor": Path(".cursor") / "extensions" / "extensions.json",
        "vscode": Path(".vscode") / "extensions" / "extensions.json",
        "vscodium": Path(".vscode-oss") / "extensions" / "extensions.json",
        "windsurf": Path(".windsurf") / "extensions" / "extensions.json",
    }
    relative = relative_paths.get(ide)
    if relative is None:
        return None
    return ExtensionMetadataAdapter(ide=ide, metadata_path=Path.home() / relative)


def _active_extension_location_from_item(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    relative = item.get("relativeLocation")
    if isinstance(relative, str) and relative:
        return relative.lower()
    location = item.get("location")
    if isinstance(location, dict):
        raw_path = location.get("path") or location.get("fsPath")
        if isinstance(raw_path, str) and raw_path:
            return Path(raw_path).name.lower()
    return None


def _active_extension_locations(metadata_path: Path) -> set[str]:
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(data, list):
        return set()
    return {
        loc for item in data
        if (loc := _active_extension_location_from_item(item)) is not None
    }


def _installed_extension_build_sha(target_ide: str) -> str | None:
    """Return the ``koruAutopilotBuild.sha`` of the currently installed extension.

    Reads ``~/<ide>/extensions/extensions.json`` to find the active extension
    directory, then reads its ``package.json`` to extract the build SHA.
    Returns ``None`` when the installed SHA cannot be determined.
    """
    metadata_path = _extensions_metadata_path_for_ide(target_ide)
    if metadata_path is None or not metadata_path.is_file():
        return None
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, list):
        return None
    ext_id = extension_id_for_ide(target_ide).lower()
    extensions_root = metadata_path.parent
    for item in data:
        if not isinstance(item, dict):
            continue
        # Match by extension ID recorded in the metadata.
        item_id = str(item.get("identifier", {}).get("id", "") or "").lower()
        if item_id != ext_id:
            continue
        # Resolve the installation directory.
        rel_loc = item.get("relativeLocation")
        if isinstance(rel_loc, str) and rel_loc:
            ext_dir = extensions_root / rel_loc
        else:
            location = item.get("location") if isinstance(item, dict) else None
            raw_path = None
            if isinstance(location, dict):
                raw_path = location.get("path") or location.get("fsPath")
            if not isinstance(raw_path, str) or not raw_path:
                continue
            ext_dir = Path(raw_path)
        pkg = ext_dir / "package.json"
        if not pkg.is_file():
            continue
        try:
            pkg_data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        build_info = pkg_data.get("koruAutopilotBuild") if isinstance(pkg_data, dict) else None
        if isinstance(build_info, dict) and isinstance(build_info.get("sha"), str):
            return build_info["sha"] or None
    return None


def _move_path_aside(path: Path, disabled_root: Path) -> Path:
    disabled_root.mkdir(parents=True, exist_ok=True)
    target = disabled_root / path.name
    if not target.exists():
        shutil.move(str(path), str(target))
        return target
    for index in range(1, 100):
        candidate = disabled_root / f"{path.name}.stale{index}"
        if not candidate.exists():
            shutil.move(str(path), str(candidate))
            return candidate
    raise OSError(f"cannot find free stale-extension target for {path}")


def _prune_stale_koru_extension_dirs(
    *,
    target_ide: str,
    dry_run: bool,
) -> tuple[str, ...]:
    metadata_path = _extensions_metadata_path_for_ide(target_ide)
    if metadata_path is None:
        return ()
    extensions_root = metadata_path.parent
    if not extensions_root.is_dir():
        return ()

    active_locations = _active_extension_locations(metadata_path)
    koru_ids = {extension_id_for_ide(target_ide).lower()}
    koru_ids.update(_conflicting_extension_ids(target_ide))
    stale_dirs = sorted(
        child
        for child in extensions_root.iterdir()
        if child.is_dir()
        and child.name.lower() not in active_locations
        and any(child.name.lower().startswith(f"{ext_id}-") for ext_id in koru_ids)
    )
    if dry_run:
        return tuple(child.name for child in stale_dirs)

    disabled_root = extensions_root.parent / "extensions-disabled"
    moved: list[str] = []
    for child in stale_dirs:
        try:
            target = _move_path_aside(child, disabled_root)
        except OSError:
            continue
        moved.append(str(target))
    return tuple(moved)


def _parse_extension_version(
    output: str,
    *,
    extension_id: str = EXTENSION_ID,
) -> str | None:
    prefix = f"{extension_id.lower()}@"
    for line in output.splitlines():
        item = line.strip()
        if item.lower().startswith(prefix):
            version = item[len(prefix) :]
            return version or None
    return None


def installed_extension_version_for_ide(
    ide: str = "auto",
    *,
    runner: Runner = _run,
) -> str | None:
    """Return installed koru extension version for a VS Code-family IDE."""
    target = resolve_target_ide(ide) or "auto"
    if target not in SUPPORTED_IDES:
        return None
    command = _resolve_ide_command(target)
    if command is None:
        return None
    try:
        proc = runner([command, "--list-extensions", "--show-versions"])
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return _parse_extension_version(
        proc.stdout, extension_id=extension_id_for_ide(target)
    )


def _reassert_extension_extra(
    command: str,
    *,
    dry_run: bool,
    runner: Runner,
    target_ide: str | None = None,
) -> tuple[list[str], str]:
    last_cmd: list[str] = [command, "--list-extensions"]
    reassert_enabled = _env_reassert_extension_install()
    vsix = resolve_extension_vsix(target_ide)
    ext_id = extension_id_for_ide(target_ide)
    # Skip --install-extension --force when the already-installed extension
    # has the same build SHA as the VSIX we would install.  Running
    # --install-extension triggers an IDE restart that reopens its previous
    # workspace, so we must not do it unnecessarily.
    installed_sha = _installed_extension_build_sha(target_ide or "")
    expected_sha = _vsix_build_sha(vsix) if vsix is not None else None
    decision = _decide_reassert_policy(
        dry_run=dry_run,
        reassert_enabled=reassert_enabled,
        force_reassert=_env_force_reassert_extension_install(),
        installed_sha=installed_sha,
        expected_sha=expected_sha,
    )
    if not decision.should_reassert:
        return last_cmd, decision.skip_message
    reassert_cmd = (
        [command, "--install-extension", str(vsix), "--force"]
        if vsix is not None
        else [command, "--install-extension", ext_id]
    )
    proc, error = _run_reassert_command(runner, reassert_cmd)
    if error:
        return last_cmd, error
    assert proc is not None
    retry = _maybe_retry_missing_vsix(
        command,
        runner=runner,
        target_ide=target_ide,
        vsix=vsix,
        proc=proc,
    )
    if retry is not None:
        retry_cmd, retry_proc, retry_error = retry
        if retry_error:
            return last_cmd, retry_error
        return retry_cmd, _reassert_extra(retry_proc, fallback=True)
    return reassert_cmd, _reassert_extra(proc)


def _decide_reassert_policy(
    *,
    dry_run: bool,
    reassert_enabled: bool,
    force_reassert: bool = False,
    installed_sha: str | None,
    expected_sha: str | None,
) -> ReassertDecision:
    if dry_run or not reassert_enabled:
        return ReassertDecision(should_reassert=False)
    if force_reassert:
        return ReassertDecision(should_reassert=True)
    if installed_sha and expected_sha and installed_sha == expected_sha:
        return ReassertDecision(
            should_reassert=False,
            skip_message="; build sha match — reassert skipped",
        )
    return ReassertDecision(should_reassert=True)


def _run_reassert_command(
    runner: Runner,
    command: list[str],
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    try:
        return runner(command, timeout=90.0), ""
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"; reassert failed: {exc}"


def _maybe_retry_missing_vsix(
    command: str,
    *,
    runner: Runner,
    target_ide: str | None,
    vsix: Path | None,
    proc: subprocess.CompletedProcess[str],
) -> tuple[list[str], subprocess.CompletedProcess[str], str] | None:
    if not _should_retry_missing_vsix(vsix, proc):
        return None
    for fallback in _fallback_vsix_candidates(
        vsix, plugin_dir_names=plugin_dir_names_for_ide(target_ide)
    ):
        if fallback == vsix:
            continue
        retry_cmd = [command, "--install-extension", str(fallback), "--force"]
        retry, error = _run_reassert_command(runner, retry_cmd)
        if error:
            return retry_cmd, proc, error
        assert retry is not None
        return retry_cmd, retry, ""
    return None


def _should_retry_missing_vsix(
    vsix: Path | None,
    proc: subprocess.CompletedProcess[str],
) -> bool:
    if proc.returncode == 0 or vsix is None or vsix.is_file():
        return False
    detail = (proc.stderr or proc.stdout or "").lower()
    return "no such file" in detail or "enoent" in detail


def _reassert_extra(proc: subprocess.CompletedProcess[str], *, fallback: bool = False) -> str:
    prefix = "; reassert fallback rc=" if fallback else "; reassert rc="
    extra = f"{prefix}{proc.returncode}"
    if proc.returncode == 0:
        return extra
    hint = (proc.stderr or proc.stdout or "").strip()
    return extra + (f" ({hint[:240]})" if hint else "")


def _result_already_installed(
    target: str,
    command: str,
    *,
    dry_run: bool,
    runner: Runner,
    settings_path: Path | None,
    socket_path_str: str | None,
    conflicts_removed: tuple[str, ...] = (),
    stale_extension_dirs_moved: tuple[str, ...] = (),
) -> PluginInstallResult:
    last_cmd, extra = _reassert_extension_extra(
        command, dry_run=dry_run, runner=runner, target_ide=target
    )
    ext_id = extension_id_for_ide(target)
    return PluginInstallResult(
        ide=target,
        status="already_installed",
        message=(
            f"{ext_id} is already installed for {target}{extra}; "
            + (
                f"removed conflicting extensions: {', '.join(conflicts_removed)}; "
                if conflicts_removed
                else ""
            )
            + (
                "moved stale extension dirs: "
                f"{', '.join(stale_extension_dirs_moved)}; "
                if stale_extension_dirs_moved
                else ""
            )
            +
            "if the IDE was already open during install/reassert, run "
            "`Developer: Reload Window` (or restart it), then run "
            "`koru: Connect autopilot daemon`"
        ),
        command=last_cmd,
        settings_path=str(settings_path) if settings_path is not None else None,
        socket_path=socket_path_str,
        conflicts_removed=conflicts_removed,
        stale_extension_dirs_moved=stale_extension_dirs_moved,
    )


def _install_extension_vsix(
    target: str,
    command: str,
    vsix: Path,
    *,
    dry_run: bool,
    runner: Runner,
    settings_path: Path | None,
    socket_path_str: str | None,
    conflicts_removed: tuple[str, ...] = (),
    stale_extension_dirs_moved: tuple[str, ...] = (),
) -> PluginInstallResult:
    cmd = [command, "--install-extension", str(vsix)]
    if dry_run:
        return PluginInstallResult(
            ide=target,
            status="dry_run",
            message="would install koru autopilot IDE extension",
            command=cmd,
            vsix=str(vsix),
            socket_path=socket_path_str,
            conflicts_removed=conflicts_removed,
            stale_extension_dirs_moved=stale_extension_dirs_moved,
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
        message=(
            f"installed {extension_id_for_ide(target)}; if {target} is already open, run "
            + (
                f"removed conflicting extensions: {', '.join(conflicts_removed)}; "
                if conflicts_removed
                else ""
            )
            + (
                "moved stale extension dirs: "
                f"{', '.join(stale_extension_dirs_moved)}; "
                if stale_extension_dirs_moved
                else ""
            )
            +
            "`Developer: Reload Window` or restart it so the extension host scans the VSIX"
        ),
        command=cmd,
        vsix=str(vsix),
        settings_path=str(settings_path) if settings_path is not None else None,
        socket_path=socket_path_str,
        conflicts_removed=conflicts_removed,
        stale_extension_dirs_moved=stale_extension_dirs_moved,
    )


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
                "no installable koru plugin for this IDE yet "
                "(supported: windsurf, cursor, vscode, vscodium)"
            ),
        )

    command = _resolve_ide_command(target)
    if command is None:
        return PluginInstallResult(
            ide=target,
            status="missing_cli",
            message=f"{target} CLI is not in PATH; cannot install the extension automatically",
        )

    _ensure_local_extension_vsix(target, dry_run=dry_run, runner=runner)

    settings_path = None if dry_run else _configure_socket_path(target, socket_path)
    socket_path_str = str(socket_path.resolve()) if socket_path is not None else None
    conflicts_removed = _remove_conflicting_extensions(
        command,
        runner,
        target_ide=target,
        dry_run=dry_run,
    )
    stale_extension_dirs_moved = _prune_stale_koru_extension_dirs(
        target_ide=target,
        dry_run=dry_run,
    )

    if _extension_is_installed(
        command, runner, extension_id=extension_id_for_ide(target)
    ) is True:
        return _result_already_installed(
            target,
            command,
            dry_run=dry_run,
            runner=runner,
            settings_path=settings_path,
            socket_path_str=socket_path_str,
            conflicts_removed=conflicts_removed,
            stale_extension_dirs_moved=stale_extension_dirs_moved,
        )

    vsix = resolve_extension_vsix(target)
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
            stale_extension_dirs_moved=stale_extension_dirs_moved,
        )

    return _install_extension_vsix(
        target,
        command,
        vsix,
        dry_run=dry_run,
        runner=runner,
        settings_path=settings_path,
        socket_path_str=socket_path_str,
        conflicts_removed=conflicts_removed,
        stale_extension_dirs_moved=stale_extension_dirs_moved,
    )


def format_plugin_install_result(result: PluginInstallResult) -> str:
    """Human-friendly single-line status for autonomous startup."""
    suffix = f" ({' '.join(result.command)})" if result.command else ""
    return f"koru autopilot plugin: {result.status} ide={result.ide}: {result.message}{suffix}"


__all__ = [
    "EXTENSION_ID",
    "PluginInstallResult",
    "extension_id_for_ide",
    "format_plugin_install_result",
    "install_plugin_for_ide",
    "installed_extension_version_for_ide",
    "plugin_dir_names_for_ide",
    "resolve_extension_vsix",
    "resolve_target_ide",
]
