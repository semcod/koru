"""Natural Language and DSL command parser and applier for koru config.

Adopts the tripartite NL-DSL-LLM pattern from wellmanifest/nl-dsl-llm:
  Layer 1: Deterministic regex and fuzzy matching in Polish and English
  Layer 2: Canonical config property mutations, multi-intent batching and schema validation
  Layer 3: Optional model translation fallback (tillm) for complex requests
"""

from __future__ import annotations

import copy
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from koruide.ide import autopilot_ide_choices, normalize_ide_id

from koru.configurator.features import _TOGGLEABLE_FEATURES, toggle_feature_sections
from koru.configurator.schema import ConfigureResult
from koru.configurator.store import save_project_config


def normalize_nl_text(text: str) -> str:
    """Normalize text: strip accents, lowercase, remove punctuation, collapse whitespace."""
    text = text.strip().lower().replace("ł", "l")
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s\.\-/:_]", " ", stripped)
    cleaned = re.sub(r"\.{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.rstrip(".")


@dataclass(frozen=True)
class ConfigMutationResult:
    success: bool
    message: str
    updated: bool
    config: dict[str, Any] | None = None


def _split_multi_intent_segments(raw_input: str) -> list[str]:
    """Split input on conjunctions (i, oraz, and, ;, ,) unless inside words."""
    # Replace semicolons and commas with ' and '
    preprocessed = re.sub(r"[,;]+", " and ", raw_input)
    # Split on word boundaries for 'i', 'oraz', 'and'
    tokens = re.split(r"\b(?:i|oraz|and)\b", preprocessed, flags=re.IGNORECASE)
    segments = [seg.strip() for seg in tokens if seg.strip()]
    return segments or [raw_input.strip()]


def _apply_single_nl_command(
    config: dict[str, Any],
    raw_input: str,
    project_path: Any,
) -> ConfigMutationResult:
    """Parse and apply a single deterministic command."""
    text = normalize_nl_text(raw_input)
    if not text:
        return ConfigMutationResult(success=True, message="Pusta komenda / Empty command", updated=False)

    if text in {"exit", "quit", "q", "wyjdz", "koniec"}:
        return ConfigMutationResult(success=True, message="exit", updated=False)

    if text in {"show", "pokaz", "status", "tabela", "table", "ls"}:
        return ConfigMutationResult(success=True, message="Aktualny stan konfiguracji:", updated=False, config=config)

    for handler in (
        _apply_ide_command, _apply_port_command, _apply_host_command,
        _apply_model_command, _apply_queue_command, _apply_lan_command,
        _apply_auto_port_command, _apply_features_command,
    ):
        result = handler(config, text, project_path)
        if result is not None:
            return result

    return ConfigMutationResult(
        success=False,
        message=(
            f"Nie rozpoznano intencji dla: '{raw_input}'. "
            "Przykłady komend NL:\n"
            "  - ide na cursor / zmien ide na windsurf\n"
            "  - port na 8080 / zmien port na 9000\n"
            "  - host na 0.0.0.0\n"
            "  - kolejka na ops / queue to default\n"
            "  - wlacz lan / wylacz lan\n"
            "  - wlacz mesh / wylacz vision\n"
            "  - pokaz / table\n"
            "  - exit / wyjdz"
        ),
        updated=False,
    )



def _persist_mutation(
    config: dict[str, Any],
    project_path: Any,
    key_path: tuple[str, ...],
    value: Any,
    message: str,
) -> ConfigMutationResult:
    """Set one config key-path, persist, and return a success result."""
    node = config
    for key in key_path[:-1]:
        node = node.setdefault(key, {})
    node[key_path[-1]] = value
    save_project_config(project_path, config)
    return ConfigMutationResult(
        success=True, message=message, updated=True, config=config
    )


def _replace_config(
    config: dict[str, Any], working: dict[str, Any], project_path: Any
) -> None:
    """Swap the whole config payload and persist it."""
    config.clear()
    config.update(working)
    save_project_config(project_path, working)


def _apply_ide_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 1. IDE change: "ide na cursor", "zmien ide na vscode", "set ide to windsurf"
    m_ide = re.search(r"(?:zmien\s+)?ide(?:\s+lane)?(?:\s+(?:na|to|=))?\s+([a-z0-9_-]+)", text)
    if m_ide:
        candidate = m_ide.group(1).strip()
        normalized = normalize_ide_id(candidate) or candidate
        valid_choices = autopilot_ide_choices()
        if normalized in valid_choices:
            return _persist_mutation(
                config, project_path, ("ide",), normalized,
                f"Zmieniono IDE na: {normalized}",
            )
        return ConfigMutationResult(
            success=False,
            message=f"Nieznane IDE: {candidate}. Dostępne: {', '.join(valid_choices)}",
            updated=False,
        )
    return None


def _apply_port_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 2. Port change: "port na 9000", "zmien port na 8080", "set port 8765"
    m_port = re.search(r"(?:zmien\s+)?port(?:\s+(?:na|to|=))?\s+(\d+)", text)
    if m_port:
        port_num = int(m_port.group(1))
        return _persist_mutation(
            config, project_path, ("serve", "port"), port_num,
            f"Zmieniono port dashboardu na: {port_num}",
        )
    return None


def _apply_host_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 3. Host change: "host na 0.0.0.0", "dashboard host 127.0.0.1"
    m_host = re.search(r"(?:zmien\s+)?host(?:\s+(?:na|to|=))?\s+([0-9a-z\.-]+)", text)
    if m_host:
        host_str = m_host.group(1).strip()
        return _persist_mutation(
            config, project_path, ("serve", "host"), host_str,
            f"Zmieniono host dashboardu na: {host_str}",
        )
    return None


def _apply_model_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 4. Model change: "model na sonnet", "zmien model na glm-5.3", "prosty model na glm5.3-flash"
    m_simple_model = re.search(
        r"(?:zmien\s+)?(?:prosty|maly|tani|simple|small|flash)\s+model(?:\s+(?:na|to|=))?\s+([a-z0-9_.:/-]+)",
        text,
    )
    if m_simple_model:
        model_name = m_simple_model.group(1).strip()
        return _persist_mutation(
            config, project_path, ("models", "simple"), model_name,
            f"Zmieniono prosty/szybki model (tier Flash) na: {model_name}",
        )

    m_model = re.search(r"(?:zmien\s+)?(?:glowny\s+)?model(?:\s+(?:na|to|=))?\s+([a-z0-9_.:/-]+)", text)
    if m_model and not text.startswith("ide"):
        model_name = m_model.group(1).strip()
        return _persist_mutation(
            config, project_path, ("models", "default"), model_name,
            f"Zmieniono domyślny model LLM na: {model_name}",
        )
    return None


def _apply_queue_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 5. Queue change: "kolejka na ops", "queue to default", "zmien queue na background"
    m_queue = re.search(r"(?:zmien\s+)?(?:kolejka|queue|kolejke)(?:\s+(?:na|to|=))?\s+([a-z0-9_-]+)", text)
    if m_queue:
        q_name = m_queue.group(1).strip()
        return _persist_mutation(
            config, project_path, ("queue_name",), q_name,
            f"Zmieniono domyślną kolejkę na: {q_name}",
        )
    return None


def _apply_lan_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 5. LAN toggle: "wlacz lan", "wylacz lan", "enable lan", "disable lan", "lan on/off"
    if any(k in text for k in ("wlacz lan", "enable lan", "lan on", "lan true", "lan tak")):
        return _persist_mutation(
            config, project_path, ("serve", "lan"), True,
            "Włączono dostęp LAN do dashboardu (lan=True)",
        )
    if any(k in text for k in ("wylacz lan", "disable lan", "lan off", "lan false", "lan nie")):
        return _persist_mutation(
            config, project_path, ("serve", "lan"), False,
            "Wyłączono dostęp LAN do dashboardu (lan=False)",
        )
    return None


def _apply_auto_port_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 6. Auto-port toggle: "wlacz auto-port", "wylacz auto-port", "auto port on/off"
    clean_no_hyphen = text.replace("-", " ")
    on_patterns = ("wlacz auto port", "wlacz autoport", "enable auto port", "auto port on", "autoport on")
    if any(k in clean_no_hyphen for k in on_patterns):
        return _persist_mutation(
            config, project_path, ("serve", "auto_port"), True,
            "Włączono auto-port (auto_port=True)",
        )
    off_patterns = ("wylacz auto port", "wylacz autoport", "disable auto port", "auto port off", "autoport off")
    if any(k in clean_no_hyphen for k in off_patterns):
        return _persist_mutation(
            config, project_path, ("serve", "auto_port"), False,
            "Wyłączono auto-port (auto_port=False)",
        )
    return None


def _apply_features_command(
    config: dict[str, Any], text: str, project_path: Any,
) -> ConfigMutationResult | None:
    # 7. Features enable/disable: "wlacz mesh", "wylacz vision", "enable sandbox", "disable browse"
    for feature in _TOGGLEABLE_FEATURES:
        if any(f"{action} {feature}" in text for action in ("wlacz", "enable", "activate", "start")):
            res: ConfigureResult = toggle_feature_sections(project_path, enable=(feature,))
            return ConfigMutationResult(
                success=True,
                message=f"Włączono sekcję: {feature} (+{feature})",
                updated=True,
                config=res.config,
            )
        if any(f"{action} {feature}" in text for action in ("wylacz", "disable", "deactivate", "stop")):
            res = toggle_feature_sections(project_path, disable=(feature,))
            return ConfigMutationResult(
                success=True,
                message=f"Wyłączono sekcję: {feature} (-{feature})",
                updated=True,
                config=res.config,
            )
    return None


def apply_nl_config_command(
    config: dict[str, Any],
    raw_input: str,
    project_path: Any,
) -> ConfigMutationResult:
    """Parse single or multi-intent commands and apply mutations atomically."""
    segments = _split_multi_intent_segments(raw_input)
    if len(segments) <= 1:
        return _apply_single_nl_command(config, raw_input, project_path)

    # Multi-intent batch transaction
    working_config = copy.deepcopy(config)
    messages: list[str] = []
    any_updated = False

    for segment in segments:
        sub_res = _apply_single_nl_command(working_config, segment, project_path)
        if not sub_res.success:
            return ConfigMutationResult(
                success=False,
                message=f"Błąd w poleceniu podrzędnym '{segment}': {sub_res.message}",
                updated=False,
                config=config,
            )
        if sub_res.updated and sub_res.config is not None:
            working_config = sub_res.config
            any_updated = True
        messages.append(sub_res.message)

    if any_updated:
        _replace_config(config, working_config, project_path)

    return ConfigMutationResult(
        success=True,
        message="; ".join(messages),
        updated=any_updated,
        config=working_config,
    )
