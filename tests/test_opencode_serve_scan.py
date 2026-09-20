"""Behavior-pinning tests for the ``opencode serve`` /proc scan.

``tests/test_dashboard_terminals.py`` mocks ``_scan_serve_processes``
directly, so these tests pin the real scan logic: cmdline reading,
argv matching, listen-argument parsing and end-to-end discovery.
"""

from __future__ import annotations

from unittest.mock import patch

from koruapi import opencode_terminals as ot


def _cmdline(names: list[str]) -> bytes:
    return b"\0".join(n.encode("utf-8") for n in names) + b"\0"


class TestReadCmdline:
    def test_splits_nul_separated_argv_and_drops_trailing_empty(self) -> None:
        class filelike:
            def read_bytes(self) -> bytes:
                return _cmdline(["opencode", "serve"])

        class dirlike:
            def __truediv__(self, other: str) -> filelike:
                return filelike()

        assert ot._read_cmdline(dirlike()) == ["opencode", "serve"]

    def test_filters_interior_empty_arguments(self) -> None:
        class filelike:
            def read_bytes(self) -> bytes:
                return b"opencode\0\0serve\0"

        class dirlike:
            def __truediv__(self, other: str) -> filelike:
                return filelike()

        assert ot._read_cmdline(dirlike()) == ["opencode", "serve"]

    def test_returns_none_on_oserror(self) -> None:
        class filelike:
            def read_bytes(self) -> bytes:
                raise OSError("gone")

        class dirlike:
            def __truediv__(self, other: str) -> filelike:
                return filelike()

        assert ot._read_cmdline(dirlike()) is None


class TestToInt:
    def test_parses_decimal(self) -> None:
        assert ot._to_int("4123") == 4123

    def test_returns_none_on_invalid(self) -> None:
        assert ot._to_int("http") is None
        assert ot._to_int("") is None


class TestIsOpencodeServe:
    def test_accepts_plain_argv(self) -> None:
        assert ot._is_opencode_serve(["opencode", "serve"]) is True

    def test_accepts_absolute_path_and_flags(self) -> None:
        names = ["/usr/local/bin/opencode", "--verbose", "serve", "--port", "1"]
        assert ot._is_opencode_serve(names) is True

    def test_accepts_serve_in_positions_one_to_three(self) -> None:
        assert ot._is_opencode_serve(["opencode", "run", "serve"]) is True
        assert ot._is_opencode_serve(["opencode", "a", "b", "serve"]) is True

    def test_rejects_serve_beyond_position_three(self) -> None:
        assert ot._is_opencode_serve(["opencode", "a", "b", "c", "serve"]) is False

    def test_rejects_short_or_foreign_argv(self) -> None:
        assert ot._is_opencode_serve(["opencode"]) is False
        assert ot._is_opencode_serve(["python", "serve"]) is False
        assert ot._is_opencode_serve([]) is False


class TestParseServeListenArgs:
    def test_space_separated_port(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve", "--port", "4123"]) == (4123, "127.0.0.1")

    def test_equals_port(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve", "--port=9999"]) == (9999, "127.0.0.1")

    def test_space_separated_hostname(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve", "--port", "1", "--hostname", "0.0.0.0"]) == (
            1,
            "0.0.0.0",
        )

    def test_equals_hostname(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve", "--hostname=localhost", "--port=2"]) == (
            2,
            "localhost",
        )

    def test_defaults_without_listen_args(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve"]) == (
            None,
            "127.0.0.1",
        )

    def test_invalid_port_value_falls_back_to_none(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve", "--port", "http"]) == (None, "127.0.0.1")
        assert ot._parse_serve_listen_args(["opencode", "serve", "--port=http"]) == (None, "127.0.0.1")

    def test_last_occurrence_wins(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve", "--port", "1", "--port=2"]) == (2, "127.0.0.1")

    def test_trailing_port_flag_without_value_is_ignored(self) -> None:
        assert ot._parse_serve_listen_args(["opencode", "serve", "--port"]) == (None, "127.0.0.1")


class _FakeCmdFile:
    def __init__(self, payload: bytes | Exception) -> None:
        self._payload = payload

    def read_bytes(self) -> bytes:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeProcEntry:
    def __init__(self, name: str, payload: bytes | Exception) -> None:
        self.name = name
        self._payload = payload

    def __truediv__(self, other: str) -> _FakeCmdFile:
        assert other == "cmdline"
        return _FakeCmdFile(self._payload)


class _FakeProcDir:
    def __init__(self, entries: list[_FakeProcEntry]) -> None:
        self._entries = entries

    def is_dir(self) -> bool:
        return True

    def iterdir(self):
        return iter(self._entries)


class _MissingProcDir:
    def is_dir(self) -> bool:
        return False


class TestScanServeProcesses:
    def _scan(self, entries, *, missing: bool = False):
        def fake_path(value):
            assert value == "/proc"
            return _MissingProcDir() if missing else _FakeProcDir(entries)

        with patch.object(ot, "Path", side_effect=fake_path):
            return ot._scan_serve_processes()

    def test_discovers_space_form_with_defaults(self) -> None:
        found = self._scan(
            [
                _FakeProcEntry("4123", _cmdline(["opencode", "serve", "--port", "4123"])),
            ]
        )
        assert found == [
            {
                "id": "proc-4123",
                "url": "http://127.0.0.1:4123",
                "pid": 4123,
                "label": "opencode serve :4123",
                "managed": False,
                "auto_answer": False,
            }
        ]

    def test_discovers_equals_form_with_hostname(self) -> None:
        found = self._scan(
            [
                _FakeProcEntry("77", _cmdline(["/opt/opencode", "serve", "--hostname=0.0.0.0", "--port=9999"])),
            ]
        )
        assert found == [
            {
                "id": "proc-9999",
                "url": "http://0.0.0.0:9999",
                "pid": 77,
                "label": "opencode serve :9999",
                "managed": False,
                "auto_answer": False,
            }
        ]

    def test_skips_non_numeric_unreadable_and_portless_entries(self) -> None:
        found = self._scan(
            [
                _FakeProcEntry("self", _cmdline(["opencode", "serve", "--port", "1"])),
                _FakeProcEntry("42", OSError("permission denied")),
                _FakeProcEntry("43", _cmdline(["opencode", "serve"])),
                _FakeProcEntry("44", _cmdline(["opencode", "serve", "--port", "http"])),
                _FakeProcEntry("45", _cmdline(["python", "serve", "--port", "5"])),
                _FakeProcEntry("46", _cmdline(["opencode", "a", "b", "c", "serve", "--port", "6"])),
            ]
        )
        assert found == []

    def test_returns_empty_when_proc_missing(self) -> None:
        assert self._scan([], missing=True) == []
