"""Command-line entrypoint for koru."""
import argparse
import asyncio
import importlib.metadata
import json
import os
import shlex
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from koru.agents import detect_agent_options
from koru.autoloop_cli import autoloop_main
from koru.autonomous import autonomous_main, stop_prior_autonomous_for_auto_start
from koru.autonomous_runtime import project_venv_reexec_argv
from koru.autopilot.cli_command import autopilot_main
from koru.bootstrap import import_flat_pipeline
from koru.context import build_context, render_markdown_handoff
from koru.dev_sync import dev_main
from koru.doctor import detected_problems as doctor_detected_problems
from koru.doctor import problem_catalog as doctor_problem_catalog
from koru.doctor import render_problem_catalog_text
from koru.doctor import render_text as render_doctor_text
from koru.doctor import run_diagnostics
from koru.events import emit_management_event
from koru.gate import VALID_MODES as GATE_VALID_MODES
from koru.gate import authorize_gate
from koru.gc import DEFAULT_KEEP_LAST, DEFAULT_MAX_AGE_DAYS, GC_STATUSES, run_gc
from koru.git_cli import git_main
from koru.init import init_project, refresh_init_agent_lane
from koru.loop import discover_repositories, run_closed_loop
from koru.queue import default_human_prompt as _queue_default_human_prompt
from koru.queue import run_api_request as _queue_run_api_request
from koru.queue import run_llm_request as _queue_run_llm_request
from koru.queue import run_process as _queue_run_process
from koru.queue import run_shell_command as _queue_run_shell_command
from koru.queue_clean import CleanupReport, clean_queue
from koru.scan import ScanResult, run_scan
from koru.cli_scan import scan_main as _scan_main
from koru.cli_gate import gate_main as _gate_main
from koru.cli_gc import gc_main as _gc_main
from koru.cli_queue import queue_main as _queue_main
from koru.cli_topology import topology_main as _topology_main
from koru.cli_init import init_main as _init_main, init_agent_lane_main as _init_agent_lane_main
from koru.cli_doctor import doctor_main as _doctor_main
from koru.cli_watch import watch_main as _watch_main
from koru.serve import DEFAULT_HOST, DEFAULT_PORT
from koru.tasks import create_nl_task
from koru.tools import build_tool_task_scaffold, detect_tools, find_tool_entry, load_tool_registry, render_tools_detect_text
from koru.watch import watch_planfile_events

def _env_truthy(name: str) -> bool:
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes', 'on')

def _command_value(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError('Command cannot be empty')
    return stripped

def _cli_version() -> str:
    try:
        return importlib.metadata.version('koru')
    except importlib.metadata.PackageNotFoundError:
        return 'unknown'

def _add_workspace_loop_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--workspace', type=Path, default=Path.cwd(), help='Workspace root.')
    parser.add_argument('--include', default='semcod/*', help='Glob (relative to workspace) selecting repositories.')
    parser.add_argument('--max-rounds', type=int, default=3, help='Maximum retries for repositories that fail.')
    parser.add_argument('--command', type=_command_value, help="Command to execute in each repository, e.g. 'python -m pytest -q'.")


def _add_queue_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--queue', action='store_true', help='Run one task from the local planfile queue instead of repository loop mode.')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Project root for --queue mode.')
    parser.add_argument('--actor', default='koru-shell', help='Actor name used when claiming planfile queue tickets.')
    parser.add_argument('--queue-name', default=None, help='Only execute tickets from this planfile execution queue.')
    parser.add_argument('--dry-run', action='store_true', help='Preview the selected planfile queue task without executing it.')
    parser.add_argument('--interactive', action='store_true', help="When the next ticket is a 'human' executor, prompt for the answer on stdin (multi-line, Ctrl-D submits, Ctrl-C cancels). On submit, the ticket is claimed/started/completed with the answer recorded in --note and --result-json.")
    parser.add_argument('--loop', action='store_true', help='Drain the planfile queue: keep fetching and running the next ticket until the queue is idle, a ticket needs human input we cannot satisfy, or --max-iterations is reached. Combine with --interactive to also handle human tickets in the same run.')
    parser.add_argument('--max-iterations', type=int, default=100, help='Safety cap on the number of tickets --loop will process (default 100).')


