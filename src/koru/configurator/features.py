"""Schema v2 feature sections: defaults, merge, migrate, and toggle."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koru.configurator.schema import CONFIG_SCHEMA_V2, ConfigureResult
from koru.configurator.store import load_project_config, save_project_config

_TOGGLEABLE_FEATURES: tuple[str, ...] = ("vision", "mesh", "browse", "sandbox")


def default_v2_feature_sections() -> dict[str, Any]:
    """Disabled-by-default sections for observation mesh (schema v2)."""
    return {
        "vision": {
            "enabled": False,
            "interval_seconds": 30,
            "format": "webp",
            "monitors": "all",
            "windows": [],
            "redact": [r"Bearer\s+\S+", r"sk-[A-Za-z0-9]{20,}"],
        },
        "mesh": {
            "enabled": False,
            "role": "peer",
            "expose": "loopback",
            "psk_path": ".koru/keys/mesh.hmac",
            "relay_url": None,
            "discovery": "mdns",
        },
        "browse": {
            "enabled": False,
            "targets": [],
            "autoinstall": True,
            "native_messaging_host": ".koru/keys/native-host.json",
        },
        "delegate": {
            "accept": [],
            "policy_path": ".koru/policies/delegate.yaml",
        },
        "sandbox": {
            "enabled": False,
            "engine": "clonebox",
            "profile": "browse-chrome",
        },
    }


def merge_v2_feature_sections(config: dict[str, Any]) -> dict[str, Any]:
    """Return *config* with v2 feature keys filled from defaults (no overwrite)."""
    merged = dict(config)
    for key, defaults in default_v2_feature_sections().items():
        if key not in merged:
            merged[key] = defaults
            continue
        current = merged.get(key)
        if not isinstance(current, dict):
            merged[key] = defaults
            continue
        section = dict(defaults)
        section.update(current)
        merged[key] = section
    return merged


def migrate_project_config(project: Path) -> ConfigureResult:
    """Upgrade ``.koru/config.json`` to schema v2 (idempotent, no side effects)."""
    project = project.expanduser().resolve()
    previous = load_project_config(project)
    if not previous:
        msg = "no .koru/config.json — run koru configure first"
        raise ValueError(msg)
    now = datetime.now(UTC).isoformat()
    config = merge_v2_feature_sections(previous)
    config["schema"] = CONFIG_SCHEMA_V2
    config["updated_at"] = now
    path = save_project_config(project, config)
    return ConfigureResult(project=project, path=path, config=config)


def toggle_feature_sections(
    project: Path,
    *,
    enable: tuple[str, ...] = (),
    disable: tuple[str, ...] = (),
) -> ConfigureResult:
    """Flip ``enabled`` on/off for v2 feature sections (vision/mesh/browse/sandbox)."""
    project = project.expanduser().resolve()
    previous = load_project_config(project)
    if not previous:
        msg = "no .koru/config.json — run koru configure first"
        raise ValueError(msg)
    config = merge_v2_feature_sections(previous)
    config["schema"] = CONFIG_SCHEMA_V2
    for name in enable:
        if name not in _TOGGLEABLE_FEATURES:
            msg = f"unknown feature {name!r}; expected one of {_TOGGLEABLE_FEATURES}"
            raise ValueError(msg)
        config[name] = {**config.get(name, {}), "enabled": True}
    for name in disable:
        if name not in _TOGGLEABLE_FEATURES:
            msg = f"unknown feature {name!r}; expected one of {_TOGGLEABLE_FEATURES}"
            raise ValueError(msg)
        config[name] = {**config.get(name, {}), "enabled": False}
    config["updated_at"] = datetime.now(UTC).isoformat()
    path = save_project_config(project, config)
    return ConfigureResult(project=project, path=path, config=config)
