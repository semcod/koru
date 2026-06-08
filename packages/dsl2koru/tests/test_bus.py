from pathlib import Path

from dsl2koru.bus import dispatch


def test_query_repair_history_empty(tmp_path: Path) -> None:
    result = dispatch("QUERY_REPAIR_HISTORY PROJECT . LIMIT 5", default_project=str(tmp_path))
    assert result.ok is True
    assert result.verb == "QUERY_REPAIR_HISTORY"


def test_validate_lane() -> None:
    result = dispatch("VALIDATE_LANE IDE auto INSTANCE default")
    assert result.ok is True
