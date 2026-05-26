from __future__ import annotations

import json
from pathlib import Path

from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide_control import ide_control_strategy
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION


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


def test_should_try_os_fallback_false_for_plugin_socket_ides() -> None:
    assert not DriveOrchestrator.should_try_os_fallback(
        plugin_ok=True,
        info={"submitted": False},
        submit_requested=True,
        plugin_ide="vscode",
        require_plugin=False,
    )


def test_should_try_os_fallback_true_for_keyboard_strategy_submit_failure() -> None:
    assert DriveOrchestrator.should_try_os_fallback(
        plugin_ok=True,
        info={"submitted": False},
        submit_requested=True,
        plugin_ide="jetbrains",
        require_plugin=False,
    )


def test_ide_control_strategies_keep_plugin_and_keyboard_lanes_separate() -> None:
    assert ide_control_strategy("vscodium").requires_plugin is True
    assert ide_control_strategy("vscodium").allow_keyboard_fallback_after_plugin_ack is False
    assert ide_control_strategy("cursor").strict_ack_supported is True
    assert ide_control_strategy("windsurf").strict_ack_supported is False
    assert ide_control_strategy("jetbrains").requires_plugin is False
    assert ide_control_strategy("jetbrains").allow_keyboard_fallback_after_plugin_ack is True


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
    assert info["intent_status"] == "fulfilled"
    assert info["intent_confidence"] == "strong"


def test_annotate_plugin_ack_rejects_vscodium_registered_submit_false_positive() -> None:
    info = DriveOrchestrator.annotate_plugin_ack(
        info={
            "delivered": True,
            "opened": True,
            "submitted": True,
            "winning_focus_open": "workbench.panel.chat+workbench.action.chat.focusInput",
            "winning_paste": "host-clipboard:wl-copy+xdotool key ctrl+v",
            "winning_submit": "workbench.action.chat.submit",
        },
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscodium",
    )

    assert info["verification"] == "submit_unverified"
    assert info["intent_status"] == "unverified"
    assert info["intent_confidence"] == "none"
    assert "registered submit command is not trusted" in info["submit_failure_reason"]


def test_annotate_plugin_ack_accepts_vscodium_registered_submit_with_verify_probe() -> None:
    info = DriveOrchestrator.annotate_plugin_ack(
        info={
            "delivered": True,
            "opened": True,
            "submitted": True,
            "winning_focus_open": "workbench.panel.chat+workbench.action.chat.focusInput",
            "winning_paste": "host-clipboard:wl-copy+xdotool key ctrl+v",
            "winning_submit": "workbench.action.chat.submit",
            "operation_trace": [
                {
                    "op": "submit",
                    "route": "accepted",
                    "ok": True,
                    "detail": {"requireEmptyAfterSubmit": True},
                },
                {"op": "submit_verify", "route": "chat-input-probe", "ok": True},
            ],
        },
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscodium",
    )

    assert info["verification"] == "strict"


def test_annotate_plugin_ack_rejects_vscodium_loose_submit_verify_probe() -> None:
    info = DriveOrchestrator.annotate_plugin_ack(
        info={
            "delivered": True,
            "opened": True,
            "submitted": True,
            "winning_focus_open": "workbench.panel.chat+workbench.action.chat.focusInput",
            "winning_paste": "editor.action.clipboardPasteAction",
            "winning_submit": "workbench.action.chat.submit",
            "operation_trace": [
                {
                    "op": "submit",
                    "route": "accepted",
                    "ok": True,
                    "detail": {"requireEmptyAfterSubmit": False},
                },
                {"op": "submit_verify", "route": "chat-input-probe", "ok": True},
            ],
        },
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscodium",
    )

    assert info["verification"] == "submit_unverified"
    assert "empty-input" in info["submit_failure_reason"]


