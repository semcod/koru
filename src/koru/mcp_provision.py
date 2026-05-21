"""Auto-provision MCP configuration for IDEs.

``koru init-ide`` detects running IDEs and writes the appropriate MCP
config files so each IDE's agent can discover koru tools automatically.

Supported targets:
    windsurf   — ~/.codeium/windsurf/mcp_config.json
    cursor     — .cursor/mcp.json (per-project)
    vscode     — .vscode/mcp.json (per-project, VS Code 1.99+)
    vscodium   — .vscode/mcp.json (per-project, VS Code-compatible layout)
    zed        — .zed/settings.json (per-project context_servers)

Usage::

    koru init-ide                        # auto-detect + provision all found
    koru init-ide --ide windsurf         # only Windsurf
    koru init-ide --ide cursor           # only Cursor
    koru init-ide --ide zed              # only Zed
    koru init-ide --dry-run              # preview without writing
    koru init-ide --remove               # remove koru entries from configs
"""


import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from koru.ide_runtime import detect_running_ides
from koruide.ide import normalize_ide_id

# ---------------------------------------------------------------------------
# IDE config locations
# ---------------------------------------------------------------------------


def _windsurf_global_config() -> Path:
    """Return the Windsurf global MCP config path."""
    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def _cursor_project_config(project: Path) -> Path:
    """Return the Cursor per-project MCP config path."""
    return project / ".cursor" / "mcp.json"


def _vscode_project_config(project: Path) -> Path:
    """Return the VS Code per-project MCP config path."""
    return project / ".vscode" / "mcp.json"


def _windsurf_project_config(project: Path) -> Path:
    """Return the Windsurf per-project MCP config path."""
    return project / ".windsurf" / "mcp_config.json"


def _zed_project_settings(project: Path) -> Path:
    """Return the Zed per-project settings path."""
    return project / ".zed" / "settings.json"


# ---------------------------------------------------------------------------
# Koru MCP server entry
# ---------------------------------------------------------------------------


def _resolved_koru_command() -> str:
    """Return an absolute ``koru`` path when on PATH.

    GUI IDEs (Windsurf, Cursor) often spawn MCP with a minimal environment and
    no shell PATH — a bare ``\"command\": \"koru\"`` then fails and the server
    stays OFF. ``shutil.which`` uses the PATH of the *provisioning* process
    (e.g. conda/venv from ``task koru:mcp:bootstrap``).
    """
    found = shutil.which("koru")
    return found if found else "koru"


def _koru_mcp_entry() -> dict[str, Any]:
    """Build the MCP server entry for koru (stdio transport)."""
    return {
        "command": _resolved_koru_command(),
        "args": ["mcp-serve"],
        "env": {
            "KORU_PROJECT_ROOT": "${workspaceFolder}",
        },
    }


def _koru_mcp_entry_cursor() -> dict[str, Any]:
    """Build the MCP server entry for koru in Cursor format."""
    return {
        "command": _resolved_koru_command(),
        "args": ["mcp-serve"],
        "transport": "stdio",
    }


def _maybe_upgrade_koru_command(servers: dict[str, Any]) -> bool:
    """If ``koru`` is registered with a bare ``command``, rewrite to absolute path.

    Returns True when ``servers`` was mutated (caller should persist config).
    """
    if "koru" not in servers:
        return False
    resolved = _resolved_koru_command()
    if resolved == "koru":
        return False
    entry = servers["koru"]
    if not isinstance(entry, dict):
        return False
    cur = entry.get("command")
    if cur == "koru":
        entry["command"] = resolved
        return True
    return False


# ---------------------------------------------------------------------------
# IDE detection
# ---------------------------------------------------------------------------


def detect_ides() -> list[str]:
    """Return list of IDE ids detected on this system."""
    detected: list[str] = []
    try:
        for ide_info in detect_running_ides():
            ide_id = ide_info.get("id") if isinstance(ide_info, dict) else str(ide_info)
            if ide_id:
                detected.append(ide_id)
    except Exception:
        pass

    # Fallback: check for config directories
    if not detected:
        if _windsurf_global_config().parent.exists():
            detected.append("windsurf")
        # Check common install locations
        for name, check in [
            ("cursor", Path.home() / ".cursor"),
            ("vscode", Path.home() / ".vscode"),
            ("vscodium", Path.home() / ".config" / "VSCodium"),
            ("zed", Path.home() / ".config" / "zed"),
        ]:
            if check.exists() and name not in detected:
                detected.append(name)

    return detected


