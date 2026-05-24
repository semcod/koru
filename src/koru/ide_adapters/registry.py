"""Registry of per-IDE diagnostic adapters.

Adapters for IDEs that have their own ``koruide.ides.<ide>`` strategy are
constructed from that strategy so their plugin policy (trusted publisher,
strict ack, etc.) cannot drift between the strategy and the diagnostic layer.

IDEs without a dedicated strategy module fall back to the historical
``VSCodeFamilyAdapter`` construction (vscode, vscodium, windsurf,
antigravity) so the diagnostic surface remains intact during the migration.
"""

from __future__ import annotations

from koru.ide_adapters.vscode_family import VSCodeFamilyAdapter
from koruide.ides import get_strategy as _get_ide_strategy

_LEGACY_ADAPTER_DEFS: tuple[tuple[str, str, bool], ...] = (
    # (ide_id, label, requires_trusted_publisher)
    ("vscode", "VS Code", True),
    ("vscodium", "VSCodium", True),
    ("windsurf", "Windsurf", False),
    ("antigravity", "Antigravity", False),
)


def _adapter_from_strategy(ide_id: str) -> VSCodeFamilyAdapter | None:
    strategy = _get_ide_strategy(ide_id)
    if strategy is None or not strategy.plugin.supports_vscode_extension:
        return None
    return VSCodeFamilyAdapter(
        ide_id=strategy.id,
        label=strategy.label,
        requires_trusted_publisher=strategy.plugin.requires_trusted_publisher,
    )


def _build_adapters() -> dict[str, VSCodeFamilyAdapter]:
    adapters: dict[str, VSCodeFamilyAdapter] = {}
    # IDEs with a dedicated strategy take precedence.
    for ide_id in ("cursor",):
        adapter = _adapter_from_strategy(ide_id)
        if adapter is not None:
            adapters[ide_id] = adapter
    # Legacy entries for IDEs not yet extracted to ``koruide.ides``.
    for ide_id, label, requires_trusted_publisher in _LEGACY_ADAPTER_DEFS:
        if ide_id in adapters:
            continue
        adapters[ide_id] = VSCodeFamilyAdapter(
            ide_id=ide_id,
            label=label,
            requires_trusted_publisher=requires_trusted_publisher,
        )
    return adapters


_ADAPTERS: dict[str, VSCodeFamilyAdapter] = _build_adapters()


def get_adapter(ide: str) -> VSCodeFamilyAdapter | None:
    return _ADAPTERS.get(ide)


def supported_adapter_ids() -> tuple[str, ...]:
    return tuple(_ADAPTERS.keys())
