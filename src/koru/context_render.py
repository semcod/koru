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
    lines: list[str] = []
    project_env = env.get("project") or {}
    markers = project_env.get("markers") or {}
    recommended = env.get("recommended_agent") or {}

    lines.append("## Detected environment")
    lines.append("")
    lines.append(f"- **project**: `{project_env.get('name') or Path(project).name}`")
    lines.append(f"- **cwd**: `{project_env.get('cwd') or project}`")
    lines.append(f"- **python**: `{project_env.get('python', '?')}`")
    koru_runtime = project_env.get("koru") or {}
    koru_version = koru_runtime.get("version") or "unknown"
    koru_executable = koru_runtime.get("executable")
    koru_details = f" (`{koru_executable}`)" if koru_executable else ""
    lines.append(f"- **koru**: `{koru_version}`{koru_details}")
    enabled_markers = [key for key, value in markers.items() if value]
    markers_text = ", ".join(f"`{marker}`" for marker in enabled_markers)
    lines.append(f"- **markers**: {markers_text if markers_text else '`none`'}")
    if recommended:
        lines.append(f"- **recommended agent**: `{recommended.get('label')}`")
    lines.append("")
    return lines


def render_agent_lanes(agents: list[dict[str, Any]]) -> list[str]:
    """Render the available LLM/IDE lanes section."""
    lines = ["## Available LLM/IDE lanes", ""]
    if agents:
        lines.append("| lane | available | launchable | note |")
        lines.append("| --- | --- | --- | --- |")
        for agent in agents:
            lines.append(
                f"| `{agent.get('id')}` | `{agent.get('available')}` | "
                f"`{agent.get('launchable')}` | {agent.get('reason', '')} |",
            )
    else:
        lines.append(
            "No known LLM/IDE lanes detected. Paste this handoff into your preferred agent.",
        )
    lines.append("")
    lines.append(
        "Coverage note: koru only orchestrates lanes shown above (plus planfile/scan/queue). "
        "Other AI tools can still be used manually, but are not auto-driven by koru unless "
        "wrapped as shell/api/llm tickets.",
    )
    lines.append("")
    return lines


def render_autonomous_mode(*, planfile_initialised: bool) -> list[str]:
    """Render autonomous-mode instructions for LLM operators."""
    lines = [
        "## Autonomous mode (one-command)",
        "",
    ]
    if not planfile_initialised:
        lines.extend(
            [
                "Project is not initialized yet. Use one command:",
                "",
                "```bash",
                "koru autonomous up --project . --max-cycles 1 --sleep-seconds 0 --no-autopilot",
                "```",
                "",
                "This bootstraps `.planfile/` first, then runs one safe queue cycle.",
                "",
            ],
        )
        return lines

    lines.extend(
        [
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
        ],
    )
    return lines


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
    lines: list[str] = []
    if not semcod_tools:
        return lines

    installed = [t for t in semcod_tools if t.get("available")]
    missing = [t for t in semcod_tools if not t.get("available")]
    lines.append("## Available semcod tools")
    lines.append("")
    if installed:
        lines.append("| tool | via | role | command |")
        lines.append("| --- | --- | --- | --- |")
        for tool in installed:
            cfg = " (configured)" if tool.get("config_present") else ""
            lines.append(
                f"| `{tool.get('id')}` | `{tool.get('via')}`{cfg} | "
                f"{tool.get('role', '')} | `{tool.get('command_hint', '')}` |",
            )
    else:
        lines.append("_No semcod tools detected on this machine._")
    if missing:
        lines.append("")
        missing_ids = ", ".join(f"`{t.get('id')}`" for t in missing)
        lines.append(
            f"_Not installed: {missing_ids}. Install with `pip install <name>` "
            "or skip — koru will not invoke them automatically._",
        )
    lines.append("")
    return lines


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
    lines: list[str] = []
    tid = ticket.get("id", "?")
    name = ticket.get("name", "")
    executor = (ticket.get("executor") or {}).get("kind", "?")
    lines.append(f"## Active ticket: `{tid}` — {name}")
    lines.append("")
    lines.append(f"- **executor**: `{executor}`")
    lines.append(f"- **status**: `{ticket.get('status', '?')}`")
    files = ticket.get("files") or []
    if files:
        lines.append(f"- **files in scope**: {', '.join(f'`{f}`' for f in files)}")
    prompt = (ticket.get("inputs") or {}).get("prompt")
    if prompt:
        lines.append("")
        lines.append("### Prompt")
        lines.append("")
        lines.append(f"> {str(prompt).replace(chr(10), chr(10)+'> ')}")
    lines.append("")
    return lines


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

    lines = [
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
    ]
    missing = [name for name, present in gate_markers.items() if not present]
    if missing:
        lines.append(
            f"_Not yet configured: {', '.join(f'`{m}`' for m in missing)}. "
            "Bootstrap any of them with `task template:install:wup` "
            "(in koru) or follow `workflows/on-change-gates.md`._",
        )
        lines.append("")
    return lines


