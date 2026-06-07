from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from koru.autonomous_cycle_drive_retry import _invoke_client_autopilot_drive


def test_invoke_drive_uses_nlp2uri_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_IDE_CONTROL_VIA_NLP2URI", "1")
    client = MagicMock()
    client.drive = MagicMock(return_value={"ok": True, "backend": "plugin"})

    nlp2uri_calls: list[dict] = []

    def _fake_nlp2uri(
        prompt: str,
        *,
        submit: bool,
        ide: str,
        client: object,
        project: Path | None = None,
    ) -> dict:
        nlp2uri_calls.append(
            {
                "prompt": prompt,
                "submit": submit,
                "ide": ide,
                "client": client,
                "project": project,
            }
        )
        return {"ok": True, "backend": "nlp2uri_control", "type": "drive"}

    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_nlp2uri_ide_control",
        _fake_nlp2uri,
    )
    monkeypatch.setenv("KORU_IDE_CONTROL_VIA_NLP2URI", "1")

    project = Path("/tmp/koru-project")
    reply, ok = _invoke_client_autopilot_drive(
        client,
        prompt="hello",
        submit=True,
        autopilot_ide="cursor",
        require_plugin=False,
        project=project,
    )
    assert ok is True
    assert reply["backend"] == "nlp2uri_control"
    client.drive.assert_not_called()
    assert nlp2uri_calls[0]["client"] is client
    assert nlp2uri_calls[0]["project"] == project
    assert nlp2uri_calls[0]["submit"] is False


def test_invoke_drive_falls_back_to_client_when_nlp2uri_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_IDE_CONTROL_VIA_NLP2URI", "1")
    client = MagicMock()
    client.drive = MagicMock(return_value={"ok": True, "backend": "plugin"})

    def _fake_nlp2uri(
        prompt: str,
        *,
        submit: bool,
        ide: str,
        client: object,
        project: Path | None = None,
    ) -> dict:
        return {"ok": False, "backend": "nlp2uri_control", "message": "failed"}

    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_nlp2uri_ide_control",
        _fake_nlp2uri,
    )

    reply, ok = _invoke_client_autopilot_drive(
        client,
        prompt="hello",
        submit=True,
        autopilot_ide="cursor",
        require_plugin=False,
        project=Path("/tmp"),
    )
    assert ok is True
    assert reply["backend"] == "plugin"
    client.drive.assert_called_once()
    assert client.drive.call_args.kwargs["submit"] is False
