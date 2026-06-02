"""Smoke tests for the JetBrains autopilot plugin scaffold."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "koru-autopilot-jetbrains"


def test_jetbrains_plugin_scaffold_files_exist() -> None:
    expected = [
        "settings.gradle.kts",
        "build.gradle.kts",
        "gradle.properties",
        "src/main/resources/META-INF/plugin.xml",
        "src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt",
        "src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotReconnectAction.kt",
        "src/main/kotlin/com/semcod/koru/autopilot/SocketPath.kt",
        "src/main/kotlin/com/semcod/koru/autopilot/ChatInjector.kt",
    ]

    missing = [path for path in expected if not (PLUGIN / path).is_file()]

    assert missing == []


def test_jetbrains_plugin_metadata_wires_service_and_action() -> None:
    plugin_xml = (PLUGIN / "src/main/resources/META-INF/plugin.xml").read_text(
        encoding="utf-8",
    )
    build_file = (PLUGIN / "build.gradle.kts").read_text(encoding="utf-8")

    assert "org.jetbrains.intellij.platform" in build_file
    assert "applicationService" in plugin_xml
    assert "KoruAutopilotService" in plugin_xml
    assert "KoruAutopilot.Reconnect" in plugin_xml


def test_jetbrains_plugin_readme_no_longer_stub() -> None:
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")

    assert "(to add)" not in readme
    assert "Status:** Gradle / IntelliJ Platform scaffold" in readme


def test_jetbrains_plugin_reports_send_proof_frames() -> None:
    service = (
        PLUGIN
        / "src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt"
    ).read_text(encoding="utf-8")

    assert '"protocolVersion" to 2' in service
    assert '"chat.events"' in service
    assert '"message.sent"' in service
    assert '"winning_focus_open"' in service
    assert '"winning_paste"' in service
    assert '"winning_submit"' in service
    assert "operation_trace" in service
    assert "is Iterable<*>" in service


def test_jetbrains_injector_attempts_before_ack_and_uses_ctrl_enter() -> None:
    injector = (
        PLUGIN
        / "src/main/kotlin/com/semcod/koru/autopilot/ChatInjector.kt"
    ).read_text(encoding="utf-8")

    assert "data class ChatInjectResult" in injector
    assert "invokeAndWait" in injector
    assert "invokeLater" not in injector
    assert "KeyEvent.VK_CONTROL" in injector
    assert "KeyEvent.VK_ENTER" in injector
    assert "jetbrains.robot.ctrlEnter" in injector