def _add_init_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--watch', action='store_true', help='Watch planfile WebSocket events.')
    parser.add_argument('--ws-url', default='ws://localhost:8000/ws', help='Planfile WebSocket URL for --watch mode.')
    parser.add_argument('--max-events', type=int, default=None, help='Stop --watch after this many events, useful for smoke tests.')
    parser.add_argument('--skip-host-environment', action='store_true', help='With --init or --init-agent-lane: skip writing .planfile/.koru/host-environment.{json,md} (desktop + injector probe). Use in CI or minimal sandboxes.')
    parser.add_argument('--bootstrap', action='store_true', help='Import a flat-format pipeline YAML into .planfile/ for queue-mode execution.')
    parser.add_argument('--from', dest='from_file', type=Path, default=None, help='Source flat-pipeline YAML for --bootstrap (e.g. examples/bootstrap.planfile.yaml).')
    parser.add_argument('--sprint', default='current', help='Target sprint name when --bootstrap writes .planfile/sprints/<sprint>.yaml.')
    parser.add_argument('--force', action='store_true', help='Overwrite an existing sprint file during --bootstrap.')
    parser.add_argument('--agent-lane', default='auto', metavar='LANE', help='With --init or --init-agent-lane: write .planfile/.koru/shell-env.sh and run-autonomous.sh for that lane. Use auto (default) to pick cursor or windsurf from project dotdirs, else local; use none/off to skip or remove helpers.')
    parser.add_argument('--init', action='store_true', help='Initialise a koru-managed project in --project: import a flat pipeline (or generate a 2-ticket starter scaffold), write .planfile/.koru/policy.yaml stub, add .planfile/.koru/ to .gitignore, and (unless --agent-lane none) emit shell-env.sh + run-autonomous.sh, and write a host-environment snapshot (host-environment.json + .md) for autopilot setup. Pass --from <yaml> to import an existing pipeline; --force to re-init.')
    parser.add_argument('--init-agent-lane', action='store_true', dest='init_agent_lane', help='On a project that already has .planfile/config.yaml, only write or remove shell-env.sh and run-autonomous.sh per --agent-lane. Does not touch sprint, policy, or pipelines. Use when `koru --init` refuses without --force.')
    parser.add_argument('--doctor', action='store_true', help='Run diagnostic checks against --project (planfile config, sprints, policy.yaml, .gitignore, planfile binary, CI command). Exits 1 if any check fails; warnings alone exit 0. Use --format json for machine-readable output.')


def _add_diagnostics_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--fix', action='store_true', help='With --doctor, include guided auto-repair commands. The top-level doctor still does not mutate the project by itself.')
    parser.add_argument('--catalog', action='store_true', help='With --doctor, include a catalog of known problems and their detection rules.')
    parser.add_argument('--context', action='store_true', help='Emit a self-service brief (ticket + policy + constraints + command vocabulary) for an LLM agent. The brief is the only thing an autonomous agent should need to act safely.')
    parser.add_argument('--ticket', default=None, help='Target a specific ticket id (e.g. PLF-074) for --context. Default is the next runnable ticket from the queue.')
    parser.add_argument('--format', dest='output_format', choices=['json', 'markdown', 'text'], default='json', help='Output format for --context (default: json).')
    parser.add_argument('--include-fixtures', dest='include_fixtures', action='store_true', default=None, help="Include test/dryrun fixture tickets (labels test-only, dryrun, synthetic, auto-close) in --context. Default is to skip them so the agent isn't pointed at planfile/koru self-test artifacts. Also controlled via the KORU_INCLUDE_FIXTURES env var.")
    parser.add_argument('--no-include-fixtures', dest='include_fixtures', action='store_false', help='Explicitly hide fixtures (overrides KORU_INCLUDE_FIXTURES env).')
    parser.add_argument('--no-log', action='store_true', help='Disable the per-run JSONL log under .planfile/.koru/runs/. Has no effect outside --queue mode.')


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run closed-loop automation on semcod repositories.')
    parser.add_argument('--version', action='version', version=f'koru {_cli_version()}')
    _add_workspace_loop_args(parser)
    _add_queue_args(parser)
    _add_init_args(parser)
    _add_diagnostics_context_args(parser)
    return parser

def _build_tools_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='koru tools', description='Inspect AI tool registry/detection status.')
    sub = parser.add_subparsers(dest='subcommand', required=True)
    detect = sub.add_parser('detect', help='Detect tools from the 2026 registry.')
    detect.add_argument('--project', type=Path, default=Path.cwd(), help='Project root.')
    detect.add_argument('--registry', type=Path, default=None, help='Override registry YAML path (default: docs/ai-tool-registry-2026.yaml).')
    detect.add_argument('--format', dest='output_format', choices=('text', 'json'), default='text', help='Output format (default: text).')
    return parser

