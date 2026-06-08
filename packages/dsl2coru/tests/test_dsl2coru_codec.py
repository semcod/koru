from dsl2coru.codec import parse_text, roundtrip_text
from dsl2coru.schema_registry import all_verbs, validate_schemas


def test_validate_schemas() -> None:
    assert validate_schemas() == []


def test_all_verbs_present() -> None:
    verbs = all_verbs()
    assert "STATUS" in verbs
    assert "AUTO" in verbs
    assert "QUERY" in verbs


def test_roundtrip_status() -> None:
    line = "STATUS --probe"
    again = roundtrip_text(line)
    assert "STATUS" in again
    payload = parse_text(line)
    assert payload["probe"] is True


def test_roundtrip_auto() -> None:
    line = "AUTO --shell bash"
    payload = parse_text(line)
    assert payload["shell"] == "bash"
    again = roundtrip_text(line)
    assert "AUTO" in again
