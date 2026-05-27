"""Hello message handlers for koruide daemon (R6).

Extracted from :mod:`koruide.daemon.handlers` to isolate plugin hello
handshake logic (version checks, client configuration, rejection logging)
into a cohesive module.
"""

from __future__ import annotations

import time
from typing import Any

from koruide.daemon.protocol import _Client, _daemon_package_version
from koruide.command_catalog_store import (
    command_catalog_enabled,
    parse_hello_command_catalog,
)
from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide import normalize_ide_id
from koruide.protocol import Message, ack, error, MIN_PLUGIN_PROTOCOL_VERSION


def _extract_hello_metadata(
    msg: Message,
) -> tuple[str | None, str | None, str | None, int | None, list[str], str | None, list[str]]:
    """Extract and validate hello message metadata."""
    raw_ide = msg.data.get("ide")
    ide = normalize_ide_id(raw_ide) if isinstance(raw_ide, str) else raw_ide
    version = msg.data.get("version")
    plugin_version = version if isinstance(version, str) else None
    build_raw = msg.data.get("buildSha")
    build_sha = build_raw if isinstance(build_raw, str) else None
    protocol_raw = msg.data.get("protocolVersion")
    protocol_version = protocol_raw if isinstance(protocol_raw, int) else None
    capabilities_raw = msg.data.get("capabilities")
    capabilities = (
        [item for item in capabilities_raw if isinstance(item, str)]
        if isinstance(capabilities_raw, list)
        else []
    )
    workspace_name_raw = msg.data.get("workspaceName")
    workspace_name = workspace_name_raw if isinstance(workspace_name_raw, str) else None
    folders_raw = msg.data.get("workspaceFolders")
    workspace_folders = (
        [item for item in folders_raw if isinstance(item, str)]
        if isinstance(folders_raw, list)
        else []
    )
    return ide, plugin_version, build_sha, protocol_version, capabilities, workspace_name, workspace_folders


def _handle_plugin_version_check(
    daemon: Any,
    client: _Client,
    msg: Message,
    ide: str,
    plugin_version: str | None,
    build_sha: str | None,
    protocol_version: int | None,
    capabilities: list[str],
) -> bool:
    """Check plugin version and return True if accepted, False if rejected."""
    version_info = DriveOrchestrator.plugin_version_info(
        plugin_ide=ide,
        connected_version=plugin_version,
        connected_build_sha=build_sha,
        protocol_version=protocol_version,
        capabilities=capabilities,
    )
    if DriveOrchestrator.should_block_plugin_version(version_info):
        message = DriveOrchestrator.plugin_version_block_message(version_info)
        daemon._send(client, error(msg.id, message).encode())
        # Route via instance method so tests calling
        # ``daemon._log_rejected_plugin_connection(...)`` directly observe
        # the same code path and shared rejection state.
        daemon._log_rejected_plugin_connection(
            ide=ide,
            plugin_version=plugin_version,
            expected_plugin_version=version_info.get("expected_plugin_version"),
            plugin_build_sha=build_sha,
            expected_plugin_build_sha=version_info.get("expected_plugin_build_sha"),
            message=message,
        )
        daemon.audit.record(
            "plugin_rejected",
            ide=ide,
            version=plugin_version,
            build_sha=build_sha,
            expected_plugin_version=version_info.get("expected_plugin_version"),
            expected_plugin_build_sha=version_info.get("expected_plugin_build_sha"),
            error=message,
        )
        daemon._drop(client)
        return False
    return True


def _configure_plugin_client(
    daemon: Any,
    client: _Client,
    ide: str,
    plugin_version: str | None,
    build_sha: str | None,
    protocol_version: int | None,
    capabilities: list[str],
    workspace_name: str | None,
    workspace_folders: list[str],
) -> None:
    """Configure client as a plugin with provided metadata."""
    client.role = "plugin"
    client.ide = ide
    client.version = plugin_version
    client.build_sha = build_sha
    client.protocol_version = protocol_version
    client.capabilities = capabilities
    client.workspace_name = workspace_name
    client.workspace_folders = workspace_folders
    daemon._plugin_router.drop_stale_plugins(client, ide)


