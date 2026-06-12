"""Resolve autopilot lane / socket for shell CLI commands (``status``, ``drive``, …).

``koru auto`` sets lane env internally; plain ``koru autopilot *`` must infer
``cursor-main`` (not bare ``cursor``) from IDE settings, supervisor registry,
or live daemon metadata so operators do not need ``coru env`` in every shell.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from koru.agents import agent_lane_environment, format_agent_lane_exports
from koru.autopilot import default_socket_path
from koru.autonomous_startup import resolve_agent_lane_id
from koru.ide_adapters.shared import SOCKET_SETTING_KEY, user_settings_path
from koru.init import resolve_project_agent_lane
from koruide.ide import canonical_autopilot_ide_id, normalize_ide_id

_INSTANCE_FROM_SOCKET = re.compile(r"^koru-autopilot-([A-Za-z0-9_-]+)\.sock$")
_CANONICAL_IDES = frozenset(
    {"auto", "vscode", "vscodium", "cursor", "windsurf", "jetbrains", "zed", "antigravity"},
)


@dataclass(frozen=True)
class LaneContext:
    instance: str
    ide: str
    socket_path: Path
    source: str


def instance_from_socket_path(socket_path: str | Path | None) -> str | None:
    if not socket_path:
        return None
    name = Path(socket_path).name
    match = _INSTANCE_FROM_SOCKET.match(name)
    if not match:
        return None
    slug = match.group(1).strip().lower()
    return slug or None


def _read_socket_setting(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    raw = payload.get(SOCKET_SETTING_KEY)
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    return value or None


def socket_path_from_ide_settings(ide: str, *, project: Path | None = None) -> str | None:
    """Read ``koruAutopilot.socketPath`` from IDE user + workspace settings."""
    canonical = normalize_ide_id(ide) or ""
    for path in (user_settings_path(canonical),):
        found = _read_socket_setting(path)
        if found:
            return found
    if project is not None:
        from koru.ide_adapters.shared import workspace_settings_path

        found = _read_socket_setting(workspace_settings_path(project.resolve(), canonical))
        if found:
            return found
    return None


def _supervisor_active_lane() -> tuple[str, str] | None:
    try:
        from coru.supervisor.paths import registry_path
        from coru.supervisor.registry import active_lane_pair

        if not registry_path().is_file():
            return None
        pair = active_lane_pair()
        if pair is None:
            return None
        ide, instance = pair
        if not ide or not instance:
            return None
        return ide, instance
    except Exception:
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _instance_from_payload(
    payload: dict,
    path: "Path",
    ide: "str | None",
) -> "tuple[str, str, float] | None":
    """Return (instance, source, uptime) from a valid daemon payload, or None."""
    pid = payload.get("pid")
    if not isinstance(pid, int) or not _pid_alive(pid):
        return None
    env = payload.get("env") if isinstance(payload.get("env"), dict) else {}
    instance = str(env.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if not instance:
        instance = instance_from_socket_path(str(payload.get("socket") or "")) or ""
    if not instance:
        stem = path.name.removeprefix("koru-autopilot-").removesuffix(".daemon.json")
        instance = stem.strip()
    if not instance:
        return None
    if ide:
        inst_ide = canonical_autopilot_ide_id(instance)
        if inst_ide != normalize_ide_id(ide):
            return None
    uptime = float(payload.get("uptime_seconds") or 0.0)
    source = f"daemon-metadata:{path.name}"
    return instance, source, uptime


def _live_daemon_instance(*, project: Path, ide: str | None = None) -> tuple[str, str] | None:
    rt = project / ".planfile" / ".koru"
    if not rt.is_dir():
        return None
    best: tuple[str, str, float] | None = None
    for path in sorted(rt.glob("koru-autopilot-*.daemon.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        result = _instance_from_payload(payload, path, ide)
        if result is None:
            continue
        if best is None or result[2] >= best[2]:
            best = result
    if best is None:
        return None
    return best[0], best[1]


def _instance_matches_ide(instance: str, ide: str) -> bool:
    return canonical_autopilot_ide_id(instance) == normalize_ide_id(ide)


def _resolve_from_requested_ide(
    requested: str,
    project_root: "Path",
) -> "tuple[str | None, str] | None":
    """Try to resolve instance for a specific (non-auto) IDE. Returns (instance, source) or None."""
    from_settings = instance_from_socket_path(
        socket_path_from_ide_settings(requested, project=project_root),
    )
    if from_settings and _instance_matches_ide(from_settings, requested):
        return from_settings, f"ide-settings:{requested}"

    supervisor = _supervisor_active_lane()
    if supervisor is not None:
        sup_ide, sup_instance = supervisor
        if normalize_ide_id(sup_ide) == requested:
            return sup_instance, "supervisor:active_lane"

    live = _live_daemon_instance(project=project_root, ide=requested)
    if live is not None:
        return live
    return None



def resolve_autopilot_instance(
    *,
    requested_ide: str | None,
    project: Path | None = None,
) -> tuple[str | None, str]:
    """Return ``(instance_slug, source_label)`` for CLI socket selection."""
    project_root = (project or Path.cwd()).resolve()

    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if env_instance and env_instance.lower() not in {"", "auto"}:
        return env_instance, "env:KORU_AUTOPILOT_INSTANCE"

    requested = normalize_ide_id(requested_ide) or "auto"

    if requested and requested not in {"auto", *_CANONICAL_IDES}:
        return requested, f"cli:{requested}"

    if requested and requested != "auto":
        resolved = _resolve_from_requested_ide(requested, project_root)
        if resolved is not None:
            return resolved

    lane, lane_source = resolve_agent_lane_id(
        project_root,
        requested if requested != "auto" else "auto",
        resolve_project_lane=resolve_project_agent_lane,
    )
    if lane and lane != "auto":
        if requested == "auto" or _instance_matches_ide(lane, requested):
            return lane, f"agent-lane:{lane_source}"

    if requested and requested != "auto":
        return requested, f"cli-fallback:{requested}"

    if lane and lane != "auto":
        return lane, f"agent-lane:{lane_source}"

    return None, "unresolved"


def resolve_lane_context(
    *,
    requested_ide: str | None,
    project: Path | None = None,
) -> LaneContext:
    instance, source = resolve_autopilot_instance(
        requested_ide=requested_ide,
        project=project,
    )
    if not instance:
        path = default_socket_path()
        return LaneContext(instance="", ide="", socket_path=path, source=source)

    ide = canonical_autopilot_ide_id(instance) or instance
    previous_instance = os.environ.get("KORU_AUTOPILOT_INSTANCE")
    previous_socket = os.environ.get("KORU_AUTOPILOT_SOCKET")
    try:
        os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
        os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
        path = default_socket_path()
    finally:
        if previous_instance is None:
            os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
        else:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = previous_instance
        if previous_socket is None:
            os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
        else:
            os.environ["KORU_AUTOPILOT_SOCKET"] = previous_socket
    return LaneContext(instance=instance, ide=ide, socket_path=path, source=source)


def resolve_client_socket_path(
    args,
    *,
    project: Path | None = None,
) -> Path:
    """Socket path for :class:`~koru.autopilot.client.AutopilotClient`."""
    explicit_arg = getattr(args, "socket", None)
    if explicit_arg is not None:
        return Path(explicit_arg).expanduser().resolve()

    env_socket = (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip()
    if env_socket:
        return Path(env_socket).expanduser().resolve()

    if (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip():
        return default_socket_path()

    ctx = resolve_lane_context(
        requested_ide=getattr(args, "ide", None),
        project=project or getattr(args, "project", None) or Path.cwd(),
    )
    return ctx.socket_path


def format_lane_env_exports(
    *,
    requested_ide: str | None,
    project: Path | None = None,
) -> tuple[str, LaneContext]:
    ctx = resolve_lane_context(requested_ide=requested_ide, project=project)
    if not ctx.instance:
        raise RuntimeError("could not resolve autopilot lane instance")
    env = agent_lane_environment(ctx.instance)
    env["KORU_AUTOPILOT_IDE"] = ctx.ide
    env["KORU_AUTOPILOT_SOCKET"] = str(ctx.socket_path)
    body = format_agent_lane_exports(env)
    header = (
        f"# koru autopilot env: instance={ctx.instance} ide={ctx.ide} "
        f"source={ctx.source}\n"
        f"# eval \"$(koru autopilot env --ide {ctx.ide})\"\n"
    )
    return header + body, ctx


__all__ = [
    "LaneContext",
    "format_lane_env_exports",
    "instance_from_socket_path",
    "resolve_autopilot_instance",
    "resolve_client_socket_path",
    "resolve_lane_context",
    "socket_path_from_ide_settings",
]
