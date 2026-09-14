from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru.doctor_constants import PASS, WARN
from koru.doctor_dependencies import check_uv_lock_freshness
from koru.doctor_models import Check
from koru.doctor_ticket_reporting import report_actionable_findings
from koru.task_models import CreatedTask


def test_uv_lock_freshness_reports_available_updates(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr("koru.doctor_dependencies.shutil.which", lambda _name: "/usr/bin/uv")

    status, detail = check_uv_lock_freshness(
        tmp_path,
        subprocess_run=lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout="Resolved 2 packages\nUpdate typer v0.27.0 -> v0.27.2\nAdd boto3 v1.43.93\n",
            stderr="",
        ),
    )

    assert status == WARN
    assert "2 available change(s)" in detail


def test_uv_lock_freshness_reports_current_lock(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr("koru.doctor_dependencies.shutil.which", lambda _name: "/usr/bin/uv")

    status, detail = check_uv_lock_freshness(
        tmp_path,
        subprocess_run=lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="Resolved 2 packages\n", stderr=""
        ),
    )

    assert status == PASS
    assert "current" in detail


def test_actionable_doctor_findings_create_once_and_clear_after_recovery(tmp_path: Path) -> None:
    created: list[str] = []
    scaffolds: list[dict[str, object]] = []

    def create_task(*_args, **kwargs):
        ticket_id = f"PLF-{len(created) + 1:03d}"
        created.append(ticket_id)
        scaffolds.append(kwargs["scaffold"])
        return CreatedTask(ticket_id, "current", tmp_path / "current.yaml", "diagnostic")

    finding = Check("python_venv_alignment", WARN, "multiple_project_venvs=.venv,venv")
    assert report_actionable_findings(tmp_path, [finding], create_task=create_task) == ["PLF-001"]
    assert report_actionable_findings(tmp_path, [finding], create_task=create_task) == []
    assert report_actionable_findings(
        tmp_path, [Check("python_venv_alignment", PASS, "aligned")], create_task=create_task
    ) == []
    assert report_actionable_findings(tmp_path, [finding], create_task=create_task) == ["PLF-002"]
    assert created == ["PLF-001", "PLF-002"]
    assert scaffolds[0]["labels"] == ["auto-diag", "doctor"]


def test_doctor_json_keeps_created_ticket_ids_in_the_document() -> None:
    import json

    from koru.cli_doctor import _doctor_json_output

    payload = json.loads(
        _doctor_json_output(
            SimpleNamespace(to_dict=lambda: {"status": "warn"}),
            [],
            None,
            None,
            False,
            ["PLF-085"],
        )
    )

    assert payload["diagnostic_tickets"] == ["PLF-085"]
