"""Unit tests for DslReconfigurator and CLI execution."""

from pathlib import Path
from unittest.mock import MagicMock

from koru.autonomy.dsl_reconfigure import DslReconfigurator
from koru.cli_reconfigure import run_reconfigure_cli


def test_dsl_reconfigurator_parsing():
    reconfigurator = DslReconfigurator()
    spec = """
    # Reconfiguration plan
    - uri: koru://workspace/allocate {"ticket_id": "ticket-100"}
    - uri: taskand://git/commit {"message": "Initial commit"}
    - uri: koru://governance/check
    """
    ops = reconfigurator.parse_spec(spec)
    assert len(ops) == 3
    assert ops[0][0].canonical_action == "koru://workspace/allocate"
    assert ops[0][1] == {"ticket_id": "ticket-100"}
    assert ops[1][0].canonical_action == "taskand://git/commit"
    assert ops[1][1] == {"message": "Initial commit"}


def test_dsl_reconfigurator_apply(tmp_path: Path):
    reconfigurator = DslReconfigurator()
    spec = """
    koru://workspace/allocate {"ticket_id": "ticket-101"}
    taskand://git/commit {"message": "Apply updates"}
    """
    result = reconfigurator.apply_to_project(tmp_path, spec)
    assert result["status"] == "success"
    assert result["operations_count"] == 2
    assert result["operations"][0]["uri"] == "koru://workspace/allocate"


def test_cli_export_gbnf(capsys):
    args = MagicMock(export_gbnf=True, list_actions=False, spec=None)
    code = run_reconfigure_cli(args)
    captured = capsys.readouterr()
    assert code == 0
    assert '"koru://workspace/allocate"' in captured.out


def test_cli_list_actions(capsys):
    args = MagicMock(export_gbnf=False, list_actions=True, spec=None)
    code = run_reconfigure_cli(args)
    captured = capsys.readouterr()
    assert code == 0
    assert "koru://governance/check" in captured.out
