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


def test_cursor_submit_sanitizer_rejects_non_chat_commands(tmp_path) -> None:
    order = pick_command_order(
        ide="cursor",
        plugin_version="0.2.1",
        catalog={
            "submit": [
                "scm.acceptInput",
                "repl.action.acceptInput",
                "composer.sendToAgent",
                "workbench.action.chat.submit",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert "scm.acceptInput" not in order["submit"]
    assert "repl.action.acceptInput" not in order["submit"]
    assert order["submit"] == [
        "workbench.action.chat.submit",
        "composer.sendToAgent",
    ]


def test_cursor_paste_sanitizer_rejects_clipboard_paste(tmp_path) -> None:
    order = pick_command_order(
        ide="cursor",
        plugin_version="0.2.2",
        catalog={
            "paste": [
                "editor.action.clipboardPasteAction",
                "workbench.action.chat.typeText",
                "composer.typeText",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert "editor.action.clipboardPasteAction" not in order["paste"]
    assert order["paste"][0] == "workbench.action.chat.typeText"


def test_cursor_paste_sanitizer_rejects_terminal_paste(tmp_path) -> None:
    order = pick_command_order(
        ide="cursor",
        plugin_version="0.2.4",
        catalog={
            "paste": [
                "workbench.action.terminal.paste",
                "workbench.action.chat.typeText",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert "workbench.action.terminal.paste" not in order["paste"]
    assert order["paste"][0] == "workbench.action.chat.typeText"


def test_cursor_submit_default_prefers_workbench_over_composer(tmp_path) -> None:
    order = pick_command_order(
        ide="cursor",
        plugin_version="0.2.2",
        catalog={
            "submit": [
                "composer.sendToAgent",
                "composer.acceptComposerStep",
                "workbench.action.chat.submit",
                "workbench.action.chat.stopListeningAndSubmit",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert order["submit"] == [
        "workbench.action.chat.stopListeningAndSubmit",
        "workbench.action.chat.submit",
        "composer.sendToAgent",
        "composer.acceptComposerStep",
    ]


def test_cursor_picker_rejects_start_composer_prompt_from_paste_and_submit(tmp_path) -> None:
    order = pick_command_order(
        ide="cursor",
        plugin_version="0.2.1",
        catalog={
            "paste": [
                "composer.startComposerPrompt2",
                "composer.startComposerPrompt",
                "composer.typeText",
            ],
            "submit": [
                "composer.startComposerPrompt2",
                "composer.sendToAgent",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )

    assert order["paste"] == ["composer.typeText"]
    assert "composer.startComposerPrompt2" not in order["submit"]
    assert order["submit"] == ["composer.sendToAgent"]


def test_cursor_focus_open_rejects_panel_chat_toggle(tmp_path) -> None:
    order = pick_command_order(
        ide="cursor",
        plugin_version="0.2.12",
        catalog={
            "focus_open": [
                "workbench.panel.chat",
                "composer.openAsPane",
                "workbench.action.chat.open",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )

    assert order["focus_open"] == ["workbench.action.chat.open"]


def test_windsurf_focus_open_prefers_existing_panel_over_new_window(tmp_path) -> None:
    order = pick_command_order(
        ide="windsurf",
        plugin_version="0.2.9",
        catalog={
            "focus_open": [
                "windsurf.action.openChat",
                "windsurf.chat.open",
                "windsurf.cascade.open",
                "windsurf.cascadePanel.focus",
                "cascade.focus",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )

    focus_open = order["focus_open"]
    # The first attempted command must focus the existing Cascade panel,
    # never an "open" command that spawns a new chat window/pane.
    assert focus_open[0] == "windsurf.cascadePanel.focus"
    assert "open" not in focus_open[0].lower()


def test_antigravity_focus_open_rejects_new_chat_action(tmp_path) -> None:
    order = pick_command_order(
        ide="antigravity",
        plugin_version="0.2.10",
        catalog={
            "focus_open": [
                "aichat.newchataction",
                "workbench.action.chat.focusInput",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )

    assert "aichat.newchataction" not in order["focus_open"]
    assert order["focus_open"][0] == "antigravity.agentSidePanel.open"


def test_antigravity_focus_open_rejects_open_agent(tmp_path) -> None:
    order = pick_command_order(
        ide="antigravity",
        plugin_version="0.2.6",
        catalog={
            "focus_open": [
                "antigravity.openAgent",
                "workbench.action.chat.focusInput",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )

    focus_open = order["focus_open"]
    assert "antigravity.openAgent" not in focus_open
    assert focus_open[0] == "antigravity.agentSidePanel.open"
    assert "antigravity.agentSidePanel.focus" in focus_open


def test_antigravity_focus_open_prefers_side_panel_when_miscategorised(tmp_path) -> None:
    # Plugin 0.2.6 puts agentSidePanel.focus in unknown_chat instead of focus_open.
    order = pick_command_order(
        ide="antigravity",
        plugin_version="0.2.6",
        catalog={
            "focus_open": [
                "workbench.action.chat.focusInput",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )

    focus_open = order["focus_open"]
    assert focus_open[0] == "antigravity.agentSidePanel.open"
    assert "antigravity.agentSidePanel.focus" in focus_open


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
                "chatgpt.sidebarView.open",
                "workbench.action.openQuickChat",
                "workbench.action.quickchat.openInChatView",
                "workbench.action.chat.focusInput",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert order["focus_open"] == ["chatgpt.sidebarView.open"]


def test_vscodium_focus_open_override_rejects_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KORU_VSCODIUM_COMMAND_ORDER_FOCUS_OPEN", "1")
    order = pick_command_order(
        ide="vscodium",
        plugin_version="0.2.8",
        catalog={
            "focus_open": [
                "workbench.action.chat.openChatEmptyStateSettings",
                "workbench.action.chat.focusInput",
            ],
        },
        telemetry=CommandTelemetry(tmp_path),
    )
    assert order.get("focus_open", []) == []
