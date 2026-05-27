"""Catalog of koru integration surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IntegrationSpec:
    """One invokable integration exposed via :mod:`koruapi`."""

    id: str
    title: str
    description: str
    transport: str
    methods: tuple[str, ...] = ()
    cli_equivalent: str | None = None
    mcp_tool: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


INTEGRATIONS: tuple[IntegrationSpec, ...] = (
    IntegrationSpec(
        id="context.build",
        title="LLM context brief",
        description="Build JSON/markdown handoff for the active project and ticket.",
        transport="koru",
        methods=("build",),
        cli_equivalent="koru --context --project <dir>",
        tags=("planfile", "llm"),
    ),
    IntegrationSpec(
        id="doctor.run",
        title="Project doctor",
        description="Run koru --doctor diagnostics for the project.",
        transport="koru",
        methods=("run",),
        cli_equivalent="koru --doctor --project <dir>",
        tags=("health",),
    ),
    IntegrationSpec(
        id="scan.apply",
        title="Scan → planfile tickets",
        description="Collect repo signals and create planfile tickets.",
        transport="koru",
        methods=("apply", "dry_run"),
        cli_equivalent="koru scan --apply --project <dir>",
        tags=("planfile", "tickets"),
    ),
    IntegrationSpec(
        id="queue.loop",
        title="Planfile queue drain",
        description="Run one or more planfile queue iterations (shell/api/llm/human).",
        transport="koru",
        methods=("loop", "once"),
        cli_equivalent="koru --queue --loop --project <dir>",
        tags=("planfile", "queue"),
    ),
    IntegrationSpec(
        id="gate.regix",
        title="Regix quality gate",
        description="Run regix gate checks for the project.",
        transport="koru",
        methods=("run",),
        cli_equivalent="koru gate authorize --project <dir>",
        tags=("quality",),
    ),
    IntegrationSpec(
        id="autopilot.status",
        title="Autopilot daemon status",
        description="Connected IDE plugins and socket path.",
        transport="koruide",
        methods=("status",),
        cli_equivalent="koru autopilot status",
        tags=("ide", "autopilot"),
    ),
    IntegrationSpec(
        id="autopilot.drive",
        title="Autopilot chat drive",
        description="Inject prompt into IDE chat (plugin or OS injector fallback).",
        transport="koruide",
        methods=("drive",),
        cli_equivalent="koru autopilot drive --ide auto '<prompt>'",
        tags=("ide", "autopilot", "chat"),
    ),
    IntegrationSpec(
        id="ide.commands",
        title="IDE command catalog",
        description="Read the normalized IDE command/action catalog for LLM strategy planning.",
        transport="koruide",
        methods=("read", "llm"),
        cli_equivalent="koru ide commands --ide all --for-llm --format json",
        mcp_tool="koru_ide_command_catalog",
        tags=("ide", "llm", "commands"),
    ),
    IntegrationSpec(
        id="ide.scenario_schema",
        title="IDE command scenario schema",
        description="Read JSON Schema for LLM-authored IDE command scenarios.",
        transport="koruide",
        methods=("read",),
        cli_equivalent="koru ide scenario-schema",
        mcp_tool="koru_ide_command_scenario_schema",
        tags=("ide", "llm", "schema"),
    ),
    IntegrationSpec(
        id="ide.scenario_validate",
        title="IDE command scenario validation",
        description="Validate an LLM-authored IDE command scenario against the Koru catalog.",
        transport="koruide",
        methods=("validate",),
        cli_equivalent="koru ide scenario-validate scenario.yaml",
        mcp_tool="koru_validate_ide_command_scenario",
        tags=("ide", "llm", "schema"),
    ),
    IntegrationSpec(
        id="autonomous.up",
        title="Autonomous loop",
        description="Scan → queue → autopilot outer loop (long-running).",
        transport="koru",
        methods=("start",),
        cli_equivalent="koru auto --project <dir>",
        tags=("autonomous",),
    ),
    IntegrationSpec(
        id="mcp.list_tickets",
        title="MCP: list tickets",
        description="List open planfile tickets (same as koru_list_tickets MCP tool).",
        transport="mcp",
        methods=("list",),
        mcp_tool="koru_list_tickets",
        tags=("mcp", "planfile"),
    ),
    IntegrationSpec(
        id="mcp.run_ticket",
        title="MCP: run ticket",
        description="Run autopilot pipeline for one ticket.",
        transport="mcp",
        methods=("run",),
        mcp_tool="koru_run_ticket",
        tags=("mcp", "planfile"),
    ),
    IntegrationSpec(
        id="mcp.quality_gates",
        title="MCP: quality gates",
        description="Run configured quality gates (regix, redup, …).",
        transport="mcp",
        methods=("run",),
        mcp_tool="koru_run_quality_gates",
        tags=("mcp", "quality"),
    ),
    IntegrationSpec(
        id="serve.dashboard",
        title="Local dashboard HTTP",
        description="Legacy koru serve dashboard on port 8765.",
        transport="http",
        methods=("GET",),
        cli_equivalent="koru serve --project <dir>",
        tags=("http", "ui"),
    ),
    IntegrationSpec(
        id="local.events",
        title="Local event buffer",
        description="NDJSON event ring buffer (koru local-serve).",
        transport="http",
        methods=("GET", "POST"),
        cli_equivalent="koru local-serve",
        tags=("http", "events"),
    ),
    IntegrationSpec(
        id="dsl.to_library",
        title="DSL → library JSON",
        description="Parse scenario DSL text to OQL library structure.",
        transport="korudsl",
        methods=("convert",),
        cli_equivalent="koru dsl to-library <file.dsl>",
        tags=("dsl", "oql"),
    ),
    IntegrationSpec(
        id="dsl.to_dsl",
        title="library JSON → DSL",
        description="Serialize OQL library JSON back to DSL text.",
        transport="korudsl",
        methods=("convert",),
        cli_equivalent="koru dsl to-dsl <file.json>",
        tags=("dsl", "oql"),
    ),
    IntegrationSpec(
        id="dsl.roundtrip",
        title="DSL round-trip check",
        description="DSL → library → DSL structural validation.",
        transport="korudsl",
        methods=("check",),
        cli_equivalent="koru dsl roundtrip <file.dsl>",
        tags=("dsl", "oql"),
    ),
    IntegrationSpec(
        id="topology.read",
        title="Topology config",
        description="Read merged topology (components + pipelines).",
        transport="koru",
        methods=("read",),
        cli_equivalent="koru topology --project <dir>",
        tags=("config",),
    ),
    IntegrationSpec(
        id="planfile.tickets",
        title="Planfile ticket list",
        description="List tickets via planfile CLI.",
        transport="planfile",
        methods=("list",),
        cli_equivalent="planfile ticket list --format json",
        tags=("planfile",),
    ),
    IntegrationSpec(
        id="lane.plan",
        title="Lane: Generate task plan",
        description="Generate 10-task engineering plan from project state, git history and LLM context.",
        transport="lane",
        methods=("plan", "tickets", "dry_run"),
        cli_equivalent="lane tickets <dir> [--sync-todo|--sync-planfile|--export-yaml]",
        tags=("lane", "llm", "planning", "tickets"),
    ),
    IntegrationSpec(
        id="tagi.analyze",
        title="Tagi: Analyze changes",
        description="Analyze project changes using Tagi for priority and risk assessment.",
        transport="koru",
        methods=("analyze", "plan", "commit"),
        cli_equivalent="tagi scan <dir> && tagi list-groups <dir>",
        tags=("tagi", "analysis", "priority", "deployment"),
    ),
    IntegrationSpec(
        id="tagi.deploy",
        title="Tagi: Deploy changes",
        description="Deploy changes using Tagi's intelligent deployment prioritization.",
        transport="koru",
        methods=("deploy", "dry_run"),
        cli_equivalent="tagi deploy <dir>",
        tags=("tagi", "deployment", "automation"),
    ),
    IntegrationSpec(
        id="tagi.auto",
        title="Tagi: Auto commit",
        description="Auto-commit all changes using Tagi's auto-ordering.",
        transport="koru",
        methods=("commit", "dry_run"),
        cli_equivalent="tagi auto <dir>",
        tags=("tagi", "automation", "commit"),
    ),
)

_INTEGRATION_BY_ID = {spec.id: spec for spec in INTEGRATIONS}


def list_integrations(*, tag: str | None = None) -> list[IntegrationSpec]:
    if not tag:
        return list(INTEGRATIONS)
    needle = tag.lower()
    return [s for s in INTEGRATIONS if needle in s.tags]


def get_integration(integration_id: str) -> IntegrationSpec | None:
    return _INTEGRATION_BY_ID.get(integration_id)
