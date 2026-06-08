"""Map validated command dicts to coru.cli argv."""

from __future__ import annotations

from typing import Any

from dsl2coru.schema_registry import normalize_verb


def to_cli_args(payload: dict[str, Any]) -> list[str]:
    verb = normalize_verb(str(payload.get("verb", "")))
    default_file = str(payload.get("file") or payload.get("default_file") or "")
    target = str(payload.get("target") or "")

    if verb == "TEXT":
        if not target:
            return ["status"]
        command = ["text", target]
        if payload.get("llm"):
            command.append("--llm")
        if shell := payload.get("shell"):
            command.extend(["--shell", str(shell)])
        if payload.get("single_action"):
            command.append("--single-action")
        return command

    if verb == "CHAT":
        command = ["chat"]
        if payload.get("llm"):
            command.append("--llm")
        if shell := payload.get("shell"):
            command.extend(["--shell", str(shell)])
        if payload.get("single_action"):
            command.append("--single-action")
        return command

    if verb == "AUTO":
        command = ["auto"]
        if shell := payload.get("shell"):
            command.extend(["--shell", str(shell)])
        if command_args := payload.get("auto_args"):
            if isinstance(command_args, str):
                command.extend(command_args.split())
            else:
                command.extend([str(item) for item in command_args])
        return command

    if verb == "ENSURE":
        command = ["ensure"]
        if payload.get("install"):
            command.append("--install")
        return command

    if verb == "LANE":
        command = ["lane-status" if payload.get("lane_status") else "lane"]
        if ide := payload.get("ide"):
            command.append(str(ide))
        if instance := payload.get("instance"):
            command.append(str(instance))
        return command

    if verb == "STATUS":
        command = ["status"]
        if payload.get("probe"):
            command.append("--probe")
        return command

    if verb == "DOCTOR":
        command = ["doctor"]
        if payload.get("fix"):
            command.append("--fix")
        if payload.get("probe"):
            command.append("--probe")
        if probe_prompt := payload.get("probe_prompt"):
            command.extend(["--probe-prompt", str(probe_prompt)])
        return command

    if verb == "CALIBRATION":
        command = ["calibration"]
        if payload.get("skip_fix"):
            command.append("--skip-fix")
        if payload.get("skip_desktop"):
            command.append("--skip-desktop")
        if payload.get("skip_bridge"):
            command.append("--skip-bridge")
        if probe_prompt := payload.get("probe_prompt"):
            command.extend(["--probe-prompt", str(probe_prompt)])
        return command

    if verb == "REPAIR_RUN":
        command = ["repair", "run"]
        if payload.get("fix"):
            command.append("--fix")
        if ide := payload.get("ide"):
            command.append(str(ide))
        if instance := payload.get("instance"):
            command.append(str(instance))
        return command

    if verb == "REPAIR_HISTORY":
        return ["repair", "history"]

    if verb == "SYNC":
        command = ["sync"]
        if payload.get("all_ides"):
            command.append("--all-ides")
        return command

    if verb == "ENV":
        if default_file:
            return ["env", "--file", default_file]
        return ["env"]

    if verb == "QUERY":
        if not target:
            return ["status"]
        lowered = target.lower().strip()
        if lowered in {"status", "diagnose"}:
            return ["status"]
        if lowered in {"lane", "lane-status"}:
            return ["lane"]
        if lowered in {"auto", "autonomous"}:
            return ["auto"]
        return ["status"]

    return ["text", verb + (f" {target}" if target else "")]
