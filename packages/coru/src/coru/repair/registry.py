"""Repair command registry — add new bugfixes by appending :class:`RepairStepDef` rows."""

from __future__ import annotations

from coru.repair.domain import RepairStepDef

REPAIR_REGISTRY: tuple[RepairStepDef, ...] = (
    RepairStepDef(
        issue_codes=frozenset({"daemon_not_running"}),
        action_id="ensure_daemon",
        mode="auto",
        priority=10,
        description="Start idempotent autopilot daemon for the lane",
        llm_playbook=(
            "When daemon is down, run `coru ensure` or `coru daemon` in a system terminal, "
            "then connect the IDE plugin to the lane socket."
        ),
    ),
    RepairStepDef(
        issue_codes=frozenset(
            {
                "plugin_extension_stale_on_disk",
                "plugin_installed_version_mismatch",
                "install_plugin_failed",
                "install_plugin_cli_sandbox",
                "probe_cache_toxic",
                "chat_focus_toggle_risk",
                "terminal_paste_risk",
            }
        ),
        action_id="manual_vsix_unpack",
        mode="auto",
        priority=20,
        description="Unpack repo VSIX into the IDE extensions directory (AppImage/CLI fallback)",
        llm_playbook=(
            "Cursor AppImage cannot `cursor --install-extension` (sandbox/zygote). "
            "Unpack the repo VSIX to ~/.cursor/extensions/, then Reload Window."
        ),
    ),
    RepairStepDef(
        issue_codes=frozenset({"install_plugin_failed", "plugin_version_missing"}),
        action_id="manage_fix",
        mode="auto",
        priority=25,
        description="Run koru autopilot manage --fix for standard VSIX install path",
        llm_playbook="Try `koru autopilot manage --fix --ide <ide>` before manual unpack.",
    ),
    RepairStepDef(
        issue_codes=frozenset(
            {
                "plugin_build_mismatch",
                "plugin_version_mismatch",
                "plugin_extension_stale_in_memory",
                "plugin_live_host_stale",
                "plugin_rejected_by_daemon",
            }
        ),
        action_id="strict_handshake_cycle",
        mode="auto",
        priority=28,
        description="Restart daemon with strict plugin policy so the IDE extension self-reloads",
        llm_playbook=(
            "Strict handshake rejects stale plugin versions on connect; the extension should "
            "self-reload. If still rejected, Developer: Reload Window + Connect autopilot daemon."
        ),
    ),
    RepairStepDef(
        issue_codes=frozenset(
            {
                "probe_cache_toxic",
                "chat_focus_toggle_risk",
                "terminal_paste_risk",
            }
        ),
        action_id="plugin_upgrade_and_reload",
        mode="auto",
        priority=29,
        description="Install latest repo VSIX and reload IDE (fixes toggle/paste probe-cache bugs)",
        llm_playbook=(
            "workbench.panel.chat and workbench.action.terminal.paste are toxic cached winners on "
            "Cursor — upgrade plugin (>=0.2.4), reload window, reconnect plugin."
        ),
    ),
    RepairStepDef(
        issue_codes=frozenset(
            {
                "plugin_not_connected",
                "plugin_installed_ok_but_not_connected",
            }
        ),
        action_id="reload_and_connect",
        mode="auto",
        priority=30,
        description="Reload IDE window (CLI reuse-window fallback) and reconnect plugin",
        llm_playbook=(
            "Command Palette → Developer: Reload Window, then koru: Connect autopilot daemon. "
            "Status bar should show koru: on."
        ),
    ),
    RepairStepDef(
        issue_codes=frozenset({"plugin_extension_stale_on_disk", "probe_cache_toxic"}),
        action_id="reload_and_connect",
        mode="auto",
        priority=35,
        description="After VSIX unpack, reload IDE and reconnect plugin",
        llm_playbook="Always reload after VSIX unpack; connect plugin before retrying drive.",
    ),
    RepairStepDef(
        issue_codes=frozenset({"terminal_lane_mismatch"}),
        action_id="cross_ide_guidance",
        mode="manual",
        priority=40,
        description="Explain terminal/lane mismatch and cross-IDE options",
        llm_playbook=(
            "Run `coru cursor auto` from Cursor integrated terminal, or set "
            "KORU_AUTOPILOT_INSTANCE to match the target lane."
        ),
    ),
    RepairStepDef(
        issue_codes=frozenset(
            {
                "submit_unverified",
                "chat_submit_host_key_failed",
                "drive_intent_unverified",
            }
        ),
        action_id="submit_unverified_guidance",
        mode="manual",
        priority=42,
        description="Operator submits manually in chat; check plugin submit strategy on Wayland",
        llm_playbook=(
            "Paste succeeded but submit failed verification (cursor-bubble-db). On Wayland, "
            "host-key Ctrl+Return often misses the chat webview — click chat input and press Enter. "
            "Ensure plugin >=0.2.4 (no terminal.paste / panel.chat toggle)."
        ),
    ),
    RepairStepDef(
        issue_codes=frozenset(
            {
                "koru_not_in_path",
                "koru_path_mismatch",
                "python_env_mismatch",
                "venv_alignment",
                "koru_runtime_identity",
                "path_koru_not_from_project_venv",
            }
        ),
        action_id="runtime_guidance",
        mode="manual",
        priority=50,
        description="Print runtime/venv alignment guidance",
        llm_playbook="Use project `.venv`: `PATH=\"$PWD/.venv/bin:$PATH\" coru ...`",
    ),
)


def registry_steps_for_code(code: str) -> list[RepairStepDef]:
    matched = [step for step in REPAIR_REGISTRY if code in step.issue_codes]
    return sorted(matched, key=lambda step: step.priority)


def registry_step(action_id: str) -> RepairStepDef | None:
    for step in REPAIR_REGISTRY:
        if step.action_id == action_id:
            return step
    return None


def playbook_for_codes(codes: set[str]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for code in sorted(codes):
        for step in registry_steps_for_code(code):
            if step.llm_playbook and step.action_id not in seen:
                seen.add(step.action_id)
                lines.append(f"- [{step.action_id}] {step.llm_playbook}")
    return "\n".join(lines)
