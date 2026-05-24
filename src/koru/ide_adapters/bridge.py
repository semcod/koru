"""Orchestrate IDE bridge diagnostics (daemon + plugin + settings)."""

from __future__ import annotations

from pathlib import Path

from koru.autopilot.client import AutopilotClient
from koru.ide_adapters.base import BridgeStatus, Hypothesis
from koru.ide_adapters import shared
from koru.ide_adapters.registry import get_adapter
from koruide.ide import detect_running_ides, normalize_ide_id


def _ide_is_running(ide: str) -> bool:
    return any(getattr(item, "id", None) == ide for item in detect_running_ides())


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
    if plugins is None and daemon_running:
        try:
            status = client.status()
            plugins = status.get("plugins") if isinstance(status, dict) else []
        except (OSError, RuntimeError):
            plugins = []
    plugin_list = plugins if isinstance(plugins, list) else []
    plugins_connected = any(
        isinstance(p, dict) and normalize_ide_id(str(p.get("ide", ""))) == ide
        for p in plugin_list
    )
    adapter = get_adapter(ide)
    status = BridgeStatus(
        ide=ide,
        socket_path=sock,
        daemon_running=daemon_running,
        plugins_connected=plugins_connected,
        project=str(project.resolve()) if project is not None else None,
    )
    if adapter is None:
        if not plugins_connected:
            status.hypotheses.append(
                Hypothesis(
                    id="ide.unsupported",
                    confidence=0.4,
                    evidence=f"Brak adaptera diagnostycznego dla ide={ide}",
                    remediation=shared.Remediation(
                        kind="manual",
                        summary="Użyj keyboard fallback lub zgłoś IDE w koru",
                    ),
                ),
            )
        return status
    status.activation = adapter.diagnose_activation()
    status.settings = adapter.analyze_settings(project=project, expected_socket=sock)
    status.hypotheses = adapter.collect_hypotheses(
        project=project,
        expected_socket=sock,
        plugins_connected=plugins_connected,
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
    return shared.gc_stale_autopilot_sockets(keep=socket_path)


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
