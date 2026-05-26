"""Orchestrate IDE bridge diagnostics (daemon + plugin + settings)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.autopilot.client import AutopilotClient
from koru.ide_adapters.base import BridgeStatus, Hypothesis
from koru.ide_adapters import shared
from koru.ide_adapters.registry import get_adapter
from koruide.ide import detect_running_ides, normalize_ide_id


def _ide_is_running(ide: str) -> bool:
    return any(getattr(item, "id", None) == ide for item in detect_running_ides())


def _stale_rejected_plugin_hypothesis(
    *,
    ide: str,
    daemon_status: dict[str, Any],
    expected_socket: str,
) -> Hypothesis | None:
    rejected = daemon_status.get("rejected_plugins")
    if not isinstance(rejected, list):
        return None
    stale_versions = sorted(
        {
            str(row.get("version"))
            for row in rejected
            if isinstance(row, dict)
            and normalize_ide_id(str(row.get("ide") or "")) == ide
            and row.get("version")
            and row.get("expected_version")
            and row.get("version") != row.get("expected_version")
        }
    )
    if not stale_versions:
        return None
    return Hypothesis(
        id=f"{ide}.plugin.live_host_stale",
        confidence=0.9,
        evidence=(
            f"Daemon odrzucił stale wersje pluginu {ide}: "
            f"{', '.join(stale_versions)}"
        ),
        remediation=shared.Remediation(
            kind="manual",
            summary=(
                "Developer: Reload Window, potem koru: Connect autopilot daemon "
                f"(socket {expected_socket})"
            ),
        ),
    )


def _daemon_status_and_plugins(
    client: AutopilotClient,
    *,
    plugins: list | None,
    daemon_running: bool,
) -> tuple[dict[str, Any], list]:
    daemon_status: dict[str, Any] = {}
    if plugins is not None or not daemon_running:
        return daemon_status, plugins if isinstance(plugins, list) else []
    try:
        daemon_status = client.status()
    except (OSError, RuntimeError):
        return {}, []
    plugins = daemon_status.get("plugins") if isinstance(daemon_status, dict) else []
    return daemon_status, plugins if isinstance(plugins, list) else []


def _plugins_connected(plugin_list: list, ide: str) -> bool:
    return any(
        isinstance(p, dict) and normalize_ide_id(str(p.get("ide", ""))) == ide
        for p in plugin_list
    )


def _bridge_status_base(
    *,
    ide: str,
    sock: str,
    project: Path | None,
    daemon_running: bool,
    plugins_connected: bool,
) -> BridgeStatus:
    return BridgeStatus(
        ide=ide,
        socket_path=sock,
        daemon_running=daemon_running,
        plugins_connected=plugins_connected,
        project=str(project.resolve()) if project is not None else None,
    )


def _add_unsupported_ide_hypothesis(status: BridgeStatus) -> None:
    if status.plugins_connected:
        return
    status.hypotheses.append(
        Hypothesis(
            id="ide.unsupported",
            confidence=0.4,
            evidence=f"Brak adaptera diagnostycznego dla ide={status.ide}",
            remediation=shared.Remediation(
                kind="manual",
                summary="Użyj keyboard fallback lub zgłoś IDE w koru",
            ),
        ),
    )


def _populate_adapter_diagnostics(
    status: BridgeStatus,
    *,
    project: Path | None,
    sock: str,
) -> None:
    adapter = get_adapter(status.ide)
    if adapter is None:
        _add_unsupported_ide_hypothesis(status)
        return
    status.activation = adapter.diagnose_activation()
    status.settings = adapter.analyze_settings(project=project, expected_socket=sock)
    status.hypotheses = adapter.collect_hypotheses(
        project=project,
        expected_socket=sock,
        plugins_connected=status.plugins_connected,
    )


def _append_stale_plugin_hypothesis(
    status: BridgeStatus,
    *,
    daemon_status: dict[str, Any],
    sock: str,
) -> None:
    stale_hypothesis = _stale_rejected_plugin_hypothesis(
        ide=status.ide,
        daemon_status=daemon_status,
        expected_socket=sock,
    )
    if stale_hypothesis is None or status.plugins_connected:
        return
    status.hypotheses.append(stale_hypothesis)
    status.hypotheses.sort(key=lambda h: h.confidence, reverse=True)


def evaluate_bridge(
    *,
    ide: str,
    socket_path: str | Path,
    project: Path | None = None,
    plugins: list | None = None,
) -> BridgeStatus:
    """Build a full bridge status for the given IDE lane."""
    ide = normalize_ide_id(ide) or ide
    sock = str(Path(socket_path).resolve())
    client = AutopilotClient(socket_path=Path(sock), timeout=1.0)
    daemon_running = client.is_running()
    daemon_status, plugin_list = _daemon_status_and_plugins(
        client,
        plugins=plugins,
        daemon_running=daemon_running,
    )
    status = _bridge_status_base(
        ide=ide,
        sock=sock,
        project=project,
        daemon_running=daemon_running,
        plugins_connected=_plugins_connected(plugin_list, ide),
    )
    _populate_adapter_diagnostics(
        status,
        project=project,
        sock=sock,
    )
    _append_stale_plugin_hypothesis(
        status,
        daemon_status=daemon_status,
        sock=sock,
    )
    return status


def apply_bridge_fixes(
    status: BridgeStatus,
    *,
    project: Path | None,
    fix: bool,
) -> BridgeStatus:
    adapter = get_adapter(status.ide)
    if adapter is None or not fix:
        return status
    status.fixes_applied.extend(
        adapter.apply_safe_fixes(
            project=project,
            expected_socket=status.socket_path,
            fix=fix,
            ide_running=_ide_is_running(status.ide),
        ),
    )
    return status


def gc_stale_sockets_for_lane(socket_path: Path) -> list[str]:
    removed: list[str] = []
    if socket_path.exists() and not shared.socket_reachable(socket_path):
        try:
            socket_path.unlink()
            removed.append(str(socket_path))
        except OSError:
            pass
    removed.extend(shared.gc_stale_autopilot_sockets(keep=socket_path, runtime_dir=socket_path.parent))
    return removed


def format_bridge_text(status: BridgeStatus, *, explain: bool = False) -> str:
    lines: list[str] = []
    mark = "✔" if status.daemon_running else "✘"
    lines.append(f"{mark} daemon: {status.socket_path}")
    if status.daemon_running:
        plug_mark = "✔" if status.plugins_connected else "✘"
        lines.append(f"{plug_mark} plugin connected (ide={status.ide})")
    if status.settings is not None and status.settings.mismatch:
        lines.append(
            f"✘ settings: workspace={status.settings.workspace_socket} "
            f"expected={status.settings.expected_socket}",
        )
    if status.ready:
        lines.append("ready: autopilot bridge OK")
        return "\n".join(lines)
    if explain or status.hypotheses:
        lines.append("diagnostics:")
        for hyp in status.hypotheses[:5]:
            lines.append(f"  · [{hyp.confidence:.0%}] {hyp.id}: {hyp.evidence}")
            lines.append(f"    → {hyp.remediation.summary}")
            if hyp.remediation.command:
                lines.append(f"      $ {hyp.remediation.command}")
    if status.fixes_applied:
        lines.append("fixes applied:")
        for item in status.fixes_applied:
            lines.append(f"  · {item}")
    top = status.top_hypothesis()
    if top is not None:
        lines.append(f"next: {top.remediation.summary}")
    return "\n".join(lines)
