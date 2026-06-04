"""Tests for Gillm GuiDriver fallback in the autonomous drive path."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import koru.autonomous as autonomous_mod
from koru import autonomous_cycle_gate
from koru.autonomy import env as autonomy_env


def test_plugin_not_required_when_gillm_fallback_enabled(monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_GILLM_FALLBACK", "1")
    assert autonomy_env.plugin_required_for_ide("cursor") is False


def test_try_gillm_gui_fallback_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_GILLM_FALLBACK", raising=False)
    assert (
        autonomous_cycle_gate.try_gillm_gui_fallback(
            "hello",
            submit=True,
            ide="cursor",
        )
        is None
    )


def test_try_gillm_gui_fallback_uses_build_client(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_GILLM_FALLBACK", "1")
    calls: list[dict] = []

    def fake_build(*, project=None, dry_run=False):
        calls.append({"project": project, "dry_run": dry_run})

        class Client:
            def drive(self, text, *, submit=True, ide="auto", **kwargs):
                return {
                    "ok": True,
                    "backend": "dry_run",
                    "message": text,
                    "submitted": submit,
                    "tool_id": ide,
                }

        return Client()

    reply = autonomous_cycle_gate.try_gillm_gui_fallback(
        "continue",
        submit=True,
        ide="cursor",
        project=Path("/tmp/proj"),
        build_client_fn=fake_build,
    )
    assert reply is not None
    assert reply["ok"] is True
    assert reply["fallback_from"] == "plugin"
    assert calls == [{"project": Path("/tmp/proj"), "dry_run": False}]


def _force_idle_drive_prompt(monkeypatch) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "resolve_idle_drive_prompt",
        lambda *_args, **_kwargs: ("idle prompt", "idle_ticket_prompt"),
    )


def test_run_cycle_autopilot_uses_gillm_fallback_before_os_injector(
    tmp_path,
    monkeypatch,
) -> None:
    class FailingClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": False, "backend": "plugin", "message": "submit_unverified"}

    monkeypatch.setattr("koru.autonomy.env.detect_terminal_host_ide_id", lambda: None)
    monkeypatch.setenv("KORU_AUTOPILOT_GILLM_FALLBACK", "1")
    monkeypatch.setenv("KORU_OS_INJECTOR_PROFILE", "cursor")
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
            last_message="",
            waiting=[],
        ),
    )
    _force_idle_drive_prompt(monkeypatch)

    gillm_calls: list[dict] = []
    injector_calls: list[dict] = []

    monkeypatch.setattr(
        autonomous_mod,
        "_try_gillm_gui_fallback",
        lambda prompt, *, submit, ide, project=None: (
            gillm_calls.append(
                {"prompt": prompt, "submit": submit, "ide": ide, "project": project}
            )
            or {"ok": True, "backend": "gillm", "submitted": submit}
        ),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "_try_os_injector_fallback",
        lambda prompt, *, submit: (
            injector_calls.append({"prompt": prompt, "submit": submit})
            or {"ok": True, "backend": "os_injector"}
        ),
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="cursor",
        drive_prompt="continue with the next ticket",
        submit=True,
        include_semcod_artifacts=False,
        client=FailingClient(),
    )

    assert queue_result.last_status == "idle"
    assert autopilot_status == "ok"
    assert len(gillm_calls) == 1
    assert gillm_calls[0]["submit"] is True
    assert gillm_calls[0]["project"] == tmp_path
    assert injector_calls == []
