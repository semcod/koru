import subprocess
import sys

from dsl2coru.codec import parse_text, roundtrip_text
from dsl2coru.schema_registry import all_verbs, validate_schemas
from dsl2koru.codec import parse_text as canonical_parse_text
from dsl2koru.grammar import parse_line as canonical_parse_line
from dsl2koru.grammar import to_text as canonical_to_text
from dsl2koru.schema_registry import all_verbs as canonical_all_verbs


def test_validate_schemas() -> None:
    assert validate_schemas() == []


def test_all_verbs_present() -> None:
    verbs = all_verbs()
    assert "STATUS" in verbs
    assert "AUTO" in verbs
    assert "QUERY" in verbs
    assert verbs == canonical_all_verbs()


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


def test_legacy_text_and_schema_apis_are_canonical_aliases() -> None:
    from dsl2coru.grammar import parse_line, to_text

    assert parse_text is canonical_parse_text
    assert parse_line is canonical_parse_line
    assert to_text is canonical_to_text


def test_canonical_parser_accepts_legacy_aliases_and_ui() -> None:
    assert canonical_parse_text("DIAGNOSE --probe") == {"verb": "STATUS", "probe": True}
    payload = canonical_parse_text('UI_TYPE "hello" IN "Chat input" WINDOW bottom')
    assert payload["value"] == "hello"
    assert payload["field"] == "Chat input"
    assert payload["window"] == "bottom"


def test_legacy_package_emits_one_release_warning() -> None:
    completed = subprocess.run(
        [sys.executable, "-W", "always", "-c", "import dsl2coru"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "dsl2coru is deprecated for one compatibility release" in completed.stderr
