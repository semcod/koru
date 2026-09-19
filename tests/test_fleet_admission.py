"""Admission failures must not cross the scan ticket-creation boundary."""

import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from koru import fleet_admission, scan
from koru.scan_types import ScanResult, Suggestion


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for key in ("ENABLED", "CONFIG", "CONFIG_DIGEST"):
        monkeypatch.delenv("KORU_FLEET_ADMISSION_" + key, raising=False)


@pytest.fixture
def configured(tmp_path, monkeypatch):
    gate = tmp_path / "gate.py"
    gate.write_text("# pinned test evaluator\n")
    monkeypatch.setattr(fleet_admission, "GATE_SHA256",
                        hashlib.sha256(gate.read_bytes()).hexdigest())
    config = {"schema": "koru.fleet-admission-config/v1", "gate_path": str(gate),
              "resume_path": str(tmp_path / "resume.json"),
              "prs_path": str(tmp_path / "prs.json"),
              "projects": {str(tmp_path): {"repository": "semcod/koru",
                                          "base_branch": "main"}}}
    path = tmp_path / "config.json"

    def save():
        path.write_text(json.dumps(config))
        monkeypatch.setenv("KORU_FLEET_ADMISSION_CONFIG", str(path))
        monkeypatch.setenv("KORU_FLEET_ADMISSION_CONFIG_DIGEST",
                           hashlib.sha256(path.read_bytes()).hexdigest())

    save()
    decision = {"schema": "autonom.fleet-admission/v1", "repository": "semcod/koru",
                "admit_new": True, "authorization_granted": False, "stage": "admit_issue"}
    launched = Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps(decision), ""))
    monkeypatch.setattr(fleet_admission.subprocess, "run", launched)
    return config, path, gate, save, decision, launched


def test_standalone_has_no_evaluator_effect(tmp_path, monkeypatch):
    launched = Mock(side_effect=AssertionError("must not launch"))
    monkeypatch.setattr(fleet_admission.subprocess, "run", launched)
    assert fleet_admission.scan_admission(tmp_path) is None
    launched.assert_not_called()


@pytest.mark.parametrize("value", ["1", "", "0", "true"])
def test_config_required_when_fleet_flag_present(tmp_path, monkeypatch, value):
    monkeypatch.setenv("KORU_FLEET_ADMISSION_ENABLED", value)
    assert fleet_admission.scan_admission(tmp_path)["admit_new"] is False


@pytest.mark.parametrize("fault", ["digest", "gate", "identity", "relative", "oversized"])
def test_invalid_input_denies_before_launch(tmp_path, monkeypatch, configured, fault):
    config, path, gate, save, _, launched = configured
    if fault == "digest":
        path.write_text(path.read_text() + " ")
    elif fault == "gate":
        gate.write_text("# tampered\n")
    elif fault == "identity":
        config["projects"] = {}
        save()
    elif fault == "relative":
        config["resume_path"] = "relative.json"
        save()
    else:
        path.write_text(" " * 65537)
        monkeypatch.setenv("KORU_FLEET_ADMISSION_CONFIG_DIGEST",
                           hashlib.sha256(path.read_bytes()).hexdigest())
    assert fleet_admission.scan_admission(tmp_path)["admit_new"] is False
    launched.assert_not_called()


def test_verified_bytes_isolation_and_boundaries(tmp_path, configured):
    _, _, gate, _, _, launched = configured
    assert fleet_admission.scan_admission(tmp_path)["admit_new"] is True
    args, kwargs = launched.call_args
    assert args[0][1:4] == ["-I", "-c", gate.read_text()]
    assert kwargs["timeout"] == 30
    assert args[0][args[0].index("--repository") + 1] == "semcod/koru"
    assert not Path(args[0][-1]).exists()  # temporary runtime pins cleaned up


@pytest.mark.parametrize("update", [
    {"repository": "other/repo"}, {"schema": "unknown"},
    {"authorization_granted": True}, {"authorization_granted": 0},
    {"admit_new": 1}, {"admit_new": False}, {"stage": "publish_pr"},
])
def test_invalid_decision_cannot_admit(tmp_path, configured, update):
    _, _, _, _, decision, launched = configured
    decision.update(update)
    launched.return_value.stdout = json.dumps(decision)
    assert fleet_admission.scan_admission(tmp_path)["admit_new"] is False


@pytest.mark.parametrize("fault", ["timeout", "exit", "invalid_json", "wrong_type"])
def test_evaluator_failure_denies(tmp_path, configured, fault):
    *_, launched = configured
    if fault == "timeout":
        launched.side_effect = subprocess.TimeoutExpired("gate", 30)
    elif fault == "exit":
        launched.return_value.returncode = 1
    else:
        launched.return_value.stdout = "{" if fault == "invalid_json" else "[]"
    assert fleet_admission.scan_admission(tmp_path)["admit_new"] is False


@pytest.fixture
def scan_effects(monkeypatch):
    suggestions = [Suggestion("todo", "first", "fix"), Suggestion("todo", "second", "fix")]
    monkeypatch.setattr(scan, "collect_suggestions", lambda *a, **kw: suggestions.copy())
    emit = Mock(return_value=ScanResult(suggestions[:1], applied=["PLF-1"]))
    monkeypatch.setattr(scan, "_apply_scan_suggestions", emit)
    return suggestions, emit


@pytest.mark.parametrize("reason", ["stale_observation", "incomplete_process_visibility",
                                    "dirty_worktree", "pending_pr", "existing_queue"])
def test_denial_creates_no_ticket_and_is_observable(tmp_path, monkeypatch, scan_effects, reason):
    suggestions, emit = scan_effects
    denied = {"admit_new": False, "authorization_granted": False, "error": reason}
    monkeypatch.setattr(scan, "scan_admission", lambda _: denied)
    result = scan.run_scan(tmp_path, apply=True)
    emit.assert_not_called()
    assert not result.applied
    assert result.skipped == [s.title for s in suggestions]
    assert result.to_dict()["fleet_admission"] == denied


def test_fleet_can_emit_only_one_suggestion(tmp_path, monkeypatch, scan_effects):
    suggestions, emit = scan_effects
    monkeypatch.setattr(scan, "scan_admission", lambda _: {"admit_new": True})
    result = scan.run_scan(tmp_path, apply=True)
    assert emit.call_args.args[1] == suggestions[:1]
    assert result.applied == ["PLF-1"]
    assert result.skipped == ["second"]


def test_read_only_scan_does_not_consult_admission(tmp_path, monkeypatch, scan_effects):
    _, emit = scan_effects
    gate = Mock(side_effect=AssertionError("read-only scan must remain available"))
    monkeypatch.setattr(scan, "scan_admission", gate)
    assert len(scan.run_scan(tmp_path).suggestions) == 2
    gate.assert_not_called()
    emit.assert_not_called()


def test_standalone_keeps_existing_batch_and_result_shape(tmp_path, scan_effects):
    suggestions, emit = scan_effects
    result = scan.run_scan(tmp_path, apply=True)
    assert emit.call_args.args[1] == suggestions
    assert "fleet_admission" not in result.to_dict()
