from dsl2koru.codec import parse_text, roundtrip_text
from dsl2koru.schema_registry import all_verbs, validate_schemas


def test_validate_schemas() -> None:
    assert validate_schemas() == []


def test_all_verbs_present() -> None:
    verbs = all_verbs()
    assert "QUERY_REPAIR_HISTORY" in verbs
    assert "REPAIR_RUN" in verbs
    assert {"STATUS", "AUTO", "UI_TYPE"} <= set(verbs)


def test_roundtrip_query_repair_history() -> None:
    line = "QUERY_REPAIR_HISTORY PROJECT . LIMIT 5"
    again = roundtrip_text(line, default_project=".")
    assert "QUERY_REPAIR_HISTORY" in again
    payload = parse_text(line, default_project=".")
    assert payload["limit"] == 5


def test_compatibility_verb_uses_canonical_codec() -> None:
    payload = parse_text("ENV", default_file="project.toml")
    assert payload == {"verb": "ENV", "file": "project.toml"}
    assert roundtrip_text("STATUS --probe") == "STATUS --probe"


def test_shared_repair_run_preserves_both_text_forms() -> None:
    canonical = parse_text("REPAIR_RUN IDE cursor INSTANCE primary PROJECT /tmp/p")
    compatibility = parse_text("REPAIR_RUN --fix --ide cursor", default_file="ignored")
    assert canonical["project"] == "/tmp/p"
    assert canonical["instance"] == "primary"
    assert compatibility == {"verb": "REPAIR_RUN", "fix": True, "ide": "cursor"}