def test_annotate_plugin_ack_accepts_vscodium_message_sent_event_after_loose_submit_probe() -> None:
    info = DriveOrchestrator.annotate_plugin_ack(
        info={
            "delivered": True,
            "opened": True,
            "submitted": True,
            "winning_focus_open": "workbench.panel.chat+workbench.action.chat.focusInput",
            "winning_paste": "editor.action.clipboardPasteAction",
            "winning_submit": "workbench.action.chat.submit",
            "operation_trace": [
                {
                    "op": "submit",
                    "route": "accepted",
                    "ok": True,
                    "detail": {"requireEmptyAfterSubmit": False},
                },
                {"op": "submit_verify", "route": "sentinel-clipboard", "ok": True},
                {"op": "message_sent", "route": "plugin-event", "ok": True},
            ],
        },
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscodium",
    )

    assert info["verification"] == "event_only"
    assert info["intent_status"] == "fulfilled"
    assert info["intent_validator"] == "message.sent"
    assert "message.sent event observed" in info["submit_success_reason"]


def test_should_defer_submit_unverified_for_vscodium_message_sent_grace() -> None:
    assert DriveOrchestrator.should_defer_submit_unverified_for_message_sent(
        info={"verification": "submit_unverified"},
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscodium",
    )


def test_should_not_defer_non_vscodium_submit_unverified() -> None:
    assert not DriveOrchestrator.should_defer_submit_unverified_for_message_sent(
        info={"verification": "submit_unverified"},
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscode",
    )


def test_annotate_plugin_ack_marks_plugin_ack_without_winning_commands() -> None:
    info = DriveOrchestrator.annotate_plugin_ack(
        info={"delivered": True, "opened": True, "submitted": True},
        plugin_ok=True,
        submit_requested=True,
    )
    assert info["verification"] == "plugin_ack"


def test_plugin_ack_summary_includes_submit_failure_details() -> None:
    summary = DriveOrchestrator.plugin_ack_summary(
        {
            "verification": "submit_unverified",
            "attempted_submit": "vscodium-submit-unavailable",
            "submit_failure_reason": "missing submit click coordinates",
            "submit_attempts": [
                "submit click skipped: missing submitClickX/submitClickY",
                "xdotool key Return => failed",
            ],
        }
    )

    assert "attempted_submit=vscodium-submit-unavailable" in summary
    assert "submit_failure_reason=missing submit click coordinates" in summary
    assert "submit_attempts=submit click skipped" in summary


def test_plugin_version_info_marks_mismatch(monkeypatch) -> None:
    monkeypatch.delenv("KORU_STRICT_PLUGIN_VERSION", raising=False)
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_version", lambda _ide=None: "0.1.13")

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


def test_plugin_build_sha_blocks_same_version_stale_build(monkeypatch) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_version", lambda _ide=None: "0.2.7")
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_build_sha", lambda _ide=None: "newbuild")

    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscodium",
        connected_version="0.2.7",
        connected_build_sha="oldbuild",
        protocol_version=2,
    )

    assert info["plugin_version_mismatch"] is False
    assert info["plugin_build_mismatch"] is True
    assert DriveOrchestrator.should_block_plugin_version(info)
    assert "build mismatch" in DriveOrchestrator.plugin_version_block_message(info)


def test_plugin_build_sha_missing_blocks_when_expected_build_known(monkeypatch) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_version", lambda _ide=None: "0.2.7")
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_build_sha", lambda _ide=None: "newbuild")

    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscodium",
        connected_version="0.2.7",
        protocol_version=2,
    )

    assert info["plugin_build_missing"] is True
    assert DriveOrchestrator.should_block_plugin_version(info)


def test_compatible_protocol_does_not_bypass_strict_version_policy(monkeypatch) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_version", lambda _ide=None: "0.1.15")

    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscode",
        connected_version="0.1.14",
        protocol_version=1,
        capabilities=["chat.submit"],
    )

    assert info["plugin_version_mismatch"] is True
    assert info["plugin_protocol_compatible"] is True
    assert info["plugin_version_policy"] == "strict"
    assert DriveOrchestrator.should_block_plugin_version(info)