def _tools_main(argv: list[str]) -> int:
    tools_args = _build_tools_parser().parse_args(argv)
    if tools_args.subcommand != 'detect':
        print(f'koru tools: unknown subcommand {tools_args.subcommand!r}', file=sys.stderr)
        return 2
    registry, registry_path = load_tool_registry(tools_args.registry)
    results = detect_tools(tools_args.project.resolve(), registry)
    if tools_args.output_format == 'json':
        payload = {'project': str(tools_args.project), 'registry': str(registry_path) if registry_path else None, 'tools': results}
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_tools_detect_text(results, registry_path=registry_path))
    emit_management_event(tool='koru.tools.detect', action='completed', status='completed', message=f'tools={len(results)}', details={'project': str(tools_args.project), 'registry': str(registry_path) if registry_path else None, 'available': sum((1 for r in results if r.get('available')))})
    return 0

def _build_task_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='koru task', description='Create a planfile ticket from a natural-language sentence.')
    parser.add_argument('text', nargs='+', help='Natural-language task description.')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Project root.')
    parser.add_argument('--sprint', default='current', help='Target planfile sprint.')
    parser.add_argument('--queue-name', default=None, help='Execution queue for the new ticket.')
    parser.add_argument('--priority', default='normal', help='Ticket priority.')
    parser.add_argument('--source-tool', default=None, help='Producer id stored in ticket source.tool (for plugin/tool intake).')
    parser.add_argument('--source-signal', default=None, help='Producer signal stored in source.context.signal.')
    parser.add_argument('--dedupe-key', default=None, help='Stable issue key shared by producers; an existing ticket with the same key is reused instead of creating a duplicate.')
    parser.add_argument('--files', action='append', default=[], help='File path associated with the ticket. Repeat for multiple files.')
    parser.add_argument('--tool', dest='tool_id', default=None, help='Build a tool-adapter scaffold ticket for this tool id (from docs/ai-tool-registry-2026.yaml).')
    parser.add_argument('--tool-kind', dest='tool_kind', choices=('human', 'shell', 'api', 'llm'), default=None, help='Override scaffolded executor hint for --tool.')
    parser.add_argument('--tool-registry', dest='tool_registry', type=Path, default=None, help='Override tool registry path for --tool lookup.')
    return parser

def _build_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='koru serve', description='Run a local dashboard for koru (live LLM brief, ticket, policy, agent lanes). Binds to 127.0.0.1 by default.')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Project root.')
    parser.add_argument('--queue-name', default=None, help='Queue used when selecting the active ticket.')
    parser.add_argument('--host', default=DEFAULT_HOST, help=f'Bind address (default {DEFAULT_HOST}).')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'TCP port to listen on (default {DEFAULT_PORT}).')
    parser.add_argument('--auto-port', action='store_true', help='If the port is busy, try the next ports (then an ephemeral port). Also on when KORU_SERVE_AUTO_PORT is 1/true/yes.')
    open_group = parser.add_mutually_exclusive_group()
    open_group.add_argument('--open', dest='open_browser', action='store_true', default=True, help='Open the dashboard URL in the default browser (default).')
    open_group.add_argument('--no-open', dest='open_browser', action='store_false', help='Do not open a browser tab; just start the server.')
    return parser

def _build_local_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='koru local-serve', description='Minimal localhost JSON/NDJSON hub for scripts and HTTP clients (see docs/local-service.md).')
    parser.add_argument('--host', default=None, help='Bind address (default: KORU_LOCAL_SERVICE_HOST or 127.0.0.1).')
    parser.add_argument('--port', type=int, default=None, help='TCP port (default: KORU_LOCAL_SERVICE_PORT or 18766). Use 0 for an ephemeral OS-assigned port.')
    parser.add_argument('--max-events', type=int, default=None, help='Ring buffer size (default: KORU_LOCAL_SERVICE_MAX_EVENTS or 256).')
    return parser

def _build_agent_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='koru agent', description='Print or launch the best available LLM/IDE handoff for this project.')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Project root.')
    parser.add_argument('--queue-name', default=None, help='Queue used when selecting the active ticket.')
    parser.add_argument('--ticket', default=None, help='Render prompt for a specific ticket id.')
    parser.add_argument('--agent', dest='agent_id', default=None, help='Agent id to select.')
    parser.add_argument('--launch', action='store_true', help='Launch the selected agent if it has a CLI.')
    parser.add_argument('--list', action='store_true', help='List detected agents and exit.')
    parser.add_argument('--format', dest='output_format', choices=('text', 'json'), default='text', help='With --list: machine-readable json (default: text).')
    parser.add_argument('--lane', dest='lane_id', default=None, help='Agent lane id for --env-exports / --env-json (e.g. cursor, windsurf, claude-code). Falls back to --agent when set.')
    parser.add_argument('--env-exports', action='store_true', help='Print shell exports for KORU_AUTOPILOT_* / queue actor hints; requires --lane or --agent.')
    parser.add_argument('--env-json', action='store_true', help='Print recommended lane env as JSON (requires --lane or --agent).')
    return parser

