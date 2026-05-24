
import shutil
import subprocess
from collections.abc import Callable
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from koru.autonomous_diag_markers import diagnostic_marker_path
from koru.autonomous_wup import WupHealthResult
from koru.bounded_contexts.wup.application import WupCommandService
from koru.bounded_contexts.wup.commands import EvaluateWupHealthCommand
from koru.redup_integration import redup_changed_scan_runner_command, redup_scan_command
from koru.tasks import create_nl_task

IdleCheck = tuple[str, str, list[str]]


def _has_redup_module() -> bool:
    return shutil.which("redup") is not None or find_spec("redup") is not None


def _code2llm_project_snapshot_command() -> list[str]:
    return [
        "code2llm",
        "./",
        "-f",
        "all",
        "-o",
        "./project",
        "--no-chunk",
        "--exclude",
        "*.md",
        "--exclude",
        "node_modules/**",
        "--exclude",
        ".venv/**",
        "--exclude",
        "dist/**",
        "--exclude",
        "build/**",
        "--exclude",
        ".git/**",
        "--exclude",
        ".planfile/**",
        "--exclude",
        ".wup/**",
        "--exclude",
        "project/**",
    ]


def build_idle_checks(project: Path, profile: str) -> list[IdleCheck]:
    """Build semcod idle diagnostic commands for the given profile."""
    profile = profile.lower()
    checks: list[IdleCheck] = []
    if shutil.which("regix"):
        checks.append(
            (
                "regix",
                "regix compare HEAD --local --format rich",
                ["regix", "compare", "HEAD", "--local", "--format", "rich"],
            ),
        )
    if shutil.which("wup") and (project / "wup.yaml").is_file():
        checks.append(("wup", "wup status", ["wup", "status"]))
    if profile not in {"full", "deep"}:
        return checks
    if profile == "deep" and shutil.which("code2llm"):
        checks.append(
            (
                "code2llm",
                "code2llm ./ -f all -o ./project --no-chunk",
                _code2llm_project_snapshot_command(),
            ),
        )
    if _has_redup_module():
        if (project / "wup.yaml").is_file():
            command = redup_changed_scan_runner_command()
            checks.append(
                (
                    "redup",
                    "python -m koru.redup_integration changed-scan "
                    "--output .redup/wup-changed.json",
                    command,
                ),
            )
        else:
            checks.append(
                (
                    "redup",
                    "python -m redup scan . --min-lines 10",
                    redup_scan_command(),
                ),
            )
    if shutil.which("testql") and any(project.rglob("*.testql.toon.yaml")):
        checks.append(
            (
                "testql",
                "testql suite --pattern *.testql.toon.yaml --output console --fail-fast",
                [
                    "testql",
                    "suite",
                    "--pattern",
                    "*.testql.toon.yaml",
                    "--output",
                    "console",
                    "--fail-fast",
                ],
            ),
        )
    if shutil.which("redsl"):
        checks.append(("redsl", "redsl gate check .", ["redsl", "gate", "check", "."]))
    if (project / "scripts" / "sumr-refresh.sh").is_file():
        checks.append(
            (
                "sumr",
                "bash scripts/sumr-refresh.sh --status",
                ["bash", "scripts/sumr-refresh.sh", "--status"],
            ),
        )
    return checks


def run_idle_check_loop(
    *,
    checks: list[IdleCheck],
    stdio_info: Callable[..., Any],
    is_topology_enabled: Callable[..., bool],
    run_command: Callable[..., bool],
    clear_marker: Callable[[Path, str], None],
    create_ticket: Callable[..., None],
    make_result: Callable[[str, list[str]], Any],
    stdio_format: str,
    project: Path,
    cycle: int,
    queue_status: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path,
    topology_integration: bool,
) -> Any:
    failed: list[str] = []
    diagnostic_state_dir.mkdir(parents=True, exist_ok=True)
    for check_id, summary, command in checks:
        if not is_topology_enabled(project, check_id, fallback=True, enabled=topology_integration):
            stdio_info(f"- {check_id} disabled in topology, skipping", fmt=stdio_format)
            continue
        if run_command(project, check_id, command, stdio_format=stdio_format):
            clear_marker(diagnostic_state_dir, check_id)
            continue
        failed.append(check_id)
        if diagnostic_tickets:
            create_ticket(
                project=project,
                check_id=check_id,
                summary=summary,
                cycle=cycle,
                queue_status=queue_status,
                queue_name=diagnostic_ticket_queue,
                priority=diagnostic_ticket_priority,
                state_dir=diagnostic_state_dir,
            )
    return make_result("failed" if failed else "ok", failed)


