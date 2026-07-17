"""Lane / IDE instance resolution helpers extracted from ``coru.cli``.

Workspace settings, project ``.koru/<ide>/settings.json``, and instance/IDE
normalization used by the thin client surface.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from coru.cli_reexec import repo_root as _repo_root

VALID_AUTOPILOT_IDES = frozenset(
    {"auto", "vscode", "vscodium", "cursor", "windsurf", "jetbrains", "zed", "antigravity"}
)

WORKSPACE_SETTINGS_BY_IDE: dict[str, Path] = {
    "cursor": Path(".cursor") / "settings.json",
    "vscode": Path(".vscode") / "settings.json",
    "vscodium": Path(".vscode-oss") / "settings.json",
    "windsurf": Path(".windsurf") / "settings.json",
    "antigravity": Path(".antigravity") / "settings.json",
}

PROJECT_IDE_SETTINGS_NAME = "settings.json"

LANE_ENV_KEYS = ("KORU_AUTOPILOT_IDE", "KORU_AUTOPILOT_INSTANCE", "KORU_AUTOPILOT_SOCKET")
STRICT_PLUGIN_ENV_KEYS = (
    "KORU_STRICT_PLUGIN_VERSION",
    "KORU_STRICT_PLUGIN_ACK",
    "KORU_PLUGIN_VERSION_POLICY",
)
LANE_SESSION_ENV_KEYS = (*LANE_ENV_KEYS, *STRICT_PLUGIN_ENV_KEYS)


def ide_from_instance(instance: str) -> str | None:
    normalized = instance.strip().lower()
    if not normalized or normalized == "auto":
        return None
    if normalized in VALID_AUTOPILOT_IDES:
        return normalized
    prefix = normalized.split("-", 1)[0]
    return prefix if prefix in VALID_AUTOPILOT_IDES else None


def instance_matches_ide(instance: str, ide: str) -> bool:
    return ide_from_instance(instance) == ide


def normalize_lane_pair(ide: str, instance: str) -> tuple[str, str]:
    """Make lane resolution deterministic: explicit instance wins over IDE hint."""
    instance_ide = ide_from_instance(instance)
    if instance_ide and ide and ide != "auto" and ide != instance_ide:
        print(
            f"[coru] lane normalized from instance: ide {ide} -> {instance_ide} "
            f"(instance={instance})",
            file=sys.stderr,
        )
        return instance_ide, instance
    if ide == "auto" and instance_ide:
        return instance_ide, instance
    return ide, instance


def workspace_settings_path_for_ide(ide: str) -> Path | None:
    root = _repo_root()
    rel = WORKSPACE_SETTINGS_BY_IDE.get((ide or "").strip().lower())
    if root is None or rel is None:
        return None
    return root / rel


def workspace_socket_path_for_ide(ide: str) -> str | None:
    path = workspace_settings_path_for_ide(ide)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    raw = payload.get("koruAutopilot.socketPath")
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    return value or None


def instance_from_socket_path(socket_path: str | None) -> str | None:
    if not socket_path:
        return None
    name = Path(socket_path).name
    match = re.match(r"^koru-autopilot-([A-Za-z0-9_-]+)\.sock$", name)
    if not match:
        return None
    instance = match.group(1).strip().lower()
    return instance or None


def workspace_lane_hint(preferred_ide: str | None = None) -> tuple[str | None, str | None]:
    order: list[str] = []
    preferred = (preferred_ide or "").strip().lower()
    if preferred in WORKSPACE_SETTINGS_BY_IDE:
        order.append(preferred)
    for ide in WORKSPACE_SETTINGS_BY_IDE:
        if ide not in order:
            order.append(ide)

    for ide in order:
        instance = instance_from_socket_path(workspace_socket_path_for_ide(ide))
        if instance:
            return ide_from_instance(instance) or ide, instance
    return None, None


def project_ide_settings_path(ide: str) -> Path | None:
    root = _repo_root()
    ide_id = (ide or "").strip().lower()
    if root is None or ide_id not in VALID_AUTOPILOT_IDES or ide_id == "auto":
        return None
    return root / ".koru" / ide_id / PROJECT_IDE_SETTINGS_NAME


def load_project_ide_settings(ide: str) -> dict[str, Any]:
    path = project_ide_settings_path(ide)
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def project_ide_settings_lane(ide: str) -> tuple[str, str] | None:
    ide_id = (ide or "").strip().lower()
    if ide_id not in VALID_AUTOPILOT_IDES or ide_id == "auto":
        return None
    settings = load_project_ide_settings(ide_id)
    raw_instance = settings.get("instance") or settings.get("agent_lane") or settings.get("lane")
    if isinstance(raw_instance, str) and raw_instance.strip():
        return normalize_lane_pair(ide_id, raw_instance.strip())
    raw_socket = settings.get("socket") or settings.get("socket_path") or settings.get("socketPath")
    if isinstance(raw_socket, str):
        instance = instance_from_socket_path(raw_socket)
        if instance:
            return normalize_lane_pair(ide_id, instance)
    return None


def remember_project_ide_settings(ide: str, instance: str) -> None:
    ide_id = (ide or "").strip().lower()
    instance_id = (instance or "").strip()
    path = project_ide_settings_path(ide_id)
    if path is None or not instance_id or ide_id == "auto":
        return
    existing = load_project_ide_settings(ide_id)
    payload: dict[str, Any] = dict(existing)
    payload["ide"] = ide_id
    payload["instance"] = instance_id
    root = _repo_root()
    if root is not None:
        payload["project"] = str(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception:
        return


def apply_strict_plugin_policy_defaults(env: dict[str, str], *, force: bool = False) -> None:
    if force or (
        env.get("KORU_STRICT_PLUGIN_VERSION") is None
        and env.get("KORU_PLUGIN_VERSION_POLICY") is None
    ):
        env["KORU_STRICT_PLUGIN_VERSION"] = "1"
    if force or env.get("KORU_STRICT_PLUGIN_ACK") is None:
        env["KORU_STRICT_PLUGIN_ACK"] = "1"


def lane_subprocess_env(
    ide: str, instance: str, *, base: Mapping[str, str] | None = None
) -> dict[str, str]:
    env = dict(base or os.environ)
    env["KORU_AUTOPILOT_IDE"] = ide
    env["KORU_AUTOPILOT_INSTANCE"] = instance
    env.pop("KORU_AUTOPILOT_SOCKET", None)
    apply_strict_plugin_policy_defaults(env)
    return env


# Historical private names for coru.cli re-exports.
_VALID_AUTOPILOT_IDES = VALID_AUTOPILOT_IDES
_WORKSPACE_SETTINGS_BY_IDE = WORKSPACE_SETTINGS_BY_IDE
_PROJECT_IDE_SETTINGS_NAME = PROJECT_IDE_SETTINGS_NAME
_LANE_SESSION_ENV_KEYS = LANE_SESSION_ENV_KEYS
_instance_matches_ide = instance_matches_ide
_ide_from_instance = ide_from_instance
_workspace_settings_path_for_ide = workspace_settings_path_for_ide
_workspace_socket_path_for_ide = workspace_socket_path_for_ide
_instance_from_socket_path = instance_from_socket_path
_workspace_lane_hint = workspace_lane_hint
_project_ide_settings_path = project_ide_settings_path
_load_project_ide_settings = load_project_ide_settings
_project_ide_settings_lane = project_ide_settings_lane
_remember_project_ide_settings = remember_project_ide_settings
_normalize_lane_pair = normalize_lane_pair
_lane_subprocess_env = lane_subprocess_env
_apply_strict_plugin_policy_defaults = apply_strict_plugin_policy_defaults

__all__ = [
    "LANE_SESSION_ENV_KEYS",
    "VALID_AUTOPILOT_IDES",
    "WORKSPACE_SETTINGS_BY_IDE",
    "apply_strict_plugin_policy_defaults",
    "ide_from_instance",
    "instance_from_socket_path",
    "instance_matches_ide",
    "lane_subprocess_env",
    "load_project_ide_settings",
    "normalize_lane_pair",
    "project_ide_settings_lane",
    "project_ide_settings_path",
    "remember_project_ide_settings",
    "workspace_lane_hint",
    "workspace_settings_path_for_ide",
    "workspace_socket_path_for_ide",
]
