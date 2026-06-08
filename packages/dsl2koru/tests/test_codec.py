from dsl2koru.codec import parse_text, roundtrip_text
from dsl2koru.schema_registry import validate_schemas
from dsl2koru.schema_registry import all_verbs


def test_validate_schemas() -> None:
    assert validate_schemas() == []


def test_all_verbs_present() -> None:
    verbs = all_verbs()
    assert "QUERY_REPAIR_HISTORY" in verbs
    assert "REPAIR_RUN" in verbs


def test_roundtrip_query_repair_history() -> None:
    line = "QUERY_REPAIR_HISTORY PROJECT . LIMIT 5"
    again = roundtrip_text(line, default_project=".")
    assert "QUERY_REPAIR_HISTORY" in again
    payload = parse_text(line, default_project=".")
    assert payload["limit"] == 5
