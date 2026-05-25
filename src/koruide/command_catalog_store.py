"""Persist and serve runtime IDE command catalogs from plugin hello envelopes."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

_CATALOG_FILENAME_RE = re.compile(r"^([a-z0-9_-]+)-([0-9][0-9a-zA-Z._-]*)\.json$")


def command_catalog_enabled() -> bool:
    """Whether hello ``commandCatalog`` payloads are accepted and persisted.

    Defaults to ON for plugin protocol v2 (shipped in 0.2.0). Opt-out via
    ``KORU_COMMAND_CATALOG=0`` (or ``false``/``no``/``off``) for the
    rare case where a buggy plugin payload pollutes the store.
    """
    raw = os.environ.get("KORU_COMMAND_CATALOG", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


def command_picker_enabled() -> bool:
    """Whether daemon attaches ``command_order`` to outgoing drives.

    Ships ON together with the catalog (protocol v2 plugins consume it
    via ``env.command_order``). Opt-out via ``KORU_COMMAND_PICKER=0``.
    """
    raw = os.environ.get("KORU_COMMAND_PICKER", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return command_catalog_enabled()


def _catalog_dir(project: Path | None) -> Path | None:
    if project is None:
        return None
    return project / ".planfile" / ".koru" / "command_catalogs"


def _normalize_catalog(raw: Any) -> dict[str, list[str]] | None:
    if not isinstance(raw, dict):
        return None
    buckets: dict[str, list[str]] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, list):
            buckets[key] = [item for item in value if isinstance(item, str)]
    return buckets or None


class CommandCatalogStore:
    """In-memory catalog per IDE with optional on-disk persistence."""

    def __init__(self, project: Path | None = None) -> None:
        self.project = project
        self._by_ide: dict[str, dict[str, Any]] = {}
        self._load_from_disk()

    def update(
        self,
        ide: str,
        *,
        plugin_version: str | None,
        catalog: dict[str, list[str]],
        unknown_sample: list[str] | None = None,
    ) -> None:
        unknown_chat = catalog.get("unknown_chat", [])
        sample = unknown_sample if unknown_sample is not None else unknown_chat
        entry = {
            "ide": ide,
            "plugin_version": plugin_version,
            "catalog": catalog,
            "unknown_chat_sample": [item for item in sample if isinstance(item, str)][:20],
            "updated_at": time.time(),
        }
        self._by_ide[ide] = entry
        self._persist(ide, plugin_version, entry)

    def get(self, ide: str) -> dict[str, Any] | None:
        return self._by_ide.get(ide)

    def catalog_for(self, ide: str) -> dict[str, list[str]] | None:
        entry = self.get(ide)
        if not entry:
            return None
        catalog = entry.get("catalog")
        return catalog if isinstance(catalog, dict) else None

    def unknown_chat_commands_for(self, ide: str) -> list[str]:
        entry = self.get(ide)
        if not entry:
            return []
        sample = entry.get("unknown_chat_sample")
        if isinstance(sample, list) and sample:
            return [item for item in sample if isinstance(item, str)]
        catalog = entry.get("catalog")
        if isinstance(catalog, dict):
            unknown = catalog.get("unknown_chat")
            if isinstance(unknown, list):
                return [item for item in unknown if isinstance(item, str)]
        return []

    def all_ides(self) -> list[str]:
        return sorted(self._by_ide)

    def _persist(self, ide: str, plugin_version: str | None, entry: dict[str, Any]) -> None:
        catalog_dir = _catalog_dir(self.project)
        if catalog_dir is None:
            return
        version = plugin_version or "unknown"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        path = catalog_dir / f"{ide}-{version}.json"
        try:
            path.write_text(json.dumps(entry, indent=2, sort_keys=True), encoding="utf-8")
        except OSError:
            return

    def _load_from_disk(self) -> None:
        catalog_dir = _catalog_dir(self.project)
        if catalog_dir is None or not catalog_dir.is_dir():
            return
        for path in sorted(catalog_dir.glob("*.json")):
            match = _CATALOG_FILENAME_RE.match(path.name)
            if not match:
                continue
            ide = match.group(1)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            catalog = _normalize_catalog(data.get("catalog"))
            if catalog is None:
                continue
            self._by_ide[ide] = {
                "ide": ide,
                "plugin_version": data.get("plugin_version"),
                "catalog": catalog,
                "unknown_chat_sample": data.get("unknown_chat_sample") or [],
                "updated_at": data.get("updated_at", 0),
            }


def parse_hello_command_catalog(msg_data: dict[str, Any]) -> dict[str, list[str]] | None:
    """Extract ``commandCatalog`` from a plugin hello envelope."""
    raw = msg_data.get("commandCatalog")
    return _normalize_catalog(raw)


__all__ = [
    "CommandCatalogStore",
    "command_catalog_enabled",
    "command_picker_enabled",
    "parse_hello_command_catalog",
]
