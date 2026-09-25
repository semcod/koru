from __future__ import annotations

from pathlib import Path

import koru.tillm_bridge as bridge


def test_normalize_tillm_model_preserves_flash_family() -> None:
    assert bridge._normalize_tillm_model("zai/glm-5.3-flash") == "glm-5.3-flash"
    assert bridge._normalize_tillm_model("z.ai/glm-5.3-flash") == "glm-5.3-flash"


def test_normalize_tillm_model_keeps_other_model_ids() -> None:
    assert bridge._normalize_tillm_model("openrouter/z-ai/glm-5.3-flash") == (
        "openrouter/z-ai/glm-5.3-flash"
    )
    assert bridge._normalize_tillm_model(None) is None


def test_drive_shell_chat_passes_bare_model_to_tillm(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_drive_koru_chat(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {"ok": True, "model": kwargs["model"]}

    monkeypatch.setattr(bridge, "ensure_local_tillm_path", lambda: None)
    monkeypatch.setattr(
        "tillm.compat.drive_koru_chat", fake_drive_koru_chat, raising=False
    )
    result = bridge.drive_shell_chat(
        client_id="opencode",
        project=tmp_path,
        prompt="test",
        execute=False,
        model="zai/glm-5.3-flash",
    )

    assert result["model"] == "glm-5.3-flash"
    assert calls[0]["model"] == "glm-5.3-flash"
