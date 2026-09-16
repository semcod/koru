"""Multi-agent orchestration for ``koru auto N`` across projects and tasks."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class MultiAgentConfig:
    workers: int = 1
    workspace: Path = field(default_factory=Path.cwd)
    sync_github: bool = False
    client: str | None = None
    provider: str | None = None
    dry_run: bool = False
    max_tickets: int = 100
    timeout_per_ticket: float = 1800.0


@dataclass
class TaskItem:
    project: Path
    ticket_id: str
    title: str = ""
    status: str = "open"


@dataclass
class ActiveWorker:
    task: TaskItem
    process: subprocess.Popen[bytes]
    start_time: float


def parse_multi_agent_args(argv: list[str]) -> MultiAgentConfig:
    parser = argparse.ArgumentParser(
        prog="koru auto <N>",
        description="Run N concurrent autonomous agents across projects/tasks in a workspace.",
    )
    parser.add_argument(
        "workers_pos",
        nargs="?",
        type=int,
        default=None,
        help="Number of concurrent worker agents (e.g. 10).",
    )
    parser.add_argument(
        "--workers",
        "-n",
        "--concurrency",
        dest="workers_opt",
        type=int,
        default=None,
        help="Number of concurrent worker agents.",
    )
    parser.add_argument(
        "--workspace",
        "--org",
        type=Path,
        default=None,
        help="Parent directory containing projects (default: current working directory).",
    )
    parser.add_argument(
        "--sync",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Synchronize Planfile with GitHub issues before task dispatch.",
    )
    parser.add_argument(
        "--client",
        type=str,
        default=None,
        help="Shell client to drive (e.g. crush, claude-code, aider, codex).",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="API provider backend (e.g. z.ai, openrouter, anthropic, openai).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan and preview tasks and worker assignments without executing.",
    )
    parser.add_argument(
        "--max-tickets",
        type=int,
        default=100,
        help="Maximum total tickets to execute across all projects (default: 100).",
    )

    args = parser.parse_args(argv)
    workers = args.workers_pos or args.workers_opt or 1
    if workers < 1:
        parser.error("Workers count must be at least 1")

    workspace = (args.workspace or Path.cwd()).expanduser().resolve()
    return MultiAgentConfig(
        workers=workers,
        workspace=workspace,
        sync_github=bool(args.sync),
        client=args.client,
        provider=args.provider,
        dry_run=args.dry_run,
        max_tickets=args.max_tickets,
    )


def is_koru_project(path: Path) -> bool:
    """True if directory contains a Planfile, koru.yaml, or git repo."""
    if not path.is_dir() or path.name.startswith("."):
        return False
    return (
        (path / ".planfile").exists()
        or (path / "koru.yaml").exists()
        or (path / "project" / "new-ticket.sh").exists()
    )


def discover_workspace_projects(workspace: Path) -> list[Path]:
    """Find candidate projects under a workspace directory."""
    child_projects: list[Path] = []
    try:
        for child in sorted(workspace.iterdir()):
            if child.is_dir() and not child.name.startswith((".", "_")) and is_koru_project(child):
                child_projects.append(child)
    except OSError:
        pass

    if child_projects:
        return child_projects

    if is_koru_project(workspace):
        # Single project mode
        return [workspace]

    return []


def has_github_sync_config(project: Path) -> bool:
    planfile_dir = project / ".planfile"
    if not planfile_dir.is_dir():
        return False
    return any(
        (planfile_dir / name).exists()
        for name in (
            "github.planfile.yaml",
            "integrations.planfile.yaml",
            "sync/github.state.yaml",
            "integrations.oql.planfile.yaml",
        )
    )


def sync_github_planfile(project: Path, timeout: int = 60) -> bool:
    if not has_github_sync_config(project):
        return False
    py = os.environ.get("PY") or sys.executable
    print(f"🔄 [{project.name}] Synchronizing GitHub Issues with Planfile...", flush=True)
    try:
        res = subprocess.run(
            [py, "-m", "planfile.cli", "sync", "github", "--direction", "both"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if res.returncode == 0:
            print(f"✓ [{project.name}] GitHub sync complete", flush=True)
            return True
        return False
    except Exception as exc:
        print(f"[{project.name}] GitHub sync error: {exc}", file=sys.stderr)
        return False


def get_pending_tasks_for_project(project: Path) -> list[TaskItem]:
    """Retrieve actionable tickets from project's Planfile current sprint or tickets."""
    tasks: list[TaskItem] = []
    current_sprint = project / ".planfile" / "sprints" / "current.yaml"

    if yaml is not None and current_sprint.is_file():
        try:
            data = yaml.safe_load(current_sprint.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                raw_tickets = data.get("tickets", {})
                if isinstance(raw_tickets, dict):
                    for ticket_id, ticket_info in raw_tickets.items():
                        if isinstance(ticket_info, dict):
                            status = str(ticket_info.get("status", "open")).lower()
                            if status in {"open", "ready", "todo", "in_progress"}:
                                title = str(ticket_info.get("name") or ticket_info.get("title") or "")
                                tasks.append(
                                    TaskItem(
                                        project=project,
                                        ticket_id=ticket_id,
                                        title=title,
                                        status=status,
                                    )
                                )
        except Exception:
            pass

    return tasks


class MultiAgentOrchestrator:
    """Manages concurrent worker agents across projects and tasks."""

    def __init__(self, config: MultiAgentConfig) -> None:
        self.config = config
        self.active_workers: list[ActiveWorker] = []
        self._interrupted = False

    def setup_signals(self) -> None:
        def _handle_sig(sig: int, _frame: Any) -> None:
            self._interrupted = True
            print("\nkoru auto: interrupt signal received, stopping workers...", file=sys.stderr)
            self.terminate_all()

        try:
            signal.signal(signal.SIGINT, _handle_sig)
            signal.signal(signal.SIGTERM, _handle_sig)
        except (ValueError, AttributeError):
            pass

    def terminate_all(self) -> None:
        for worker in self.active_workers:
            try:
                if worker.process.poll() is None:
                    worker.process.terminate()
            except Exception:
                pass

    def build_worker_command(self, task: TaskItem) -> list[str]:
        koru_bin = sys.argv[0] if sys.argv and sys.argv[0].endswith("koru") else "koru"
        cmd = [
            koru_bin,
            "ticket",
            "auto",
            task.ticket_id,
            "--project",
            str(task.project),
        ]
        return cmd

    def build_worker_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.config.client:
            env["KORU_AUTOPILOT_IDE"] = self.config.client
            env["KORU_TILLM_CLIENT"] = self.config.client
        if self.config.provider:
            env["TILLM_PROVIDER"] = self.config.provider
        env["KORU_STDIO_FORMAT"] = env.get("KORU_STDIO_FORMAT", "human")
        return env

    def run(self) -> int:
        self.setup_signals()
        projects = discover_workspace_projects(self.config.workspace)
        if not projects:
            print(f"koru auto: no governed projects found in {self.config.workspace}", file=sys.stderr)
            return 1

        print(
            f"koru auto: discovered {len(projects)} project(s) in {self.config.workspace} "
            f"(concurrency={self.config.workers})"
        )

        # 1. Sync GitHub if requested
        if self.config.sync_github:
            if self.config.dry_run:
                print("koru auto: [dry-run] would synchronize GitHub issues with Planfile for configured projects.")
            else:
                from concurrent.futures import ThreadPoolExecutor

                sync_targets = [p for p in projects if has_github_sync_config(p)]
                if sync_targets:
                    print(f"koru auto: synchronizing GitHub issues across {len(sync_targets)} project(s)...")
                    with ThreadPoolExecutor(max_workers=min(len(sync_targets), 8)) as pool:
                        list(pool.map(sync_github_planfile, sync_targets))

        # 2. Collect pending tasks
        pending_queue: list[TaskItem] = []
        for proj in projects:
            tasks = get_pending_tasks_for_project(proj)
            pending_queue.extend(tasks)

        if not pending_queue:
            print("koru auto: no open Planfile tickets found across discovered projects.")
            return 0

        print(f"koru auto: {len(pending_queue)} actionable ticket(s) queued.")

        if self.config.dry_run:
            print("\n[Dry Run Plan]")
            for i, task in enumerate(pending_queue[: self.config.max_tickets], start=1):
                client_desc = f" (client: {self.config.client})" if self.config.client else ""
                print(f"  {i}. [{task.project.name}] {task.ticket_id}: {task.title}{client_desc}")
            return 0

        completed_count = 0
        failed_count = 0
        queue = pending_queue[: self.config.max_tickets]

        while (queue or self.active_workers) and not self._interrupted:
            # Poll existing workers
            still_active: list[ActiveWorker] = []
            for worker in self.active_workers:
                code = worker.process.poll()
                if code is None:
                    # Check timeout
                    if time.time() - worker.start_time > self.config.timeout_per_ticket:
                        print(
                            f"koru auto: worker [{worker.task.project.name} / {worker.task.ticket_id}] "
                            "timed out, terminating...",
                            file=sys.stderr,
                        )
                        worker.process.terminate()
                        failed_count += 1
                    else:
                        still_active.append(worker)
                else:
                    duration = time.time() - worker.start_time
                    if code == 0:
                        print(
                            f"✓ [{worker.task.project.name}] {worker.task.ticket_id} "
                            f"completed successfully in {duration:.1f}s"
                        )
                        completed_count += 1
                    else:
                        print(
                            f"✗ [{worker.task.project.name}] {worker.task.ticket_id} "
                            f"exited with error code {code} ({duration:.1f}s)",
                            file=sys.stderr,
                        )
                        failed_count += 1
            self.active_workers = still_active

            # Spawn new workers up to capacity
            # Keep safety invariant: at most one worker per project simultaneously
            active_project_paths = {w.task.project for w in self.active_workers}

            eligible_idx = None
            for idx, task in enumerate(queue):
                if task.project not in active_project_paths:
                    eligible_idx = idx
                    break

            if eligible_idx is not None and len(self.active_workers) < self.config.workers and not self._interrupted:
                task = queue.pop(eligible_idx)
                cmd = self.build_worker_command(task)
                env = self.build_worker_env()
                print(
                    f"▶ Spawning agent [{len(self.active_workers) + 1}/{self.config.workers}] "
                    f"for [{task.project.name}] {task.ticket_id}: {' '.join(cmd)}"
                )
                try:
                    proc = subprocess.Popen(cmd, cwd=str(task.project), env=env)
                    self.active_workers.append(
                        ActiveWorker(task=task, process=proc, start_time=time.time())
                    )
                except Exception as exc:
                    print(
                        f"koru auto: failed to start worker for [{task.project.name}] {task.ticket_id}: {exc}",
                        file=sys.stderr,
                    )
                    failed_count += 1
                continue

            time.sleep(0.5)

        print(
            f"\nkoru auto: run finished. Completed: {completed_count}, "
            f"Failed: {failed_count}, Remaining: {len(queue)}"
        )
        return 0 if failed_count == 0 else 1


def run_multi_agent_auto(argv: list[str]) -> int:
    """Entry point for ``koru auto <N>``."""
    config = parse_multi_agent_args(argv)
    orchestrator = MultiAgentOrchestrator(config)
    return orchestrator.run()
