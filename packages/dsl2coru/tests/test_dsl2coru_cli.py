"""Smoke tests for the dsl2coru subcommand parser (locks in args/defaults/choices)."""

from __future__ import annotations

import pytest
from dsl2coru.cli import _build_subcommand_parser


def _parse(argv: list[str]) -> dict:
    args = _build_subcommand_parser().parse_args(argv)
    return vars(args)


def test_encode_defaults_and_overrides() -> None:
    parsed = _parse(["encode", "STATUS --probe"])
    assert parsed["line"] == "STATUS --probe"
    assert parsed["file"] == ""
    assert parsed["format"] == "protobuf"
    assert parsed["output"] is None

    parsed = _parse(["encode", "x", "--format", "json", "--output", "/tmp/o", "--file", "f"])
    assert parsed["format"] == "json"
    assert parsed["output"] == "/tmp/o"
    assert parsed["file"] == "f"
    assert parsed["project"] == "."


def test_decode_requires_input() -> None:
    assert _parse(["decode", "--input", "x.bin"])["format"] == "protobuf"
    with pytest.raises(SystemExit):
        _parse(["decode"])


def test_invalid_format_choice_rejected() -> None:
    with pytest.raises(SystemExit):
        _parse(["encode", "x", "--format", "yaml"])


def test_roundtrip_and_replay_defaults() -> None:
    assert _parse(["roundtrip", "STATUS"])["file"] == ""
    replay = _parse(["replay"])
    assert replay["file"] == "."
    assert replay["format"] == "auto"


def test_run_optional_script_and_flags() -> None:
    parsed = _parse(["run", "-c", "STATUS", "--json"])
    assert parsed["command"] == "STATUS"
    assert parsed["json"] is True
    assert parsed["script"] is None
    assert _parse(["run", "script.dsl"])["script"] == "script.dsl"


def test_exec_subcommand() -> None:
    parsed = _parse(["exec", "STATUS --probe", "--file", "ctx"])
    assert parsed["command"] == "STATUS --probe"
    assert parsed["file"] == "ctx"
    assert parsed["json"] is False


def test_validate_schema_subcommand() -> None:
    assert _parse(["validate-schema"])["cmd"] == "validate-schema"


def test_subcommand_is_required() -> None:
    with pytest.raises(SystemExit):
        _parse([])


def test_legacy_cli_is_the_canonical_cli() -> None:
    from dsl2coru import cli as legacy_cli
    from dsl2koru import cli as canonical_cli

    assert legacy_cli.main is canonical_cli.main
    assert legacy_cli._build_subcommand_parser is canonical_cli._build_subcommand_parser


def test_parser_accepts_native_project_context() -> None:
    parsed = _parse(["run", "-c", "VALIDATE_LANE", "--project", "/workspace"])
    assert parsed["project"] == "/workspace"
    assert parsed["file"] == ""


def test_context_selection_preserves_both_console_dialects() -> None:
    from dsl2koru.cli import _build_subcommand_parser as build_parser
    from dsl2koru.cli import _selected_context

    native = build_parser(program="dsl2koru").parse_args(["replay"])
    compat = build_parser(program="dsl2coru").parse_args(["replay"])
    explicit_file = build_parser(program="dsl2koru").parse_args(["replay", "--file", "."])
    explicit_project = build_parser(program="dsl2coru").parse_args(["replay", "--project", "."])

    assert _selected_context(native) == ("native", ".")
    assert _selected_context(compat) == ("compat", ".")
    assert _selected_context(explicit_file) == ("compat", ".")
    assert _selected_context(explicit_project) == ("native", ".")
