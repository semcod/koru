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
