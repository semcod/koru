from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dsl2koru import cli


@pytest.mark.parametrize(
    ("program", "argv", "expected"),
    [
        ("dsl2koru", ["run", "-c", "STATUS", "--project", "repo"], {"default_project": "repo"}),
        ("dsl2coru", ["run", "-c", "STATUS", "--file", "lane.env"], {"default_file": "lane.env"}),
        ("dsl2koru", ["exec", "STATUS", "--file", "lane.env"], {"default_file": "lane.env"}),
        ("dsl2coru", ["exec", "STATUS", "--project", "repo"], {"default_project": "repo"}),
    ],
)
def test_command_matrix_preserves_dialect_and_explicit_context(
    monkeypatch: pytest.MonkeyPatch,
    program: str,
    argv: list[str],
    expected: dict[str, str],
) -> None:
    observed: list[tuple[str, dict[str, Any]]] = []

    def fake_dispatch(line: str, **kwargs: Any) -> SimpleNamespace:
        observed.append((line, kwargs))
        return SimpleNamespace(ok=True, error=None, output="", to_dict=lambda: {"ok": True})

    monkeypatch.setattr(sys, "argv", [program])
    monkeypatch.setattr(cli, "dispatch", fake_dispatch)

    assert cli.main(argv) == 0
    assert observed == [("STATUS", expected)]


def test_script_and_stdin_share_execution_without_changing_legacy_empty_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: list[tuple[str, dict[str, Any]]] = []
    script = tmp_path / "commands.dsl"
    script.write_text("STATUS\n", encoding="utf-8")

    def fake_execute(text: str, **kwargs: Any) -> list[Any]:
        observed.append((text, kwargs))
        return []

    monkeypatch.setattr(cli, "execute_dsl", fake_execute)
    monkeypatch.setattr(sys, "argv", ["dsl2koru"])

    assert cli.main([str(script), "--project", "repo"]) == 0
    monkeypatch.setattr(sys, "stdin", io.StringIO("STATUS\n"))
    assert cli.main(["run", "--file", "lane.env"]) == 0
    assert observed == [
        ("STATUS\n", {"default_project": "repo"}),
        ("STATUS\n", {"default_file": "lane.env"}),
    ]

    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert cli.main([]) == 1
    assert "usage: dsl2koru" in capsys.readouterr().out


def test_json_encode_decode_round_trip_uses_selected_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "command.json"
    monkeypatch.setattr(sys, "argv", ["dsl2coru"])

    assert cli.main(["encode", "ENV", "--file", "lane.env", "--format", "json", "--output", str(output)]) == 0
    assert cli.main(["decode", "--input", str(output), "--format", "json"]) == 0

    decoded = json.loads(capsys.readouterr().out)
    assert decoded == {"verb": "ENV", "file": "lane.env"}


@pytest.mark.parametrize(
    ("program", "format_name", "expected_factory", "expected_method"),
    [
        ("dsl2koru", "auto", ("project", "."), "replay"),
        ("dsl2coru", "jsonl", ("default", "."), "read_all"),
        ("dsl2coru", "protobuf", ("default", "."), "replay_pb"),
    ],
)
def test_replay_matrix_preserves_store_and_format_routing(
    monkeypatch: pytest.MonkeyPatch,
    program: str,
    format_name: str,
    expected_factory: tuple[str, str],
    expected_method: str,
) -> None:
    observed: list[tuple[str, Any]] = []

    class Store:
        def replay(self) -> list[Any]:
            observed.append(("method", "replay"))
            return []

        def read_all(self) -> list[Any]:
            observed.append(("method", "read_all"))
            return []

        def replay_pb(self) -> list[Any]:
            observed.append(("method", "replay_pb"))
            return []

    class Stores:
        @staticmethod
        def for_project(path: Path) -> Store:
            observed.append(("project", str(path)))
            return Store()

        @staticmethod
        def for_default(path: str | None) -> Store:
            observed.append(("default", path))
            return Store()

    monkeypatch.setattr(sys, "argv", [program])
    monkeypatch.setattr(cli, "EventStore", Stores)

    assert cli.main(["replay", "--format", format_name]) == 0
    assert observed == [expected_factory, ("method", expected_method)]


def test_schema_validation_keeps_success_and_failure_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["dsl2koru"])
    monkeypatch.setattr(cli, "validate_schemas", lambda: [])
    assert cli.main(["validate-schema"]) == 0
    assert capsys.readouterr().out == "schema OK\n"

    monkeypatch.setattr(cli, "validate_schemas", lambda: ["bad schema"])
    assert cli.main(["validate-schema"]) == 1
    assert capsys.readouterr().err == "bad schema\n"
