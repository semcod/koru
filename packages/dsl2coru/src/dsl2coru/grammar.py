"""Text DSL grammar → validated command dict."""

from __future__ import annotations

import shlex
from typing import Any

from dsl2coru.schema_registry import normalize_verb


def _split_command(line: str) -> list[str]:
    line = line.strip()
    if not line or line.startswith("#"):
        return []
    return shlex.split(line, posix=True)


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    return str(value).lower() in {"1", "true", "yes"}


def parse_line(line: str, *, default_file: str | None = None) -> dict[str, Any]:
    tokens = _split_command(line)
    if not tokens:
        return {}
    raw_verb = tokens[0].upper()
    verb = normalize_verb(raw_verb)
    rest = tokens[1:]
    payload: dict[str, Any] = {"verb": verb}

    def _flag(name: str) -> str | None:
        key = f"--{name.replace('_', '-')}"
        if key in rest:
            idx = rest.index(key)
            if idx + 1 < len(rest) and not rest[idx + 1].startswith("--"):
                return rest[idx + 1]
            return "true"
        upper = name.upper()
        if upper in rest:
            idx = rest.index(upper)
            if idx + 1 < len(rest) and not rest[idx + 1].startswith("--"):
                return rest[idx + 1]
        return None

    if verb == "STATUS":
        if _flag("probe"):
            payload["probe"] = True
        return payload

    if verb == "REPAIR_HISTORY":
        return payload

    if verb == "ENV":
        file_val = _flag("file") or default_file
        if file_val:
            payload["file"] = file_val
        return payload

    if verb == "QUERY":
        args = [t for t in rest if not t.startswith("--")]
        if args:
            payload["target"] = " ".join(args)
        return payload

    if verb == "AUTO":
        if shell := _flag("shell"):
            payload["shell"] = shell
        if auto_args := _flag("auto_args"):
            payload["auto_args"] = auto_args
        args = [t for t in rest if not t.startswith("--")]
        if args:
            payload["target"] = " ".join(args)
        return payload

    if verb == "LANE":
        if ide := _flag("ide"):
            payload["ide"] = ide
        if instance := _flag("instance"):
            payload["instance"] = instance
        if file_val := _flag("file"):
            payload["file"] = file_val
        if raw_verb in {"LANE_STATUS", "LANE-STATUS"}:
            payload["lane_status"] = True
        return payload

    if verb == "ENSURE":
        if _flag("install"):
            payload["install"] = True
        return payload

    if verb == "DOCTOR":
        if _flag("fix"):
            payload["fix"] = True
        if _flag("probe"):
            payload["probe"] = True
        if probe_prompt := _flag("probe_prompt") or _flag("probe-prompt"):
            payload["probe_prompt"] = probe_prompt
        return payload

    if verb == "CALIBRATION":
        for key, flag in (
            ("skip_fix", "skip-fix"),
            ("skip_desktop", "skip-desktop"),
            ("skip_bridge", "skip-bridge"),
        ):
            if _flag(flag) or _flag(key):
                payload[key] = True
        if probe_prompt := _flag("probe_prompt") or _flag("probe-prompt"):
            payload["probe_prompt"] = probe_prompt
        return payload

    if verb == "CHAT":
        if _flag("llm"):
            payload["llm"] = True
        if shell := _flag("shell"):
            payload["shell"] = shell
        if _flag("single_action") or _flag("single-action"):
            payload["single_action"] = True
        return payload

    if verb == "TEXT":
        args = [t for t in rest if not t.startswith("--")]
        if args:
            payload["target"] = " ".join(args)
        if _flag("llm"):
            payload["llm"] = True
        if shell := _flag("shell"):
            payload["shell"] = shell
        if _flag("single_action") or _flag("single-action"):
            payload["single_action"] = True
        return payload

    if verb == "SYNC":
        if _flag("all_ides") or _flag("all-ides"):
            payload["all_ides"] = True
        return payload

    if verb == "REPAIR_RUN":
        if _flag("fix"):
            payload["fix"] = True
        if ide := _flag("ide"):
            payload["ide"] = ide
        if instance := _flag("instance"):
            payload["instance"] = instance
        return payload

    if verb.startswith("UI_"):
        if image := _flag("image"):
            payload["image"] = image
        if window := _flag("window"):
            payload["window"] = window
        if _flag("execute") == "0" or _flag("dry_run"):
            payload["execute"] = False
        else:
            payload["execute"] = True

        def _ui_args() -> list[str]:
            skip = {"WINDOW", "IMAGE", "EXECUTE"}
            out: list[str] = []
            i = 0
            while i < len(rest):
                tok = rest[i]
                if tok.startswith("--"):
                    i += 2 if i + 1 < len(rest) and not rest[i + 1].startswith("--") else 1
                    continue
                if tok.upper() in skip:
                    i += 2 if tok.upper() in {"WINDOW", "IMAGE"} and i + 1 < len(rest) else 1
                    continue
                out.append(tok)
                i += 1
            return out

        if verb == "UI_TYPE":
            args = _ui_args()
            if len(args) >= 2 and args[0].upper() == "IN":
                payload["value"] = ""
                payload["field"] = " ".join(args[1:]).strip('"')
            elif len(args) >= 3 and args[1].upper() == "IN":
                payload["value"] = args[0].strip('"')
                payload["field"] = " ".join(args[2:]).strip('"')
            elif args:
                payload["value"] = args[0].strip('"')
        elif verb == "UI_KEY":
            args = _ui_args()
            if args:
                payload["keys"] = args[0]
        elif verb == "UI_CLICK":
            args = _ui_args()
            if args:
                payload["target"] = " ".join(args).strip('"')
        elif verb == "UI_NL":
            args = _ui_args()
            if args:
                payload["prompt"] = " ".join(args).strip('"')
        return payload

    raise ValueError(f"unknown DSL verb: {verb}")