def test_explicit_protocol_policy_allows_compatible_version_drift(monkeypatch) -> None:
    monkeypatch.setenv("KORU_PLUGIN_VERSION_POLICY", "protocol")
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_version", lambda _ide=None: "0.1.15")

    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscode",
        connected_version="0.1.14",
        protocol_version=1,
        capabilities=["chat.submit"],
    )

    assert info["plugin_version_mismatch"] is True
    assert info["plugin_protocol_compatible"] is True
    assert info["plugin_version_policy"] == "protocol"
    assert not DriveOrchestrator.should_block_plugin_version(info)


def test_incompatible_protocol_blocks_even_without_version_drift() -> None:
    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscode",
        connected_version="0.1.15",
        expected_version="0.1.15",
        protocol_version=0,
    )

    assert info["plugin_protocol_incompatible"] is True
    assert DriveOrchestrator.should_block_plugin_version(info)
    assert "protocol mismatch" in DriveOrchestrator.plugin_version_block_message(info)


def test_missing_protocol_blocks_developer_plugin() -> None:
    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscode",
        connected_version="0.1.16",
        expected_version="0.1.16",
    )

    assert info["plugin_protocol_missing"] is True
    assert DriveOrchestrator.should_block_plugin_version(info)
    assert "protocol missing" in DriveOrchestrator.plugin_version_block_message(info)


def test_bundled_expected_plugin_version_matches_vscode_package_json() -> None:
    package_json = (
        Path(__file__).resolve().parents[1] / "plugins" / "koru-autopilot-vscode" / "package.json"
    )
    data = json.loads(package_json.read_text(encoding="utf-8"))

    assert EXPECTED_VSCODE_PLUGIN_VERSION == data["version"]


def test_plugin_ack_summary_includes_operation_trace() -> None:
    summary = DriveOrchestrator.plugin_ack_summary(
        {
            "verification": "submit_unverified",
            "operation_trace": [
                {"op": "focus_open", "route": "command", "ok": True, "command": "chat.open"},
                {"op": "paste", "route": "host-clipboard", "ok": True, "command": "wl-copy+wtype"},
                {
                    "op": "submit",
                    "route": "host-key",
                    "ok": False,
                    "reason": "input still contains pasted text",
                },
            ],
        },
    )

    assert "route_trace=" in summary
    assert "focus_open/command=ok:chat.open" in summary
    assert "submit/host-key=fail:input still contains pasted text" in summary


def test_operation_trace_dsl_renders_one_line_per_step() -> None:
    """Each plugin operation_trace step becomes a self-contained DSL line.

    This is the transparent decision log the operator asked for:
    instead of a single ``route_trace=op/route=ok:cmd > op/route=...``
    glob, we render one ``#NNN act=... intent="..." route=... ok=...``
    line per step so the daemon log can be grepped step-by-step.
    """
    lines = DriveOrchestrator.operation_trace_dsl(
        {
            "operation_trace": [
                {"op": "focus_open", "route": "command", "ok": True, "command": "chat.open"},
                {
                    "op": "paste",
                    "route": "host-clipboard",
                    "ok": True,
                    "command": "wl-copy+wtype",
                },
                {
                    "op": "submit",
                    "route": "host-key",
                    "ok": False,
                    "reason": "input still contains pasted text",
                },
            ],
        },
    )

    assert len(lines) == 3
    assert lines[0].startswith("#001 act=focus_open")
    assert "intent=" in lines[0]
    assert "route=command:chat.open" in lines[0]
    assert "ok=true" in lines[0]
    assert lines[1].startswith("#002 act=paste")
    assert "route=host-clipboard:wl-copy+wtype" in lines[1]
    assert lines[2].startswith("#003 act=submit")
    assert "ok=false" in lines[2]
    assert 'reason="input still contains pasted text"' in lines[2]


