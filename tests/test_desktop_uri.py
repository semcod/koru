from __future__ import annotations

import pytest

from koruapi import desktop_uri
from koruapi.mcp_server_desktop_uri import tool_desktop_uri_handle, tool_desktop_uri_plan


def test_desktop_uri_plan_open_firefox() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")

    payload = desktop_uri.desktop_uri_plan("open firefox", platform="linux")
    assert payload["ok"] is True
    assert payload["plan"]["uri"].startswith("app://firefox/open")
    assert payload["plan"]["intent"] == "open_app"


def test_desktop_uri_handle_dry_run() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")

    payload = desktop_uri.desktop_uri_handle("capture screen", platform="linux", dry_run=True)
    assert payload["plan"]["uri"].startswith("desktop-screenshot://screen")
    assert payload["result"]["ok"] is True
    assert "grim" in payload["result"]["output"] or "scrot" in payload["result"]["output"]


def test_mcp_tool_desktop_uri_plan() -> None:
    payload = tool_desktop_uri_plan({"prompt": "focus firefox", "platform": "linux"})
    if not desktop_uri.nlp2uri_available():
        assert payload["ok"] is False
        assert "nlp2uri" in payload["error"]
        return
    assert payload["ok"] is True
    assert "desktop-window://focus" in payload["plan"]["uri"]


def test_mcp_tool_desktop_uri_handle_defaults_dry_run() -> None:
    payload = tool_desktop_uri_handle({"prompt": "open settings", "platform": "linux"})
    if not desktop_uri.nlp2uri_available():
        assert payload["ok"] is False
        return
    assert payload["result"]["ok"] is True


def test_nlp2uri_missing_message_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop_uri, "_NLP2URI_AVAILABLE", False)
    payload = desktop_uri.desktop_uri_plan("open firefox")
    assert payload["ok"] is False
    assert "koru[desktop]" in payload["error"]


def test_desktop_uri_list_getv_uris() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")
    payload = desktop_uri.desktop_uri_list_getv()
    assert payload.get("ok") is True
    assert payload.get("entries") or payload.get("by_name")


def test_desktop_uri_resolve_getv_prompt() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")
    payload = desktop_uri.desktop_uri_resolve_getv("GROQ_API_KEY")
    assert "uri" in payload or payload.get("ok") is False


def test_desktop_uri_plan_ide_chat_control_plan() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")

    payload = desktop_uri.desktop_uri_plan(
        "wyślij prompt do Cursor w tym projekcie",
        platform="linux",
    )
    assert payload["ok"] is True
    assert payload["plan"]["uri"].startswith("ide-chat://cursor/send")
    assert payload.get("control_surface") == "ide_chat"
    control_plan = payload.get("control_plan") or payload["plan"].get("control_plan")
    assert control_plan is not None
    action = control_plan["actions"][0]
    assert action["command_version"] == "koru.control.v1"
    assert action["transport"] == "koruide_socket"
    assert action["replay"]["mcp"] == "koru_ide_drive"
    assert "text=" not in payload["plan"]["uri"]


def test_desktop_uri_control_plan() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")

    payload = desktop_uri.desktop_uri_control_plan(
        "wyślij test do cursor",
        platform="linux",
    )
    assert payload["ok"] is True
    assert payload["control_plan"]["actions"][0]["transport"] == "koruide_socket"


def test_desktop_uri_control_execute_dry_run() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")

    payload = desktop_uri.desktop_uri_control_execute(
        "send hello to cursor",
        platform="linux",
        dry_run=True,
    )
    assert payload["ok"] is True
    assert payload["execution"]["results"][0]["dry_run"] is True


def test_desktop_uri_control_execute_no_submit_overrides_nlp_plan() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")

    payload = desktop_uri.desktop_uri_control_execute(
        "wyślij test do cursor",
        platform="linux",
        ide="cursor",
        submit=False,
        workspace="/tmp/koru",
        dry_run=True,
    )

    assert payload["ok"] is True
    assert "submit=false" in payload["uri"]
    assert "workspace=%2Ftmp%2Fkoru" in payload["uri"]
    action = payload["control_plan"]["actions"][0]
    assert action["submit"] is False
    assert action["workspace"] == "/tmp/koru"
    assert action["verification"]["expect_message_sent"] is False
    assert "--no-submit" in action["replay"]["cli"]


def test_desktop_uri_control_execute_direct_fallback() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")

    payload = desktop_uri.desktop_uri_control_execute(
        "probe test",
        platform="linux",
        ide="cursor",
        dry_run=True,
    )
    assert payload["ok"] is True
    assert payload.get("drive_mode") == "direct"
    assert payload["uri"].startswith("ide-chat://cursor/send")


def test_desktop_uri_list_system_uris_requires_context() -> None:
    if not desktop_uri.nlp2uri_available():
        pytest.skip("nlp2uri not installed")
    payload = desktop_uri.desktop_uri_list_system_uris()
    assert payload.get("ok") is False or "uris" in payload