def to_text(payload: dict[str, Any]) -> str:
    verb = str(payload.get("verb", "")).upper()
    parts = [verb]

    def _append_flag(name: str, *, flag: str | None = None) -> None:
        value = payload.get(name)
        if value is True:
            parts.append(flag or f"--{name.replace('_', '-')}")
        elif value not in (None, "", False):
            parts.extend([flag or f"--{name.replace('_', '-')}", str(value)])

    if verb == "STATUS":
        if payload.get("probe"):
            parts.append("--probe")
    elif verb == "ENV":
        if payload.get("file"):
            parts.extend(["--file", str(payload["file"])])
    elif verb == "QUERY":
        if payload.get("target"):
            parts.append(str(payload["target"]))
    elif verb == "AUTO":
        _append_flag("shell")
        _append_flag("auto_args")
        if payload.get("target"):
            parts.append(str(payload["target"]))
    elif verb == "LANE":
        _append_flag("ide")
        _append_flag("instance")
        _append_flag("file")
    elif verb == "ENSURE":
        if payload.get("install"):
            parts.append("--install")
    elif verb == "DOCTOR":
        if payload.get("fix"):
            parts.append("--fix")
        if payload.get("probe"):
            parts.append("--probe")
        _append_flag("probe_prompt", flag="--probe-prompt")
    elif verb == "CALIBRATION":
        for key in ("skip_fix", "skip_desktop", "skip_bridge"):
            if payload.get(key):
                parts.append(f"--{key.replace('_', '-')}")
        _append_flag("probe_prompt", flag="--probe-prompt")
    elif verb == "CHAT":
        if payload.get("llm"):
            parts.append("--llm")
        _append_flag("shell")
        if payload.get("single_action"):
            parts.append("--single-action")
    elif verb == "TEXT":
        if payload.get("target"):
            parts.append(str(payload["target"]))
        if payload.get("llm"):
            parts.append("--llm")
        _append_flag("shell")
        if payload.get("single_action"):
            parts.append("--single-action")
    elif verb == "SYNC":
        if payload.get("all_ides"):
            parts.append("--all-ides")
    elif verb == "REPAIR_RUN":
        if payload.get("fix"):
            parts.append("--fix")
        _append_flag("ide")
        _append_flag("instance")
    elif verb == "REPAIR_HISTORY":
        pass
    elif verb.startswith("UI_"):
        _append_flag("image")
        _append_flag("window")
        if payload.get("execute") is False:
            parts.append("EXECUTE 0")
        if verb == "UI_TYPE":
            if payload.get("value") is not None:
                parts.append(f'"{payload["value"]}"')
            if payload.get("field"):
                parts.extend(["IN", f'"{payload["field"]}"'])
        elif verb == "UI_KEY" and payload.get("keys"):
            parts.append(str(payload["keys"]))
        elif verb == "UI_CLICK" and payload.get("target"):
            parts.append(f'"{payload["target"]}"')
        elif verb == "UI_NL" and payload.get("prompt"):
            parts.append(f'"{payload["prompt"]}"')
    else:
        raise ValueError(f"cannot serialize verb: {verb}")
    return " ".join(parts)