def _load_tool_scaffold(tool_id: str, tool_registry: str | None, tool_kind: str | None) -> tuple[dict[str, Any] | None, Path | None, int | None]:
    """Load scaffold from tool registry. Returns (scaffold, registry_path, error_code)."""
    registry, registry_path = load_tool_registry(tool_registry)
    if not registry:
        print('koru task: tool registry is empty or missing. Use --tool-registry PATH or ensure docs/ai-tool-registry-2026.yaml exists.')
        return (None, None, 2)
    tool = find_tool_entry(registry, tool_id)
    if tool is None:
        known = ', '.join(sorted((str(t.get('id')) for t in registry if t.get('id'))))
        print(f"koru task: unknown --tool '{tool_id}'. Known ids: {known}")
        return (None, None, 2)
    scaffold = build_tool_task_scaffold(tool, adapter_kind=tool_kind)
    if registry_path is not None:
        scaffold.setdefault('source_context', {})
        if isinstance(scaffold.get('source_context'), dict):
            scaffold['source_context']['registry'] = str(registry_path)
    return (scaffold, registry_path, None)

def _merge_cli_scaffold(scaffold: dict[str, Any] | None, *, source_tool: str | None, source_signal: str | None, dedupe_key: str | None, files: list[str] | None) -> dict[str, Any] | None:
    if not (source_tool or source_signal or dedupe_key or files):
        return scaffold
    scaffold = dict(scaffold or {})
    if source_tool:
        scaffold['source_tool'] = source_tool
    context = dict(scaffold.get('source_context')) if isinstance(scaffold.get('source_context'), dict) else {}
    if source_signal:
        context['signal'] = source_signal
    if dedupe_key:
        context['dedupe_key'] = dedupe_key
    scaffold['source_context'] = context
    if files:
        scaffold['files'] = list(files)
    return scaffold

def _print_task_result(created: object, task_args: Any) -> None:
    action = 'reused' if getattr(created, 'reused', False) else 'created'
    print(f'koru task: ✓ {action} {created.ticket_id} in {created.path}')
    print(f'  name:  {created.name}')
    print(f"  queue: {task_args.queue_name or 'default'}")
    if task_args.tool_id:
        print(f'  tool:  {task_args.tool_id}')
        print('  note: scaffold ticket created — fill concrete executor inputs before queue run')
    print('Next: run `koru` to get the LLM prompt, or `koru --queue` to execute one task.')
    emit_management_event(tool='koru.task', action='created', status='completed', message=created.name, queue=task_args.queue_name, details={'ticket_id': created.ticket_id, 'project': str(task_args.project), 'sprint': task_args.sprint, 'priority': task_args.priority})

def _task_main(argv: list[str]) -> int:
    task_args = _build_task_parser().parse_args(argv)
    scaffold: dict[str, Any] | None = None
    if task_args.tool_id:
        scaffold, _registry_path, error_code = _load_tool_scaffold(task_args.tool_id, task_args.tool_registry, task_args.tool_kind)
        if error_code is not None:
            return error_code
    scaffold = _merge_cli_scaffold(scaffold, source_tool=task_args.source_tool, source_signal=task_args.source_signal, dedupe_key=task_args.dedupe_key, files=task_args.files)
    try:
        created = create_nl_task(task_args.project, ' '.join(task_args.text), sprint=task_args.sprint, queue_name=task_args.queue_name, priority=task_args.priority, scaffold=scaffold)
    except ValueError as exc:
        print(f'koru task: {exc}')
        return 2
    _print_task_result(created, task_args)
    return 0

def _serve_main(argv: list[str]) -> int:
    from koruapi.dashboard import dashboard_main
    return dashboard_main(argv)

def _local_serve_main(argv: list[str]) -> int:
    from koruapi.local import local_main
    return local_main(argv)

def _agent_main(argv: list[str]) -> int:
    from koru.agent_cli_helpers import print_agent_list, run_agent_handoff, try_agent_env_exports
    agent_args = _build_agent_parser().parse_args(argv)
    project = agent_args.project.resolve()
    env_code = try_agent_env_exports(agent_args)
    if env_code is not None:
        return env_code
    if agent_args.list:
        print_agent_list(agent_args, detect_agent_options(project))
        return 0
    return run_agent_handoff(project, agent_args)