def create_diagnostic_ticket(
    *,
    stdio_info: Any,
    stdio_format: str = "human",
    project: Path,
    check_id: str,
    summary: str,
    cycle: int,
    queue_status: str,
    queue_name: str,
    priority: str,
    state_dir: Path,
) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    marker = diagnostic_marker_path(state_dir, check_id)
    if marker.exists():
        stdio_info(
            f"- diagnostic ticket marker exists for {check_id}, skipping create",
            fmt=stdio_format,
        )
        return
    title = f"[AUTO-DIAG] {check_id} needs attention"
    prompt = (
        f"{title} in cycle {cycle}. queue_status={queue_status}. "
        f"Check: {summary}. Investigate and fix regression, stale quality artifact, "
        "or broken diagnostic gate."
    )
    from koru.activity_log import activity

    activity("TICKET", f"[AUTO-DIAG] tworzę ticket dla {check_id}", preview=prompt)
    created = create_nl_task(project, prompt, queue_name=queue_name, priority=priority)
    marker.write_text(created.ticket_id, encoding="utf-8")
    activity("TICKET", f"[AUTO-DIAG] {check_id} → {created.ticket_id} (queue={queue_name})")
    stdio_info(
        f"+ created diagnostic ticket {created.ticket_id} for {check_id} (queue={queue_name})",
        fmt=stdio_format,
    )


def clear_diagnostic_marker(state_dir: Path, check_id: str) -> None:
    diagnostic_marker_path(state_dir, check_id).unlink(missing_ok=True)


def run_command_check(
    *,
    stdio_info: Any,
    project: Path,
    check_id: str,
    command: list[str],
    stdio_format: str = "human",
) -> bool:
    stdio_info(f"+ {' '.join(command)}", fmt=stdio_format)
    result = subprocess.run(command, cwd=project, check=False)
    if result.returncode != 0:
        stdio_info(f"! {check_id} failed (continuing loop)", fmt=stdio_format)
        return False
    return True


def read_wup_health(
    *,
    project: Path,
    state: Any,
    diagnostic_tickets: bool,
    ticket_queue: str,
    state_dir: Path,
    create_ticket: Any,
) -> WupHealthResult:
    command_service = WupCommandService()
    return command_service.evaluate_health(
        EvaluateWupHealthCommand(
            project=project,
            state=state,
            diagnostic_tickets=diagnostic_tickets,
            ticket_queue=ticket_queue,
            state_dir=state_dir,
            create_diagnostic_ticket=create_ticket,
        ),
    )


def run_idle_diagnostics(
    *,
    stdio_info: Any,
    is_topology_enabled: Any,
    run_command: Any,
    clear_marker: Any,
    create_ticket: Any,
    make_result: Any,
    stdio_format: str = "human",
    project: Path,
    profile: str,
    cycle: int,
    queue_status: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path,
    topology_integration: bool,
) -> Any:
    profile = profile.lower()
    if profile in {"off", "none"}:
        stdio_info(
            f"koru autonomous: idle diagnostics disabled (profile={profile})",
            fmt=stdio_format,
        )
        return make_result("off", [])
    if not is_topology_enabled(
        project,
        "idle-diagnostics",
        fallback=True,
        enabled=topology_integration,
    ):
        stdio_info("koru autonomous: idle diagnostics disabled in topology", fmt=stdio_format)
        return make_result("disabled(topology)", [])
    stdio_info(
        f"koru autonomous: queue idle -> running semcod diagnostics (profile={profile})",
        fmt=stdio_format,
    )
    checks = build_idle_checks(project, profile)
    return run_idle_check_loop(
        checks=checks,
        stdio_info=stdio_info,
        is_topology_enabled=is_topology_enabled,
        run_command=run_command,
        clear_marker=clear_marker,
        create_ticket=create_ticket,
        make_result=make_result,
        stdio_format=stdio_format,
        project=project,
        cycle=cycle,
        queue_status=queue_status,
        diagnostic_tickets=diagnostic_tickets,
        diagnostic_ticket_queue=diagnostic_ticket_queue,
        diagnostic_ticket_priority=diagnostic_ticket_priority,
        diagnostic_state_dir=diagnostic_state_dir,
        topology_integration=topology_integration,
    )
