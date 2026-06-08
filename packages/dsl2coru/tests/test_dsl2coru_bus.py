from dsl2coru.bus import dispatch


def _mock_runner(argv: list[str]) -> tuple[int, str, str]:
    return 0, f"mock:{':'.join(argv)}", ""


def test_status_query_mocked() -> None:
    result = dispatch("STATUS", runner=_mock_runner)
    assert result.ok is True
    assert result.verb == "STATUS"
    assert result.action == "status"
    assert "mock:status" in result.output


def test_auto_command_mocked() -> None:
    result = dispatch("AUTO --shell bash", runner=_mock_runner)
    assert result.ok is True
    assert result.verb == "AUTO"
    assert result.action == "auto"
    assert "mock:auto" in result.output
    assert "bash" in result.output


def test_noop_line() -> None:
    result = dispatch("   ")
    assert result.ok is True
    assert result.action == "noop"
