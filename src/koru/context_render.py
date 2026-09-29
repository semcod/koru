"""Markdown rendering functions for koru context handoff."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def render_header(project: str) -> list[str]:
    """Render the header section of the markdown handoff."""
    return [
        f"# koru handoff — {project}",
        "",
        "## What koru is",
        "",
        "Koru is the project-local automation gate: it detects the repository "
        "context, exposes planfile tickets, gives the LLM exact operating rules, "
        "and keeps work traceable through ticket lifecycle events.",
        "",
    ]


def render_environment(env: dict[str, Any], project: str) -> list[str]:
    """Render the detected environment section."""
    project_env = env.get("project") or {}
    markers = project_env.get("markers") or {}
    recommended = env.get("recommended_agent") or {}

    koru_runtime = project_env.get("koru") or {}
    koru_version = koru_runtime.get("version") or "unknown"
    koru_executable = koru_runtime.get("executable")
    koru_details = f" (`{koru_executable}`)" if koru_executable else ""
    enabled_markers = [key for key, value in markers.items() if value]
    markers_text = ", ".join(f"`{marker}`" for marker in enabled_markers)
    return [
        "## Detected environment",
        "",
        f"- **project**: `{project_env.get('name') or Path(project).name}`",
        f"- **cwd**: `{project_env.get('cwd') or project}`",
        f"- **python**: `{project_env.get('python', '?')}`",
        f"- **koru**: `{koru_version}`{koru_details}",
        f"- **markers**: {markers_text if markers_text else '`none`'}",
        *([f"- **recommended agent**: `{recommended.get('label')}`"] if recommended else []),
        "",
    ]


def render_agent_lanes(agents: list[dict[str, Any]]) -> list[str]:
    """Render the available LLM/IDE lanes section."""
    rows = (
        [
            "| lane | available | launchable | note |",
            "| --- | --- | --- | --- |",
            *(
                f"| `{agent.get('id')}` | `{agent.get('available')}` | "
                f"`{agent.get('launchable')}` | {agent.get('reason', '')} |"
                for agent in agents
            ),
        ]
        if agents
        else [
            "No known LLM/IDE lanes detected. Paste this handoff into your preferred agent.",
        ]
    )
    return [
        "## Available LLM/IDE lanes",
        "",
        *rows,
        "",
        "Coverage note: koru only orchestrates lanes shown above (plus planfile/scan/queue). "
        "Other AI tools can still be used manually, but are not auto-driven by koru unless "
        "wrapped as shell/api/llm tickets.",
        "",
    ]


def render_autonomous_mode(*, planfile_initialised: bool) -> list[str]:
    """Render autonomous-mode instructions for LLM operators."""
    header = [
        "## Autonomous mode (one-command)",
        "",
    ]
    if not planfile_initialised:
        return [
            *header,
            "Project is not initialized yet. Use one command:",
            "",
            "```bash",
            "koru autonomous up --project . --max-cycles 1 --sleep-seconds 0 --no-autopilot",
            "```",
            "",
            "This bootstraps `.planfile/` first, then runs one safe queue cycle.",
            "",
        ]

    return [
        *header,
        "Use this when operator asks for unattended execution:",
        "",
        "```bash",
        "koru autonomous up --project .",
        "```",
        "",
        "Useful flags:",
        "- `--max-cycles 1 --sleep-seconds 0` for a smoke run",
        "- `--ticket-sources all` to include scan intake",
        "- `--no-autopilot` for queue/scan only",
        "- `--autopilot-ide auto|windsurf|jetbrains|cursor|vscode|zed`",
        "",
        "Multi-IDE / several chat panes on one machine:",
        "- Set a **distinct** `KORU_AUTOPILOT_INSTANCE` per IDE window (e.g. `cursor-a`,",
        "  `windsurf-b`) so each autopilot daemon gets its own Unix socket; or set",
        "  `KORU_AUTOPILOT_SOCKET` to an absolute path.",
        "- Queue drains for the same repo are **serialized** via "
        "`.planfile/.koru/queue-runner.lock` (POSIX); disable only if you accept races:",
        "  `KORU_QUEUE_RUNNER_LOCK=0`.",
        "- Use a **unique** `--actor` / `ACTOR` per automated lane so `ticket claim`",
        "  ownership is visible in planfile.",
        "",
    ]


def render_ai_tool_support_2026() -> list[str]:
    """Render a concise support matrix for popular 2026 AI coding tools."""
    return [
        "## AI tool support (2026)",
        "",
        "Koru does not need a bespoke hardcoded integration for every tool. "
        "It supports three modes:",
        "",
        "1. **native lane** — directly orchestrated by koru (`autopilot`, `agent`, `queue`).",
        "2. **adapter lane** — tool used via `planfile` executors (`shell` / `api` / `llm`).",
        "3. **manual lane** — no stable automation API yet; operator uses it directly.",
        "",
        "Current native GUI lane includes: `windsurf`, `vscode`, `cursor`, `jetbrains`, `zed`. "
        "Shell LLM clients such as `claude-code`, `aider`, and `codex` are delegated to `tillm`.",
        "",
        "For tools not listed as native (e.g. Gemini CLI, Cline, OpenCode, Qwen Code, "
        "Copilot/Tabnine plugins, app builders), use adapter lane first; promote to native "
        "only when reliability is proven.",
        "",
        "Roadmap: `docs/ai-tool-support-roadmap-2026.md`.",
        "",
    ]


def render_semcod_tools(semcod_tools: list[dict[str, Any]]) -> list[str]:
    """Render the available semcod tools section."""
    if not semcod_tools:
        return []

    installed = [t for t in semcod_tools if t.get("available")]
    missing = [t for t in semcod_tools if not t.get("available")]
    rows = (
        [
            "| tool | via | role | command |",
            "| --- | --- | --- | --- |",
            *(
                f"| `{tool.get('id')}` | `{tool.get('via')}`"
                f"{' (configured)' if tool.get('config_present') else ''} | "
                f"{tool.get('role', '')} | `{tool.get('command_hint', '')}` |"
                for tool in installed
            ),
        ]
        if installed
        else ["_No semcod tools detected on this machine._"]
    )
    missing_ids = ", ".join(f"`{t.get('id')}`" for t in missing)
    return [
        "## Available semcod tools",
        "",
        *rows,
        *(
            [
                "",
                f"_Not installed: {missing_ids}. Install with `pip install <name>` "
                "or skip — koru will not invoke them automatically._",
            ]
            if missing
            else []
        ),
        "",
    ]


def render_setup_required(project: str) -> list[str]:
    """Render the setup required section when planfile is not initialized."""
    return [
        "## ⚠ Setup required",
        "",
        "This project has no `.planfile/` directory yet, so there is "
        "no sprint to claim tickets from.",
        "",
        "Run **one** of these from the project root:",
        "",
        "```bash",
        "koru --init --project .                       # 2-ticket starter scaffold",
        "koru --init --project . --from pipeline.yaml  # import an existing flat pipeline",
        "```",
        "",
        "Then re-run `koru` to refresh this brief.",
        "",
    ]


def render_active_ticket(ticket: dict[str, Any]) -> list[str]:
    """Render the active ticket section."""
    tid = ticket.get("id", "?")
    name = ticket.get("name", "")
    executor = (ticket.get("executor") or {}).get("kind", "?")
    files = ticket.get("files") or []
    prompt = (ticket.get("inputs") or {}).get("prompt")
    return [
        f"## Active ticket: `{tid}` — {name}",
        "",
        f"- **executor**: `{executor}`",
        f"- **status**: `{ticket.get('status', '?')}`",
        *([f"- **files in scope**: {', '.join(f'`{f}`' for f in files)}"] if files else []),
        *(
            ["", "### Prompt", "", f"> {str(prompt).replace(chr(10), chr(10) + '> ')}"]
            if prompt
            else []
        ),
        "",
    ]


def _compact_ticket_error(ticket_error: str) -> str:
    text = " ".join(str(ticket_error or "").split())
    if not text:
        return "no ticket"
    if "Traceback" in text:
        return "planfile error (traceback hidden; run `planfile ticket next --format json`)"
    if len(text) > 160:
        return f"{text[:157].rstrip()}..."
    return text


def render_no_active_ticket(ticket_error: str) -> list[str]:
    """Render the no active ticket section."""
    compact_error = _compact_ticket_error(ticket_error)
    return [
        f"## No active ticket — {compact_error}",
        "",
        "### Immediate action (autopilot)",
        "",
        "Do not ask the operator what to do next. Start this flow immediately:",
        "",
        "```bash",
        "koru scan --apply",
        "planfile ticket next --format json",
        "planfile ticket start <id>",
        "```",
        "",
    ]


def render_gates(markers: dict[str, Any]) -> list[str]:
    """Render the on-change gates section."""
    gate_markers = {
        "wup": markers.get("wup_yaml", False),
        "regix": markers.get("regix_yaml", False),
        "testql": markers.get("testql_scenarios", False),
    }
    if not any(gate_markers.values()):
        return []

    missing = [name for name, present in gate_markers.items() if not present]
    return [
        "## On-change gates",
        "",
        "These packages run automatically (or on demand via "
        "`/koru-gate`) to detect regressions BEFORE you call "
        "`planfile ticket done <id>`. See "
        "`workflows/on-change-gates.md` for the full cycle.",
        "",
        "| gate | configured | role | command |",
        "| --- | --- | --- | --- |",
        f"| `wup` | `{gate_markers['wup']}` | "
        "intelligent file watcher (3-layer: detect → quick → full) | "
        "`wup watch` (daemon) / `wup status` |",
        f"| `regix` | `{gate_markers['regix']}` | "
        "regression metrics (CC / MI / coverage delta) | "
        "`regix gates` (absolute) / `regix compare` (delta) |",
        f"| `testql` | `{gate_markers['testql']}` | "
        "behavioural HTTP probes (TOON YAML scenarios) | "
        "`testql run <scenario>` |",
        "",
        *(
            [
                f"_Not yet configured: {', '.join(f'`{m}`' for m in missing)}. "
                "Bootstrap any of them with `task template:install:wup` "
                "(in koru) or follow `workflows/on-change-gates.md`._",
                "",
            ]
            if missing
            else []
        ),
    ]


def render_project_pipeline(pipeline: dict[str, Any] | None) -> list[str]:
    if not pipeline:
        return []
    prof = pipeline.get("extends_profile")
    phase_rows = [
        row
        for ph in pipeline.get("phases") or []
        for row in [
            (
                f"### `{ph.get('id', '?')}` — {(ph.get('description') or '').strip()}"
                if (ph.get("description") or "").strip()
                else f"### `{ph.get('id', '?')}`"
            ),
            "",
            *(f"- `{cmd}`" for cmd in ph.get("commands") or []),
            "",
        ]
    ]
    return [
        "## Project pipeline (`koru.yaml`)",
        "",
        f"Root file: `{pipeline.get('path', 'koru.yaml')}` "
        f"(schema `{pipeline.get('schema', '?')}`).",
        "",
        *([f"Profile reference: `{prof}`", ""] if prof else []),
        *phase_rows,
        "_This section is advisory — koru does not execute these commands automatically._",
        "",
    ]


def render_policy(policy: dict[str, Any]) -> list[str]:
    """Render the policy section."""
    return [
        "## Policy (you MUST obey)",
        "",
        "| gate | value |",
        "| --- | --- |",
        *(
            f"| `{k}` | `{policy.get(k)}` |"
            for k in (
                "allow_commit",
                "allow_push",
                "allow_branch_create",
                "allow_branch_switch",
                "allow_tag",
                "allow_destructive_shell",
                "require_planfile_lifecycle",
                "require_ci_pass_before_complete",
            )
        ),
        *([f"| `ci_command` | `{policy['ci_command']}` |"] if policy.get("ci_command") else []),
        "",
    ]


def render_rules(instructions: list[str]) -> list[str]:
    """Render the rules section."""
    return ["## Rules", "", *(f"- {rule}" for rule in instructions), ""]


def render_self_service(self_service: dict[str, Any]) -> list[str]:
    """Render the self-service commands section."""
    return [
        "## Self-service commands",
        "",
        *(f"- **{k}**: `{v}`" for k, v in self_service.items()),
        '- **add_nl_task**: `koru task "Describe the next change"`',
        "- **agent_prompt**: `koru agent`",
        "- **launch_agent**: `koru agent --launch`",
        "- **scan_repo**: `koru scan` (dry-run) / `koru scan --apply` "
        "(create tickets from pytest collect errors, TODO/FIXME, missing "
        "gates and semcod tools)",
        "",
    ]


def render_dashboard() -> list[str]:
    """Render the dashboard section."""
    return [
        "## Dashboard",
        "",
        "Uruchom lokalny dashboard koru z automatycznym otwarciem zakładki w przeglądarce:",
        "",
        "```bash",
        "koru serve                        # http://127.0.0.1:8765 + auto-open tab",
        "koru serve --port 9000            # custom port",
        "koru serve --no-open              # start server, don't open browser",
        "```",
        "",
        "Dashboard auto-odświeża co 5 s i pokazuje aktywny ticket, "
        "policy, agent lanes oraz on-change gates. Endpointy: "
        "`/api/context` (JSON), `/api/handoff` (markdown brief), "
        "`/health`.",
        "",
    ]


def _autonomy_loop_block(ctx: dict[str, Any]) -> dict[str, Any]:
    value = ctx.get("autonomy_loop") or {}
    return value if isinstance(value, dict) else {}


def render_autonomy_loop_brief(ctx: dict[str, Any]) -> list[str]:
    autonomy_loop = _autonomy_loop_block(ctx)
    snap = autonomy_loop.get("last_run_snapshot")
    snapshot_rows = (
        [
            "_Last completed cycle (`.planfile/.koru/autonomy-telemetry.json`):_",
            "",
            "```json",
            json.dumps(snap, indent=2, sort_keys=True),
            "```",
            "",
        ]
        if isinstance(snap, dict) and snap
        else [
            "_No autonomy telemetry file yet — it appears after at least one "
            "`koru autonomous up` cycle._",
            "",
        ]
    )
    hints = autonomy_loop.get("environment_hints") or {}
    tf = autonomy_loop.get("telemetry_file")
    return [
        "## Autonomy loop (koru autonomous)",
        "",
        *snapshot_rows,
        *(
            [
                "Relevant process environment (only non-empty keys):",
                *(f"- `{key}`={hints[key]!r}" for key in sorted(hints)),
                "",
            ]
            if hints
            else []
        ),
        *([f"Telemetry path: `{tf}`", ""] if tf else []),
    ]


@dataclass(frozen=True)
class _HandoffRenderParts:
    project: Any
    ticket: Any
    policy: dict[str, Any]
    environment: dict[str, Any]
    initialised: bool
    markers: dict[str, Any]
    agents: list[Any]
    semcod_tools: list[Any]


def _handoff_render_parts(context: dict[str, Any]) -> _HandoffRenderParts:
    env = context.get("environment") or {}
    project_env = env.get("project") or {}
    return _HandoffRenderParts(
        project=context.get("project", "?"),
        ticket=context.get("ticket"),
        policy=context.get("policy", {}),
        environment=env,
        initialised=bool(env.get("planfile_initialised")),
        markers=project_env.get("markers") or {},
        agents=env.get("llm_agents") or [],
        semcod_tools=env.get("semcod_tools") or [],
    )


def _render_ticket_scope(context: dict[str, Any], parts: _HandoffRenderParts) -> list[str]:
    if not parts.initialised:
        return render_setup_required(parts.project)
    if parts.ticket:
        return render_active_ticket(parts.ticket)
    ticket_error = context.get("ticket_error") or "no ticket"
    return render_no_active_ticket(ticket_error)


def render_markdown_handoff(context: dict[str, Any]) -> str:
    """Turn a context dict into a Markdown brief for the operator.

    Designed to be pasted into an IDE chat or TILLM shell-client prompt to onboard
    the LLM with the policy and ticket scope in one shot.
    """
    parts = _handoff_render_parts(context)
    sections = [
        render_header(parts.project),
        render_environment(parts.environment, parts.project),
        render_autonomy_loop_brief(context),
        render_agent_lanes(parts.agents),
        render_semcod_tools(parts.semcod_tools),
        _render_ticket_scope(context, parts),
        render_autonomous_mode(planfile_initialised=parts.initialised),
        render_ai_tool_support_2026(),
        render_project_pipeline(context.get("project_pipeline")),
        render_gates(parts.markers),
        render_policy(parts.policy),
        render_rules(context.get("instructions", [])),
        render_self_service(context.get("self_service") or {}),
        render_dashboard(),
    ]

    return "\n".join(line for section in sections for line in section)
