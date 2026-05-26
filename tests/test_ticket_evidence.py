from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from koru.cli_queue import queue_main
from koru.ticket_evidence import render_ticket_evidence_report, validate_ticket_evidence


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _ticket(
    tmp_path: Path,
    *,
    sha256: str,
    size_bytes: int | None = None,
) -> dict:
    return {
        "id": "STARTER-1",
        "name": "Refactor generated finding",
        "status": "open",
        "source": {
            "tool": "koru-project-discovery",
            "context": {
                "evidence": {
                    "schema": "koru.ticket_evidence.v1",
                    "kind": "code2llm_discovery",
                    "artifact": {
                        "path": "project/analysis.toon.yaml",
                        "sha256": sha256,
                        "size_bytes": size_bytes,
                    },
                    "regenerate_command": f"code2llm {tmp_path} -f all -o {tmp_path / 'project'}",
                }
            },
        },
    }


def test_validate_ticket_evidence_reports_current_snapshot(tmp_path: Path) -> None:
    artifact = tmp_path / "project" / "analysis.toon.yaml"
    artifact.parent.mkdir()
    artifact.write_text("DUP 2\n", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

    def runner(cmd, _cwd):
        assert cmd[:4] == ["planfile", "ticket", "show", "STARTER-1"]
        return _ok(json.dumps(_ticket(tmp_path, sha256=digest, size_bytes=artifact.stat().st_size)))

    report = validate_ticket_evidence(tmp_path, ticket_id="STARTER-1", runner=runner)

    assert report.current_count == 1
    assert report.stale_count == 0
    validation = report.validations[0]
    assert validation.evidence_status == "current"
    assert validation.checks[0].status == "current"
    text = render_ticket_evidence_report(report)
    assert "summary: tickets=1 current=1 stale=0 missing_evidence=0" in text
    assert "regenerate: code2llm" in text


def test_validate_ticket_evidence_reports_stale_snapshot_and_regenerate_command(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "project" / "analysis.toon.yaml"
    artifact.parent.mkdir()
    artifact.write_text("current\n", encoding="utf-8")
    old_digest = hashlib.sha256(b"old\n").hexdigest()

    report = validate_ticket_evidence(
        tmp_path,
        ticket_id="STARTER-1",
        runner=lambda _cmd, _cwd: _ok(json.dumps(_ticket(tmp_path, sha256=old_digest))),
    )

    validation = report.validations[0]
    assert validation.evidence_status == "stale"
    assert validation.checks[0].status == "changed"
    assert validation.regenerate_command.startswith("code2llm ")
    assert "next: rerun regenerate_command" in render_ticket_evidence_report(report)


def test_validate_ticket_evidence_loads_full_ticket_details_from_list(tmp_path: Path) -> None:
    artifact = tmp_path / "project" / "analysis.toon.yaml"
    artifact.parent.mkdir()
    artifact.write_text("OK\n", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    calls: list[list[str]] = []

    def runner(cmd, _cwd):
        calls.append(list(cmd))
        if cmd[:3] == ["planfile", "ticket", "list"]:
            return _ok(json.dumps([{"id": "STARTER-1", "name": "short list item"}]))
        if cmd[:4] == ["planfile", "ticket", "show", "STARTER-1"]:
            return _ok(json.dumps(_ticket(tmp_path, sha256=digest, size_bytes=artifact.stat().st_size)))
        raise AssertionError(cmd)

    report = validate_ticket_evidence(tmp_path, runner=runner)

    assert [call[:3] for call in calls] == [
        ["planfile", "ticket", "list"],
        ["planfile", "ticket", "show"],
    ]
    assert report.validations[0].evidence_status == "current"


def test_missing_evidence_is_reported_as_validation_problem(tmp_path: Path) -> None:
    report = validate_ticket_evidence(
        tmp_path,
        ticket_id="STARTER-1",
        runner=lambda _cmd, _cwd: _ok(
            json.dumps({"id": "STARTER-1", "name": "Manual ticket", "status": "open"}),
        ),
    )

    assert report.missing_evidence_count == 1
    assert report.validations[0].reason == "ticket has no source.context.evidence block"


def test_queue_validate_evidence_cli_exits_nonzero_for_missing_evidence(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    def fake_validate(project, *, ticket_id, status):
        return validate_ticket_evidence(
            project,
            ticket_id=ticket_id,
            status=status,
            runner=lambda _cmd, _cwd: _ok(
                json.dumps({"id": "STARTER-1", "name": "Manual ticket", "status": "open"}),
            ),
        )

    monkeypatch.setattr("koru.cli_queue.validate_ticket_evidence", fake_validate)

    rc = queue_main(["validate-evidence", "--ticket", "STARTER-1", "--project", str(tmp_path)])

    assert rc == 1
    assert "missing_evidence=1" in capsys.readouterr().out