def test_operation_trace_dsl_marks_ambiguous_when_ok_unknown() -> None:
    lines = DriveOrchestrator.operation_trace_dsl(
        {
            "operation_trace": [
                {"op": "submit", "route": "command", "ok": None, "command": "composer.send"},
            ],
        },
    )

    assert lines == ["#001 act=submit "
                     'intent="send the prompt as a user message" '
                     "route=command:composer.send ok=ambiguous"]


def test_operation_trace_dsl_handles_missing_trace() -> None:
    assert DriveOrchestrator.operation_trace_dsl({}) == []
    assert DriveOrchestrator.operation_trace_dsl({"operation_trace": "garbage"}) == []


def test_drive_outcome_dsl_includes_winners_and_reason() -> None:
    line = DriveOrchestrator.drive_outcome_dsl(
        {
            "delivered": False,
            "verification": "submit_unverified",
            "winning_focus_open": "composer.openComposer",
            "winning_paste": "editor.action.clipboardPasteAction",
            "winning_submit": "",
            "submit_failure_reason": "no fresh user bubble after 2.5s",
        },
    )

    assert line.startswith("#999 act=drive")
    assert "delivered=false" in line
    assert "verification=submit_unverified" in line
    assert (
        "winners=focus=composer.openComposer|paste=editor.action.clipboardPasteAction|submit=-"
        in line
    )
    assert 'reason="no fresh user bubble after 2.5s"' in line


def test_drive_validation_dsl_separates_action_from_intent() -> None:
    lines = DriveOrchestrator.drive_validation_dsl(
        {
            "verification": "submit_unverified",
            "intent": "send_prompt",
            "intent_status": "unverified",
            "intent_confidence": "none",
            "intent_validator": "submit_unverified",
            "intent_reason": "type newline is not a chat send proof",
        }
    )

    assert lines[0].startswith("#800 act=validate")
    assert "validator=submit_unverified" in lines[0]
    assert "ok=false" in lines[0]
    assert "confidence=none" in lines[0]
    assert lines[1].startswith("#801 act=intent name=send_prompt")
    assert "status=unverified" in lines[1]


def test_drive_operator_dsl_adds_diagnosis_next_replay_and_validate() -> None:
    lines = DriveOrchestrator.drive_operator_dsl(
        {
            "delivered": False,
            "verification": "submit_unverified",
            "attempted_submit": "workbench.action.chat.submit",
            "submit_failure_reason": "input still contains pasted text",
            "replay_command": (
                "KORU_AUTOPILOT_INSTANCE=vscodium koru autopilot drive --ide "
                "vscodium --require-plugin --prompt-file /tmp/drive.prompt"
            ),
            "validate_command": (
                "koru autopilot trace --project /tmp/project --format drive-dsl --limit 30"
            ),
        },
        plugin_ok=False,
    )

    assert lines[0].startswith("#900 act=diagnose severity=error code=submit_not_verified")
    assert 'because="input still contains pasted text"' in lines[0]
    assert lines[1].startswith("#901 act=next owner=operator")
    assert "inspect replay trace" in lines[1]
    assert lines[2].startswith("#902 act=replay shell=")
    assert "--prompt-file /tmp/drive.prompt" in lines[2]
    assert lines[3].startswith("#903 act=validate shell=")
    assert "--format drive-dsl" in lines[3]


def test_drive_operator_dsl_marks_strict_submit_as_koru_owned_next_step() -> None:
    lines = DriveOrchestrator.drive_operator_dsl(
        {"delivered": True, "verification": "strict"},
        plugin_ok=True,
    )

    assert lines[0].startswith("#900 act=diagnose severity=ok code=submit_verified")
    assert lines[1].startswith("#901 act=next owner=koru")


def test_strict_plugin_version_blocks_when_expected_version_missing(monkeypatch) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(DriveOrchestrator, "expected_plugin_version", lambda _ide=None: None)

    info = DriveOrchestrator.plugin_version_info(
        plugin_ide="vscode",
        connected_version="0.1.11",
    )

    assert info["plugin_version_expected_missing"] is True
    assert DriveOrchestrator.should_block_plugin_version(info)
