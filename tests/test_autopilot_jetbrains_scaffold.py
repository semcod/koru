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
