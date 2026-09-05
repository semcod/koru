"""Behavioral contracts for photo-VQL results crossing the drive facade."""

from __future__ import annotations

from copy import deepcopy

import pytest

from koru.integrations import vdisplay_client as vc


@pytest.fixture
def policy(monkeypatch):
    flags = {"capture_override": False, "map_override": False, "surface_safe": False}
    monkeypatch.setattr(vc, "_allow_actuation_on_capture_mismatch", lambda: flags["capture_override"])
    monkeypatch.setattr(vc, "_map_source_mismatch_actuation_allowed", lambda: flags["map_override"])
    monkeypatch.setattr(vc, "_surface_bounds_target_safe_for_actuation", lambda **kwargs: flags["surface_safe"])
    monkeypatch.setattr(vc, "_trusted_visual_target_id", lambda target_id: target_id.startswith("map:"))
    return flags


@pytest.mark.parametrize(
    ("extra", "flags", "expected_ok"),
    [
        pytest.param({}, {}, True, id="successful-chat"),
        pytest.param({"capture_confirmed": False}, {}, False, id="unconfirmed-capture"),
        pytest.param({"ide_window_warning": {"message": "different IDE"}}, {}, False, id="ide-mismatch"),
        pytest.param({"verified": False}, {}, False, id="failed-verification"),
        pytest.param({"vql_command_plan": {"inference_ok": False}}, {}, False, id="failed-inference"),
        pytest.param(
            {"capture_confirmed": False, "verified": False, "vql_target": {"id": "map:chat"}},
            {"capture_override": True},
            True,
            id="trusted-map-override",
        ),
        pytest.param(
            {"capture_confirmed": False, "verified": False, "vql_target": {"id": "unknown"}},
            {"capture_override": True},
            False,
            id="override-needs-trusted-target",
        ),
        pytest.param(
            {"verified": False, "vql_command_plan": {"inference_ok": False}},
            {"surface_safe": True},
            True,
            id="safe-surface-override",
        ),
        pytest.param(
            {"edit": {"ok": False}, "verified": False},
            {"surface_safe": True},
            False,
            id="surface-needs-successful-edit",
        ),
        pytest.param(
            {"vql_command_plan": {"map_capture_mismatch": {"message": "wrong monitor"}}},
            {},
            False,
            id="nested-monitor-mismatch",
        ),
        pytest.param(
            {"map_capture_mismatch": {"message": "wrong monitor"}},
            {"capture_override": True},
            False,
            id="monitor-policy-is-independent",
        ),
        pytest.param(
            {"map_capture_mismatch": {"message": "wrong monitor"}},
            {"map_override": True},
            True,
            id="explicit-monitor-override",
        ),
        pytest.param(
            {"is_code_edit": True, "capture_confirmed": False, "verified": False},
            {},
            True,
            id="existing-code-edit-precedence",
        ),
    ],
)
def test_current_gate_precedence(extra, flags, expected_ok, policy):
    policy.update(flags)
    photo = {"ok": True, "edit": {"ok": True, "method": "paste"}, **extra}
    before = deepcopy(photo)

    out = vc._normalize_photo_vql_drive_result(photo, ide="jetbrains", submit=False)

    assert out["ok"] is expected_ok
    assert out["photo_vql"] is photo
    assert photo == before


def test_result_preserves_provenance_and_submit_details(policy):
    photo = {
        "ok": True,
        "edit": {"ok": True, "message": "typed"},
        "capture_confirmed": False,
        "capture_provenance": {"capture_confirmed": True, "source": "DP-1"},
        "verification": {"method": "ocr"},
        "verified": True,
        "submitted": True,
        "submit": {"ok": True},
        "llm_used": True,
        "llm_decision": {"confidence": 0.9},
        "vql_command_plan": {"inference_ok": True},
        "coords": [12, 34],
        "target": "chat",
    }

    out = vc._normalize_photo_vql_drive_result(photo, ide="cursor", submit=True)

    assert out["capture_confirmed"] is False  # Explicit capture state wins over provenance.
    assert out["ok"] is False
    assert out["message"] == "typed (submitted)"
    assert out["backend"] == "vdisplay+photo-vql"
    assert out["type"] == "drive"
    assert out["fallback_from"] == "plugin"
    assert out["ide"] == "cursor"
    assert out["submit"] is True
    assert out["submitted"] is True
    assert out["submit_result"] == photo["submit"]
    for key in (
        "capture_provenance",
        "verification",
        "verified",
        "llm_used",
        "llm_decision",
        "vql_command_plan",
        "coords",
        "target",
    ):
        assert out[key] == photo[key]


def test_monitor_mismatch_message_takes_precedence(policy):
    photo = {
        "ok": True,
        "edit": {"ok": True, "message": "typed"},
        "map_capture_mismatch": {"message": "map calibrated for DP-2"},
        "vql_command_plan": {"map_capture_mismatch": {"message": "nested mismatch"}},
    }
    out = vc._normalize_photo_vql_drive_result(photo, ide="jetbrains", submit=False)
    assert out["ok"] is False
    assert out["message"] == "map calibrated for DP-2"
    assert out["map_capture_mismatch"] is photo["map_capture_mismatch"]


def test_facade_resolves_policy_callbacks_on_each_call(monkeypatch, policy):
    photo = {"ok": True, "map_capture_mismatch": {"message": "different monitor"}}
    assert vc._normalize_photo_vql_drive_result(photo, ide="cursor", submit=False)["ok"] is False

    monkeypatch.setattr(vc, "_map_source_mismatch_actuation_allowed", lambda: True)

    assert vc._normalize_photo_vql_drive_result(photo, ide="cursor", submit=False)["ok"] is True
