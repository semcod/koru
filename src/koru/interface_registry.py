"""Machine-readable registry of Koru control/observation interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class InterfaceVerification:
    mode: str
    can_confirm_submit: bool


@dataclass(frozen=True)
class InterfaceDescriptor:
    id: str
    family: str
    direction: str
    transport: str
    surface: str
    authority: str
    write_mode: str
    verification: InterfaceVerification
    blocking_modes: tuple[str, ...]
    operator_recovery: tuple[str, ...]
    primary_code: tuple[str, ...]


@dataclass(frozen=True)
class InterfaceRegistry:
    schema: str
    interfaces: tuple[InterfaceDescriptor, ...]


def interface_registry_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "interfaces" / "koru-interface-registry.yaml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("docs/interfaces/koru-interface-registry.yaml not found")


def _as_str_tuple(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(item).strip() for item in raw if str(item).strip())


def _parse_verification(raw: object) -> InterfaceVerification | None:
    if not isinstance(raw, dict):
        return None
    mode = str(raw.get("mode") or "").strip()
    if not mode:
        return None
    return InterfaceVerification(
        mode=mode,
        can_confirm_submit=bool(raw.get("can_confirm_submit")),
    )


def _parse_descriptor(raw: object) -> InterfaceDescriptor | None:
    if not isinstance(raw, dict):
        return None
    verification = _parse_verification(raw.get("verification"))
    if verification is None:
        return None
    required = (
        "id",
        "family",
        "direction",
        "transport",
        "surface",
        "authority",
        "write_mode",
    )
    values: dict[str, str] = {}
    for key in required:
        value = str(raw.get(key) or "").strip()
        if not value:
            return None
        values[key] = value
    return InterfaceDescriptor(
        id=values["id"],
        family=values["family"],
        direction=values["direction"],
        transport=values["transport"],
        surface=values["surface"],
        authority=values["authority"],
        write_mode=values["write_mode"],
        verification=verification,
        blocking_modes=_as_str_tuple(raw.get("blocking_modes")),
        operator_recovery=_as_str_tuple(raw.get("operator_recovery")),
        primary_code=_as_str_tuple(raw.get("primary_code")),
    )


def load_interface_registry(path: Path | None = None) -> InterfaceRegistry:
    registry_path = path or interface_registry_path()
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("interface registry must be a mapping")
    schema = str(payload.get("schema") or "").strip()
    if not schema:
        raise ValueError("interface registry schema is missing")
    raw_items = payload.get("interfaces")
    if not isinstance(raw_items, list):
        raise ValueError("interface registry interfaces must be a list")
    parsed: list[InterfaceDescriptor] = []
    for item in raw_items:
        descriptor = _parse_descriptor(item)
        if descriptor is None:
            raise ValueError(f"invalid interface descriptor: {item!r}")
        parsed.append(descriptor)
    return InterfaceRegistry(schema=schema, interfaces=tuple(parsed))


def iter_interfaces() -> tuple[InterfaceDescriptor, ...]:
    return load_interface_registry().interfaces


def list_interface_ids() -> tuple[str, ...]:
    return tuple(item.id for item in iter_interfaces())


def get_interface_descriptor(interface_id: str) -> InterfaceDescriptor | None:
    key = interface_id.strip()
    for item in iter_interfaces():
        if item.id == key:
            return item
    return None


def summarize_interfaces_by_family() -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in iter_interfaces():
        counts[item.family] = counts.get(item.family, 0) + 1
    return counts


__all__ = [
    "InterfaceDescriptor",
    "InterfaceRegistry",
    "InterfaceVerification",
    "get_interface_descriptor",
    "interface_registry_path",
    "iter_interfaces",
    "list_interface_ids",
    "load_interface_registry",
    "summarize_interfaces_by_family",
]
