"""Small decision helpers for autopilot drive / ack flow."""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any, ClassVar

from koruide.ide_control import ide_control_strategy
from koruide.plugin_version import (
    EXPECTED_VSCODE_PLUGIN_VERSION,
    expected_plugin_version_for_ide,
)
from koruide.protocol import MIN_PLUGIN_PROTOCOL_VERSION


class DriveOrchestrator:
    """Pure helpers used by the autopilot daemon."""

    @staticmethod
    def plugin_required_message(ide: str | None) -> str:
        label = ide or "auto"
        return (
            f"no connected autopilot plugin for ide={label}; "
            "keyboard fallback disabled for this request. "
            "Reload the IDE window or run the `koru: Connect autopilot daemon` command "
            "so the extension connects to this socket."
        )

    @staticmethod
    def should_try_os_fallback(
        *,
        plugin_ok: bool,
        info: dict[str, Any],
        submit_requested: bool,
        plugin_ide: str | None,
        require_plugin: bool,
    ) -> bool:
        if require_plugin or not plugin_ide:
            return False
        strategy = ide_control_strategy(plugin_ide)
        if not strategy.allow_keyboard_fallback_after_plugin_ack:
            return False
        focus_error = "chat input is not focused/open" in str(info.get("message", "")).lower()
        submit_failed = submit_requested and info.get("submitted") is False
        undelivered = info.get("delivered") is False
        return ((not plugin_ok) and focus_error) or (not plugin_ok) or submit_failed or undelivered

    @staticmethod
    def build_message_sent_info(
        *,
        submit_requested: bool,
        plugin_ide: str | None,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        info: dict[str, Any] = {
            "backend": "plugin",
            "delivered": True,
            "opened": True,
            "submitted": submit_requested,
            "event": "message.sent",
        }
        if plugin_ide:
            info["ide"] = plugin_ide
        if isinstance(event_data.get("chat"), str):
            info["chat"] = event_data["chat"]
        info["verification"] = "event_only"
        return info

    @staticmethod
    def annotate_plugin_ack(
        *,
        info: dict[str, Any],
        plugin_ok: bool,
        submit_requested: bool,
        plugin_ide: str | None = None,
    ) -> dict[str, Any]:
        enriched = dict(info)
        if not plugin_ok:
            enriched.setdefault("verification", "plugin_error")
            enriched.update(
                DriveOrchestrator.drive_intent_evidence(
                    enriched,
                    plugin_ok=plugin_ok,
                    submit_requested=submit_requested,
                    plugin_ide=plugin_ide,
                )
            )
            return enriched
        if enriched.get("event") == "message.sent":
            enriched["verification"] = "event_only"
            enriched.update(
                DriveOrchestrator.drive_intent_evidence(
                    enriched,
                    plugin_ok=plugin_ok,
                    submit_requested=submit_requested,
                    plugin_ide=plugin_ide,
                )
            )
            return enriched
        if submit_requested:
            has_submit_proof = bool(enriched.get("winning_submit"))
            has_paste_proof = bool(enriched.get("winning_paste"))
            has_open_proof = bool(enriched.get("winning_focus_open"))
            if DriveOrchestrator.is_poisoned_submit_ack(enriched, plugin_ide):
                if DriveOrchestrator.has_message_sent_event(enriched):
                    enriched["verification"] = "event_only"
                    enriched.setdefault(
                        "submit_success_reason",
                        "message.sent event observed after untrusted registered submit command",
                    )
                    enriched.update(
                        DriveOrchestrator.drive_intent_evidence(
                            enriched,
                            plugin_ok=plugin_ok,
                            submit_requested=submit_requested,
                            plugin_ide=plugin_ide,
                        )
                    )
                    return enriched
                enriched["verification"] = "submit_unverified"
                enriched.setdefault(
                    "submit_failure_reason",
                    "VSCodium registered submit command is not trusted as send proof "
                    "without strict empty-input verification",
                )
                enriched.update(
                    DriveOrchestrator.drive_intent_evidence(
                        enriched,
                        plugin_ok=plugin_ok,
                        submit_requested=submit_requested,
                        plugin_ide=plugin_ide,
                    )
                )
                return enriched
            if has_submit_proof and has_paste_proof and has_open_proof:
                enriched["verification"] = "strict"
            else:
                enriched["verification"] = "plugin_ack"
        else:
            enriched.setdefault("verification", "plugin_ack")
        enriched.update(
            DriveOrchestrator.drive_intent_evidence(
                enriched,
                plugin_ok=plugin_ok,
                submit_requested=submit_requested,
                plugin_ide=plugin_ide,
            )
        )
        return enriched

    @staticmethod
    def drive_intent_evidence(
        info: dict[str, Any],
        *,
        plugin_ok: bool | None,
        submit_requested: bool,
        plugin_ide: str | None = None,
    ) -> dict[str, str]:
        """Classify whether the user's send-prompt intent was fulfilled.

        This is deliberately stricter than per-action success. A command can
        return ok=true, and a probe can observe changed input, without proving
        that a user message was created in the IDE chat.
        """
        verification = str(info.get("verification") or "").lower()
        ide = str(plugin_ide or info.get("ide") or "").lower()
        if not submit_requested:
            return {
                "intent": "deliver_prompt",
                "intent_status": "fulfilled" if plugin_ok is not False else "failed",
                "intent_confidence": "strong" if plugin_ok is not False else "none",
                "intent_validator": "paste_ack",
                "intent_reason": "submit was not requested",
            }
        if plugin_ok is False or verification in {"plugin_error", "submit_unverified"}:
            return {
                "intent": "send_prompt",
                "intent_status": "unverified" if info.get("delivered") else "failed",
                "intent_confidence": "none",
                "intent_validator": verification or "plugin_ack",
                "intent_reason": str(
                    info.get("submit_failure_reason")
                    or info.get("reason")
                    or info.get("message")
                    or "no trusted proof that a user message was created"
                ),
            }
        if verification == "event_only":
            return {
                "intent": "send_prompt",
                "intent_status": "fulfilled",
                "intent_confidence": "medium",
                "intent_validator": "message.sent",
                "intent_reason": "message.sent event observed without full plugin ack proof",
            }
        if verification == "strict":
            validator = "plugin_strict_ack"
            confidence = "strong"
            if ide == "vscodium":
                validator = "vscodium_strict_ack"
            return {
                "intent": "send_prompt",
                "intent_status": "fulfilled",
                "intent_confidence": confidence,
                "intent_validator": validator,
                "intent_reason": "focus, paste, and submit proofs were accepted",
            }
        return {
            "intent": "send_prompt",
            "intent_status": "unverified",
            "intent_confidence": "weak",
            "intent_validator": verification or "plugin_ack",
            "intent_reason": f"verification={verification or '-'} is not a send-proof",
        }

    @staticmethod
    def is_poisoned_submit_ack(info: dict[str, Any], plugin_ide: str | None) -> bool:
        """Reject known false-positive submit proofs before strict ack accepts them."""
        ide = str(plugin_ide or info.get("ide") or "").lower()
        if ide != "vscodium":
            return False
        if str(info.get("winning_submit") or "") != "workbench.action.chat.submit":
            return False
        return not DriveOrchestrator.has_strong_submit_verification(info, require_empty=True)

    @staticmethod
    def has_strong_submit_verification(
        info: dict[str, Any],
        *,
        require_empty: bool = False,
    ) -> bool:
        """Return True when the plugin proved the input was committed.

        VSCodium's registered submit command has produced false positives
        before, so the command name alone is not enough. A successful
        post-submit input probe is stronger evidence: the prompt was pasted,
        submit was attempted, and the input no longer contains that prompt.
        """
        if info.get("submitted") is not True:
            return False
        trace = info.get("operation_trace")
        if not isinstance(trace, list):
            return False
        saw_empty_required_accept = not require_empty
        saw_successful_probe = False
        for raw_step in trace:
            if not isinstance(raw_step, dict):
                continue
            if raw_step.get("op") == "submit" and raw_step.get("route") == "accepted":
                detail = raw_step.get("detail")
                if isinstance(detail, dict) and detail.get("requireEmptyAfterSubmit") is True:
                    saw_empty_required_accept = True
            if raw_step.get("op") == "submit_verify" and raw_step.get("ok") is True:
                saw_successful_probe = True
        return saw_successful_probe and saw_empty_required_accept

    @staticmethod
    def has_message_sent_event(info: dict[str, Any]) -> bool:
        """Return True when the plugin trace includes a trusted message.sent event."""
        trace = info.get("operation_trace")
        if not isinstance(trace, list):
            return False
        for raw_step in trace:
            if not isinstance(raw_step, dict):
                continue
            if raw_step.get("op") != "message_sent":
                continue
            if raw_step.get("ok") is not True:
                continue
            route = str(raw_step.get("route") or "")
            if route == "plugin-event":
                return True
        return False

    @staticmethod
    def strict_plugin_ack_required() -> bool:
        raw = os.environ.get("KORU_STRICT_PLUGIN_ACK", "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    def should_defer_submit_unverified_for_message_sent(
        *,
        info: dict[str, Any],
        plugin_ok: bool,
        submit_requested: bool,
        plugin_ide: str | None,
    ) -> bool:
        """Allow a short grace window for late ``message.sent`` plugin events."""
        if not submit_requested or not plugin_ok:
            return False
        if str(plugin_ide or info.get("ide") or "").lower() != "vscodium":
            return False
        return str(info.get("verification") or "").lower() == "submit_unverified"

    @staticmethod
    def expected_plugin_version(ide_id: str | None = None) -> str | None:
        """Resolve expected plugin VSIX version for ``ide_id``.

        Each per-IDE plugin lives under ``plugins/<dir>/package.json``;
        we prefer the live ``package.json`` (fresh dev builds) and fall
        back to the static table in ``koruide.plugin_version``.
        """

        # Lazy import to avoid a top-level cycle when this module is
        # loaded before ``koruide.plugin_installer``.
        from koruide.plugin_installer import plugin_dir_names_for_ide

        here = Path(__file__).resolve()
        for dir_name in plugin_dir_names_for_ide(ide_id):
            for parent in here.parents:
                package_json = parent / "plugins" / dir_name / "package.json"
                if not package_json.is_file():
                    continue
                try:
                    data = json.loads(package_json.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return None
                version = data.get("version")
                return str(version) if version else None
        return expected_plugin_version_for_ide(ide_id) or EXPECTED_VSCODE_PLUGIN_VERSION

    @staticmethod
    def expected_plugin_build_sha(ide_id: str | None = None) -> str | None:
        """Resolve expected VSIX build hash for ``ide_id`` from package.json."""

        from koruide.plugin_installer import plugin_dir_names_for_ide

        here = Path(__file__).resolve()
        for dir_name in plugin_dir_names_for_ide(ide_id):
            for parent in here.parents:
                package_json = parent / "plugins" / dir_name / "package.json"
                if not package_json.is_file():
                    continue
                try:
                    data = json.loads(package_json.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return None
                build = data.get("koruAutopilotBuild")
                if isinstance(build, dict) and isinstance(build.get("sha"), str):
                    return build["sha"]
                return None
        return None

    @staticmethod
    def strict_plugin_version_required() -> bool:
        raw = os.environ.get("KORU_STRICT_PLUGIN_VERSION", "").strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        policy = os.environ.get("KORU_PLUGIN_VERSION_POLICY", "").strip().lower()
        return policy in {"strict", "fail", "fail-fast", "block"}

    @staticmethod
    def protocol_plugin_version_policy() -> bool:
        policy = os.environ.get("KORU_PLUGIN_VERSION_POLICY", "").strip().lower()
        return policy in {"protocol", "compatible", "compat"}

    @staticmethod
    def plugin_version_info(
        *,
        plugin_ide: str | None,
        connected_version: str | None,
        expected_version: str | None = None,
        connected_build_sha: str | None = None,
        expected_build_sha: str | None = None,
        protocol_version: int | None = None,
        capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        expected = expected_version or DriveOrchestrator.expected_plugin_version(plugin_ide)
        expected_build = (
            expected_build_sha
            if expected_build_sha is not None
            else DriveOrchestrator.expected_plugin_build_sha(plugin_ide)
        )
        strict = DriveOrchestrator.strict_plugin_version_required()
        mismatch = bool(connected_version and expected and connected_version != expected)
        build_missing = bool(strict and expected_build and not connected_build_sha)
        build_mismatch = bool(connected_build_sha and expected_build and connected_build_sha != expected_build)
        protocol_missing = protocol_version is None
        protocol_compatible = bool(
            protocol_version is not None and protocol_version >= MIN_PLUGIN_PROTOCOL_VERSION
        )
        protocol_incompatible = bool(
            protocol_missing or protocol_version < MIN_PLUGIN_PROTOCOL_VERSION
        )
        missing_connected = bool(strict and expected and connected_version is None)
        unknown_expected = bool(strict and connected_version and not expected)
        protocol_policy = DriveOrchestrator.protocol_plugin_version_policy()
        info: dict[str, Any] = {
            "plugin_version": connected_version,
            "expected_plugin_version": expected,
            "plugin_version_mismatch": mismatch,
            "plugin_build_sha": connected_build_sha,
            "expected_plugin_build_sha": expected_build,
            "plugin_build_missing": build_missing,
            "plugin_build_mismatch": build_mismatch,
            "plugin_protocol_version": protocol_version,
            "minimum_plugin_protocol_version": MIN_PLUGIN_PROTOCOL_VERSION,
            "plugin_protocol_missing": protocol_missing,
            "plugin_protocol_compatible": protocol_compatible,
            "plugin_protocol_incompatible": protocol_incompatible,
            "plugin_version_missing": missing_connected,
            "plugin_version_expected_missing": unknown_expected,
            "plugin_version_policy": (
                "protocol" if protocol_policy else "strict" if strict else "warn"
            ),
        }
        if capabilities is not None:
            info["plugin_capabilities"] = capabilities
        if plugin_ide:
            info["ide"] = plugin_ide
        return info

    @staticmethod
    def should_block_plugin_version(info: dict[str, Any]) -> bool:
        if info.get("plugin_protocol_incompatible"):
            return True
        if (
            info.get("plugin_protocol_compatible")
            and DriveOrchestrator.protocol_plugin_version_policy()
        ):
            return False
        return bool(
            info.get("plugin_version_mismatch")
            or info.get("plugin_version_missing")
            or info.get("plugin_version_expected_missing")
            or info.get("plugin_build_missing")
            or info.get("plugin_build_mismatch"),
        ) and DriveOrchestrator.strict_plugin_version_required()

    @staticmethod
    def plugin_version_block_message(info: dict[str, Any]) -> str:
        if info.get("plugin_protocol_incompatible"):
            if info.get("plugin_protocol_missing"):
                return (
                    "connected autopilot plugin protocol missing: "
                    f"minimum={info.get('minimum_plugin_protocol_version') or '-'}; "
                    "install the current VSIX, reload the IDE window, then run "
                    "`koru: Connect autopilot daemon`."
                )
            return (
                "connected autopilot plugin protocol mismatch: "
                f"connected={info.get('plugin_protocol_version') or '-'} "
                f"minimum={info.get('minimum_plugin_protocol_version') or '-'}; "
                "install the current VSIX, reload the IDE window, then run "
                "`koru: Connect autopilot daemon`."
            )
        if info.get("plugin_version_mismatch") or info.get("plugin_version_missing"):
            return (
                "connected autopilot plugin version mismatch: "
                f"connected={info.get('plugin_version') or '-'} "
                f"expected={info.get('expected_plugin_version') or '-'}; "
                "reload the IDE window after installing the current VSIX, then run "
                "`koru: Connect autopilot daemon`."
            )
        if info.get("plugin_build_missing") or info.get("plugin_build_mismatch"):
            return (
                "connected autopilot plugin build mismatch: "
                f"connected={info.get('plugin_build_sha') or '-'} "
                f"expected={info.get('expected_plugin_build_sha') or '-'} "
                f"version={info.get('plugin_version') or '-'}; "
                "reload the IDE window after installing the current VSIX, then run "
                "`koru: Connect autopilot daemon`."
            )
        return (
            "connected autopilot plugin version mismatch: "
            f"connected={info.get('plugin_version') or '-'} "
            f"expected={info.get('expected_plugin_version') or '-'}; "
            "reload the IDE window after installing the current VSIX, then run "
            "`koru: Connect autopilot daemon`."
        )

    @staticmethod
    def should_fail_strict_plugin_ack(
        *,
        info: dict[str, Any],
        plugin_ok: bool,
        submit_requested: bool,
        plugin_ide: str | None,
    ) -> bool:
        if not DriveOrchestrator.strict_plugin_ack_required():
            return False
        if not plugin_ok or not submit_requested:
            return False
        if not ide_control_strategy(plugin_ide).strict_ack_supported:
            return False
        return str(info.get("verification", "")) != "strict"

    @staticmethod
    def plugin_ack_summary(info: dict[str, Any]) -> str:
        parts: list[str] = []
        verification = info.get("verification")
        if verification:
            parts.append(f"verification={verification}")
        for key in (
            "winning_focus_open",
            "winning_paste",
            "winning_submit",
            "attempted_submit",
            "submit_failure_reason",
        ):
            value = info.get(key)
            if value:
                parts.append(f"{key}={value}")
        attempts = info.get("submit_attempts")
        if isinstance(attempts, list) and attempts:
            parts.append("submit_attempts=" + " | ".join(str(item) for item in attempts))
        route_trace = DriveOrchestrator.operation_trace_summary(info)
        if route_trace:
            parts.append(f"route_trace={route_trace}")
        if info.get("plugin_version_mismatch"):
            parts.append(
                "plugin_version="
                f"{info.get('plugin_version') or '-'}"
                f"/expected={info.get('expected_plugin_version') or '-'}"
            )
        if info.get("plugin_build_missing") or info.get("plugin_build_mismatch"):
            parts.append(
                "plugin_build="
                f"{info.get('plugin_build_sha') or '-'}"
                f"/expected={info.get('expected_plugin_build_sha') or '-'}"
            )
        if info.get("event"):
            parts.append(f"event={info['event']}")
        return " ".join(parts)

    @staticmethod
    def operation_trace_summary(info: dict[str, Any]) -> str:
        trace = info.get("operation_trace")
        if not isinstance(trace, list):
            return ""
        pieces: list[str] = []
        for raw_step in trace:
            if not isinstance(raw_step, dict):
                continue
            op = str(raw_step.get("op") or "?")
            route = str(raw_step.get("route") or "?")
            ok = "ok" if raw_step.get("ok") is True else "fail" if raw_step.get("ok") is False else "?"
            command = raw_step.get("command")
            reason = raw_step.get("reason")
            suffix = ""
            if command:
                suffix = f":{command}"
            elif reason:
                suffix = f":{reason}"
            pieces.append(f"{op}/{route}={ok}{suffix}")
            if len(pieces) >= 12:
                break
        return " > ".join(pieces)

    # ------------------------------------------------------------------
    # Koru Drive DSL — transparent, line-per-step integration trace.
    #
    # Goal: when a drive fails ("plugin wkleil ale nie wyslal"), give the
    # operator a single human-readable sequence describing exactly what
    # the plugin tried, why each candidate was chosen, whether it worked,
    # and why it failed. The DSL is generated from the structured
    # ``operation_trace`` the plugin already sends with every ack, plus
    # the post-ack diagnostic fields the daemon enriches with
    # (``winning_*``, ``verification``, ``submit_failure_reason``).
    #
    # Format per line (one operation step):
    #
    #     #NNN act=<op> intent="..." route=<route>[:cmd] ok=<true|false|ambiguous>
    #          [verify=<probe>] [reason="..."]
    #
    # Lines are intended to be logged verbatim — each line is a complete,
    # grep-friendly record of one decision in the drive pipeline.
    # ------------------------------------------------------------------
    _INTENT_BY_OP: ClassVar[dict[str, str]] = {
        "focus_open": "make the chat panel the foreground surface",
        "focus_input": "land the caret inside the chat input",
        "input_probe": "check whether the chat input is empty before pasting",
        "input_busy_probe": "check whether the chat input is empty before pasting",
        "paste": "write the prompt text into the chat input",
        "submit": "send the prompt as a user message",
        "submit_verify": "verify a fresh user message was actually committed",
        "submit_host": "send via host-level key/click after registered commands failed",
        "host_clipboard": "stage the prompt via OS clipboard",
        "clipboard": "stage the prompt via OS clipboard",
        "drive": "top-level autopilot drive pipeline",
    }

    @staticmethod
    def _dsl_intent(op: str) -> str:
        return DriveOrchestrator._INTENT_BY_OP.get(op, f"plugin-internal step '{op}'")

    @staticmethod
    def _dsl_ok_token(value: Any) -> str:
        if value is True:
            return "true"
        if value is False:
            return "false"
        return "ambiguous"

    @staticmethod
    def _dsl_quote(value: Any, *, max_len: int = 160) -> str:
        """Quote ``value`` for inclusion in a DSL line, hiding ANSI noise."""
        text = str(value).strip()
        if not text:
            return '""'
        text = text.replace("\n", " ").replace('"', "'")
        if max_len > 0 and len(text) > max_len:
            text = text[: max_len - 3] + "..."
        return f'"{text}"'

    @staticmethod
    def operation_trace_dsl(info: dict[str, Any]) -> list[str]:
        """Render the plugin's ``operation_trace`` as one DSL line per step.

        Returns at most 40 lines (the same cap the plugin already
        enforces on the wire) so a runaway ladder can't blow up the
        daemon log.
        """
        trace = info.get("operation_trace")
        if not isinstance(trace, list):
            return []
        lines: list[str] = []
        for index, raw_step in enumerate(trace, start=1):
            if not isinstance(raw_step, dict):
                continue
            op = str(raw_step.get("op") or "?")
            route = str(raw_step.get("route") or "?")
            command = raw_step.get("command")
            reason = raw_step.get("reason")
            detail = raw_step.get("detail")
            ok_token = DriveOrchestrator._dsl_ok_token(raw_step.get("ok"))
            intent = DriveOrchestrator._dsl_intent(op)
            route_token = route
            if command:
                route_token = f"{route}:{command}"
            parts = [
                f"#{index:03d}",
                f"act={op}",
                f'intent={DriveOrchestrator._dsl_quote(intent)}',
                f"route={route_token}",
                f"ok={ok_token}",
            ]
            if reason:
                parts.append(f"reason={DriveOrchestrator._dsl_quote(reason)}")
            if isinstance(detail, dict) and detail:
                short = {
                    k: v
                    for k, v in detail.items()
                    if k in {"empty", "matched", "tail", "rowid", "ide", "verification"}
                }
                if short:
                    parts.append(f"detail={DriveOrchestrator._dsl_quote(short)}")
            lines.append(" ".join(parts))
            if len(lines) >= 40:
                break
        return lines

    @staticmethod
    def drive_outcome_dsl(info: dict[str, Any]) -> str:
        """Render the *final* drive verdict as a single DSL line.

        Combines the plugin's ``verification`` field, the cached winners
        (``winning_focus_open``/``winning_paste``/``winning_submit``)
        and any structured failure reason so the operator sees the
        bottom line without grepping the step trace.
        """
        verification = str(info.get("verification") or "-")
        delivered = bool(info.get("delivered"))
        wfocus = info.get("winning_focus_open") or "-"
        wpaste = info.get("winning_paste") or "-"
        wsubmit = info.get("winning_submit") or "-"
        reason = (
            info.get("submit_failure_reason")
            or info.get("reason")
            or info.get("message")
        )
        parts = [
            "#999",
            "act=drive",
            f'intent={DriveOrchestrator._dsl_quote(DriveOrchestrator._dsl_intent("drive"))}',
            f"delivered={'true' if delivered else 'false'}",
            f"verification={verification}",
            f"winners=focus={wfocus}|paste={wpaste}|submit={wsubmit}",
        ]
        if reason:
            parts.append(f"reason={DriveOrchestrator._dsl_quote(reason)}")
        return " ".join(parts)

    @staticmethod
    def drive_validation_dsl(info: dict[str, Any]) -> list[str]:
        """Render validation and intent verdict lines for the drive DSL."""
        validator = str(info.get("intent_validator") or info.get("verification") or "-")
        status = str(info.get("intent_status") or "unverified")
        confidence = str(info.get("intent_confidence") or "weak")
        intent = str(info.get("intent") or "send_prompt")
        reason = str(
            info.get("intent_reason")
            or info.get("submit_failure_reason")
            or info.get("reason")
            or info.get("message")
            or ""
        )
        ok = "true" if status == "fulfilled" else "false"
        validate = [
            "#800",
            "act=validate",
            f'intent={DriveOrchestrator._dsl_quote(intent)}',
            f"validator={validator}",
            f"ok={ok}",
            f"confidence={confidence}",
        ]
        intent_line = [
            "#801",
            "act=intent",
            f"name={intent}",
            f"status={status}",
            f"confidence={confidence}",
        ]
        if reason:
            validate.append(f"reason={DriveOrchestrator._dsl_quote(reason)}")
            intent_line.append(f"reason={DriveOrchestrator._dsl_quote(reason)}")
        return [" ".join(validate), " ".join(intent_line)]

    @staticmethod
    def drive_diagnosis(info: dict[str, Any], *, plugin_ok: bool | None = None) -> dict[str, str]:
        verification = str(info.get("verification") or "")
        intent_status = str(info.get("intent_status") or "")
        reason = str(
            info.get("submit_failure_reason")
            or info.get("reason")
            or info.get("message")
            or ""
        )
        winning_submit = str(info.get("winning_submit") or info.get("attempted_submit") or "")
        if intent_status and intent_status != "fulfilled":
            return {
                "severity": "error",
                "code": "intent_not_validated",
                "because": reason or str(info.get("intent_reason") or "intent was not fulfilled"),
                "next": "do not redrive blindly; inspect validation evidence and fix the failed validator",
            }
        if plugin_ok is False or verification in {"plugin_error", "submit_unverified"}:
            code = "submit_not_verified" if "submit" in verification or winning_submit else "drive_not_verified"
            return {
                "severity": "error",
                "code": code,
                "because": reason or "plugin did not provide a trusted submit proof",
                "next": "do not redrive blindly; inspect replay trace and retry after submit strategy fix",
            }
        if verification == "strict":
            return {
                "severity": "ok",
                "code": "submit_verified",
                "because": "plugin ack carried required focus/paste/submit proofs",
                "next": "wait for IDE/LLM response or ticket state transition",
            }
        if verification == "event_only":
            return {
                "severity": "warning",
                "code": "event_only",
                "because": "message.sent event completed the drive without full ack proof",
                "next": "prefer full plugin ack before considering the ticket advanced",
            }
        if verification == "input_busy":
            return {
                "severity": "warning",
                "code": "chat_input_busy",
                "because": reason or "chat input already contained text",
                "next": "ask operator/IDE to submit or clear the existing draft before retry",
            }
        return {
            "severity": "warning",
            "code": "ambiguous_drive",
            "because": reason or f"verification={verification or '-'}",
            "next": "inspect DSL trace before retrying",
        }

    @staticmethod
    def drive_operator_dsl(info: dict[str, Any], *, plugin_ok: bool | None = None) -> list[str]:
        diag = DriveOrchestrator.drive_diagnosis(info, plugin_ok=plugin_ok)
        lines = [
            " ".join(
                [
                    "#900",
                    "act=diagnose",
                    f"severity={diag['severity']}",
                    f"code={diag['code']}",
                    f"because={DriveOrchestrator._dsl_quote(diag['because'])}",
                ]
            ),
            " ".join(
                [
                    "#901",
                    "act=next",
                    f"owner={'koru' if diag['severity'] == 'ok' else 'operator'}",
                    f"action={DriveOrchestrator._dsl_quote(diag['next'])}",
                ]
            ),
        ]
        replay_command = info.get("replay_command")
        if replay_command:
            lines.append(
                "#902 act=replay "
                f"shell={DriveOrchestrator._dsl_quote(replay_command, max_len=1000)}"
            )
        validate_command = info.get("validate_command")
        if validate_command:
            lines.append(
                "#903 act=validate "
                f"shell={DriveOrchestrator._dsl_quote(validate_command, max_len=1000)}"
            )
        return lines

    @staticmethod
    def command_catalog_for(store: Any, ide: str) -> dict[str, list[str]] | None:
        if store is None:
            return None
        catalog_for = getattr(store, "catalog_for", None)
        if callable(catalog_for):
            result = catalog_for(ide)
            return result if isinstance(result, dict) else None
        return None

    @staticmethod
    def unknown_chat_commands_for(store: Any, ide: str) -> list[str]:
        if store is None:
            return []
        unknown_for = getattr(store, "unknown_chat_commands_for", None)
        if callable(unknown_for):
            result = unknown_for(ide)
            if isinstance(result, list):
                return [item for item in result if isinstance(item, str)]
        return []


__all__ = ["DriveOrchestrator"]