def _is_bare_invocation(cli_namespace: argparse.Namespace) -> bool:
    """True when the user typed only ``koru`` (or ``koru --project P``).

    Bare = no action flag (init/bootstrap/context/queue/watch) and no
    ``--command``. We route this to the markdown brief — the friendliest
    starting point for both humans and LLM agents.
    """
    return not (
        cli_namespace.init
        or cli_namespace.init_agent_lane
        or cli_namespace.doctor
        or cli_namespace.bootstrap
        or cli_namespace.context
        or cli_namespace.queue
        or cli_namespace.watch
        or cli_namespace.command
    )

def _build_runtime_context_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='koru runtime-context', description='Show the current project runtime context: systems, libraries, algorithms, APIs, applications, pipelines, and topology.')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Project root.')
    parser.add_argument('--format', dest='output_format', choices=('json', 'text'), default='json', help='Output format (default json).')
    return parser

def _render_runtime_context_text(context: dict[str, Any]) -> str:
    summary = context.get('summary') or {}
    lines = [f"koru runtime-context: {summary.get('project') or context.get('project_root')}", f"  version: {summary.get('version') or '-'}", f"  services: {summary.get('services', 0)}", f"  workspaces: {summary.get('workspaces', 0)}", f"  pipelines: {summary.get('pipelines', 0)}", f"  topology nodes: {summary.get('topology_nodes', 0)}", '', 'Systems:']
    for service in context.get('systems') or []:
        ports = ', '.join(service.get('ports') or []) or '-'
        files = ', '.join(service.get('compose_files') or []) or '-'
        lines.append(f"  {service.get('name')}: ports={ports} compose={files}")
    lines.append('')
    lines.append('Pipelines:')
    for pipeline in context.get('pipelines') or []:
        mode = 'interactive' if pipeline.get('interactive') else 'batch'
        lines.append(f"  {pipeline.get('name')}: {mode} — {pipeline.get('description') or '-'}")
    return '\n'.join(lines)

