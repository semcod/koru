"""CLI for ``koru ide control`` — nlp2uri IDE control plan/execute/list-uris."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.ide_doctor_cli import _resolve_socket


def _add_common_lane_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ide", default="auto", help="IDE lane (default: auto).")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--socket", type=Path, default=None, help="Autopilot socket override.")
    parser.add_argument(
        "--instance",
        default=None,
        help="Set KORU_AUTOPILOT_INSTANCE for this run (e.g. cursor-main).",
    )


def _add_control_plan_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    plan = sub.add_parser(
        "plan",
        help="Resolve NL prompt to koru.control.v1 plan (MCP: koru_ide_control_plan).",
    )
    plan.add_argument("prompt", help="Natural-language IDE control request.")
    plan.add_argument("--locale", default=None)
    _add_common_lane_args(plan)
    plan.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "text"),
        default="json",
    )


def _add_control_execute_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    execute = sub.add_parser(
        "execute",
        help="Plan + drive IDE chat via koruide socket (MCP: koru_ide_control_execute).",
    )
    execute.add_argument(
        "prompt",
        help="NL request or raw chat message (bare text drives when NL does not match).",
    )
    execute.add_argument("--locale", default=None)
    execute.add_argument("--dry-run", action="store_true", help="Plan only; do not drive.")
    execute.add_argument("--text", default=None, help="Override message text for drive.")
    execute.add_argument("--no-submit", action="store_true", help="Paste only; do not submit.")
    _add_common_lane_args(execute)
    execute.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "text"),
        default="json",
    )


def _add_control_list_uris_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    list_uris = sub.add_parser(
        "list-uris",
        help="URI index from live autopilot status (MCP: koru_ide_list_uris).",
    )
    _add_common_lane_args(list_uris)
    list_uris.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "text"),
        default="json",
    )


def add_control_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    control = sub.add_parser(
        "control",
        help="nlp2uri IDE control: plan, execute, list-uris (koru_ide_* MCP equivalents).",
    )
    nested = control.add_subparsers(dest="control_action", required=True)
    _add_control_plan_parser(nested)
    _add_control_execute_parser(nested)
    _add_control_list_uris_parser(nested)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _resolve_control_ide(args: argparse.Namespace) -> str:
    from koruide.ide import canonical_autopilot_ide_id, normalize_ide_id
    from koruide.plugin_installer import resolve_target_ide

    requested = normalize_ide_id(getattr(args, "ide", "auto") or "auto")
    if requested and requested != "auto":
        return canonical_autopilot_ide_id(requested)
    instance = (
        getattr(args, "instance", None) or os.environ.get("KORU_AUTOPILOT_INSTANCE") or ""
    ).strip()
    if instance:
        return canonical_autopilot_ide_id(instance)
    return canonical_autopilot_ide_id(resolve_target_ide("auto") or "cursor")


def _resolve_workspace_from_status(
    status: dict,
    ide: str,
    project: Path,
) -> str:
    plugins = status.get("plugins") if isinstance(status.get("plugins"), list) else []
    project_path = str(project.expanduser().resolve())
    for row in plugins:
        if not isinstance(row, dict):
            continue
        if str(row.get("ide") or "").strip().lower() != ide.strip().lower():
            continue
        folders = row.get("workspaceFolders")
        if not isinstance(folders, list) or not folders:
            continue
        for folder in folders:
            folder_s = str(folder).strip()
            if folder_s == project_path:
                return folder_s
        return str(folders[0]).strip()
    return ""


def _client_factory_for_args(
    args: argparse.Namespace,
    ide: str,
) -> tuple[Callable[[], Any], Path]:
    socket_path = Path(_resolve_socket(args, ide)).expanduser().resolve()

    def factory() -> Any:
        from koruide.client import KoruIDEClient

        return KoruIDEClient(socket_path=socket_path)

    return factory, socket_path


def action_ide_control_plan(args: argparse.Namespace) -> int:
    from koruapi.desktop_uri import desktop_uri_control_plan

    ide = _resolve_control_ide(args)
    payload = desktop_uri_control_plan(args.prompt, locale=args.locale)
    if not payload.get("control_plan"):
        from koruapi.desktop_uri import desktop_uri_direct_ide_chat_execute

        message = args.prompt.strip()
        if message:
            payload = desktop_uri_direct_ide_chat_execute(
                message,
                ide=ide,
                dry_run=True,
            )
            payload["ok"] = True
            payload["plan_hint"] = "NL did not match; showing direct ide-chat plan"
    if args.output_format == "json":
        _print_json(payload)
    else:
        if not payload.get("ok"):
            print(f"koru ide control plan: {payload.get('error', '?')}", file=sys.stderr)
            return 1
        print(payload.get("control_plan") or payload.get("plan", {}).get("uri", "?"))
    return 0 if payload.get("ok") else 1


def action_ide_control_execute(args: argparse.Namespace) -> int:
    from koruapi.desktop_uri import desktop_uri_control_execute

    ide = _resolve_control_ide(args)
    client_factory, socket_path = _client_factory_for_args(args, ide)
    workspace = ""
    status, _status_err = _fetch_autopilot_status(socket_path)
    if status:
        workspace = _resolve_workspace_from_status(status, ide, args.project)
    payload = desktop_uri_control_execute(
        args.prompt,
        locale=args.locale,
        dry_run=args.dry_run,
        text=args.text,
        ide=ide,
        submit=not args.no_submit,
        workspace=workspace,
        client_factory=client_factory,
    )
    if args.output_format == "json":
        _print_json(payload)
    else:
        if not payload.get("ok"):
            exec_payload = payload.get("execution") or {}
            results = exec_payload.get("results") or []
            reply = (results[0] or {}).get("reply") if results else {}
            if isinstance(reply, dict) and reply.get("delivered"):
                print(
                    "koru ide control execute: text pasted but submit not verified "
                    "(try --no-submit or press Enter in chat manually)",
                    file=sys.stderr,
                )
            err = (
                payload.get("error")
                or (results[0] or {}).get("error")
                or exec_payload.get("error")
                or "?"
            )
            if err != "?":
                print(f"koru ide control execute: {err}", file=sys.stderr)
            return 1
        exec_payload = payload.get("execution") or {}
        results = exec_payload.get("results") or []
        top = results[0] if results else {}
        mode = payload.get("drive_mode", "?")
        print(f"ok={payload.get('ok')} backend={top.get('backend', '?')} mode={mode}")
    return 0 if payload.get("ok") else 1


def _fetch_autopilot_status(socket_path: Path) -> tuple[dict | None, str | None]:
    try:
        from koruide.client import KoruIDEClient
    except ImportError as exc:
        return None, f"koruide client unavailable: {exc}"
    resolved = Path(socket_path).expanduser().resolve()
    client = KoruIDEClient(socket_path=resolved)
    if not client.is_running():
        return None, f"autopilot daemon not running on {resolved}"
    try:
        return client.status(), None
    except (OSError, RuntimeError) as exc:
        return None, str(exc)


def action_ide_control_list_uris(args: argparse.Namespace) -> int:
    from koruapi.desktop_uri import desktop_uri_list_koru_ide_uris

    ide = _resolve_control_ide(args)
    _client_factory, socket_path = _client_factory_for_args(args, ide)
    status, err = _fetch_autopilot_status(socket_path)
    if status is None:
        print(f"koru ide control list-uris: {err}", file=sys.stderr)
        return 1
    payload = desktop_uri_list_koru_ide_uris(status, socket_path=str(socket_path))
    plugins = status.get("plugins") if isinstance(status.get("plugins"), list) else []
    if args.output_format == "json":
        _print_json(payload)
    else:
        entries = payload.get("entries") or {}
        print(f"socket={socket_path} entries={len(entries)}")
        for uri in sorted(entries):
            print(uri)
    if not plugins:
        instance = (args.instance or os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
        hint = (
            "hint: no IDE plugin on this socket — try "
            f"KORU_AUTOPILOT_INSTANCE=cursor-main koru ide control list-uris "
            "or koru ide doctor --fix"
        )
        if instance:
            hint = (
                f"hint: no IDE plugin on socket {socket_path} "
                f"(instance={instance!r}); run koru ide doctor --ide {ide} --fix"
            )
        print(hint, file=sys.stderr)
    return 0 if payload.get("ok") else 1


def dispatch_control_action(args: argparse.Namespace) -> int:
    if args.control_action == "plan":
        return action_ide_control_plan(args)
    if args.control_action == "execute":
        return action_ide_control_execute(args)
    if args.control_action == "list-uris":
        return action_ide_control_list_uris(args)
    print(f"koru ide control: unknown action {args.control_action}", file=sys.stderr)
    return 2
