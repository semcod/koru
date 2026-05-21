from __future__ import annotations

from koruide.drive_orchestrator import DriveOrchestrator


def test_plugin_required_message_mentions_ide_and_connect_command() -> None:
    message = DriveOrchestrator.plugin_required_message("vscode")
    assert "ide=vscode" in message
    assert "Connect autopilot daemon" in message


def test_should_try_os_fallback_false_when_plugin_required() -> None:
    assert not DriveOrchestrator.should_try_os_fallback(
        plugin_ok=False,
        info={"submitted": False},
        submit_requested=True,
        plugin_ide="vscode",
        require_plugin=True,
    )


def test_should_try_os_fallback_true_for_submit_failure() -> None:
    assert DriveOrchestrator.should_try_os_fallback(
        plugin_ok=True,
        info={"submitted": False},
        submit_requested=True,
        plugin_ide="vscode",
        require_plugin=False,
    )


def test_build_message_sent_info_keeps_chat_and_backend() -> None:
    info = DriveOrchestrator.build_message_sent_info(
        submit_requested=True,
        plugin_ide="vscode",
        event_data={"chat": "default"},
    )
    assert info["backend"] == "plugin"
    assert info["event"] == "message.sent"
    assert info["chat"] == "default"
    assert info["ide"] == "vscode"
    assert info["verification"] == "event_only"


def test_annotate_plugin_ack_marks_strict_when_winning_commands_exist() -> None:
    info = DriveOrchestrator.annotate_plugin_ack(
        info={
            "delivered": True,
            "opened": True,
            "submitted": True,
            "winning_focus_open": "workbench.action.chat.open",
            "winning_paste": "editor.action.clipboardPasteAction",
            "winning_submit": "workbench.action.chat.submit",
        },
        plugin_ok=True,
        submit_requested=True,
    )
    assert info["verification"] == "strict"


def test_annotate_plugin_ack_marks_plugin_ack_without_winning_commands() -> None:
    info = DriveOrchestrator.annotate_plugin_ack(
        info={"delivered": True, "opened": True, "submitted": True},
        plugin_ok=True,
        submit_requested=True,
    )
    assert info["verification"] == "plugin_ack"


def test_plugin_version_info_marks_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_version", lambda: "0.1.13")

    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscode",
        connected_version="0.1.11",
    )

    assert info["plugin_version"] == "0.1.11"
    assert info["expected_plugin_version"] == "0.1.13"
    assert info["plugin_version_mismatch"] is True
    assert info["plugin_version_policy"] == "warn"


def test_plugin_version_policy_can_block(monkeypatch) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    info = {"plugin_version_mismatch": True}

    assert DriveOrchestrator.should_block_plugin_version(info)
