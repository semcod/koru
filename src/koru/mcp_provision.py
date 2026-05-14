"""Auto-provision MCP configuration for IDEs.

``koru init-ide`` detects running IDEs and writes the appropriate MCP
config files so each IDE's agent can discover koru tools automatically.

Supported targets:
    windsurf   — ~/.codeium/windsurf/mcp_config.json
    cursor     — .cursor/mcp.json (per-project)
    vscode     — .vscode/mcp.json (per-project, VS Code 1.99+)

Usage::

    koru init-ide                        # auto-detect + provision all found
    koru init-ide --ide windsurf         # only Windsurf
    koru init-ide --ide cursor           # only Cursor
    koru init-ide --dry-run              # preview without writing
    koru init-ide --remove               # remove koru entries from configs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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


# ---------------------------------------------------------------------------
# Koru MCP server entry
# ---------------------------------------------------------------------------

def _koru_mcp_entry() -> dict[str, Any]:
    """Build the MCP server entry for koru (stdio transport)."""
    return {
        "command": "koru",
        "args": ["mcp-serve"],
        "env": {
            "KORU_PROJECT_ROOT": "${workspaceFolder}",
        },
    }


def _koru_mcp_entry_cursor() -> dict[str, Any]:
    """Build the MCP server entry for koru in Cursor format."""
    return {
        "command": "koru",
        "args": ["mcp-serve"],
        "transport": "stdio",
    }


# ---------------------------------------------------------------------------
# IDE detection (reuses autopilot.ide when available)
# ---------------------------------------------------------------------------

def detect_ides() -> list[str]:
    """Return list of IDE ids detected on this system."""
    detected: list[str] = []
    try:
        from .autopilot.ide import detect_running_ides

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
    if project_cfg.parent.exists():
        config_path = project_cfg
    else:
        config_path = _windsurf_global_config()

    config = _read_json(config_path)
    servers = config.setdefault("mcpServers", {})

    if "koru" in servers:
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
        return {"ide": "vscode", "action": "already_configured", "path": str(config_path)}

    servers["koru"] = _koru_mcp_entry()
    written = _write_json(config_path, config, dry_run=dry_run)
    return {"ide": "vscode", "action": "added", "path": written, "dry_run": dry_run}


def remove_from_config(config_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Remove the koru entry from an MCP config file."""
    config = _read_json(config_path)
    servers = config.get("mcpServers", {})
    if "koru" not in servers:
        return {"action": "not_present", "path": str(config_path)}
    del servers["koru"]
    if not dry_run:
        _write_json(config_path, config)
    return {"action": "removed", "path": str(config_path), "dry_run": dry_run}


_PROVISIONERS: dict[str, Any] = {
    "windsurf": provision_windsurf,
    "cursor": provision_cursor,
    "vscode": provision_vscode,
}

_IDE_ALIASES: dict[str, str] = {
    "code": "vscode",
    "vs-code": "vscode",
    "antigravity": "vscode",  # VSCode-fork, same config layout
}


def _resolve_targets(ide: str) -> list[str]:
    if ide == "auto":
        detected = detect_ides()
        return detected or ["windsurf", "cursor"]
    if ide == "all":
        return list(_PROVISIONERS.keys())
    return [_IDE_ALIASES.get(ide, ide)]


def _removal_paths_for_ide(ide: str, project: Path) -> list[Path]:
    if ide == "windsurf":
        return [_windsurf_project_config(project), _windsurf_global_config()]
    if ide == "cursor":
        return [_cursor_project_config(project)]
    if ide == "vscode":
        return [_vscode_project_config(project)]
    return []


def _apply_target(ide: str, project: Path, *, remove: bool, dry_run: bool) -> list[dict[str, Any]]:
    provisioner = _PROVISIONERS.get(ide)
    if provisioner is None:
        return [{"ide": ide, "action": "unsupported"}]

    if not remove:
        return [provisioner(project, dry_run=dry_run)]

    results: list[dict[str, Any]] = []
    for path in _removal_paths_for_ide(ide, project):
        result = remove_from_config(path, dry_run=dry_run)
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
            "Cursor Agent, VS Code Copilot) can discover koru tools."
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
        choices=["auto", "windsurf", "cursor", "vscode", "all"],
        help="Target IDE (default: auto-detect).",
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
