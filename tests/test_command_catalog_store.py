from __future__ import annotations

import json

from koruide.command_catalog_store import (
    CommandCatalogStore,
    command_catalog_enabled,
    parse_hello_command_catalog,
)


def test_command_catalog_enabled_defaults_on_for_v2_plugins(monkeypatch) -> None:
    """Plugin 0.2.x ships protocol v2 by default; catalog is on unless opted out."""
    monkeypatch.delenv("KORU_COMMAND_CATALOG", raising=False)
    assert command_catalog_enabled() is True
    monkeypatch.setenv("KORU_COMMAND_CATALOG", "0")
    assert command_catalog_enabled() is False
    monkeypatch.setenv("KORU_COMMAND_CATALOG", "1")
    assert command_catalog_enabled() is True


def test_parse_hello_command_catalog() -> None:
    catalog = parse_hello_command_catalog(
        {
            "commandCatalog": {
                "submit": ["workbench.action.chat.submit"],
                "paste": ["composer.startComposerPrompt2"],
            }
        }
    )
    assert catalog is not None
    assert catalog["submit"] == ["workbench.action.chat.submit"]


def test_command_catalog_store_persists(tmp_path) -> None:
    store = CommandCatalogStore(tmp_path)
    store.update(
        "cursor",
        plugin_version="0.2.0",
        catalog={"submit": ["composer.sendToAgent", "workbench.action.chat.submit"]},
        unknown_sample=["cursor.experimental"],
    )
    reloaded = CommandCatalogStore(tmp_path)
    catalog = reloaded.catalog_for("cursor")
    assert catalog is not None
    assert "workbench.action.chat.submit" in catalog["submit"]
    path = tmp_path / ".planfile" / ".koru" / "command_catalogs" / "cursor-0.2.0.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["ide"] == "cursor"
