from __future__ import annotations

import json
from pathlib import Path

import pytest

from koru.ide_doctor_cli import ide_main
from koruide.command_catalog import (
    build_ide_command_catalog,
    command_catalog_for_llm,
    format_command_catalog_text,
    supported_catalog_ides,
)
from koruide.command_catalog_store import CommandCatalogStore, parse_hello_command_catalog
from koruide.command_scenario import (
    ide_command_scenario_schema,
    validate_ide_command_scenario,
)


def _ids(catalog: dict, ide: str, category: str) -> set[str]:
    return {
        row["id"]
        for row in catalog["ides"][ide]["commands"]
        if row["category"] == category
    }


def test_command_catalog_contains_supported_ide_surfaces() -> None:
    catalog = build_ide_command_catalog()

    assert set(supported_catalog_ides()) == {
        "antigravity",
        "cursor",
        "jetbrains",
        "vscode",
        "vscodium",
        "windsurf",
        "zed",
    }
    assert "workbench.action.chat.open" in _ids(catalog, "vscode", "focus_open")
    assert (
        "workbench.action.chat.openChatEmptyStateSettings"
        in _ids(catalog, "vscodium", "focus_open_avoid")
    )
    assert "composer.sendToAgent" in _ids(catalog, "cursor", "submit")
    assert "windsurf.sendTextToChat" in _ids(catalog, "windsurf", "atomic_send")
    assert "AIAssistant.OpenAIAssistantToolWindow" in _ids(catalog, "jetbrains", "focus_open")
    assert "host:return" in _ids(catalog, "zed", "submit")


def test_llm_catalog_is_compact_and_policy_driven() -> None:
    catalog = command_catalog_for_llm("cursor")

    assert set(catalog["ides"]) == {"cursor"}
    assert "runtime_verification" in catalog["policy"]
    assert "submit" in catalog["ides"]["cursor"]["categories"]
    assert "commands" not in catalog["ides"]["cursor"]


def test_command_catalog_text_marks_risk() -> None:
    text = format_command_catalog_text("vscodium", for_llm=True)

    assert "vscodium" in text
    assert "host:ctrl+return[medium]" in text


def test_unknown_catalog_ide_raises() -> None:
    with pytest.raises(ValueError):
        build_ide_command_catalog("unknown")


def test_ide_commands_cli_outputs_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = ide_main(["commands", "--ide", "cursor", "--for-llm", "--format", "json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["ides"]) == {"cursor"}
    assert "composer.sendToAgent" in {
        row["id"] for row in payload["ides"]["cursor"]["categories"]["submit"]
    }


def test_scenario_schema_exposes_steps_contract() -> None:
    schema = ide_command_scenario_schema()

    assert schema["properties"]["ide"]["enum"]
    assert "steps" in schema["required"]
    assert "paste_text" in schema["properties"]["steps"]["items"]["properties"]["action"]["enum"]


def test_validate_ide_command_scenario_accepts_known_cursor_flow() -> None:
    result = validate_ide_command_scenario(
        {
            "ide": "cursor",
            "steps": [
                {"action": "focus_input", "command": "composer.focusComposer"},
                {
                    "action": "paste_text",
                    "command": "composer.typeText",
                    "args": {"text": "hello"},
                },
                {"action": "submit", "command": "composer.sendToAgent"},
            ],
        },
    )

    assert result.ok is True
    assert result.normalized["schema"] == "koru.ide_command_scenario.v1"


def test_validate_ide_command_scenario_blocks_high_risk_without_reason() -> None:
    result = validate_ide_command_scenario(
        {
            "ide": "cursor",
            "steps": [{"action": "focus_open", "command": "composer.openAsPane"}],
        },
    )

    assert result.ok is False
    assert any("high risk" in err for err in result.errors)


def test_ide_scenario_validate_cli_outputs_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario = tmp_path / "scenario.json"
    scenario.write_text(
        json.dumps(
            {
                "ide": "windsurf",
                "steps": [{"action": "atomic_send", "command": "windsurf.sendTextToChat"}],
            },
        ),
        encoding="utf-8",
    )

    code = ide_main(["scenario-validate", str(scenario), "--format", "json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_command_catalog_store_persists_unknown_chat_bucket(tmp_path: Path) -> None:
    catalog = parse_hello_command_catalog(
        {
            "commandCatalog": {
                "submit": ["composer.sendToAgent"],
                "unknown_chat": ["cursor.chat.experimentalFoo"],
            },
        },
    )
    assert catalog is not None

    store = CommandCatalogStore(tmp_path)
    store.update("cursor", plugin_version="0.1.82", catalog=catalog)

    reloaded = CommandCatalogStore(tmp_path)
    assert reloaded.catalog_for("cursor") == catalog
    assert reloaded.unknown_chat_commands_for("cursor") == ["cursor.chat.experimentalFoo"]
