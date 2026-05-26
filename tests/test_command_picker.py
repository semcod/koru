from __future__ import annotations

import json

from koru.autonomy_strategy.openrouter import OpenRouterStrategyResponse
from koruide.command_picker import HeuristicPicker, OpenRouterPicker, pick_command_order
from koruide.command_telemetry import CommandTelemetry


def test_heuristic_picker_orders_by_success_rate(tmp_path) -> None:
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
        command="workbench.action.chat.submit",
        ok=True,
    )
    telemetry.record(
        ide="cursor",
        plugin_version="0.2.0",
        capability="submit",
        command="composer.sendToAgent",
        ok=False,
    )
    picker = HeuristicPicker(telemetry=telemetry)
    ordered = picker.pick(
        "cursor",
        "submit",
        catalog={
            "submit": ["composer.sendToAgent", "workbench.action.chat.submit"],
        },
        plugin_version="0.2.0",
    )
    assert ordered[0] == "workbench.action.chat.submit"


def test_openrouter_picker_falls_back_on_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KORU_LLM_PICKER", "always")

    def _fail(*_args, **_kwargs):
        return OpenRouterStrategyResponse(ok=False, content="", error="timeout")

    monkeypatch.setattr("koruide.command_picker.call_openrouter_json", _fail)
    telemetry = CommandTelemetry(tmp_path)
    telemetry.record(
        ide="cursor",
        plugin_version="0.2.0",
        capability="submit",
        command="workbench.action.chat.submit",
        ok=True,
    )
    picker = OpenRouterPicker(heuristic=HeuristicPicker(telemetry=telemetry))
    ordered = picker.pick(
        "cursor",
        "submit",
        catalog={"submit": ["composer.sendToAgent", "workbench.action.chat.submit"]},
        plugin_version="0.2.0",
    )
    assert ordered[0] == "workbench.action.chat.submit"


def test_openrouter_picker_parses_json(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KORU_LLM_PICKER", "always")

    def _ok(*_args, **_kwargs):
        return OpenRouterStrategyResponse(
            ok=True,
            content=json.dumps(
                {"ordered": ["composer.sendToAgent"], "why": "vendor native"},
            ),
        )

    monkeypatch.setattr("koruide.command_picker.call_openrouter_json", _ok)
    picker = OpenRouterPicker(heuristic=HeuristicPicker(telemetry=CommandTelemetry(tmp_path)))
    ordered = picker.pick(
        "cursor",
        "submit",
        catalog={"submit": ["composer.sendToAgent", "workbench.action.chat.submit"]},
        plugin_version="0.2.0",
    )
    assert ordered == ["composer.sendToAgent"]


def test_pick_command_order_returns_capabilities(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KORU_COMMAND_CATALOG", "1")
    order = pick_command_order(
        ide="cursor",
        plugin_version="0.2.0",
        catalog={
            "focus_open": ["composer.openComposer"],
            "paste": ["composer.startComposerPrompt2"],
            "submit": ["workbench.action.chat.submit"],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert "submit" in order
    assert order["submit"]


def test_vscodium_focus_open_avoids_quick_chat(tmp_path) -> None:
    order = pick_command_order(
        ide="vscodium",
        plugin_version="0.2.7",
        catalog={
            "focus_open": [
                "workbench.action.openQuickChat",
                "workbench.action.quickchat.openInChatView",
                "workbench.action.chat.focusInput",
            ],
            "submit": ["workbench.action.chat.submit"],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert "focus_open" not in order


def test_vscodium_focus_open_override_can_be_enabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KORU_VSCODIUM_COMMAND_ORDER_FOCUS_OPEN", "1")
    order = pick_command_order(
        ide="vscodium",
        plugin_version="0.2.7",
        catalog={
            "focus_open": [
                "workbench.action.openQuickChat",
                "workbench.action.quickchat.openInChatView",
                "workbench.action.chat.focusInput",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert order["focus_open"] == ["workbench.action.chat.focusInput"]
