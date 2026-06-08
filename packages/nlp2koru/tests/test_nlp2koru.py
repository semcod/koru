from nlp2koru.apply import apply_nl
from nlp2koru.to_dsl import to_dsl


def test_to_dsl_repair_history() -> None:
    line = to_dsl("show repair history", project=".")
    assert line.startswith("QUERY_REPAIR_HISTORY")


def test_apply_validate_lane() -> None:
    result = apply_nl("validate lane", project=".")
    assert result.dsl.startswith("VALIDATE_LANE")
    assert result.ok is True
