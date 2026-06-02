from __future__ import annotations

from koruide.ides.antigravity import AntigravityStrategy
from koruide.ides.cursor import CursorStrategy
from koruide.ides.jetbrains import JetbrainsStrategy
from koruide.ides.vscode import VscodeStrategy
from koruide.ides.vscodium import VscodiumStrategy
from koruide.ides.windsurf import WindsurfStrategy
from koruide.ides.zed import ZedStrategy
from korullm.strategies.claude import ClaudeStrategy
from korullm.strategies.codex import CodexStrategy
from korullm.strategies.gpt import GptStrategy
from korullm.strategies.ide_chat import IdeChatStrategy
from korullm.strategies.ollama import OllamaStrategy
from koruos.strategies.darwin import DarwinStrategy
from koruos.strategies.wayland_linux import WaylandLinuxStrategy
from koruos.strategies.windows import WindowsStrategy
from koruos.strategies.x11_linux import X11LinuxStrategy


def test_ide_metadata_accessors_stable() -> None:
    assert CursorStrategy().id == "cursor"
    assert CursorStrategy().label == "Cursor"
    assert CursorStrategy().config_folder_name == "Cursor"

    assert VscodeStrategy().id == "vscode"
    assert VscodeStrategy().label == "VS Code"
    assert VscodeStrategy().config_folder_name == "Code"

    assert VscodiumStrategy().id == "vscodium"
    assert VscodiumStrategy().label == "VSCodium"
    assert VscodiumStrategy().config_folder_name == "VSCodium"

    assert WindsurfStrategy().id == "windsurf"
    assert WindsurfStrategy().label == "Windsurf"
    assert WindsurfStrategy().config_folder_name == "Windsurf"

    assert AntigravityStrategy().id == "antigravity"
    assert AntigravityStrategy().label == "Antigravity"
    assert AntigravityStrategy().config_folder_name == "Antigravity"

    assert JetbrainsStrategy().id == "jetbrains"
    assert JetbrainsStrategy().label == "JetBrains IDE"

    assert ZedStrategy().id == "zed"
    assert ZedStrategy().label == "Zed"


def test_os_metadata_accessors_stable() -> None:
    assert WaylandLinuxStrategy().id == "linux-wayland"
    assert WaylandLinuxStrategy().label == "Linux / Wayland"

    assert X11LinuxStrategy().id == "linux-x11"
    assert X11LinuxStrategy().label == "Linux / X11"

    assert DarwinStrategy().id == "darwin"
    assert DarwinStrategy().label == "macOS"

    assert WindowsStrategy().id == "windows"
    assert WindowsStrategy().label == "Windows"


def test_llm_metadata_accessors_stable() -> None:
    assert IdeChatStrategy().id == "ide_chat"
    assert IdeChatStrategy().label == "IDE embedded chat"

    assert GptStrategy().id == "openai"
    assert GptStrategy().label == "OpenAI / GPT"

    assert ClaudeStrategy().id == "anthropic"
    assert ClaudeStrategy().label == "Anthropic / Claude"

    assert OllamaStrategy().id == "ollama"
    assert OllamaStrategy().label == "Ollama"

    assert CodexStrategy().id == "codex"
    assert CodexStrategy().label == "OpenAI Codex CLI"