def _runtime_context_main(argv: list[str]) -> int:
    runtime_args = _build_runtime_context_parser().parse_args(argv)
    try:
        from planfile.runtime_context import build_runtime_context
    except ImportError as exc:
        print('koru runtime-context: planfile.runtime_context is not available. Install/update semcod/planfile or add it to PYTHONPATH.', file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2
    context = build_runtime_context(runtime_args.project)
    if runtime_args.output_format == 'text':
        print(_render_runtime_context_text(context))
    else:
        print(json.dumps(context, indent=2, sort_keys=True, default=str))
    return 0

def _init_ci_main(_argv: list[str]) -> int:
    """Print where to copy the reference GitHub Actions workflow (Epic 2 thin CI)."""
    print('koru init-ci:\n  After copying the reference workflow, it should live at:\n    .github/workflows/koru-ci.yml\n  Upstream reference (semcod/koru):\n    https://github.com/semcod/koru/blob/main/.github/workflows/koru-ci.yml\n  How to adapt for your repo:\n    https://github.com/semcod/koru/blob/main/docs/ci-github.md\n  GitLab — example pipeline in this repo:\n    examples/ci/gitlab-ci.example.yml\n    https://github.com/semcod/koru/blob/main/examples/ci/gitlab-ci.example.yml\n  GitLab — how to adapt:\n    https://github.com/semcod/koru/blob/main/docs/ci-gitlab.md')
    return 0

def _mcp_serve_main(argv: list[str]) -> int:
    from koruapi.mcp import mcp_main
    return mcp_main(argv)

def _agent_backends_main(argv: list[str]) -> int:
    """List or describe IDE agent backend profiles (``agent_backends``)."""
    from dataclasses import asdict
    from koru.agent_backends import get_agent_backend_profile, iter_agent_backend_profiles
    parser = argparse.ArgumentParser(prog='koru agent-backends')
    parser.add_argument('--format', dest='output_format', choices=('text', 'json'), default='text')
    parser.add_argument('backend_id', nargs='?', default=None, metavar='BACKEND_ID', help='When set, print one profile; otherwise list every profile id.')
    backend_args = parser.parse_args(argv)
    if backend_args.backend_id:
        profile = get_agent_backend_profile(backend_args.backend_id)
        if profile is None:
            sys.stderr.write(f'koru agent-backends: unknown id {backend_args.backend_id!r}\n')
            sys.stderr.write('  run `koru agent-backends` for ids.\n')
            return 2
    else:
        profile = None
    if backend_args.output_format == 'json':
        if profile:
            print(json.dumps(asdict(profile), indent=2, sort_keys=True))
        else:
            print(json.dumps([asdict(p) for p in iter_agent_backend_profiles()], indent=2, sort_keys=True))
        return 0
    if profile:
        print(f'id                 {profile.id}')
        print(f'transport          {profile.transport}')
        print(f'can_push_chat      {profile.can_push_chat}')
        print(f'can_pull_chat_text {profile.can_pull_chat_text}')
        print(f'needs_gui_session  {profile.needs_gui_session}')
        print(f'mcp_tools_only     {profile.mcp_tools_only}')
        print(f'primary_code       {profile.primary_code}')
        return 0
    for p in iter_agent_backend_profiles():
        print(p.id)
    return 0

def _init_ide_main(argv: list[str]) -> int:
    from koru.mcp_provision import init_ide_main
    return init_ide_main(argv)

def _refactor_planfile_handoff_main(argv: list[str]) -> int:
    """CLI: ``koru refactor-planfile-handoff`` — markdown for IDE chat (planfile tickets)."""
    import argparse
    from koru.refactor_planfile_handoff import render_planfile_refactor_handoff
    p = argparse.ArgumentParser(prog='koru refactor-planfile-handoff', description='Print markdown instructions for attaching project/analysis.toon.yaml and drafting planfile refactor tickets in the IDE chat.')
    p.add_argument('--project', type=Path, default=Path.cwd(), help='Project root.')
    handoff_args = p.parse_args(argv)
    print(render_planfile_refactor_handoff(handoff_args.project), end='')
    return 0

def ide_router_main(argv: list[str]) -> int:
    """CLI: ``koru ide-router`` — print resolved IDE / headless routing."""
    import argparse
    import json
    from koru.ide_router import resolve_ide_route
    p = argparse.ArgumentParser(prog='koru ide-router')
    p.add_argument('--cli-ide', default='auto', help='Preview merge as if autonomous passed --autopilot-ide (default: auto).')
    p.add_argument('--format', choices=('text', 'json'), default='text', help='text lines (default) or json for scripts')
    router_args = p.parse_args(argv)
    route = resolve_ide_route(cli_autopilot_ide=router_args.cli_ide)
    payload = {'autopilot_ide': route.autopilot_ide, 'headless': route.headless, 'primary_surface': route.primary_surface, 'recommend_mcp': route.recommend_mcp, 'recommend_autopilot_drive': route.recommend_autopilot_drive, 'notes': route.notes}
    if router_args.format == 'json':
        print(json.dumps(payload, sort_keys=True))
    else:
        for key, val in payload.items():
            print(f'{key}: {val}')
    return 0

def _dsl_main(argv: list[str]) -> int:
    from korudsl.cli import main as dsl_main
    return dsl_main(argv)

def _api_main(argv: list[str]) -> int:
    from koruapi.cli import main as api_main
    return api_main(argv)

def _peek_project_from_argv(argv: list[str]) -> Path:
    for idx, part in enumerate(argv):
        if part == '--project' and idx + 1 < len(argv):
            return Path(argv[idx + 1]).expanduser().resolve()
        if part.startswith('--project='):
            return Path(part.split('=', 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()

def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True

def _project_cli_reexec_argv(project: Path) -> list[str] | None:
    """Return argv for re-execing generic CLI commands inside repo-local .venv."""
    if os.environ.get('KORU_CLI_REEXECED') or _env_truthy('KORU_CLI_NO_REEXEC'):
        return None
    local_venv = (project / '.venv').resolve()
    local_koru = local_venv / 'bin' / 'koru'
    if not (local_koru.is_file() and os.access(local_koru, os.X_OK)):
        return None
    executable = Path(sys.executable).expanduser()
    prefix = Path(sys.prefix).expanduser()
    if _path_is_relative_to(executable, local_venv) or _path_is_relative_to(prefix, local_venv):
        return None
    return [str(local_koru), *sys.argv[1:]]

def _maybe_print_project_venv_hint(raw_args: list[str]) -> None:
    """Print a deterministic hint to run the project-local CLI entrypoint."""
    if _env_truthy('KORU_SUPPRESS_VENV_HINT'):
        return
    project = _peek_project_from_argv(raw_args)
    local_koru = (project / '.venv' / 'bin' / 'koru').resolve()
    if not (local_koru.is_file() and os.access(local_koru, os.X_OK)):
        return
    command = ' '.join((shlex.quote(part) for part in [str(local_koru), *raw_args]))
    print('koru: hint: project-local CLI detected; if you hit unrecognized args, rerun:', file=sys.stderr)
    print(f'  {command}', file=sys.stderr)

def _should_suggest_wizard(argv: list[str], project: Path) -> bool:
    """Heuristic: only nudge brand-new users running ``koru auto`` with no args.

    We require: TTY stdin/stdout, no extra args, no ``.planfile`` in project,
    and no ``KORU_AUTO_SKIP_WIZARD`` env override.
    """
    if argv:
        return False
    if os.environ.get('KORU_AUTO_SKIP_WIZARD', '').strip().lower() in ('1', 'true', 'yes'):
        return False
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    return not (project / '.planfile').exists() and (not (project / '.koru').exists())

def _auto_main(argv: list[str]) -> int:
    """``koru auto``: stop prior autonomous/auto loops, then start with ``--replace-existing``.

    On a brand-new project (no ``.planfile``, interactive TTY, no args) we
    suggest running ``koru wizard`` first so the user can pick a strategy
    instead of blindly entering the autonomous loop with an empty backlog.
    """
    if any((arg in {'-h', '--help'} for arg in argv)):
        return autonomous_main(argv, invoked_as_auto=True)
    project = _peek_project_from_argv(argv)
    if _should_suggest_wizard(argv, project):
        print('koru auto: no .planfile detected — recommended first step is `koru wizard` to pick a strategy and seed the first ticket.', file=sys.stderr)
        if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
            print("  GUI: `koru wizard --gui` opens a browser wizard (requires pip install 'koru[api]').", file=sys.stderr)
        print('(skip with KORU_AUTO_SKIP_WIZARD=1 or run `koru auto --allow-duplicate`)', file=sys.stderr)
    if '--allow-duplicate' not in argv:
        stdio = os.environ.get('KORU_STDIO_FORMAT', 'human')
        stop_prior_autonomous_for_auto_start(project, stdio_format=stdio)
    if '--replace-existing' not in argv and '--allow-duplicate' not in argv:
        argv = ['--replace-existing', *argv]
    return autonomous_main(argv, invoked_as_auto=True)
_SUBCOMMANDS: dict[str, Callable[[list[str]], int]] = {'doctor': _doctor_subcommand_main, 'configure': lambda argv: __import__('koru.configurator', fromlist=['configure_main']).configure_main(argv), 'mesh': lambda argv: __import__('korumesh.cli', fromlist=['mesh_main']).mesh_main(argv), 'vision': lambda argv: __import__('koruvision.cli', fromlist=['vision_main']).vision_main(argv), 'observe': lambda argv: __import__('koruobserve.cli', fromlist=['observe_main']).observe_main(argv), 'init-ci': _init_ci_main, 'init-ide': _init_ide_main, 'agent-backends': _agent_backends_main, 'task': _task_main, 'agent': _agent_main, 'local-serve': _local_serve_main, 'serve': _serve_main, 'scan': _scan_main, 'refactor-planfile-handoff': _refactor_planfile_handoff_main, 'gate': _gate_main, 'queue': _queue_main, 'gc': _gc_main, 'git': git_main, 'tools': _tools_main, 'mcp-serve': _mcp_serve_main, 'ide-router': ide_router_main, 'autopilot': autopilot_main, 'autoloop': autoloop_main, 'autonomous': autonomous_main, 'auto': lambda argv: _auto_main(argv), 'wizard': lambda argv: __import__('koru.wizard.cli', fromlist=['wizard_main']).wizard_main(argv), 'dsl': _dsl_main, 'api': _api_main, 'topology': _topology_main, 'runtime-context': _runtime_context_main, 'dev': dev_main}

def _context_main(context_args: argparse.Namespace) -> int:
    ctx = build_context(project=context_args.project, ticket_id=context_args.ticket, queue_name=context_args.queue_name, include_fixtures=getattr(context_args, 'include_fixtures', None))
    if context_args.output_format == 'markdown':
        print(render_markdown_handoff(ctx))
    else:
        print(json.dumps(ctx, indent=2, sort_keys=True))
    return 0

def _bootstrap_main(bootstrap_args: argparse.Namespace) -> int:
    emit_management_event(tool='koru.bootstrap', action='started', status='running', message=str(bootstrap_args.from_file or ''), queue=bootstrap_args.queue_name, details={'project': str(bootstrap_args.project), 'sprint': bootstrap_args.sprint})
    if bootstrap_args.from_file is None:
        parser = _build_parser()
        parser.error('--bootstrap requires --from PATH')
    try:
        report = import_flat_pipeline(bootstrap_args.from_file, bootstrap_args.project, sprint=bootstrap_args.sprint, overwrite=bootstrap_args.force)
    except FileExistsError as exc:
        print(f'koru bootstrap: {exc}')
        emit_management_event(tool='koru.bootstrap', action='failed', status='failed', level='error', message=str(exc), queue=bootstrap_args.queue_name)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f'koru bootstrap: {exc}')
        emit_management_event(tool='koru.bootstrap', action='failed', status='failed', level='error', message=str(exc), queue=bootstrap_args.queue_name)
        return 2
    print('koru bootstrap: ✓ imported')
    print(report.summary())
    emit_management_event(tool='koru.bootstrap', action='completed', status='completed', message=report.summary(), queue=bootstrap_args.queue_name, details={'project': str(bootstrap_args.project), 'sprint': bootstrap_args.sprint})
    return 0

def _command_loop_main(loop_args: argparse.Namespace) -> int:
    emit_management_event(tool='koru.loop', action='started', status='running', message=loop_args.command, details={'workspace': str(loop_args.workspace), 'include': loop_args.include})
    repositories = discover_repositories(loop_args.workspace, loop_args.include)
    command = shlex.split(loop_args.command)
    report = run_closed_loop(command=command, repositories=repositories, max_rounds=loop_args.max_rounds)
    print(f'koru: repos={len(report.succeeded) + len(report.failed)} succeeded={len(report.succeeded)} failed={len(report.failed)} rounds={report.rounds_executed}')
    for repository in report.failed:
        print(f'FAILED: {repository}')
    exit_code = 0 if not report.failed else 1
    emit_management_event(tool='koru.loop', action='completed' if exit_code == 0 else 'failed', status='completed' if exit_code == 0 else 'failed', level='error' if exit_code else 'info', message=f'repos={len(report.succeeded) + len(report.failed)} succeeded={len(report.succeeded)} failed={len(report.failed)}', details={'failed': [str(item) for item in report.failed]})
    return exit_code

def _maybe_reexec_for_project_venv(raw_args: list[str]) -> None:
    subcommand = raw_args[0] if raw_args else ''
    if not raw_args:
        return
    project = _peek_project_from_argv(raw_args)
    if subcommand in {'auto', 'autonomous'}:
        if (reexec_argv := project_venv_reexec_argv(project)):
            env = dict(os.environ)
            env['KORU_AUTONOMOUS_REEXECED'] = '1'
            env['KORU_CLI_REEXECED'] = '1'
            print(f"koru: switching to project venv: {' '.join(reexec_argv)}", file=sys.stderr)
            os.execvpe(reexec_argv[0], reexec_argv, env)
        return
    if subcommand == 'doctor' or '--doctor' in raw_args:
        if (reexec_argv := _project_cli_reexec_argv(project)):
            env = dict(os.environ)
            env['KORU_CLI_REEXECED'] = '1'
            print(f"koru: switching to project venv CLI: {' '.join(reexec_argv)}", file=sys.stderr)
            os.execvpe(reexec_argv[0], reexec_argv, env)

def _dispatch_flag_action(cli_namespace: argparse.Namespace, raw_args: list[str]) -> int | None:
    if cli_namespace.doctor:
        return _doctor_main(cli_namespace, raw_args)
    if cli_namespace.init_agent_lane:
        return _init_agent_lane_main(cli_namespace)
    if cli_namespace.init:
        return _init_main(cli_namespace)
    if cli_namespace.context:
        return _context_main(cli_namespace)
    if cli_namespace.bootstrap:
        return _bootstrap_main(cli_namespace)
    if cli_namespace.watch:
        return _watch_main(cli_namespace)
    if cli_namespace.queue:
        return _queue_run_main(cli_namespace)
    return None

def main() -> int:
    raw_args = sys.argv[1:]
    _maybe_reexec_for_project_venv(raw_args)
    subcommand = raw_args[0] if raw_args else ''
    if subcommand in _SUBCOMMANDS:
        return _SUBCOMMANDS[subcommand](raw_args[1:])
    try:
        main_args = _build_parser().parse_args(raw_args)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 2 and ('doctor' in raw_args or '--doctor' in raw_args):
            _maybe_print_project_venv_hint(raw_args)
        return code
    if _is_bare_invocation(main_args):
        main_args.context = True
        main_args.output_format = 'markdown'
    if (rc := _dispatch_flag_action(main_args, raw_args)) is not None:
        return rc
    if not main_args.command:
        parser = _build_parser()
        parser.error('--command is required unless --queue is used')
    return _command_loop_main(main_args)
if __name__ == '__main__':
    raise SystemExit(main())
