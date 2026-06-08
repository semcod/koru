from nlp2coru.apply import apply_prompt
from nlp2coru.heuristic import to_dsl_lines
from nlp2coru.to_dsl import to_dsl


def test_to_dsl_offline_status() -> None:
    line = to_dsl("show lane status")
    assert "LANE" in line or "STATUS" in line


def test_heuristic_lines_offline() -> None:
    lines = to_dsl_lines("check status")
    assert lines
    assert lines[0] == "STATUS"


def test_apply_offline_no_execute(monkeypatch) -> None:
    monkeypatch.setattr(
        "nlp2coru.apply._execute_line",
        lambda line, default_file=None: {"ok": True, "verb": line.split()[0]},
    )
    result = apply_prompt("check status", use_llm=False)
    assert result.ok is True
    assert result.lines
