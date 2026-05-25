"""Tests for koruapi package."""

from __future__ import annotations

from pathlib import Path

import pytest

from koruapi import list_integrations
from koruapi.cli import main as koru_api_main
from koruapi.invoke import InvokeError, invoke_integration


def test_list_integrations_has_dsl_and_scan() -> None:
    ids = {s.id for s in list_integrations()}
    assert "dsl.to_library" in ids
    assert "scan.apply" in ids
    assert "autopilot.drive" in ids
    assert "ide.commands" in ids
    assert "ide.scenario_validate" in ids


def test_dsl_roundtrip_invoke() -> None:
    result = invoke_integration(
        "dsl.roundtrip",
        project=Path("."),
        body={"dsl": "GOAL: t\nSET a=1\n"},
    )
    assert result["ok"] is True


def test_unknown_integration() -> None:
    with pytest.raises(InvokeError):
        invoke_integration("no.such.integration", project=Path("."))


def test_koru_api_main_uses_process_argv_for_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["koru-api", "--help"])

    with pytest.raises(SystemExit) as exc:
        koru_api_main()

    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_koru_api_main_uses_process_argv_for_version(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["koru-api", "--version"])

    with pytest.raises(SystemExit) as exc:
        koru_api_main()

    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("koru-api ")


def test_wired_handlers_are_catalogued() -> None:
    from koruapi.invoke_handlers import INTEGRATION_HANDLERS

    catalog_ids = {s.id for s in list_integrations()}
    assert catalog_ids.issuperset(INTEGRATION_HANDLERS.keys())


def test_tool_list_tickets_status_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    from koruapi.mcp_server import (
        _serialize_mcp_ticket,
        _tickets_for_status_filter,
        tool_list_tickets,
    )

    ctx = {
        "all_tickets": [
            {"id": "A", "name": "Open", "status": "open"},
            {"id": "B", "name": "Done", "status": "done"},
            {"id": "C", "name": "WIP", "status": "in_progress"},
        ],
        "open_tickets": [{"id": "A", "name": "Open", "status": "open"}],
    }
    assert [t["id"] for t in _tickets_for_status_filter(ctx, "open")] == ["A"]
    assert len(_tickets_for_status_filter(ctx, "all")) == 3
    assert _serialize_mcp_ticket(ctx["all_tickets"][0])["title"] == "Open"

    monkeypatch.setattr(
        "koru.context.build_context",
        lambda **_: ctx,
    )
    out = tool_list_tickets({"project_root": ".", "status": "done"})
    assert out["tickets"][0]["id"] == "B"


def test_koru_api_main_dispatch_table_covers_all_subparser_actions() -> None:
    """All argparse subparsers must have a corresponding handler in _ACTIONS."""
    from koruapi.cli import _ACTIONS, _build_parser

    parser = _build_parser()
    subparser_actions = next(
        a for a in parser._actions if hasattr(a, "choices") and a.choices
    )
    declared = set(subparser_actions.choices.keys())
    assert declared == set(_ACTIONS.keys()), (
        f"subparsers and _ACTIONS keys diverged: "
        f"only-in-subparsers={declared - set(_ACTIONS.keys())} "
        f"only-in-actions={set(_ACTIONS.keys()) - declared}"
    )


def test_koru_api_main_list_action_emits_integrations(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Direct test for the extracted _action_list handler via main()."""
    monkeypatch.setattr("sys.argv", ["koru-api", "list"])
    rc = koru_api_main()
    assert rc == 0
    out = capsys.readouterr().out
    assert '"integrations"' in out


def test_openapi_document_lists_invoke_path() -> None:
    from koruapi.openapi import build_openapi_document

    doc = build_openapi_document()
    assert doc["openapi"].startswith("3.")
    assert "/api/v1/invoke" in doc["paths"]
    assert (
        "dsl.roundtrip"
        in doc["paths"]["/api/v1/invoke"]["post"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["properties"]["integration_id"]["enum"]
    )
    assert "/api/v1/ide/commands" in doc["paths"]
    assert "/api/v1/ide/scenario-schema" in doc["paths"]


def test_ide_command_catalog_invoke() -> None:
    result = invoke_integration(
        "ide.commands",
        project=Path("."),
        method="llm",
        body={"ide": "cursor"},
    )

    assert result["ok"] is True
    assert set(result["catalog"]["ides"]) == {"cursor"}


def test_ide_scenario_validate_invoke() -> None:
    result = invoke_integration(
        "ide.scenario_validate",
        project=Path("."),
        body={
            "scenario": {
                "ide": "cursor",
                "steps": [{"action": "submit", "command": "composer.sendToAgent"}],
            },
        },
    )

    assert result["ok"] is True
    assert result["validation"]["normalized"]["ide"] == "cursor"
