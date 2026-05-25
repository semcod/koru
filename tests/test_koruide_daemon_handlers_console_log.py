"""Unit tests for koruide.daemon console-log handlers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from koruide.daemon import handlers
from koruide.protocol import Message


def _client(**overrides: object) -> SimpleNamespace:
    data = {"ide": "vscodium", "version": "0.2.0"}
    data.update(overrides)
    return SimpleNamespace(**data)


def test_console_log_payload_requires_message_and_timestamp() -> None:
    assert handlers._console_log_payload(Message(type="console_log", data={})) is None
    assert (
        handlers._console_log_payload(
            Message(type="console_log", data={"message": "hello", "timestamp": "t", "data": {"n": 1}})
        )
        == ("hello", {"n": 1}, "t")
    )


def test_console_log_meta_prefers_payload_then_client() -> None:
    client = _client(ide="cursor", version="1.0.0")
    msg = Message(
        type="console_log",
        data={"message": "hello", "timestamp": "t", "ide": "vscodium", "version": "0.2.0"},
    )
    assert handlers._console_log_meta(client, msg) == ("vscodium", "0.2.0")

    fallback = Message(type="console_log", data={"message": "hello", "timestamp": "t"})
    assert handlers._console_log_meta(client, fallback) == ("cursor", "1.0.0")


def test_handle_console_log_records_valid_entry() -> None:
    daemon = mock.Mock()
    client = _client(ide="windsurf", version="0.1.45")
    msg = Message(
        type="console_log",
        data={
            "message": "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
            "data": {"attempt": 1},
            "timestamp": "2026-05-22T12:00:00Z",
        },
    )

    with mock.patch("koruide.daemon.handlers.add_console_log") as add_console_log:
        handlers.handle_console_log(daemon, client, msg)

    add_console_log.assert_called_once_with(
        "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
        {"attempt": 1},
        "2026-05-22T12:00:00Z",
        ide="windsurf",
        version="0.1.45",
    )
    daemon.log.assert_not_called()


def test_handle_console_log_ignores_invalid_payload() -> None:
    daemon = mock.Mock()
    client = _client()

    with mock.patch("koruide.daemon.handlers.add_console_log") as add_console_log:
        handlers.handle_console_log(
            daemon,
            client,
            Message(type="console_log", data={"message": "missing timestamp"}),
        )

    add_console_log.assert_not_called()
    daemon.log.assert_not_called()


def test_handle_console_log_surfaces_live_dsl_line() -> None:
    daemon = mock.Mock()
    client = _client(ide="vscode")
    msg = Message(
        type="console_log",
        data={
            "message": "[DSL-LIVE] #001 act=submit route=command ok=true",
            "timestamp": "2026-05-22T12:00:00Z",
            "ide": "vscodium",
        },
    )

    with mock.patch("koruide.daemon.handlers.add_console_log"):
        handlers.handle_console_log(daemon, client, msg)

    daemon.log.assert_called_once_with(
        "[DSL] #001 act=submit route=command ok=true via=plugin ide=vscodium"
    )
