"""Parity: same DSL line → same result shape across input formats."""

from dsl2coru.bus import dispatch


def _mock_runner(argv: list[str]) -> tuple[int, str, str]:
    return 0, f"ok:{argv[0]}", ""


def test_parity_status_text_dict() -> None:
    line = "STATUS"
    r1 = dispatch(line, runner=_mock_runner)
    r2 = dispatch({"verb": "STATUS"}, runner=_mock_runner)
    assert r1.ok is True
    assert r2.ok is True
    assert r1.action == r2.action == "status"
    assert r1.output == r2.output


def test_parity_auto_text_dict() -> None:
    line = "AUTO --shell zsh"
    r1 = dispatch(line, runner=_mock_runner)
    r2 = dispatch({"verb": "AUTO", "shell": "zsh"}, runner=_mock_runner)
    assert r1.ok is True
    assert r2.ok is True
    assert r1.action == r2.action == "auto"
