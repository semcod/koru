"""Pin the blocked-gate persistence wiring of vdisplay/focus_edit.

The five photo-VQL gates route their abort payloads through
``_persist_blocked_gate_result``, which owns the autonomy-session persist
stanza (PLF-043 / ticket-239: previously repeated inline in every gate —
the code2llm `Shotgun Surgery: blocked` finding). These tests pin the
phase/event name each gate persists under, the returned payload identity,
and the no-session path, using the facade-level monkeypatch surface.
"""

from __future__ import annotations

from typing import Any

import pytest

from koru.integrations import vdisplay_client as vc

_SESSION_DIR = "/tmp/koru-test-autonomy-session"


@pytest.fixture()
def persisted(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, Any]]:
    """Record persist_autonomy_phase calls against an active fake session."""
    calls: list[tuple[str, str, Any]] = []
    monkeypatch.setattr(vc._autonomy_session, "active_session_dir", lambda: _SESSION_DIR)
    monkeypatch.setattr(
        vc._autonomy_session,
        "persist_autonomy_phase",
        lambda session, phase, event, payload: calls.append((phase, event, payload)),
    )
    return calls


def _no_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vc._autonomy_session, "active_session_dir", lambda: None)


def test_unverified_chat_gate_persists_chat_actuation_blocked(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"ok": False, "error": "chat target not verified"}
    monkeypatch.setattr(vc, "_photo_vql_should_block_unverified_chat", lambda **kwargs: True)
    monkeypatch.setattr(vc, "_photo_vql_unverified_chat_blocked", lambda **kwargs: payload)

    out = vc._photo_vql_unverified_chat_gate(
        command_plan={"inference_ok": False},
        t={"id": "window_0-input-46"},
        target_desc="chat",
        x=10,
        y=20,
        ide="jetbrains",
        mismatch=None,
        is_code_edit=False,
    )

    assert out is payload
    assert persisted == [("act", "chat_actuation_blocked", payload)]


def test_unverified_chat_gate_passes_through_when_allowed(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(vc, "_photo_vql_should_block_unverified_chat", lambda **kwargs: False)

    out = vc._photo_vql_unverified_chat_gate(
        command_plan={"inference_ok": True},
        t={},
        target_desc="chat",
        x=0,
        y=0,
        ide="jetbrains",
        mismatch=None,
        is_code_edit=False,
    )

    assert out is None
    assert persisted == []


def test_map_source_preflight_gate_persists_preflight_blocked(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"ok": False, "error": "map source mismatch"}
    monkeypatch.setattr(
        vc, "_map_capture_mismatch_for_ide", lambda **kwargs: {"map_path": "map.json"}
    )
    monkeypatch.setattr(vc, "_map_source_mismatch_actuation_allowed", lambda: False)
    monkeypatch.setattr(vc, "_photo_vql_map_source_mismatch_error", lambda **kwargs: payload)

    out = vc._photo_vql_map_source_preflight_gate(
        ide="jetbrains", source="DP-1", is_code_edit=False
    )

    assert out is payload
    assert persisted == [("act", "map_source_mismatch_preflight_blocked", payload)]


def test_map_source_preflight_gate_skips_without_mismatch(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(vc, "_map_capture_mismatch_for_ide", lambda **kwargs: None)

    out = vc._photo_vql_map_source_preflight_gate(
        ide="jetbrains", source="DP-1", is_code_edit=False
    )

    assert out is None
    assert persisted == []


def test_target_map_mismatch_gate_persists_blocked_and_returns_mismatch(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"ok": False, "error": "per-target map mismatch"}
    mismatch = {"map_path": "map.json", "reason": "stale"}
    monkeypatch.setattr(vc, "_map_capture_mismatch_for_target", lambda **kwargs: mismatch)
    monkeypatch.setattr(vc, "_map_source_mismatch_actuation_allowed", lambda: False)
    monkeypatch.setattr(vc, "_photo_vql_map_source_mismatch_error", lambda **kwargs: payload)

    blocked, map_source_mismatch = vc._photo_vql_target_map_mismatch_gate(
        {"id": "map:prompt"}, ide="jetbrains", source="DP-1", is_code_edit=False
    )

    assert blocked is payload
    assert map_source_mismatch is mismatch
    assert persisted == [("act", "map_source_mismatch_blocked", payload)]


def test_target_map_mismatch_gate_allows_and_annotates_target(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    mismatch = {"map_path": "map.json", "reason": "stale"}
    monkeypatch.setattr(vc, "_map_capture_mismatch_for_target", lambda **kwargs: mismatch)
    monkeypatch.setattr(vc, "_map_source_mismatch_actuation_allowed", lambda: True)
    t = {"id": "map:prompt"}

    blocked, map_source_mismatch = vc._photo_vql_target_map_mismatch_gate(
        t, ide="jetbrains", source="DP-1", is_code_edit=False
    )

    assert blocked is None
    assert map_source_mismatch is mismatch
    assert t["map_capture_mismatch"] is mismatch
    assert persisted == []


def test_capture_mismatch_gate_persists_ide_capture_blocked(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"ok": False, "error": "capture mismatch"}
    monkeypatch.setattr(vc, "_photo_vql_capture_mismatch_blocks", lambda **kwargs: True)
    monkeypatch.setattr(vc, "_photo_vql_capture_mismatch_error", lambda **kwargs: payload)

    out = vc._photo_vql_capture_mismatch_gate(
        mismatch={"ide": "jetbrains"}, ide="jetbrains", is_code_edit=False
    )

    assert out is payload
    assert persisted == [("decide", "ide_capture_blocked", payload)]


def test_stale_metadata_gate_persists_stale_abort(
    persisted: list[tuple[str, str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(vc, "load_vql_metadata", lambda: {"error": "stale probe failed"})
    monkeypatch.setattr(vc, "_dry_run", lambda: False)
    monkeypatch.setattr(vc, "_photo_vql_stale_gate_override_ok", lambda **kwargs: False)

    out = vc._photo_vql_stale_metadata_gate(ide="jetbrains", is_code_edit=False)

    assert out is not None and out["ok"] is False
    assert out["error"] == "stale probe failed"
    assert persisted == [("decide", "stale_abort", out)]


def test_blocked_gates_skip_persistence_without_active_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, Any]] = []
    _no_session(monkeypatch)
    monkeypatch.setattr(
        vc._autonomy_session,
        "persist_autonomy_phase",
        lambda session, phase, event, payload: calls.append((phase, event, payload)),
    )
    payload = {"ok": False, "error": "capture mismatch"}
    monkeypatch.setattr(vc, "_photo_vql_capture_mismatch_blocks", lambda **kwargs: True)
    monkeypatch.setattr(vc, "_photo_vql_capture_mismatch_error", lambda **kwargs: payload)

    out = vc._photo_vql_capture_mismatch_gate(
        mismatch={"ide": "jetbrains"}, ide="jetbrains", is_code_edit=False
    )

    assert out is payload
    assert calls == []