def _log_plugin_hello_accepted(
    daemon: Any,
    ide: str,
    plugin_version: str | None,
    build_sha: str | None,
    protocol_version: int | None,
    capabilities: list[str],
    version_info: dict[str, Any],
    matching_cmds: Any,
    workspace_name: str | None,
    workspace_folders: list[str],
) -> None:
    """Log successful plugin hello acceptance."""
    command_count = len(matching_cmds) if isinstance(matching_cmds, list) else "-"
    daemon.log(
        "plugin hello accepted: "
        f"ide={ide} version={plugin_version or '-'} "
        f"expected={version_info.get('expected_plugin_version') or '-'} "
        f"build={build_sha or '-'} expected_build={version_info.get('expected_plugin_build_sha') or '-'} "
        f"policy={version_info.get('plugin_version_policy') or 'warn'} "
        f"protocol={protocol_version or '-'} min_protocol={MIN_PLUGIN_PROTOCOL_VERSION} "
        f"capabilities={len(capabilities)} matching_commands={command_count} "
        f"workspace={workspace_name or '-'} folders={workspace_folders[:3] or '-'}",
    )


def _store_hello_command_catalog(
    daemon: Any,
    client: _Client,
    msg: Message,
    ide: str,
    plugin_version: str | None,
) -> Any:
    matching_cmds = msg.data.get("matchingCommands")
    catalog = parse_hello_command_catalog(msg.data)
    if catalog and command_catalog_enabled():
        client.command_catalog = catalog
        unknown = catalog.get("unknown_chat") or []
        daemon._command_catalog_store.update(
            ide,
            plugin_version=plugin_version,
            catalog=catalog,
            unknown_sample=unknown[:20] if isinstance(unknown, list) else None,
        )
        daemon.log(
            f"plugin command catalog stored: ide={ide} "
            f"focus_open={len(catalog.get('focus_open', []))} "
            f"paste={len(catalog.get('paste', []))} "
            f"submit={len(catalog.get('submit', []))} "
            f"unknown_chat={len(catalog.get('unknown_chat', []))}",
        )
    return matching_cmds


def _accept_plugin_hello(
    daemon: Any,
    client: _Client,
    msg: Message,
    ide: str,
    plugin_version: str | None,
    build_sha: str | None,
    protocol_version: int | None,
    capabilities: list[str],
    workspace_name: str | None,
    workspace_folders: list[str],
) -> None:
    version_info = DriveOrchestrator.plugin_version_info(
        plugin_ide=ide,
        connected_version=plugin_version,
        connected_build_sha=build_sha,
        protocol_version=protocol_version,
        capabilities=capabilities,
    )
    matching_cmds = _store_hello_command_catalog(
        daemon,
        client,
        msg,
        ide,
        plugin_version,
    )
    _log_plugin_hello_accepted(
        daemon,
        ide,
        plugin_version,
        build_sha,
        protocol_version,
        capabilities,
        version_info,
        matching_cmds,
        workspace_name,
        workspace_folders,
    )
    daemon._send(client, ack(msg.id or "", info={"role": "plugin"}).encode())
    daemon.audit.record(
        "plugin_connected",
        ide=ide,
        version=plugin_version,
        build_sha=build_sha,
    )


def handle_hello(daemon: Any, client: _Client, msg: Message) -> None:
    """Handle plugin hello message."""
    (
        ide,
        plugin_version,
        build_sha,
        protocol_version,
        capabilities,
        workspace_name,
        workspace_folders,
    ) = _extract_hello_metadata(msg)
    if not isinstance(ide, str) or not ide:
        daemon._send(client, error(msg.id, "hello requires 'ide'").encode())
        return

    if not _handle_plugin_version_check(
        daemon, client, msg, ide, plugin_version, build_sha, protocol_version, capabilities
    ):
        return

    _configure_plugin_client(
        daemon,
        client,
        ide,
        plugin_version,
        build_sha,
        protocol_version,
        capabilities,
        workspace_name,
        workspace_folders,
    )
    _accept_plugin_hello(
        daemon,
        client,
        msg,
        ide,
        plugin_version,
        build_sha,
        protocol_version,
        capabilities,
        workspace_name,
        workspace_folders,
    )