# ---------------------------------------------------------------------------
# Config read/write helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, returning {} if missing or invalid."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict[str, Any], *, dry_run: bool = False) -> str:
    """Write JSON to a file, creating parent dirs. Returns the path written."""
    if dry_run:
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return str(path)


# ---------------------------------------------------------------------------
# Provision / remove
# ---------------------------------------------------------------------------


def provision_windsurf(project: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Add koru MCP server to Windsurf config."""
    # Prefer per-project config if .windsurf/ exists; else global
    project_cfg = _windsurf_project_config(project)
    config_path = project_cfg if project_cfg.parent.exists() else _windsurf_global_config()

    config = _read_json(config_path)
    servers = config.setdefault("mcpServers", {})

    if "koru" in servers:
        if _maybe_upgrade_koru_command(servers):
            written = _write_json(config_path, config, dry_run=dry_run)
            return {"ide": "windsurf", "action": "updated", "path": written, "dry_run": dry_run}
        return {"ide": "windsurf", "action": "already_configured", "path": str(config_path)}

    servers["koru"] = _koru_mcp_entry()
    written = _write_json(config_path, config, dry_run=dry_run)
    return {"ide": "windsurf", "action": "added", "path": written, "dry_run": dry_run}


def provision_cursor(project: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Add koru MCP server to Cursor per-project config."""
    config_path = _cursor_project_config(project)
    config = _read_json(config_path)
    servers = config.setdefault("mcpServers", {})

    if "koru" in servers:
        if _maybe_upgrade_koru_command(servers):
            written = _write_json(config_path, config, dry_run=dry_run)
            return {"ide": "cursor", "action": "updated", "path": written, "dry_run": dry_run}
        return {"ide": "cursor", "action": "already_configured", "path": str(config_path)}

    servers["koru"] = _koru_mcp_entry_cursor()
    written = _write_json(config_path, config, dry_run=dry_run)
    return {"ide": "cursor", "action": "added", "path": written, "dry_run": dry_run}


def provision_vscode(project: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Add koru MCP server to VS Code per-project config."""
    config_path = _vscode_project_config(project)
    config = _read_json(config_path)
    servers = config.setdefault("mcpServers", {})

    if "koru" in servers:
        if _maybe_upgrade_koru_command(servers):
            written = _write_json(config_path, config, dry_run=dry_run)
            return {"ide": "vscode", "action": "updated", "path": written, "dry_run": dry_run}
        return {"ide": "vscode", "action": "already_configured", "path": str(config_path)}

    servers["koru"] = _koru_mcp_entry()
    written = _write_json(config_path, config, dry_run=dry_run)
    return {"ide": "vscode", "action": "added", "path": written, "dry_run": dry_run}


def provision_vscodium(project: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Add koru MCP server to VSCodium using the VS Code-compatible layout."""
    result = provision_vscode(project, dry_run=dry_run)
    result["ide"] = "vscodium"
    return result


def provision_zed(project: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Add koru MCP server to Zed per-project settings."""
    config_path = _zed_project_settings(project)
    config = _read_json(config_path)
    servers = config.setdefault("context_servers", {})

    if "koru" in servers:
        if _maybe_upgrade_koru_command(servers):
            written = _write_json(config_path, config, dry_run=dry_run)
            return {"ide": "zed", "action": "updated", "path": written, "dry_run": dry_run}
        return {"ide": "zed", "action": "already_configured", "path": str(config_path)}

    servers["koru"] = _koru_mcp_entry()
    written = _write_json(config_path, config, dry_run=dry_run)
    return {"ide": "zed", "action": "added", "path": written, "dry_run": dry_run}


def remove_from_config(
    config_path: Path,
    *,
    dry_run: bool = False,
    server_key: str = "mcpServers",
) -> dict[str, Any]:
    """Remove the koru entry from an MCP config file."""
    config = _read_json(config_path)
    servers = config.get(server_key, {})
    if "koru" not in servers:
        return {"action": "not_present", "path": str(config_path)}
    del servers["koru"]
    if not dry_run:
        _write_json(config_path, config)
    return {"action": "removed", "path": str(config_path), "dry_run": dry_run}


def ensure_koru_mcp_not_disabled(project: Path) -> list[dict[str, Any]]:
    """Best-effort: fix workspace MCP JSON so ``koru`` can start after IDE reload.

    - Upgrades a bare ``\"command\": \"koru\"`` to an absolute path (same logic
      as ``init-ide``) so GUI IDEs with minimal PATH can spawn the server.
    - Removes ``\"disabled\": true`` on the ``koru`` server entry when present;
      some products persist the OFF toggle in this file.
    - Also checks Windsurf **global** ``~/.codeium/windsurf/mcp_config.json`` when
      that file exists (Windsurf often uses global MCP instead of per-repo).

    Does **not** flip purely UI-internal state stored only outside these files.
    """
    out: list[dict[str, Any]] = []
    global_windsurf = _windsurf_global_config()
    paths: list[tuple[Path, str]] = [
        (_cursor_project_config(project), "mcpServers"),
        (_vscode_project_config(project), "mcpServers"),
        (_windsurf_project_config(project), "mcpServers"),
        (_zed_project_settings(project), "context_servers"),
    ]
    if all(global_windsurf != path for path, _server_key in paths):
        paths.append((global_windsurf, "mcpServers"))

    for config_path, server_key in paths:
        if not config_path.is_file():
            continue
        config = _read_json(config_path)
        servers = config.get(server_key)
        if not isinstance(servers, dict) or "koru" not in servers:
            continue
        mutated = _maybe_upgrade_koru_command(servers)
        koru = servers.get("koru")
        if isinstance(koru, dict) and koru.get("disabled") is True:
            koru.pop("disabled", None)
            mutated = True
        if mutated:
            _write_json(config_path, config, dry_run=False)
            out.append({"action": "mcp_refreshed", "path": str(config_path)})
    return out


_PROVISIONERS: dict[str, Any] = {
    "windsurf": provision_windsurf,
    "cursor": provision_cursor,
    "vscode": provision_vscode,
    "vscodium": provision_vscodium,
    "zed": provision_zed,
}

_IDE_ALIASES: dict[str, str] = {
    "code": "vscode",
    "vs-code": "vscode",
    "antigravity": "vscode",  # VSCode-fork, same config layout
    "codium": "vscodium",
    "code-oss": "vscodium",
    "zed-editor": "zed",
}


def _resolve_targets(ide: str) -> list[str]:
    if ide == "auto":
        detected = detect_ides()
        return detected or ["windsurf", "cursor"]
    if ide == "all":
        return list(_PROVISIONERS.keys())
    normalized = normalize_ide_id(ide) or ide
    return [_IDE_ALIASES.get(ide, normalized)]


def _removal_paths_for_ide(ide: str, project: Path) -> list[Path]:
    if ide == "windsurf":
        return [_windsurf_project_config(project), _windsurf_global_config()]
    if ide == "cursor":
        return [_cursor_project_config(project)]
    if ide == "vscode":
        return [_vscode_project_config(project)]
    if ide == "vscodium":
        return [_vscode_project_config(project)]
    if ide == "zed":
        return [_zed_project_settings(project)]
    return []


def _apply_target(ide: str, project: Path, *, remove: bool, dry_run: bool) -> list[dict[str, Any]]:
    provisioner = _PROVISIONERS.get(ide)
    if provisioner is None:
        return [{"ide": ide, "action": "unsupported"}]

    if not remove:
        return [provisioner(project, dry_run=dry_run)]

    results: list[dict[str, Any]] = []
    server_key = "context_servers" if ide == "zed" else "mcpServers"
    for path in _removal_paths_for_ide(ide, project):
        result = remove_from_config(path, dry_run=dry_run, server_key=server_key)
        result["ide"] = ide
        results.append(result)
    return results


def _render_results(results: list[dict[str, Any]], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(results, indent=2))
        return

    for result in results:
        ide = result.get("ide", "?")
        action = result.get("action", "?")
        path = result.get("path", "")
        dry = " (dry-run)" if result.get("dry_run") else ""
        print(f"  {ide}: {action} → {path}{dry}")
    if not results:
        print("  (no IDEs targeted)")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def init_ide_main(argv: list[str]) -> int:
    """Entry point for ``koru init-ide``."""
    parser = argparse.ArgumentParser(
        prog="koru init-ide",
        description=(
            "Auto-provision MCP configuration so IDE agents (Windsurf Cascade, "
            "Cursor Agent, VS Code-family editors, and Zed) can discover koru tools."
        ),
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root (default: cwd).",
    )
    parser.add_argument(
        "--ide",
        default="auto",
        help="Target IDE or alias: auto, all, windsurf, cursor, vscode, vscodium, zed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without modifying files.",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove koru entries from IDE MCP configs instead of adding.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args(argv)
    project = args.project.resolve()

    targets = _resolve_targets(args.ide)

    results: list[dict[str, Any]] = []

    for ide in targets:
        results.extend(_apply_target(ide, project, remove=args.remove, dry_run=args.dry_run))

    _render_results(results, args.output_format)

    return 0
