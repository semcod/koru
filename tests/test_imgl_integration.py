"""Tests for imgl vision fallback integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from koru import autonomous_cycle_gate
from koru.agent_backend_runtime import ImglDesktopBackend, build_agent_backend
from koru.integrations import imgl_client
from koruapi import desktop_uri


def test_imgl_fallback_disabled_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_IMGL_FALLBACK", raising=False)
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: False)
    assert autonomous_cycle_gate.try_imgl_gui_fallback("hello", submit=True, ide="cursor") is None


def test_imgl_fallback_auto_enables_for_jetbrains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_IMGL_FALLBACK", raising=False)
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)
    assert imgl_client.imgl_fallback_enabled(ide="jetbrains") is True
    assert imgl_client.imgl_prefer_before_keyboard("jetbrains") is True


def test_imgl_fallback_explicit_off_blocks_jetbrains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_IMGL_FALLBACK", "0")
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)
    assert imgl_client.imgl_fallback_enabled(ide="jetbrains") is False


def test_imgl_fallback_calls_send_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_IMGL_FALLBACK", "1")
    calls: list[dict] = []

    def fake_send_chat(prompt: str, *, ide: str, submit: bool, dry_run=None):
        calls.append({"prompt": prompt, "ide": ide, "submit": submit})
        return {"ok": True, "backend": "imgl", "submitted": submit}

    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)
    monkeypatch.setattr(imgl_client, "send_chat", fake_send_chat)

    reply = autonomous_cycle_gate.try_imgl_gui_fallback(
        "continue refactor",
        submit=True,
        ide="cursor",
    )
    assert reply is not None
    assert reply["ok"] is True
    assert reply["fallback_from"] == "plugin"
    assert calls == [{"prompt": "continue refactor", "ide": "cursor", "submit": True}]


def test_imgl_backend_dry_run() -> None:
    backend = ImglDesktopBackend(dry_run=True)
    reply = backend.send_chat(Path("/tmp"), "hello", ide="cursor", submit=True)
    assert reply["ok"] is True
    assert reply["dry_run"] is True


def test_build_agent_backend_imgl_alias() -> None:
    backend = build_agent_backend(backend_id="imgl")
    assert isinstance(backend, ImglDesktopBackend)


def test_is_ui_prompt() -> None:
    assert imgl_client.is_ui_prompt("kliknij Projects")
    assert imgl_client.is_ui_prompt("wpisz test w chat")
    assert not imgl_client.is_ui_prompt("open firefox")


def test_desktop_uri_routes_to_imgl_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_IMGL_DESKTOP", "1")

    def fake_execute(prompt: str, **kwargs):
        return {"ok": True, "backend": "imgl", "output": prompt}

    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)
    monkeypatch.setattr(imgl_client, "execute_nl", fake_execute)

    payload = desktop_uri.desktop_uri_handle("kliknij Save", dry_run=True)
    assert payload["transport"] == "imgl"
    assert payload["ok"] is True


def test_desktop_uri_explicit_transport_imgl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        imgl_client,
        "execute_nl",
        lambda prompt, **kwargs: {"ok": True, "backend": "imgl"},
    )
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)

    payload = desktop_uri.desktop_uri_handle(
        "anything",
        dry_run=True,
        transport="imgl",
    )
    assert payload["transport"] == "imgl"


def test_imgl_command_records_surface(tmp_path: Path) -> None:
    from koru.control_commands import control_command_replay_plan, imgl_command

    event = imgl_command(
        tmp_path,
        corr="test-corr",
        operation="UI_TYPE",
        prompt="wpisz hello w Chat input",
        window="region-bottom",
    )
    plan = control_command_replay_plan(event)
    assert plan["surface"] == "desktop_gui"
    assert plan["transport"] == "imgl"
    assert plan["interface_id"] == "imgl_rest_or_nlp2imgl"


def test_mcp_koru_imgl_execute_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    from koruapi.mcp_server_desktop_uri import tool_koru_imgl_execute

    monkeypatch.setattr(
        imgl_client,
        "execute_nl",
        lambda prompt, **kwargs: {"ok": True, "backend": "imgl", "output": prompt},
    )
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)

    payload = tool_koru_imgl_execute({"prompt": "kliknij Save", "dry_run": True})
    assert payload["ok"] is True
    assert payload["transport"] == "imgl"


def test_desktop_uri_plan_suggests_imgl_for_ui_prompt() -> None:
    payload = desktop_uri.desktop_uri_plan("kliknij Projects", platform="linux")
    assert payload.get("ok") is True
    assert payload.get("suggested_transport") == "imgl"
    assert payload.get("transport") == "imgl"


def test_drive_retry_prefers_imgl_before_daemon_for_jetbrains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autonomous_cycle_drive_retry import _invoke_client_autopilot_drive

    class OkClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": True, "backend": "os_injector"}

    order: list[str] = []

    def fake_imgl(*_args, **_kwargs):
        order.append("imgl")
        return {"ok": True, "backend": "imgl"}

    monkeypatch.setattr(
        "koru.integrations.imgl_client.imgl_prefer_before_keyboard",
        lambda ide: ide == "jetbrains",
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_imgl_gui_fallback",
        fake_imgl,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_nlp2uri_ide_control",
        lambda *_a, **_k: None,
    )

    reply, ok = _invoke_client_autopilot_drive(
        OkClient(),
        prompt="hello",
        submit=True,
        autopilot_ide="jetbrains",
        require_plugin=False,
    )
    assert ok is True
    assert reply["backend"] == "imgl"
    assert order == ["imgl"]


def test_drive_retry_prefers_imgl_before_gillm(monkeypatch: pytest.MonkeyPatch) -> None:
    from koru.autonomous_cycle_drive_retry import _invoke_client_autopilot_drive

    class FailingClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": False, "backend": "plugin", "message": "fail"}

    order: list[str] = []

    def fake_imgl(*_args, **_kwargs):
        order.append("imgl")
        return {"ok": True, "backend": "imgl"}

    def fake_gillm(*_args, **_kwargs):
        order.append("gillm")
        return {"ok": True, "backend": "gillm"}

    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_imgl_gui_fallback",
        fake_imgl,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_gillm_gui_fallback",
        fake_gillm,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_os_injector_fallback",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_nlp2uri_ide_control",
        lambda *_a, **_k: None,
    )

    reply, ok = _invoke_client_autopilot_drive(
        FailingClient(),
        prompt="hello",
        submit=True,
        autopilot_ide="cursor",
        require_plugin=False,
    )
    assert ok is True
    assert reply["backend"] == "imgl"
    assert order == ["imgl"]


def test_build_operation_step_from_type_message() -> None:
    from koru.integrations.imgl_autodiag import build_operation_step

    result = {
        "ok": True,
        "verb": "TYPE",
        "output": "type 'test' @ (775, 1090)",
        "data": {
            "execute": {
                "ok": True,
                "dry_run": False,
                "method": "xdotool",
                "message": "type 'test' @ (775, 1090)",
            }
        },
    }
    step = build_operation_step(result, dry_run=False)
    assert step["executed"] is True
    assert step["text_typed"] == "test"
    assert step["coordinates"] == [775, 1090]
    assert step["method"] == "xdotool"


def test_build_execute_report_dry_run() -> None:
    from koru.integrations.imgl_autodiag import build_execute_report

    capture = {"verdict": "real_ui", "scene_class": "ui_with_text", "ok": True}
    result = {
        "ok": True,
        "output": "type 'x' @ (1, 2)",
        "data": {"execute": {"ok": True, "dry_run": True, "method": "dry-run"}},
    }
    report = build_execute_report(
        prompt="wpisz x",
        image="/tmp/s.png",
        window="region-bottom",
        dry_run=True,
        capture=capture,
        result=result,
    )
    assert report["verdict"] == "planned_ok"
    assert report["checks"]["operation_executed"] is False


def test_render_report_formats() -> None:
    from koru.integrations.imgl_autodiag import build_execute_report, render_report

    payload = build_execute_report(
        prompt="wpisz test",
        image="/tmp/a.png",
        window="region-bottom",
        dry_run=False,
        capture={"verdict": "real_ui", "path": "/tmp/a.png", "summary": "UI ok"},
        result={
            "ok": True,
            "output": "type 'test' @ (1, 2)",
            "diagnostics": {"verdict": "executed_ok"},
            "data": {"execute": {"ok": True, "method": "xdotool", "dry_run": False}},
        },
    )
    md = render_report(payload, "markdown")
    assert "# imgl" in md
    assert "real_ui" in md
    js = render_report(payload, "json")
    assert '"verdict": "executed_ok"' in js
    assert "diagnostics" not in js
    yml = render_report(payload, "yaml")
    assert "verdict:" in yml


def test_execute_nl_blocks_stale_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)
    monkeypatch.setenv("KORU_IMGL_STALE_BLOCK", "1")

    def fake_diag(_path, **_kwargs):
        return {
            "ok": False,
            "verdict": "stale_capture",
            "is_fresh": False,
            "age_seconds": 120.0,
            "max_age_seconds": 60,
            "summary": "zrzut przestarzały",
        }

    monkeypatch.setattr("imgl.autodiag.diagnose_capture", fake_diag)
    monkeypatch.setattr(
        "imgl.freshness.sync_vql_cache_with_image",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(
        "nlp2imgl.control.apply_nl",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    out = imgl_client.execute_nl(
        "wpisz test",
        image="/tmp/koru-imgl-screen.png",
        dry_run=False,
        with_diagnostics=True,
    )
    assert out["ok"] is False
    assert out["blocked_by"] == "stale_capture"
    assert out["diagnostics"]["verdict"] == "stale_capture_error"


def test_image_freshness_uses_sidecar(tmp_path: Path) -> None:
    from koru.integrations.imgl_autodiag import capture_sidecar_path, image_freshness

    image = tmp_path / "screen.png"
    image.write_bytes(b"png")
    old = image.stat().st_mtime
    import os
    import time

    os.utime(image, (old - 7200, old - 7200))
    sidecar = capture_sidecar_path(image)
    sidecar.write_text(str(time.time()), encoding="utf-8")

    fresh = image_freshness(image)
    assert fresh["is_fresh"] is True
    assert fresh["capture_source"] == "sidecar"


def test_vql_cache_paths_use_png_stem() -> None:
    from koru.integrations.imgl_autodiag import clear_vql_cache, vql_cache_paths

    paths = vql_cache_paths(Path("/tmp/koru-imgl-screen.png"))
    assert [p.name for p in paths] == [
        "koru-imgl-screen.vql.imgl.json",
        "koru-imgl-screen.vql.json",
    ]
    for path in paths:
        path.write_text("{}", encoding="utf-8")
    removed = clear_vql_cache(Path("/tmp/koru-imgl-screen.png"))
    assert len(removed) == 2


def test_execute_nl_blocks_blank_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)
    monkeypatch.setattr(imgl_client, "_IMGL_DIRECT", True)
    monkeypatch.setenv("KORU_IMGL_DIAG_BLOCK", "1")

    def fake_diag(_path, **_kwargs):
        return {
            "ok": True,
            "verdict": "blank_capture",
            "scene_class": "empty_dark_screen",
            "summary": "pusty ekran",
        }

    monkeypatch.setattr("imgl.autodiag.diagnose_capture", fake_diag)
    monkeypatch.setattr(
        "imgl.freshness.sync_vql_cache_with_image",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(
        "nlp2imgl.control.apply_nl",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    out = imgl_client.execute_nl(
        "wpisz test",
        image="/tmp/koru-imgl-screen.png",
        dry_run=False,
        with_diagnostics=True,
    )
    assert out["ok"] is False
    assert out["blocked_by"] == "capture_diagnose"
    assert out["diagnostics"]["verdict"] == "blank_capture_error"


def test_desktop_uri_imgl_includes_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(imgl_client, "imgl_available", lambda: True)

    def fake_execute(prompt: str, **kwargs):
        return {
            "ok": True,
            "backend": "imgl",
            "output": prompt,
            "diagnostics": {
                "verdict": "planned_ok",
                "operation": {"planned": prompt},
            },
        }

    monkeypatch.setattr(imgl_client, "execute_nl", fake_execute)
    payload = desktop_uri.desktop_uri_imgl_execute("wpisz x", dry_run=True)
    assert payload.get("diagnostics") is not None
    assert payload["verdict"] == "planned_ok"