def render_project_pipeline(pipeline: dict[str, Any] | None) -> list[str]:
    if not pipeline:
        return []
    lines = [
        "## Project pipeline (`koru.yaml`)",
        "",
        f"Root file: `{pipeline.get('path', 'koru.yaml')}` "
        f"(schema `{pipeline.get('schema', '?')}`).",
        "",
    ]
    prof = pipeline.get("extends_profile")
    if prof:
        lines.append(f"Profile reference: `{prof}`")
        lines.append("")
    for ph in pipeline.get("phases") or []:
        pid = ph.get("id", "?")
        desc = (ph.get("description") or "").strip()
        if desc:
            lines.append(f"### `{pid}` — {desc}")
        else:
            lines.append(f"### `{pid}`")
        lines.append("")
        for cmd in ph.get("commands") or []:
            lines.append(f"- `{cmd}`")
        lines.append("")
    lines.append("_This section is advisory — koru does not execute these commands automatically._")
    lines.append("")
    return lines


def render_policy(policy: dict[str, Any]) -> list[str]:
    """Render the policy section."""
    lines = [
        "## Policy (you MUST obey)",
        "",
        "| gate | value |",
        "| --- | --- |",
    ]
    for k in (
        "allow_commit",
        "allow_push",
        "allow_branch_create",
        "allow_branch_switch",
        "allow_tag",
        "allow_destructive_shell",
        "require_planfile_lifecycle",
        "require_ci_pass_before_complete",
    ):
        lines.append(f"| `{k}` | `{policy.get(k)}` |")
    if policy.get("ci_command"):
        lines.append(f"| `ci_command` | `{policy['ci_command']}` |")
    lines.append("")
    return lines


def render_rules(instructions: list[str]) -> list[str]:
    """Render the rules section."""
    lines = ["## Rules", ""]
    for rule in instructions:
        lines.append(f"- {rule}")
    lines.append("")
    return lines


def render_self_service(self_service: dict[str, Any]) -> list[str]:
    """Render the self-service commands section."""
    lines = [
        "## Self-service commands",
        "",
    ]
    for k, v in self_service.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append('- **add_nl_task**: `koru task "Describe the next change"`')
    lines.append("- **agent_prompt**: `koru agent`")
    lines.append("- **launch_agent**: `koru agent --launch`")
    lines.append(
        "- **scan_repo**: `koru scan` (dry-run) / `koru scan --apply` "
        "(create tickets from pytest collect errors, TODO/FIXME, missing "
        "gates and semcod tools)",
    )
    lines.append("")
    return lines


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
    lines: list[str] = ["## Autonomy loop (koru autonomous)", ""]
    snap = autonomy_loop.get("last_run_snapshot")
    if isinstance(snap, dict) and snap:
        lines.append("_Last completed cycle (`.planfile/.koru/autonomy-telemetry.json`):_")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(snap, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    else:
        lines.append(
            "_No autonomy telemetry file yet — it appears after at least one "
            "`koru autonomous up` cycle._",
        )
        lines.append("")
    hints = autonomy_loop.get("environment_hints") or {}
    if hints:
        lines.append("Relevant process environment (only non-empty keys):")
        for key in sorted(hints):
            lines.append(f"- `{key}`={hints[key]!r}")
        lines.append("")
    tf = autonomy_loop.get("telemetry_file")
    if tf:
        lines.append(f"Telemetry path: `{tf}`")
        lines.append("")
    return lines


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
    lines: list[str] = []
    parts = _handoff_render_parts(context)

    lines.extend(render_header(parts.project))
    lines.extend(render_environment(parts.environment, parts.project))
    lines.extend(render_autonomy_loop_brief(context))
    lines.extend(render_agent_lanes(parts.agents))
    lines.extend(render_semcod_tools(parts.semcod_tools))
    lines.extend(_render_ticket_scope(context, parts))
    lines.extend(render_autonomous_mode(planfile_initialised=parts.initialised))
    lines.extend(render_ai_tool_support_2026())

    lines.extend(render_project_pipeline(context.get("project_pipeline")))
    lines.extend(render_gates(parts.markers))
    lines.extend(render_policy(parts.policy))
    lines.extend(render_rules(context.get("instructions", [])))
    lines.extend(render_self_service(context.get("self_service") or {}))
    lines.extend(render_dashboard())

    return "\n".join(lines)
