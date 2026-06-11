"""Repair pipeline execution (write model) with optional event emission."""

from __future__ import annotations

import json
import shutil
import time
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coru.repair.diagnostics import _plugin_row_for_ide, _read_package_build_sha
from coru.repair.domain import RepairAttempt, RepairPlan, RepairProblem, RepairStepDef
from coru.repair.registry import registry_step, registry_steps_for_code

RunKoru = Callable[[Sequence[str]], int]
ReplayFn = Callable[[str, str, Sequence[str]], int]
StatusPayloadFn = Callable[[str, str], dict[str, Any] | None]
IdeReloadFn = Callable[[str, Path | None], RepairAttempt]
IdeConnectFn = Callable[[str], RepairAttempt]
StrictHandshakeFn = Callable[[], RepairAttempt]
EventCallback = Callable[[str, dict[str, Any]], None]

_EXTENSION_LAYOUT: dict[str, tuple[str, str]] = {
    "cursor": (".cursor/extensions", "semcod.koru-autopilot-cursor"),
    "vscode": (".vscode/extensions", "semcod.koru-autopilot-vscode"),
    "vscodium": (".vscode-oss/extensions", "semcod.koru-autopilot-vscodium"),
    "windsurf": (".windsurf/extensions", "semcod.koru-autopilot-windsurf"),
    "antigravity": (".antigravity/extensions", "semcod.koru-autopilot-antigravity"),
}

_PLUGIN_DIR_NAMES: dict[str, str] = {
    "cursor": "koru-autopilot-cursor",
    "vscode": "koru-autopilot-vscode",
    "vscodium": "koru-autopilot-vscodium",
    "windsurf": "koru-autopilot-windsurf",
    "antigravity": "koru-autopilot-antigravity",
}


def _emit(on_event: EventCallback | None, event_type: str, payload: dict[str, Any]) -> None:
    if on_event is not None:
        on_event(event_type, payload)