def _log_rejected_plugin_connection(
    daemon: Any,
    *,
    ide: str,
    plugin_version: str | None,
    expected_plugin_version: Any,
    message: str,
    plugin_build_sha: str | None = None,
    expected_plugin_build_sha: Any = None,
) -> None:
    """Log rejected plugin connection with rate limiting."""
    from koruide.daemon.handlers import _ide_reload_label, _plugin_rejection_log_interval_seconds

    expected = expected_plugin_version if isinstance(expected_plugin_version, str) else None
    key = (ide, plugin_version, expected)
    now = time.monotonic()
    last, suppressed = daemon._plugin_rejection_log_state.get(key, (0.0, 0))
    if _plugin_rejection_rate_limited(last, now, _plugin_rejection_log_interval_seconds()):
        daemon._plugin_rejection_log_state[key] = (last, suppressed + 1)
        return
    _log_plugin_rejection_header(daemon, ide=ide, message=message, suppressed=suppressed)
    _log_plugin_rejection_guidance(
        daemon,
        ide=ide,
        plugin_version=plugin_version,
        expected=expected,
        plugin_build_sha=plugin_build_sha,
        expected_plugin_build_sha=expected_plugin_build_sha,
        ide_reload_label=_ide_reload_label,
    )
    daemon._plugin_rejection_log_state[key] = (now, 0)
    _remember_plugin_rejection(
        daemon,
        ide=ide,
        plugin_version=plugin_version,
        expected=expected,
        plugin_build_sha=plugin_build_sha,
        expected_plugin_build_sha=expected_plugin_build_sha,
        message=message,
        suppressed=suppressed,
    )


def _plugin_rejection_rate_limited(last: float, now: float, interval_seconds: float) -> bool:
    return bool(last and now - last < interval_seconds)


def _log_plugin_rejection_header(daemon: Any, *, ide: str, message: str, suppressed: int) -> None:
    suffix = f" (suppressed {suppressed} repeated reconnects)" if suppressed else ""
    daemon.log(f"rejecting plugin connection: ide={ide} {message}{suffix}")


def _log_plugin_rejection_guidance(
    daemon: Any,
    *,
    ide: str,
    plugin_version: str | None,
    expected: str | None,
    plugin_build_sha: str | None,
    expected_plugin_build_sha: Any,
    ide_reload_label: Any,
) -> None:
    if expected and plugin_version and plugin_version != expected:
        ide_label = ide_reload_label(ide)
        daemon.log(
            f"  → installed VSIX is v{plugin_version} but daemon expects "
            f"v{expected}. The IDE is still running the older plugin. "
            f"Action: in {ide_label} run `Developer: Reload Window` then "
            "`koru: Connect autopilot daemon` from the command palette. "
            "If still mismatched after reload, rebuild and reinstall the "
            "VSIX from plugins/koru-autopilot-vscode/.",
        )
        return
    if _plugin_build_mismatch(plugin_build_sha, expected_plugin_build_sha):
        ide_label = ide_reload_label(ide)
        daemon.log(
            f"  → installed VSIX version matches, but build hash is {plugin_build_sha}; "
            f"daemon expects {expected_plugin_build_sha}. Action: in {ide_label} run "
            "`Developer: Reload Window` then `koru: Connect autopilot daemon`. "
            "If still mismatched after reload, rebuild and reinstall the VSIX.",
        )
        return
    if expected and not plugin_version:
        daemon.log(
            f"  → plugin sent no version; daemon expects v{expected}. "
            "This usually means the VSIX is older than the policy gate. "
            "Action: reinstall the VSIX from plugins/koru-autopilot-vscode/ "
            "and reload the IDE window.",
        )


def _plugin_build_mismatch(plugin_build_sha: str | None, expected_plugin_build_sha: Any) -> bool:
    return bool(
        isinstance(expected_plugin_build_sha, str)
        and plugin_build_sha
        and plugin_build_sha != expected_plugin_build_sha
    )


def _remember_plugin_rejection(
    daemon: Any,
    *,
    ide: str,
    plugin_version: str | None,
    expected: str | None,
    plugin_build_sha: str | None,
    expected_plugin_build_sha: Any,
    message: str,
    suppressed: int,
) -> None:
    daemon._plugin_rejections.append(
        {
            "ide": ide,
            "version": plugin_version,
            "expected_version": expected,
            "build_sha": plugin_build_sha,
            "expected_build_sha": (
                expected_plugin_build_sha if isinstance(expected_plugin_build_sha, str) else None
            ),
            "message": message,
            "suppressed": suppressed,
            "at": time.time(),
        }
    )
    if len(daemon._plugin_rejections) > 20:
        del daemon._plugin_rejections[:-20]
