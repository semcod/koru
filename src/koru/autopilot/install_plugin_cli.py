"""CLI actions for autopilot plugin installation commands."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from koru.autopilot.ide import (
    detect_focused_ide_id,
    detect_running_ides,
    detect_terminal_host_ide_id,
    normalize_ide_id,
)

PLUGIN_IDE_CLI: dict[str, tuple[str, ...]] = {
    "antigravity": ("antigravity",),
    "windsurf": ("windsurf",),
    "cursor": ("cursor",),
    "vscode": ("code", "code-insiders"),
    "vscodium": ("vscodium", "codium", "code-oss"),
}

PLUGIN_INSTALL_IDE_ALIASES: dict[str, str] = {
    "pycharm": "jetbrains",
}

PLUGIN_INSTALL_IDES = frozenset(
    {"antigravity", "windsurf", "vscode", "vscodium", "cursor", "jetbrains"}
)


def plugin_repo_dir(ide: str | None = None) -> Path:
    """Return the plugin source directory for ``ide``.

    Cursor has its own ``plugins/koru-autopilot-cursor`` package;
    every other VS Code-family IDE still shares the legacy umbrella
    ``plugins/koru-autopilot-vscode`` until it is extracted into its
    own VSIX.
    """

    from koruide.plugin_installer import plugin_dir_names_for_ide

    repo = Path(__file__).resolve().parents[3] / "plugins"
    for dir_name in plugin_dir_names_for_ide(ide):
        candidate = repo / dir_name
        if candidate.is_dir():
            return candidate
    return repo / "koru-autopilot-vscode"


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


def _versioned_plugin_vsix_candidates(plugin_dir: Path) -> list[Path]:
    version = _plugin_package_version(plugin_dir)
    if not version:
        return []
    name = _plugin_package_name(plugin_dir) or "koru-autopilot"
    return [
        plugin_dir / f"{name}-{version}.vsix",
        plugin_dir / f"koru-autopilot-{version}.vsix",
        plugin_dir / f"koru-autopilot-vscode-{version}.vsix",
    ]


def bundled_plugin_vsix_candidates(ide: str | None = None) -> list[Path]:
    from koruide.plugin_installer import plugin_dir_names_for_ide

    out: list[Path] = []
    for dir_name in plugin_dir_names_for_ide(ide):
        try:
            root = resources.files("koru").joinpath("assets", dir_name)
        except (ModuleNotFoundError, AttributeError):
            continue
        try:
            out.extend(
                Path(str(candidate)) for candidate in root.iterdir()
                if candidate.name.endswith(".vsix")
            )
        except (FileNotFoundError, NotADirectoryError, OSError):
            continue
    files = [candidate for candidate in out if candidate.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def jetbrains_plugin_repo_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "plugins" / "koru-autopilot-jetbrains"


def resolve_plugin_vsix_path(vsix: Path | None, ide: str | None = None) -> Path:
    if vsix is not None:
        candidate = vsix.expanduser().resolve()
        if not candidate.is_file():
            raise RuntimeError(f"vsix not found: {candidate}")
        return candidate
    plugin_dir = plugin_repo_dir(ide)
    for candidate in _versioned_plugin_vsix_candidates(plugin_dir):
        if candidate.is_file():
            return candidate.resolve()
    matches = sorted(
        plugin_dir.glob("*.vsix"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        for candidate in bundled_plugin_vsix_candidates(ide):
            if candidate.is_file():
                return candidate.resolve()
        raise RuntimeError(
            f"no packaged .vsix found under {plugin_dir}; "
            f"build one with: `cd {plugin_dir} && npm install && npm run package`",
        )
    return matches[0]


def resolve_jetbrains_plugin_dir(raw_dir: Path | None) -> Path:
    plugin_dir = (raw_dir or jetbrains_plugin_repo_dir()).expanduser().resolve()
    if not plugin_dir.is_dir():
        raise RuntimeError(f"jetbrains plugin dir not found: {plugin_dir}")
    if not (plugin_dir / "build.gradle.kts").is_file():
        raise RuntimeError(f"missing build.gradle.kts in jetbrains plugin dir: {plugin_dir}")
    return plugin_dir


def resolve_gradle_bin(raw: str) -> str:
    candidate = (raw or "gradle").strip()
    if not candidate:
        candidate = "gradle"
    candidate_path = Path(candidate).expanduser()
    if candidate_path.is_file() and os.access(candidate_path, os.X_OK):
        return str(candidate_path.resolve())
    resolved = shutil.which(candidate)
    if resolved:
        return resolved
    raise RuntimeError(f"could not find Gradle executable in PATH: {candidate}")


def resolve_jetbrains_plugin_artifact(plugin_dir: Path) -> Path:
    dist_dir = plugin_dir / "build" / "distributions"
    matches = sorted(
        dist_dir.glob("*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise RuntimeError(
            "no JetBrains plugin ZIP found under build/distributions; "
            "run `gradle buildPlugin` in plugins/koru-autopilot-jetbrains"
        )
    return matches[0]


def ide_from_terminal_env() -> str | None:
    if os.environ.get("PYCHARM_HOSTED"):
        return "jetbrains"
    detected = normalize_ide_id(detect_terminal_host_ide_id())
    if detected:
        return detected
    term_program = os.environ.get("TERM_PROGRAM", "").strip().lower()
    normalized = normalize_ide_id(term_program)
    if normalized:
        return normalized
    if os.environ.get("VSCODE_PID"):
        return "vscode"
    return None


def resolve_plugin_target_ide(raw_ide: str) -> str:
    requested = PLUGIN_INSTALL_IDE_ALIASES.get(raw_ide, normalize_ide_id(raw_ide) or raw_ide)
    if requested != "auto":
        return requested
    env_guess = ide_from_terminal_env()
    if env_guess:
        return env_guess
    focused = normalize_ide_id(detect_focused_ide_id())
    if focused:
        return str(focused)
    detected = [ide for ide in detect_running_ides() if ide.id in PLUGIN_INSTALL_IDES]
    if len(detected) == 1:
        return detected[0].id
    if not detected:
        raise RuntimeError(
            "could not detect running editor for plugin install; pass --ide "
            "antigravity|windsurf|vscode|vscodium|cursor|jetbrains|pycharm|zed",
        )
    ids = ", ".join(ide.id for ide in detected)
    raise RuntimeError(
        "multiple supported IDEs detected with no clear active one "
        f"({ids}); pass --ide antigravity|windsurf|vscode|vscodium|cursor|jetbrains|pycharm|zed",
    )


def resolve_plugin_editor_bin(ide: str) -> str:
    if ide == "jetbrains":
        raise RuntimeError(
            "jetbrains plugin install is not supported via `koru autopilot install-plugin`; "
            "build/install the IntelliJ plugin from `plugins/koru-autopilot-jetbrains` "
            "(see README.md)"
        )
    if ide == "zed":
        raise RuntimeError(
            "zed does not support the VS Code VSIX plugin; use `koru init-ide --ide zed` "
            "for MCP and `koru autopilot drive --ide zed` for keyboard/OS injection"
        )
    if ide not in PLUGIN_IDE_CLI:
        raise RuntimeError(f"unsupported editor for plugin install: {ide}")
    for candidate in PLUGIN_IDE_CLI[ide]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    choices = "|".join(PLUGIN_IDE_CLI[ide])
    raise RuntimeError(f"could not find editor CLI in PATH for {ide} (tried: {choices})")


def render_install_plugin_dry_run(
    ide: str,
    editor_bin: str,
    vsix_path: Path,
    cmd: list[str],
    output_format: str,
) -> None:
    payload = {
        "ide": ide,
        "editor": editor_bin,
        "vsix": str(vsix_path),
        "command": cmd,
        "dry_run": True,
        "ok": True,
    }
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("koru autopilot install-plugin: dry-run")
        print(f"  {' '.join(cmd)}")


def render_install_plugin_result(
    ide: str,
    editor_bin: str,
    cmd: list[str],
    ok: bool,
    stdout: str,
    stderr: str,
    output_format: str,
) -> None:
    payload = {
        "ide": ide,
        "editor": editor_bin,
        "command": cmd,
        "ok": ok,
        "returncode": 0 if ok else 1,
        "stdout": stdout,
        "stderr": stderr,
    }
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if ok:
            print(f"koru autopilot install-plugin: installed for {ide} via {editor_bin}")
        else:
            print(f"koru autopilot install-plugin: install failed for {ide}", file=sys.stderr)
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)


def action_install_plugin(
    args: argparse.Namespace,
    *,
    resolve_target_ide: Callable[[str], str] = resolve_plugin_target_ide,
    resolve_editor_bin: Callable[[str], str] = resolve_plugin_editor_bin,
    resolve_vsix_path: Callable[..., Path] = resolve_plugin_vsix_path,
) -> int:
    try:
        ide = resolve_target_ide(args.ide)
        editor_bin = resolve_editor_bin(ide)
        # Newer ``resolve_plugin_vsix_path`` accepts ``ide``; legacy
        # callers (test doubles) still implement ``(vsix)`` only —
        # fall back gracefully so this CLI keeps working in both modes.
        try:
            vsix_path = resolve_vsix_path(args.vsix, ide=ide)
        except TypeError:
            vsix_path = resolve_vsix_path(args.vsix)
    except RuntimeError as exc:
        print(f"koru autopilot install-plugin: {exc}", file=sys.stderr)
        return 1

    cmd = [editor_bin, "--install-extension", str(vsix_path)]
    if args.force:
        cmd.append("--force")

    if args.dry_run:
        render_install_plugin_dry_run(ide, editor_bin, vsix_path, cmd, args.output_format)
        return 0

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        print(f"koru autopilot install-plugin: {exc}", file=sys.stderr)
        return 1

    ok = proc.returncode == 0
    render_install_plugin_result(
        ide,
        editor_bin,
        cmd,
        ok,
        proc.stdout.strip(),
        proc.stderr.strip(),
        args.output_format,
    )
    return 0 if ok else 1


def _render_jetbrains_failure(
    *,
    plugin_dir: Path,
    cmd: list[str],
    returncode: int,
    stdout: str,
    stderr: str,
    output_format: str,
) -> None:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "ok": False,
                    "plugin_dir": str(plugin_dir),
                    "command": cmd,
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    print("koru autopilot install-plugin-jetbrains: build failed", file=sys.stderr)
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)


def _render_jetbrains_success(
    *,
    plugin_dir: Path,
    cmd: list[str],
    artifact: Path,
    stdout: str,
    stderr: str,
    output_format: str,
) -> None:
    hint = (
        "Install in PyCharm/IntelliJ: Settings -> Plugins -> gear icon -> "
        "Install Plugin from Disk..."
    )
    if output_format == "json":
        print(
            json.dumps(
                {
                    "ok": True,
                    "plugin_dir": str(plugin_dir),
                    "command": cmd,
                    "artifact": str(artifact),
                    "manual_install_hint": hint,
                    "stdout": stdout,
                    "stderr": stderr,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    print("koru autopilot install-plugin-jetbrains: built plugin package")
    print(f"  artifact: {artifact}")
    print(f"  {hint}")
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)


def action_install_plugin_jetbrains(
    args: argparse.Namespace,
    *,
    resolve_plugin_dir: Callable[[Path | None], Path] = resolve_jetbrains_plugin_dir,
    resolve_gradle: Callable[[str], str] = resolve_gradle_bin,
    resolve_artifact: Callable[[Path], Path] = resolve_jetbrains_plugin_artifact,
) -> int:
    try:
        plugin_dir = resolve_plugin_dir(args.plugin_dir)
    except RuntimeError as exc:
        print(f"koru autopilot install-plugin-jetbrains: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        requested_gradle = (args.gradle_bin or "gradle").strip() or "gradle"
        cmd = [requested_gradle, args.gradle_task]
        payload = {
            "ok": True,
            "dry_run": True,
            "plugin_dir": str(plugin_dir),
            "command": cmd,
        }
        if args.output_format == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("koru autopilot install-plugin-jetbrains: dry-run")
            print(f"  cwd: {plugin_dir}")
            print(f"  {' '.join(cmd)}")
        return 0

    try:
        gradle_bin = resolve_gradle(args.gradle_bin)
    except RuntimeError as exc:
        print(f"koru autopilot install-plugin-jetbrains: {exc}", file=sys.stderr)
        return 1

    cmd = [gradle_bin, args.gradle_task]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(plugin_dir),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f"koru autopilot install-plugin-jetbrains: {exc}", file=sys.stderr)
        return 1

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        _render_jetbrains_failure(
            plugin_dir=plugin_dir,
            cmd=cmd,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            output_format=args.output_format,
        )
        return 1

    try:
        artifact = resolve_artifact(plugin_dir)
    except RuntimeError as exc:
        print(f"koru autopilot install-plugin-jetbrains: {exc}", file=sys.stderr)
        return 1

    _render_jetbrains_success(
        plugin_dir=plugin_dir,
        cmd=cmd,
        artifact=artifact,
        stdout=stdout,
        stderr=stderr,
        output_format=args.output_format,
    )
    return 0
