"""Registry of per-IDE adapters."""

from __future__ import annotations

from koru.ide_adapters.vscode_family import VSCodeFamilyAdapter

_ADAPTERS: dict[str, VSCodeFamilyAdapter] = {
    "cursor": VSCodeFamilyAdapter(
        ide_id="cursor",
        label="Cursor",
        requires_trusted_publisher=True,
    ),
    "vscode": VSCodeFamilyAdapter(
        ide_id="vscode",
        label="VS Code",
        requires_trusted_publisher=True,
    ),
    "vscodium": VSCodeFamilyAdapter(
        ide_id="vscodium",
        label="VSCodium",
        requires_trusted_publisher=True,
    ),
    "windsurf": VSCodeFamilyAdapter(
        ide_id="windsurf",
        label="Windsurf",
        requires_trusted_publisher=False,
    ),
    "antigravity": VSCodeFamilyAdapter(
        ide_id="antigravity",
        label="Antigravity",
        requires_trusted_publisher=False,
    ),
}


def get_adapter(ide: str) -> VSCodeFamilyAdapter | None:
    return _ADAPTERS.get(ide)


def supported_adapter_ids() -> tuple[str, ...]:
    return tuple(_ADAPTERS.keys())
