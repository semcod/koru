from __future__ import annotations

import pytest

from koru import autonomous_cycle_gate


def test_try_nlp2uri_ide_control_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_IDE_CONTROL_VIA_NLP2URI", raising=False)
    assert (
        autonomous_cycle_gate.try_nlp2uri_ide_control("hello", submit=True, ide="cursor")
        is None
    )


def test_effective_ide_control_submit_cursor_paste_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_IDE_CONTROL_VIA_NLP2URI", raising=False)
    assert autonomous_cycle_gate.effective_ide_control_submit(submit=True, ide="cursor") is False
    assert autonomous_cycle_gate.effective_ide_control_submit(submit=True, ide="vscode") is True
    monkeypatch.setenv("KORU_IDE_CONTROL_FORCE_SUBMIT", "1")
    assert autonomous_cycle_gate.effective_ide_control_submit(submit=True, ide="cursor") is True


def test_try_nlp2uri_ide_control_uses_fake_client(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("nlp2uri")
    monkeypatch.setenv("KORU_IDE_CONTROL_VIA_NLP2URI", "1")

    class _FakeClient:
        def is_running(self) -> bool:
            return True

        def drive(self, text: str, **kwargs) -> dict:
            return {"ok": True, "backend": "plugin", "message": text, **kwargs}

    def _factory() -> _FakeClient:
        return _FakeClient()

    import nlp2uri.control_execute as control_execute

    original = control_execute.execute_control_plan

    captured: dict[str, object] = {}

    def _patched(plan, **kwargs):
        kwargs["client_factory"] = _factory
        captured["plan"] = plan
        return original(plan, **kwargs)

    monkeypatch.setattr(control_execute, "execute_control_plan", _patched)

    class _StatusClient(_FakeClient):
        def status(self) -> dict:
            return {
                "plugins": [
                    {
                        "ide": "cursor",
                        "workspaceFolders": ["/tmp/koru-project"],
                    }
                ]
            }

    reply = autonomous_cycle_gate.try_nlp2uri_ide_control(
        "ticket prompt",
        submit=True,
        ide="cursor",
        client=_StatusClient(),
        project=__import__("pathlib").Path("/tmp/koru-project"),
    )
    assert reply is not None
    assert reply["ok"] is True
    assert reply["backend"] == "koruide_socket"
    assert reply["submit"] is False
    assert reply["workspace"] == "/tmp/koru-project"
    plan = captured["plan"]
    assert plan.actions[0].submit is False
    assert plan.actions[0].workspace == "/tmp/koru-project"
