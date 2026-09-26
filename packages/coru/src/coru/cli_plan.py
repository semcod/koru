"""Heuristic/LLM plan chain construction, execution and the interactive chat loop extracted from ``coru.cli``."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from coru.cli import Plan, SessionContext
def _intent_to_plan(intent) -> Plan:
    from coru.cli import Plan
    return Plan(
        action=str(intent.action),
        ide=intent.ide,
        instance=intent.instance,
        install=bool(intent.install),
        auto_args=tuple(intent.auto_args),
    )


def _import_heuristic_plan_fn():
    try:
        from nlp2coru.heuristic import heuristic_plan

        return heuristic_plan
    except ImportError:
        pass
    repo_root = Path(__file__).resolve().parents[4]
    sibling_src_dirs = (
        repo_root / "packages" / "nlp2coru" / "src",
        repo_root / "packages" / "dsl2coru" / "src",
        repo_root / "packages" / "dsl2koru" / "src",
    )
    if not any(path.is_dir() for path in sibling_src_dirs):
        return None
    import sys

    for sibling_src in sibling_src_dirs:
        if not sibling_src.is_dir():
            continue
        path = str(sibling_src)
        if path not in sys.path:
            sys.path.insert(0, path)
    try:
        from nlp2coru.heuristic import heuristic_plan

        return heuristic_plan
    except ImportError:
        return None


def _heuristic_plan(text: str) -> Plan:
    from coru.cli import Plan
    heuristic_plan = _import_heuristic_plan_fn()
    if heuristic_plan is None:
        return Plan(action="status")
    try:
        coru_plan = heuristic_plan(text)
        if coru_plan.steps:
            return _intent_to_plan(coru_plan.steps[0])
    except Exception:
        pass
    return Plan(action="status")


def _llm_plan(text: str) -> Plan | None:
    from coru.cli import Plan
    try:
        from nlp2coru.llm import llm_plan
    except Exception:
        return None
    model = os.environ.get("CORU_LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    try:
        coru_plan = llm_plan(text, model=model)
    except Exception:
        return None
    if not coru_plan.steps:
        return None
    step = coru_plan.steps[0]
    action = step.action
    if action not in {"ensure", "lane", "diagnose", "status", "auto", "doctor", "calibration", "repair", "sync"}:
        action = "diagnose"
    return Plan(
        action=action,
        ide=step.ide,
        instance=step.instance,
        install=step.install,
    )


def _resolve_defaults(plan: Plan, *, context: SessionContext | None = None) -> Plan:
    from coru.cli import (
        Plan,
        _infer_default_ide,
        _infer_default_instance,
        _maybe_warn_lane_override,
        _normalize_lane_pair,
        _trace,
    )
    _trace("resolve_defaults.start", action=plan.action, plan_ide=plan.ide or "(none)",
           plan_instance=plan.instance or "(none)")
    ide = plan.ide or (context.ide if context else None) or _infer_default_ide()
    instance = plan.instance or (context.instance if context else None) or _infer_default_instance(ide=ide)
    pre_normalize = f"{ide}/{instance}"
    ide, instance = _normalize_lane_pair(ide, instance)
    _trace("resolve_defaults.result", ide=ide, instance=instance,
           pre_normalize=pre_normalize, action=plan.action)
    _maybe_warn_lane_override(ide, instance, context=context)
    if context is not None:
        context.ide = ide
        context.instance = instance
    return Plan(
        action=plan.action,
        ide=ide,
        instance=instance,
        text=plan.text,
        install=plan.install,
        auto_args=plan.auto_args,
    )


def _default_lane(ide: str | None, instance: str | None) -> tuple[str, str]:
    from coru.cli import _infer_default_ide, _infer_default_instance, _normalize_lane_pair
    resolved_ide = ide or _infer_default_ide()
    resolved_instance = instance or _infer_default_instance(ide=resolved_ide)
    return _normalize_lane_pair(resolved_ide, resolved_instance)


def _dispatch_plan_action(resolved: Plan, shell: str) -> int:
    from coru.cli import (
        _diagnose_lane,
        _ensure_commands,
        _lane_calibration,
        _lane_doctor,
        _lane_env,
        _lane_manage_fix,
        _run_auto_with_readiness,
    )
    if resolved.action == "ensure":
        return _ensure_commands(install=resolved.install)
    if resolved.action == "lane":
        return _lane_env(resolved.ide, resolved.instance, shell)
    if resolved.action == "manage":
        return _lane_manage_fix(resolved.ide, resolved.instance)
    if resolved.action in {"status", "diagnose"}:
        return _diagnose_lane(resolved.ide, resolved.instance, skip_ensure=True)
    if resolved.action == "doctor":
        return _lane_doctor(resolved.ide, resolved.instance, fix=False, probe=False, skip_ensure=False)
    if resolved.action == "calibration":
        return _lane_calibration(resolved.ide, resolved.instance)
    if resolved.action == "auto":
        return _run_auto_with_readiness(resolved.ide, resolved.instance, list(resolved.auto_args))
    print(f"unsupported action: {resolved.action}", file=sys.stderr)
    return 2


def _execute_plan(
    plan: Plan,
    *,
    shell: str = "bash",
    context: SessionContext | None = None,
) -> int:
    resolved = _resolve_defaults(plan, context=context)
    return _dispatch_plan_action(resolved, shell)


def _build_plan_chain(prompt: str, *, use_llm: bool = False, single_action: bool = False) -> list[Plan]:
    from coru.cli import Plan, _heuristic_plan, _refactor_intent
    first = _llm_plan(prompt) if use_llm else None
    if first is None:
        first = _heuristic_plan(prompt)
    if single_action:
        return [first]

    text = prompt.strip().lower()
    wants_auto = first.action == "auto" or _refactor_intent(text) or any(
        k in text for k in ("auto", "autonomous", "autopilot")
    )
    wants_setup = any(k in text for k in ("setup", "prepare", "przygotuj", "uruchom", "start"))

    if wants_auto or wants_setup:
        chain = [
            Plan(action="ensure", ide=first.ide, instance=first.instance, install=True),
            Plan(action="lane", ide=first.ide, instance=first.instance),
            Plan(action="manage", ide=first.ide, instance=first.instance),
            Plan(action="diagnose", ide=first.ide, instance=first.instance),
        ]
        if wants_auto:
            chain.append(Plan(action="auto", ide=first.ide, instance=first.instance, auto_args=first.auto_args))
        return chain

    return [first]


def _preflight_failure_ok_to_continue(plans: Sequence[Plan], index: int) -> bool:
    """Allow manage/diagnose preflights to continue into auto when they still report issues."""
    plan = plans[index]
    if plan.action not in {"manage", "status", "diagnose"}:
        return False
    return any(p.action == "auto" for p in plans[index + 1 :])


def _plan_step_identity(plan: Plan, ctx: SessionContext) -> tuple[str, str]:
    return plan.ide or ctx.ide or "-", plan.instance or ctx.instance or "-"


def _emit_plan_step_log(
    plan: Plan,
    ctx: SessionContext,
    *,
    announce: bool,
    result: str,
    level: str = "info",
    rc: int | None = None,
) -> None:
    from coru.cli import _emit_log
    ide, instance = _plan_step_identity(plan, ctx)
    if announce and result == "started":
        print(f"[coru] step={plan.action} ide={ide} instance={instance}")
    kwargs: dict[str, Any] = {
        "component": "planner",
        "level": level,
        "action": plan.action,
        "result": result,
        "verbose": announce,
        "ide": plan.ide or ctx.ide or "",
        "instance": plan.instance or ctx.instance or "",
    }
    if rc is not None:
        kwargs["rc"] = rc
    _emit_log(**kwargs)


def _plan_failure_return(
    plan: Plan,
    *,
    index: int,
    plans_list: list[Plan],
    rc: int,
) -> int | None:
    if plan.action in {"manage", "status", "diagnose"} and _preflight_failure_ok_to_continue(plans_list, index):
        print(
            "[coru] preflight: autopilot bridge not ready; "
            "continuing to auto (koru will retry and/or repair)",
            file=sys.stderr,
        )
        return None
    return rc


def _run_single_plan_with_logging(
    plan: Plan,
    *,
    index: int,
    plans_list: list[Plan],
    ctx: SessionContext,
    shell: str,
    announce: bool,
) -> int | None:
    """Execute one plan, emit logs, and return rc or None to continue past preflight."""
    from coru.cli import _execute_plan
    _emit_plan_step_log(plan, ctx, announce=announce, result="started")
    rc = _execute_plan(plan, shell=shell, context=ctx)
    _emit_plan_step_log(
        plan,
        ctx,
        announce=announce,
        result="ok" if rc == 0 else "failed",
        level="info" if rc == 0 else "error",
        rc=rc,
    )
    if rc != 0:
        return _plan_failure_return(plan, index=index, plans_list=plans_list, rc=rc)
    return rc


def _chat_print_header(
    *,
    startup_lane: Plan,
    verbose: bool,
    require_plugin: bool,
) -> None:
    from coru.cli import _print_runtime_versions, _print_troubleshooting_log_locations
    print("coru chat mode. Type 'quit' to exit.")
    _print_runtime_versions()
    if verbose:
        print("verbose: on")
    print("chat mode: message -> IDE chat (use '/<command>' for coru actions)")
    _print_troubleshooting_log_locations(startup_lane.ide, startup_lane.instance)
    transport_label = "plugin-only (no keyboard fallback)" if require_plugin else "plugin or keyboard fallback"
    print(f"chat mode transport: {transport_label}")


def _chat_ensure_daemon(
    ide: str,
    instance: str,
    *,
    action: str,
    verbose: bool,
) -> int:
    from coru.cli import _emit_log, _start_autopilot_daemon_for_lane
    daemon_rc = _start_autopilot_daemon_for_lane(ide, instance)
    _emit_log(
        component="chat",
        level="info" if daemon_rc == 0 else "error",
        action=action,
        result="ok" if daemon_rc == 0 else "failed",
        rc=daemon_rc,
        verbose=verbose,
        ide=ide,
        instance=instance,
    )
    if daemon_rc == 0 and verbose:
        print(f"[coru] daemon ready for ide={ide} instance={instance}; retrying drive")
    return daemon_rc


def _chat_drive_with_retry(
    ide: str,
    instance: str,
    outbound: str,
    *,
    require_plugin: bool,
    verbose: bool,
) -> int:
    from coru.cli import _emit_log, _lane_chat_prompt
    rc = _lane_chat_prompt(ide, instance, outbound, require_plugin=require_plugin)
    _emit_log(
        component="chat",
        level="info" if rc == 0 else "warning",
        action="drive",
        result="ok" if rc == 0 else "retry_pending" if rc == 2 else "failed",
        rc=rc,
        verbose=verbose,
        ide=ide,
        instance=instance,
    )
    if rc != 2 or not ide or ide == "auto":
        return rc
    daemon_rc = _chat_ensure_daemon(ide, instance, action="daemon_autostart", verbose=verbose)
    if daemon_rc != 0:
        return rc
    rc = _lane_chat_prompt(ide, instance, outbound, require_plugin=require_plugin)
    _emit_log(
        component="chat",
        level="info" if rc == 0 else "error",
        action="drive_retry",
        result="ok" if rc == 0 else "failed",
        rc=rc,
        verbose=verbose,
        ide=ide,
        instance=instance,
    )
    return rc


def _chat_handle_drive(
    line: str,
    ctx: SessionContext,
    *,
    use_llm: bool,
    require_plugin: bool,
    verbose: bool,
) -> None:
    from coru.cli import Plan, _chat_llm_enabled, _lane_status, _llm_rewrite_chat_prompt
    resolved = _resolve_defaults(Plan(action="status"), context=ctx)
    outbound = line
    if _chat_llm_enabled(use_llm):
        outbound = _llm_rewrite_chat_prompt(line, ide=resolved.ide, instance=resolved.instance)
        if verbose and outbound != line:
            print(f"[coru] llm rewrite: {outbound}")
    if verbose:
        print(f"[coru] drive ide={resolved.ide} instance={resolved.instance}")
    if require_plugin and resolved.ide and resolved.ide != "auto":
        if _lane_status(resolved.ide, resolved.instance) != 0:
            _chat_ensure_daemon(resolved.ide, resolved.instance, action="daemon_preflight", verbose=verbose)
    rc = _chat_drive_with_retry(
        resolved.ide,
        resolved.instance,
        outbound,
        require_plugin=require_plugin,
        verbose=verbose,
    )
    if rc != 0:
        print(f"[coru] failed rc={rc}")


def _chat_handle_command(
    line: str,
    ctx: SessionContext,
    *,
    use_llm: bool,
    shell: str,
    single_action: bool,
) -> None:
    command_text = line[1:].strip()
    if not command_text:
        return
    del ctx, shell  # lane context preserved in session; DSL dispatch uses runner env
    from coru.control import apply_nl

    rc = apply_nl(command_text, use_llm=use_llm, single_action=single_action)
    if rc != 0:
        print(f"[coru] failed rc={rc}")


def _chat_loop(
    *,
    use_llm: bool,
    shell: str,
    single_action: bool,
    verbose: bool = False,
    require_plugin: bool = True,
) -> int:
    from coru.cli import Plan, SessionContext
    ctx = SessionContext()
    startup_lane = _resolve_defaults(Plan(action="status"), context=ctx)
    _chat_print_header(startup_lane=startup_lane, verbose=verbose, require_plugin=require_plugin)
    while True:
        try:
            line = input("coru> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 130
        if not line:
            continue
        if line.lower() in {"quit", "exit", "q"}:
            return 0
        if line.startswith("/"):
            _chat_handle_command(line, ctx, use_llm=use_llm, shell=shell, single_action=single_action)
        else:
            _chat_handle_drive(line, ctx, use_llm=use_llm, require_plugin=require_plugin, verbose=verbose)
