from __future__ import annotations

from koruide.command_telemetry import CommandTelemetry


def test_command_telemetry_accounting_and_persistence(tmp_path) -> None:
    telemetry = CommandTelemetry(tmp_path)
    telemetry.record(
        ide="cursor",
        plugin_version="0.2.0",
        capability="submit",
        command="workbench.action.chat.submit",
        ok=True,
    )
    telemetry.record(
        ide="cursor",
        plugin_version="0.2.0",
        capability="submit",
        command="composer.sendToAgent",
        ok=False,
        reason="no bubble",
    )
    assert (
        telemetry.success_rate("cursor", "0.2.0", "submit", "workbench.action.chat.submit")
        == 1.0
    )
    assert telemetry.attempts("cursor", "0.2.0", "submit", "composer.sendToAgent") == 1

    reloaded = CommandTelemetry(tmp_path)
    assert reloaded.attempts("cursor", "0.2.0", "submit", "composer.sendToAgent") == 1


def test_record_from_ack_operation_trace(tmp_path) -> None:
    telemetry = CommandTelemetry(tmp_path)
    telemetry.record_from_ack(
        ide="cursor",
        plugin_version="0.2.0",
        info={
            "operation_trace": [
                {"op": "submit", "command": "composer.sendToAgent", "ok": False},
                {"op": "paste", "command": "composer.startComposerPrompt2", "ok": True},
            ],
            "winning_submit": "workbench.action.chat.submit",
            "ok": True,
        },
    )
    assert telemetry.attempts("cursor", "0.2.0", "submit", "composer.sendToAgent") == 1
    assert telemetry.attempts("cursor", "0.2.0", "submit", "workbench.action.chat.submit") == 1