def _installed_extension_dir(ide: str) -> Path | None:
    layout = _EXTENSION_LAYOUT.get(ide)
    if layout is None:
        return None
    rel_root, ext_prefix = layout
    ext_root = Path.home() / rel_root
    if not ext_root.is_dir():
        return None
    matches = sorted(
        ext_root.glob(f"{ext_prefix}-*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def _resolve_repo_vsix(repo_root: Path, ide: str, version: str | None) -> Path | None:
    dir_name = _PLUGIN_DIR_NAMES.get(ide)
    if not dir_name:
        return None
    plugin_dir = repo_root / "plugins" / dir_name
    if not plugin_dir.is_dir():
        return None
    if version:
        candidate = plugin_dir / f"{dir_name}-{version}.vsix"
        if candidate.is_file():
            return candidate
    vsix_files = sorted(plugin_dir.glob("*.vsix"), key=lambda p: p.stat().st_mtime, reverse=True)
    return vsix_files[0] if vsix_files else None


def _get_installed_version(ide: str) -> str | None:
    installed_dir = _installed_extension_dir(ide)
    if installed_dir is None:
        return None
    pkg = installed_dir / "package.json"
    if not pkg.is_file():
        return None
    try:
        return (
            str(json.loads(pkg.read_text(encoding="utf-8")).get("version") or "").strip()
            or None
        )
    except (OSError, json.JSONDecodeError):
        return None


def _read_vsix_version(vsix: Path) -> str | None:
    try:
        with zipfile.ZipFile(vsix) as archive:
            pkg = json.loads(archive.read("extension/package.json"))
            return str(pkg.get("version") or "0.0.0")
    except (OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError):
        return None


def _unpack_vsix_archive(vsix: Path, target: Path, tmp: Path) -> str | None:
    """Unpacks vsix zip archive to tmp and moves 'extension' to target.
    Returns error message if any, or None if successful.
    """
    if target.exists():
        shutil.rmtree(target)
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(vsix) as archive:
            archive.extractall(tmp)
        extracted = tmp / "extension"
        if not extracted.is_dir():
            return f"VSIX layout missing extension/ in {vsix}"
        shutil.move(str(extracted), str(target))
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _vsix_unpack_layout(ide: str) -> tuple[Path, str, str] | RepairAttempt:
    layout = _EXTENSION_LAYOUT.get(ide)
    if layout is None:
        return RepairAttempt(
            action_id="manual_vsix_unpack",
            mode="auto",
            ok=False,
            message=f"unsupported ide for manual VSIX unpack: {ide}",
        )
    rel_root, ext_prefix = layout
    ext_root = Path.home() / rel_root
    ext_root.mkdir(parents=True, exist_ok=True)
    return ext_root, ext_prefix, ide


def _vsix_source(ide: str, repo_root: Path) -> Path | RepairAttempt:
    version = _get_installed_version(ide)
    vsix = _resolve_repo_vsix(repo_root, ide, version)
    if vsix is None:
        return RepairAttempt(
            action_id="manual_vsix_unpack",
            mode="auto",
            ok=False,
            message=f"no VSIX found under {repo_root}/plugins for ide={ide}",
        )
    return vsix


def _vsix_unpack_result(
    ext_root: Path,
    ext_prefix: str,
    vsix: Path,
) -> RepairAttempt:
    vsix_version = _read_vsix_version(vsix)
    if vsix_version is None:
        return RepairAttempt(
            action_id="manual_vsix_unpack",
            mode="auto",
            ok=False,
            message=f"cannot read VSIX package.json from {vsix}",
        )

    target = ext_root / f"{ext_prefix}-{vsix_version}"
    tmp = ext_root / f".{ext_prefix}-{vsix_version}.tmp"

    err = _unpack_vsix_archive(vsix, target, tmp)
    if err:
        return RepairAttempt(
            action_id="manual_vsix_unpack",
            mode="auto",
            ok=False,
            message=err,
        )

    build_sha = _read_package_build_sha(target / "package.json")
    return RepairAttempt(
        action_id="manual_vsix_unpack",
        mode="auto",
        ok=True,
        message=(
            f"installed {target.name} build={build_sha or '-'} "
            f"from {vsix.name}; reload IDE window required"
        ),
    )


def manual_vsix_unpack(*, ide: str, repo_root: Path) -> RepairAttempt:
    layout = _vsix_unpack_layout(ide)
    if isinstance(layout, RepairAttempt):
        return layout
    ext_root, ext_prefix, _ = layout

    vsix = _vsix_source(ide, repo_root)
    if isinstance(vsix, RepairAttempt):
        return vsix

    return _vsix_unpack_result(ext_root, ext_prefix, vsix)



def plugin_build_aligned(
    status: Mapping[str, Any] | None,
    *,
    ide: str,
    expected_build: str | None,
) -> bool:
    if not expected_build:
        return _plugin_row_for_ide(status, ide) is not None
    row = _plugin_row_for_ide(status, ide)
    if row is None:
        return False
    return str(row.get("buildSha") or "").strip() == expected_build


def _expected_build_from_problems(problems: Sequence[RepairProblem]) -> str | None:
    for problem in problems:
        ctx = problem.context
        if isinstance(ctx, Mapping) and ctx.get("expected_build"):
            return str(ctx["expected_build"])
    for problem in problems:
        if "build" in problem.code and isinstance(problem.context, Mapping):
            value = str(problem.context.get("expected_build") or "").strip()
            if value:
                return value
    return None


def _poll_plugin_ready(
    *,
    ide: str,
    instance: str,
    fetch_status: StatusPayloadFn,
    expected_build: str | None,
    timeout_seconds: float,
) -> tuple[bool, Mapping[str, Any] | None]:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    last_status: Mapping[str, Any] | None = None
    while time.monotonic() < deadline:
        status = fetch_status(ide, instance)
        if isinstance(status, dict):
            last_status = status
        if plugin_build_aligned(status, ide=ide, expected_build=expected_build):
            return True, last_status
        if expected_build is None and _plugin_row_for_ide(status, ide) is not None:
            return True, last_status
        time.sleep(0.5)
    return False, last_status


def _run_reload_and_connect(
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    fetch_status: StatusPayloadFn,
    expected_build: str | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    if ide_reload is None:
        return [
            RepairAttempt(
                action_id="reload_and_connect",
                mode="auto",
                ok=False,
                message="no IDE reload handler registered",
            )
        ]
    out: list[RepairAttempt] = []
    reload_attempt = ide_reload(ide, repo_root)
    out.append(reload_attempt)
    if reload_attempt.ok:
        time.sleep(5.0)
    ready, _status = _poll_plugin_ready(
        ide=ide,
        instance=instance,
        fetch_status=fetch_status,
        expected_build=expected_build,
        timeout_seconds=20.0 if reload_attempt.ok else 4.0,
    )
    connect_attempt: RepairAttempt | None = None
    if not ready and ide_connect is not None:
        connect_attempt = ide_connect(ide)
        out.append(connect_attempt)
        if connect_attempt.ok:
            time.sleep(2.0)
        ready, _status = _poll_plugin_ready(
            ide=ide,
            instance=instance,
            fetch_status=fetch_status,
            expected_build=expected_build,
            timeout_seconds=15.0,
        )
    out.append(
        RepairAttempt(
            action_id="reload_and_connect",
            mode="auto",
            ok=ready,
            message=(
                f"reload ok={reload_attempt.ok} "
                f"connect ok={connect_attempt.ok if connect_attempt else 'skipped'} "
                f"plugin_ready={ready}"
            ),
        )
    )
    return out


def _exec_ensure_daemon(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    return [
        RepairAttempt(
            action_id=step.action_id,
            mode=step.mode,
            ok=False,
            message="skipped in step loop",
        )
    ]


def _exec_manage_fix(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    rc = run_koru(["autopilot", "manage", "--ide", ide, "--fix"])
    return [
        RepairAttempt(
            action_id=step.action_id,
            mode=step.mode,
            ok=rc == 0,
            message="manage --fix completed" if rc == 0 else f"manage --fix rc={rc}",
        )
    ]


def _exec_manual_vsix_unpack(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    if repo_root is None:
        return [
            RepairAttempt(
                action_id=step.action_id,
                mode=step.mode,
                ok=False,
                message="repo root unknown; cannot unpack VSIX",
            )
        ]
    return [manual_vsix_unpack(ide=ide, repo_root=repo_root)]


def _exec_plugin_upgrade_and_reload(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    if repo_root is None:
        return [
            RepairAttempt(
                action_id=step.action_id,
                mode="auto",
                ok=False,
                message="repo root unknown; cannot upgrade plugin",
            )
        ]
    unpack = manual_vsix_unpack(ide=ide, repo_root=repo_root)
    if not unpack.ok:
        return [
            unpack,
            RepairAttempt(
                action_id=step.action_id,
                mode="auto",
                ok=False,
                message=f"upgrade failed at unpack: {unpack.message}",
            ),
        ]
    reload_steps = _run_reload_and_connect(
        ide=ide,
        instance=instance,
        repo_root=repo_root,
        fetch_status=fetch_status,
        expected_build=expected_build,
        ide_reload=ide_reload,
        ide_connect=ide_connect,
    )
    ready = reload_steps[-1].ok if reload_steps else False
    return [
        unpack,
        *reload_steps[:-1],
        RepairAttempt(
            action_id=step.action_id,
            mode="auto",
            ok=ready,
            message=reload_steps[-1].message if reload_steps else "reload/connect failed",
        ),
    ]


def _exec_strict_handshake_cycle(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    if strict_handshake is None:
        return [
            RepairAttempt(
                action_id=step.action_id,
                mode="auto",
                ok=False,
                message="no strict handshake handler registered",
            )
        ]
    hs_attempt = strict_handshake()
    if hs_attempt.ok:
        time.sleep(3.0)
    ready, _status = _poll_plugin_ready(
        ide=ide,
        instance=instance,
        fetch_status=fetch_status,
        expected_build=expected_build,
        timeout_seconds=40.0 if hs_attempt.ok else 6.0,
    )
    return [
        RepairAttempt(
            action_id=step.action_id,
            mode="auto",
            ok=ready,
            message=f"{hs_attempt.message}; plugin_ready={ready}",
        )
    ]


def _exec_reload_and_connect(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    return _run_reload_and_connect(
        ide=ide,
        instance=instance,
        repo_root=repo_root,
        fetch_status=fetch_status,
        expected_build=expected_build,
        ide_reload=ide_reload,
        ide_connect=ide_connect,
    )


def _exec_cross_ide_guidance(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    return [
        RepairAttempt(
            action_id=step.action_id,
            mode="manual",
            ok=True,
            automated=False,
            message=(
                "terminal/lane mismatch: run from target IDE terminal, or "
                "export KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
            ),
        )
    ]


def _exec_submit_unverified_guidance(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    step_def = registry_step(step.action_id)
    return [
        RepairAttempt(
            action_id=step.action_id,
            mode="manual",
            ok=True,
            automated=False,
            message=step_def.llm_playbook if step_def else "submit manually in IDE chat",
        )
    ]


def _exec_default(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    return [
        RepairAttempt(
            action_id=step.action_id,
            mode="manual",
            ok=True,
            automated=False,
            message="see manage report fix hint or coru doctor output",
        )
    ]


_STEP_EXECUTORS: dict[str, Callable[..., list[RepairAttempt]]] = {
    "ensure_daemon": _exec_ensure_daemon,
    "manage_fix": _exec_manage_fix,
    "manual_vsix_unpack": _exec_manual_vsix_unpack,
    "plugin_upgrade_and_reload": _exec_plugin_upgrade_and_reload,
    "strict_handshake_cycle": _exec_strict_handshake_cycle,
    "reload_and_connect": _exec_reload_and_connect,
    "cross_ide_guidance": _exec_cross_ide_guidance,
    "submit_unverified_guidance": _exec_submit_unverified_guidance,
}


def _execute_step(
    step: RepairStepDef,
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    expected_build: str | None,
    run_koru: RunKoru,
    fetch_status: StatusPayloadFn,
    strict_handshake: StrictHandshakeFn | None,
    ide_reload: IdeReloadFn | None,
    ide_connect: IdeConnectFn | None,
) -> list[RepairAttempt]:
    executor = _STEP_EXECUTORS.get(step.action_id, _exec_default)
    return executor(
        step,
        ide=ide,
        instance=instance,
        repo_root=repo_root,
        expected_build=expected_build,
        run_koru=run_koru,
        fetch_status=fetch_status,
        strict_handshake=strict_handshake,
        ide_reload=ide_reload,
        ide_connect=ide_connect,
    )


def _drop_codes_after_action(
    remaining: list[RepairProblem],
    round_actions: Sequence[RepairAttempt],
    *,
    action_id: str,
    codes: set[str],
) -> list[RepairProblem]:
    if not any(action.action_id == action_id and action.ok for action in round_actions):
        return remaining
    return [problem for problem in remaining if problem.code not in codes]


_ROUND_RESOLUTION_RULES: tuple[tuple[str, set[str]], ...] = (
    (
        "manual_vsix_unpack",
        {
            "plugin_extension_stale_on_disk",
            "install_plugin_failed",
            "install_plugin_cli_sandbox",
            "plugin_installed_version_mismatch",
        },
    ),
    (
        "plugin_upgrade_and_reload",
        {
            "probe_cache_toxic",
            "chat_focus_toggle_risk",
            "terminal_paste_risk",
            "plugin_extension_stale_on_disk",
        },
    ),
    (
        "strict_handshake_cycle",
        {
            "plugin_build_mismatch",
            "plugin_version_mismatch",
            "plugin_extension_stale_in_memory",
            "plugin_live_host_stale",
            "plugin_rejected_by_daemon",
        },
    ),
    (
        "reload_and_connect",
        {
            "plugin_build_mismatch",
            "plugin_version_mismatch",
            "plugin_extension_stale_in_memory",
            "plugin_live_host_stale",
            "plugin_not_connected",
            "plugin_installed_ok_but_not_connected",
        },
    ),
)


def _apply_round_resolution(
    remaining: list[RepairProblem],
    round_actions: Sequence[RepairAttempt],
) -> tuple[list[RepairProblem], bool]:
    for action_id, codes in _ROUND_RESOLUTION_RULES:
        remaining = _drop_codes_after_action(
            remaining,
            round_actions,
            action_id=action_id,
            codes=codes,
        )
    return remaining, not remaining


@dataclass
class _PipelineState:
    attempts: list[RepairAttempt]
    remaining: list[RepairProblem]
    resolved: bool
    expected_build: str | None


@dataclass(frozen=True)
class _PipelineContext:
    session_id: str
    ide: str
    instance: str
    repo_root: Path | None
    run_koru: RunKoru
    fetch_status: StatusPayloadFn
    ensure_daemon: Callable[[], int] | None
    ide_reload: IdeReloadFn | None
    ide_connect: IdeConnectFn | None
    strict_handshake: StrictHandshakeFn | None
    on_event: EventCallback | None


def _emit_session_started(
    ctx: _PipelineContext,
    *,
    trigger: str,
    problem_count: int,
) -> None:
    _emit(
        ctx.on_event,
        "repair.session.started",
        {
            "session_id": ctx.session_id,
            "ide": ctx.ide,
            "instance": ctx.instance,
            "trigger": trigger,
            "problem_count": problem_count,
        },
    )


def _emit_problems_detected(
    ctx: _PipelineContext,
    problems: Sequence[RepairProblem],
) -> None:
    _emit(
        ctx.on_event,
        "repair.problems.detected",
        {
            "session_id": ctx.session_id,
            "problems": [
                {
                    "code": p.code,
                    "severity": p.severity,
                    "message": p.message,
                    "fix_hint": p.fix_hint,
                    "context": dict(p.context),
                }
                for p in problems
            ],
        },
    )


def _emit_session_finished(ctx: _PipelineContext, state: _PipelineState) -> None:
    _emit(
        ctx.on_event,
        "repair.session.finished",
        {
            "session_id": ctx.session_id,
            "resolved": state.resolved,
            "attempt_count": len(state.attempts),
            "remaining_codes": sorted({p.code for p in state.remaining}),
        },
    )


def _record_attempt(ctx: _PipelineContext, state: _PipelineState, attempt: RepairAttempt) -> None:
    state.attempts.append(attempt)
    _emit(
        ctx.on_event,
        "repair.attempt.finished",
        {"session_id": ctx.session_id, **attempt.__dict__},
    )


def _attempt_ensure_daemon(
    ctx: _PipelineContext,
    state: _PipelineState,
    *,
    round_index: int,
    codes: set[str],
) -> bool:
    if "daemon_not_running" not in codes or ctx.ensure_daemon is None:
        return False

    _emit(
        ctx.on_event,
        "repair.command.dispatched",
        {"session_id": ctx.session_id, "action_id": "ensure_daemon", "round": round_index},
    )
    started = time.monotonic()
    rc = ctx.ensure_daemon()
    _record_attempt(
        ctx,
        state,
        RepairAttempt(
            action_id="ensure_daemon",
            mode="auto",
            ok=rc == 0,
            message="daemon ensure ok" if rc == 0 else f"daemon ensure failed rc={rc}",
            duration_ms=(time.monotonic() - started) * 1000,
        ),
    )
    if rc != 0:
        return True

    state.remaining = [p for p in state.remaining if p.code != "daemon_not_running"]
    state.resolved = not state.remaining
    return state.resolved


def _steps_for_codes(codes: set[str]) -> tuple[list[RepairStepDef], list[str]]:
    steps: list[RepairStepDef] = []
    for code in codes:
        steps.extend(registry_steps_for_code(code))

    unique_steps = {step.action_id: step for step in steps}
    ordered_steps = sorted(unique_steps.values(), key=lambda s: s.priority)
    mapped_codes = {code for step in ordered_steps for code in step.issue_codes}
    unmapped_codes = sorted(code for code in codes if code not in mapped_codes)
    return ordered_steps, unmapped_codes


def _set_step_duration(step_attempts: Sequence[RepairAttempt], elapsed_ms: float) -> None:
    if len(step_attempts) == 1:
        step_attempts[0].duration_ms = elapsed_ms


def _run_repair_step(
    ctx: _PipelineContext,
    state: _PipelineState,
    step: RepairStepDef,
    *,
    round_index: int,
    codes: set[str],
) -> None:
    _emit(
        ctx.on_event,
        "repair.command.dispatched",
        {
            "session_id": ctx.session_id,
            "action_id": step.action_id,
            "mode": step.mode,
            "round": round_index,
            "targets": sorted(step.issue_codes & codes),
        },
    )
    started = time.monotonic()
    step_attempts = _execute_step(
        step,
        ide=ctx.ide,
        instance=ctx.instance,
        repo_root=ctx.repo_root,
        expected_build=state.expected_build,
        run_koru=ctx.run_koru,
        fetch_status=ctx.fetch_status,
        strict_handshake=ctx.strict_handshake,
        ide_reload=ctx.ide_reload,
        ide_connect=ctx.ide_connect,
    )
    _set_step_duration(step_attempts, (time.monotonic() - started) * 1000)
    for attempt in step_attempts:
        _record_attempt(ctx, state, attempt)


def _run_repair_steps(
    ctx: _PipelineContext,
    state: _PipelineState,
    *,
    round_index: int,
    codes: set[str],
    steps: Sequence[RepairStepDef],
) -> None:
    for step in steps:
        if step.action_id != "ensure_daemon":
            _run_repair_step(ctx, state, step, round_index=round_index, codes=codes)


def _record_unmapped_guidance(
    ctx: _PipelineContext,
    state: _PipelineState,
    unmapped_codes: Sequence[str],
) -> None:
    for code in unmapped_codes:
        _record_attempt(
            ctx,
            state,
            RepairAttempt(
                action_id=f"manual_guidance:{code}",
                mode="manual",
                ok=True,
                automated=False,
                message=(
                    f"no automatic repair registered for issue code {code}; "
                    "add a RepairStepDef to coru.repair.registry.REPAIR_REGISTRY"
                ),
            ),
        )


def _clear_plugin_not_connected_if_ready(
    ctx: _PipelineContext,
    state: _PipelineState,
    status: Mapping[str, Any] | None,
) -> bool:
    if state.expected_build or _plugin_row_for_ide(status, ctx.ide) is None:
        return False
    state.remaining = [p for p in state.remaining if p.code not in {"plugin_not_connected"}]
    state.resolved = not state.remaining
    return state.resolved


def _refresh_status_resolution(ctx: _PipelineContext, state: _PipelineState) -> bool:
    status = ctx.fetch_status(ctx.ide, ctx.instance)
    if state.expected_build is None:
        state.expected_build = _expected_build_from_problems(state.remaining)
    if plugin_build_aligned(status, ide=ctx.ide, expected_build=state.expected_build):
        state.remaining = []
        state.resolved = True
        return True
    return _clear_plugin_not_connected_if_ready(ctx, state, status)


def _apply_round_actions(state: _PipelineState, *, round_start: int) -> bool:
    round_actions = state.attempts[round_start:]
    state.remaining, state.resolved = _apply_round_resolution(state.remaining, round_actions)
    return state.resolved


def _run_repair_round(
    ctx: _PipelineContext,
    state: _PipelineState,
    *,
    round_index: int,
) -> bool:
    if not state.remaining:
        state.resolved = True
        return True

    codes = {problem.code for problem in state.remaining}
    if _attempt_ensure_daemon(ctx, state, round_index=round_index, codes=codes):
        return True

    codes = {problem.code for problem in state.remaining}
    steps, unmapped_codes = _steps_for_codes(codes)
    round_start = len(state.attempts)
    _run_repair_steps(ctx, state, round_index=round_index, codes=codes, steps=steps)
    _record_unmapped_guidance(ctx, state, unmapped_codes)

    if _refresh_status_resolution(ctx, state):
        return True
    return _apply_round_actions(state, round_start=round_start)


def run_repair_pipeline(
    *,
    session_id: str,
    ide: str,
    instance: str,
    repo_root: Path | None,
    problems: Sequence[RepairProblem],
    run_koru: RunKoru,
    replay: ReplayFn,
    fetch_status: StatusPayloadFn,
    ensure_daemon: Callable[[], int] | None = None,
    ide_reload: IdeReloadFn | None = None,
    ide_connect: IdeConnectFn | None = None,
    strict_handshake: StrictHandshakeFn | None = None,
    max_rounds: int = 3,
    trigger: str = "manual",
    on_event: EventCallback | None = None,
) -> RepairPlan:
    """Execute registry repairs until problems clear or rounds exhaust."""

    state = _PipelineState(
        attempts=[],
        remaining=list(problems),
        resolved=not problems,
        expected_build=_expected_build_from_problems(problems),
    )
    ctx = _PipelineContext(
        session_id=session_id,
        ide=ide,
        instance=instance,
        repo_root=repo_root,
        run_koru=run_koru,
        fetch_status=fetch_status,
        ensure_daemon=ensure_daemon,
        ide_reload=ide_reload,
        ide_connect=ide_connect,
        strict_handshake=strict_handshake,
        on_event=on_event,
    )

    _emit_session_started(ctx, trigger=trigger, problem_count=len(problems))
    _emit_problems_detected(ctx, problems)

    for round_index in range(max(1, max_rounds)):
        if _run_repair_round(ctx, state, round_index=round_index):
            break

    _emit_session_finished(ctx, state)

    return RepairPlan(
        session_id=session_id,
        problems=tuple(problems),
        attempts=tuple(state.attempts),
        resolved=state.resolved,
        trigger=trigger,
    )


def format_repair_lines(plan: RepairPlan, *, prefix: str = "[coru] repair") -> list[str]:
    lines: list[str] = []
    for problem in plan.problems:
        lines.append(f"{prefix}: [{problem.severity.upper()}] {problem.code}: {problem.message}")
        if problem.fix_hint:
            lines.append(f"{prefix}: hint → {problem.fix_hint}")
    for attempt in plan.attempts:
        state = "ok" if attempt.ok else "failed"
        auto = "auto" if attempt.automated else "manual"
        lines.append(f"{prefix}: action {attempt.action_id} ({auto}) → {state}: {attempt.message}")
    if plan.resolved:
        lines.append(f"{prefix}: bridge repair complete (session={plan.session_id})")
    elif plan.problems:
        lines.append(
            f"{prefix}: bridge still blocked after repair attempts (session={plan.session_id})"
        )
    return lines


__all__ = [
    "format_repair_lines",
    "manual_vsix_unpack",
    "plugin_build_aligned",
    "run_repair_pipeline",
]
