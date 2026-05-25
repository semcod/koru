"""IDE command catalog for autonomy planning.

This module is intentionally conservative: it lists commands/actions Koru can
reason about, while the live plugin still verifies what the active IDE actually
exports before a command is used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class IdeCommand:
    category: str
    id: str
    kind: str
    confidence: str
    risk: str
    args: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["args"] = list(self.args)
        return row


SOURCES: tuple[dict[str, str], ...] = (
    {
        "id": "vscode-commands-guide",
        "title": "VS Code Extension API: Commands",
        "url": "https://code.visualstudio.com/api/extension-guides/command",
        "applies_to": "vscode_family",
    },
    {
        "id": "vscode-built-in-commands",
        "title": "VS Code Extension API: Built-in Commands",
        "url": "https://code.visualstudio.com/api/references/commands",
        "applies_to": "vscode_family",
    },
    {
        "id": "jetbrains-action-system",
        "title": "IntelliJ Platform Plugin SDK: Action System",
        "url": "https://plugins.jetbrains.com/docs/intellij/action-system.html",
        "applies_to": "jetbrains",
    },
    {
        "id": "cursor-vscode-migration",
        "title": "Cursor Docs: VS Code migration",
        "url": "https://docs.cursor.com/ja/guides/migration/vscode",
        "applies_to": "cursor",
    },
    {
        "id": "windsurf-chat",
        "title": "Windsurf Docs: Chat overview",
        "url": "https://docs.windsurf.com/chat",
        "applies_to": "windsurf",
    },
    {
        "id": "antigravity-ide-overview",
        "title": "Google Antigravity Docs: IDE overview",
        "url": "https://antigravity.google/docs/ide-overview?app=antigravity",
        "applies_to": "antigravity",
    },
)

CATALOG_VERSION = 1


def _command(
    category: str,
    id: str,
    *,
    kind: str = "vscode_command",
    confidence: str = "heuristic",
    risk: str = "medium",
    args: tuple[str, ...] = (),
    notes: str = "",
) -> IdeCommand:
    return IdeCommand(
        category=category,
        id=id,
        kind=kind,
        confidence=confidence,
        risk=risk,
        args=args,
        notes=notes,
    )


def _rows(category: str, ids: tuple[str, ...], **kwargs: Any) -> tuple[IdeCommand, ...]:
    return tuple(_command(category, id, **kwargs) for id in ids)


GENERIC_VSCODE_FAMILY: tuple[IdeCommand, ...] = (
    *_rows(
        "focus_open",
        (
            "composer.showComposer",
            "workbench.panel.chat",
            "workbench.panel.chat.view.copilot.focus",
            "aichat.newchataction",
            "cursor.composer.open",
            "workbench.panel.aichat.view.copilot.focus",
        ),
        confidence="runtime_introspected",
        risk="medium",
        notes=(
            "Candidate ladder; plugin filters to commands returned by "
            "vscode.commands.getCommands(false)."
        ),
    ),
    *_rows(
        "focus_input",
        (
            "workbench.action.chat.focusInput",
            "chat.action.focus",
            "workbench.chat.action.focusLastFocused",
            "workbench.action.focusAuxiliaryBar",
            "workbench.action.focusPanel",
            "workbench.action.focusSideBar",
        ),
        confidence="runtime_introspected",
        risk="medium",
        notes="Focus candidates need editor-snapshot or chat-event verification before reuse.",
    ),
    *_rows(
        "paste_text",
        (
            "workbench.action.chat.insertText",
            "workbench.action.chat.typeText",
            "aichat.typeText",
        ),
        confidence="runtime_introspected",
        risk="low",
        args=("text",),
        notes="Direct text argument is preferred over clipboard paste when the command exists.",
    ),
    *_rows(
        "submit",
        (
            "workbench.action.chat.submit",
            "workbench.action.chat.acceptInput",
            "workbench.action.chat.send",
            "workbench.action.chat.sendMessage",
            "workbench.action.interactive.accept",
            "composer.submit",
            "aichat.submit",
        ),
        confidence="runtime_introspected",
        risk="medium",
        notes=(
            "Submit commands can no-op or insert a newline in some IDEs; "
            "Koru probes before caching."
        ),
    ),
    *_rows(
        "reload_reconnect",
        (
            "workbench.action.reloadWindow",
            "koruAutopilot.connect",
            "koruAutopilot.openChat",
        ),
        confidence="public_api",
        risk="low",
        notes="Koru-owned or VS Code-family command used for bridge readiness.",
    ),
)


VSCODE_SPECIFIC: tuple[IdeCommand, ...] = (
    _command(
        "focus_open",
        "workbench.action.chat.open",
        confidence="runtime_introspected",
        risk="low",
        notes="Preferred VS Code chat opener when registered.",
    ),
    *_rows(
        "focus_open_avoid",
        (
            "workbench.panel.chat",
            "workbench.panel.chat.view.copilot.focus",
            "workbench.panel.aichat.view.copilot.focus",
            "workbench.action.chat.openagent",
            "workbench.action.chat.openask",
        ),
        confidence="runtime_introspected",
        risk="high",
        notes=(
            "May toggle panels or force a new agent/ask surface; use only "
            "with explicit strategy."
        ),
    ),
)


VSCODIUM_SPECIFIC: tuple[IdeCommand, ...] = (
    _command(
        "submit",
        "host:ctrl+return",
        kind="host_key",
        confidence="host_fallback",
        risk="medium",
        notes=(
            "VSCodium strategy prefers Ctrl+Return because plain Return can "
            "leave text unsubmitted."
        ),
    ),
)


CURSOR_SPECIFIC: tuple[IdeCommand, ...] = (
    *_rows(
        "paste_text",
        (
            "cursor.action.chat.typeText",
            "composer.typeText",
            "aichat.typeText",
        ),
        confidence="private_or_vendor_specific",
        risk="low",
        args=("text",),
        notes="Cursor direct paste candidates; runtime getCommands verification required.",
    ),
    *_rows(
        "submit",
        (
            "composer.sendToAgent",
            "composer.acceptComposerStep",
            "composer.startComposerPrompt",
            "composer.startComposerPrompt2",
            "composer.submit",
            "aichat.submit",
        ),
        confidence="private_or_vendor_specific",
        risk="medium",
        notes="Cursor Composer submit/action candidates; prefer registered command over host key.",
    ),
    *_rows(
        "focus_input",
        (
            "composer.focusComposer",
            "cursor.composer.focus",
            "workbench.panel.chat.view.copilot.focus",
            "workbench.panel.aichat.view.copilot.focus",
        ),
        confidence="private_or_vendor_specific",
        risk="medium",
        notes="Must be verified against the current Composer/chat surface.",
    ),
    *_rows(
        "focus_open_avoid",
        (
            "aichat.newchataction",
            "composer.openAsPane",
        ),
        confidence="private_or_vendor_specific",
        risk="high",
        notes="Can create a new chat or toggle an existing pane; do not cache as default.",
    ),
)


WINDSURF_SPECIFIC: tuple[IdeCommand, ...] = (
    *_rows(
        "atomic_send",
        (
            "windsurf.sendTextToChat",
        ),
        confidence="private_or_vendor_specific",
        risk="low",
        args=("text",),
        notes="Preferred Windsurf atomic text injection when registered.",
    ),
    *_rows(
        "paste_text",
        (
            "windsurf.action.chat.typeText",
            "windsurf.action.cascade.typeText",
            "windsurf.chat.typeText",
            "windsurf.cascade.typeText",
            "cascade.typeText",
        ),
        confidence="private_or_vendor_specific",
        risk="low",
        args=("text",),
        notes="Cascade/chat text commands; runtime getCommands verification required.",
    ),
    *_rows(
        "submit",
        (
            "windsurf.action.cascade.submit",
            "windsurf.action.submitCascade",
            "windsurf.action.submitChat",
            "windsurf.action.chat.submit",
            "windsurf.chat.submit",
            "windsurf.cascade.submit",
            "cascade.submit",
        ),
        confidence="private_or_vendor_specific",
        risk="medium",
        notes="Windsurf/Cascade submit candidates.",
    ),
    *_rows(
        "focus_input",
        (
            "windsurf.cascadePanel.focus",
            "windsurf.action.focusChatInput",
            "windsurf.chat.focusInput",
            "windsurf.cascade.focusInput",
            "cascade.focusInput",
            "windsurf.action.focusCascadeInput",
        ),
        confidence="private_or_vendor_specific",
        risk="medium",
        notes="Windsurf chat/cascade focus candidates.",
    ),
    *_rows(
        "focus_open",
        (
            "windsurf.cascadePanel.open",
            "windsurf.cascadePanel.focus",
            "windsurf.action.openChat",
            "windsurf.chat.open",
            "windsurf.cascade.open",
            "windsurf.panel.chat",
            "cascade.focus",
            "windsurf.action.showCascade",
        ),
        confidence="private_or_vendor_specific",
        risk="medium",
        notes="Windsurf/Cascade open candidates.",
    ),
)


ANTIGRAVITY_SPECIFIC: tuple[IdeCommand, ...] = (
    _command(
        "atomic_send",
        "antigravity.sendPromptToAgentPanel",
        confidence="private_or_vendor_specific",
        risk="low",
        args=("text",),
        notes=(
            "Preferred Antigravity atomic send command when registered by the host IDE."
        ),
    ),
    *_rows(
        "focus_open",
        (
            "antigravity.openAgent",
            "antigravity.agentSidePanel.open",
            "antigravity.agentSidePanel.focus",
        ),
        confidence="private_or_vendor_specific",
        risk="medium",
        notes="Antigravity agent panel open/focus candidates.",
    ),
)


JETBRAINS_SPECIFIC: tuple[IdeCommand, ...] = (
    *_rows(
        "focus_open",
        (
            "AIAssistant.OpenAIAssistantToolWindow",
            "AIAssistant.Chat.OpenChat",
            "AiAssistant.OpenAiAssistantToolWindow",
            "Grazie.OpenAssistant",
        ),
        kind="jetbrains_action",
        confidence="runtime_introspected",
        risk="medium",
        notes=(
            "ActionManager action IDs; exact availability depends on installed "
            "JetBrains AI plugins."
        ),
    ),
    _command(
        "paste_text",
        "host:clipboard-paste",
        kind="host_key",
        confidence="host_fallback",
        risk="medium",
        args=("text",),
        notes="JetBrains plugin currently pastes through clipboard and AWT Robot.",
    ),
    _command(
        "submit",
        "host:enter",
        kind="host_key",
        confidence="host_fallback",
        risk="medium",
        notes="JetBrains plugin submit fallback after paste.",
    ),
)


ZED_SPECIFIC: tuple[IdeCommand, ...] = (
    _command(
        "paste_text",
        "host:keyboard-type",
        kind="host_key",
        confidence="host_fallback",
        risk="medium",
        args=("text",),
        notes="Zed has no native Koru plugin bridge in this repo; OS injector is current fallback.",
    ),
    _command(
        "paste_text",
        "host:clipboard-paste",
        kind="host_key",
        confidence="host_fallback",
        risk="medium",
        args=("text",),
        notes="Clipboard paste fallback for Zed when keyboard typing is unsuitable.",
    ),
    _command(
        "submit",
        "host:return",
        kind="host_key",
        confidence="host_fallback",
        risk="medium",
        notes="Default Zed submit fallback from KeyboardPolicy.",
    ),
)


IDE_ROWS: dict[str, tuple[IdeCommand, ...]] = {
    "vscode": (*VSCODE_SPECIFIC, *GENERIC_VSCODE_FAMILY),
    "vscodium": (*VSCODIUM_SPECIFIC, *GENERIC_VSCODE_FAMILY),
    "cursor": (*CURSOR_SPECIFIC, *GENERIC_VSCODE_FAMILY),
    "windsurf": (*WINDSURF_SPECIFIC, *GENERIC_VSCODE_FAMILY),
    "antigravity": (*ANTIGRAVITY_SPECIFIC, *GENERIC_VSCODE_FAMILY),
    "jetbrains": JETBRAINS_SPECIFIC,
    "zed": ZED_SPECIFIC,
}

VS_CODE_FAMILY_IDES = frozenset({"antigravity", "cursor", "vscode", "vscodium", "windsurf"})

POLICY: dict[str, Any] = {
    "runtime_verification": (
        "Treat this catalog as candidates. For VS Code-family IDEs, verify live "
        "availability with vscode.commands.getCommands(false) from the connected "
        "Koru VSIX before use. For JetBrains, "
        "verify ActionManager.getAction(actionId) returns an action."
    ),
    "llm_contract": (
        "LLMs may propose a strategy and preferred categories, but Koru executes only through its "
        "plugin/daemon protocol, probe ladder, or explicit operator-approved host fallback."
    ),
    "safety": (
        "Avoid high-risk focus_open_avoid commands unless the strategy explicitly wants a new chat "
        "or pane toggle. Prefer direct text commands or Koru-owned protocol "
        "commands over clipboard."
    ),
}


def supported_catalog_ides() -> tuple[str, ...]:
    return tuple(sorted(IDE_ROWS))


def build_ide_command_catalog(ide: str | None = None) -> dict[str, Any]:
    """Return the full command catalog for one IDE or all supported IDEs."""
    selected = _selected_ide_rows(ide)
    return {
        "schema": "koru.ide_command_catalog.v1",
        "version": CATALOG_VERSION,
        "sources": list(SOURCES),
        "policy": POLICY,
        "ides": {
            ide_id: {
                "family": "vscode" if ide_id in VS_CODE_FAMILY_IDES else ide_id,
                "commands": [row.to_dict() for row in rows],
            }
            for ide_id, rows in selected.items()
        },
    }


def command_catalog_for_llm(ide: str | None = None) -> dict[str, Any]:
    """Return a compact, category-oriented catalog for strategy prompts."""
    selected = _selected_ide_rows(ide)
    ides: dict[str, Any] = {}
    for ide_id, rows in selected.items():
        categories: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            categories.setdefault(row.category, []).append(
                {
                    "id": row.id,
                    "kind": row.kind,
                    "confidence": row.confidence,
                    "risk": row.risk,
                },
            )
        ides[ide_id] = {
            "family": "vscode" if ide_id in VS_CODE_FAMILY_IDES else ide_id,
            "categories": categories,
        }
    return {
        "schema": "koru.ide_command_catalog.compact.v1",
        "policy": POLICY,
        "ides": ides,
    }


def format_command_catalog_text(ide: str | None = None, *, for_llm: bool = False) -> str:
    catalog = command_catalog_for_llm(ide) if for_llm else build_ide_command_catalog(ide)
    lines = [
        f"{catalog['schema']}",
        "policy:",
        f"  runtime_verification: {catalog['policy']['runtime_verification']}",
        f"  safety: {catalog['policy']['safety']}",
    ]
    for ide_id, data in catalog["ides"].items():
        lines.append(f"\n{ide_id} ({data['family']}):")
        if for_llm:
            for category, rows in data["categories"].items():
                ids = ", ".join(f"{row['id']}[{row['risk']}]" for row in rows)
                lines.append(f"  {category}: {ids}")
            continue
        categories: dict[str, list[dict[str, Any]]] = {}
        for row in data["commands"]:
            categories.setdefault(row["category"], []).append(row)
        for category, rows in categories.items():
            lines.append(f"  {category}:")
            for row in rows:
                lines.append(
                    "    - "
                    f"{row['id']} ({row['kind']}, {row['confidence']}, risk={row['risk']})",
                )
    return "\n".join(lines)


def _selected_ide_rows(ide: str | None) -> dict[str, tuple[IdeCommand, ...]]:
    if ide is None or ide == "all":
        return dict(IDE_ROWS)
    ide_id = ide.strip().lower()
    if ide_id not in IDE_ROWS:
        raise ValueError(
            f"unknown IDE catalog {ide!r}; supported: {', '.join(supported_catalog_ides())}",
        )
    return {ide_id: IDE_ROWS[ide_id]}


__all__ = [
    "CATALOG_VERSION",
    "IdeCommand",
    "build_ide_command_catalog",
    "command_catalog_for_llm",
    "format_command_catalog_text",
    "supported_catalog_ides",
]
