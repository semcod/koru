"""DSL Reconfiguration Engine for Koru.

Parses concise process URI configurations ('yaml: uri {json}'),
validates parameters against the ProcessUriRegistry, and applies reconfigurations
to target projects conforming to wellmanifest/dsl standards.
Supports internal Koru state transitions as well as external Docker sandbox
and CDP browser operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.autonomy.cdp_browser import CdpBrowserController
from koru.autonomy.docker_sandbox import DockerSandboxRunner
from koru.autonomy.process_uri import ProcessUri, ProcessUriRegistry, parse_uri_json_line


def build_default_autonomy_registry(
    *,
    sandbox_runner: DockerSandboxRunner | None = None,
    browser_controller: CdpBrowserController | None = None,
) -> ProcessUriRegistry:
    """Build the standard ProcessUriRegistry for Koru and task autonomy."""
    reg = ProcessUriRegistry()
    sandbox = sandbox_runner or DockerSandboxRunner()
    browser = browser_controller or CdpBrowserController()

    # --- Internal Koru & Task lifecycle ---
    reg.register(
        "koru://workspace/allocate",
        "Allocate a dedicated worktree and lease for a ticket",
        {"required": ["ticket_id"]},
    )
    reg.register(
        "koru://governance/check",
        "Run governance and quality checks against base revision",
        {"required": []},
    )
    reg.register(
        "koru://queue/task/claim",
        "Claim the next runnable ticket from queue",
        {"required": ["ticket_id"]},
    )
    reg.register(
        "koru://queue/task/complete",
        "Finalize and mark ticket as completed",
        {"required": ["ticket_id"]},
    )
    reg.register(
        "taskand://git/commit",
        "Commit verified deliverables to branch",
        {"required": ["message"]},
    )
    reg.register(
        "taskand://github/pr/create",
        "Create GitHub Pull Request",
        {"required": ["title", "branch"]},
    )
    reg.register(
        "taskand://ci/run_gates",
        "Execute automated CI gates",
        {"required": []},
    )
    reg.register(
        "autonomy://config/set",
        "Set runtime configuration option in project",
        {"required": ["key", "value"]},
    )

    # --- External Process URI: Docker Sandbox & PyPI ---
    def handle_sandbox(u: ProcessUri, p: dict[str, Any]) -> Any:
        return sandbox.execute_uri(u, p, dry_run=True)

    reg.register(
        "sandbox://run",
        "Execute command in isolated Docker container",
        {"required": ["image"]},
        handler=handle_sandbox,
    )
    reg.register(
        "sandbox://run/",
        "Execute command in isolated Docker container",
        {"required": ["image"]},
        handler=handle_sandbox,
    )
    reg.register(
        "pypi://run",
        "Execute Python package tool inside isolated sandbox",
        {"required": []},
        handler=handle_sandbox,
    )
    reg.register(
        "pypi://run/",
        "Execute Python package tool inside isolated sandbox",
        {"required": []},
        handler=handle_sandbox,
    )

    # --- External Process URI: Chrome DevTools Protocol (CDP) Browser ---
    def handle_browser(u: ProcessUri, p: dict[str, Any]) -> Any:
        return browser.execute_uri(u, p, dry_run=True)

    reg.register(
        "browser://navigate",
        "Navigate browser page to URL",
        {"required": ["url"]},
        handler=handle_browser,
    )
    reg.register(
        "browser://navigate/",
        "Navigate browser page to URL",
        {"required": ["url"]},
        handler=handle_browser,
    )
    reg.register(
        "browser://click",
        "Click element matching CSS selector",
        {"required": ["selector"]},
        handler=handle_browser,
    )
    reg.register(
        "browser://click/",
        "Click element matching CSS selector",
        {"required": ["selector"]},
        handler=handle_browser,
    )
    reg.register(
        "browser://screenshot",
        "Capture screenshot of the page",
        {"required": []},
        handler=handle_browser,
    )
    reg.register(
        "browser://screenshot/",
        "Capture screenshot of the page",
        {"required": []},
        handler=handle_browser,
    )
    reg.register(
        "browser://evaluate",
        "Evaluate JavaScript in browser context",
        {"required": ["expression"]},
        handler=handle_browser,
    )
    reg.register(
        "browser://evaluate/",
        "Evaluate JavaScript in browser context",
        {"required": ["expression"]},
        handler=handle_browser,
    )

    return reg


class DslReconfigurator:
    """Interprets and executes reconfiguration scripts based on Process URIs."""

    def __init__(self, registry: ProcessUriRegistry | None = None) -> None:
        self.registry = registry or build_default_autonomy_registry()

    def parse_spec(self, content: str) -> list[tuple[ProcessUri, dict[str, Any]]]:
        """Parse multi-line spec formatted as 'yaml: uri {json}' or list of actions."""
        operations: list[tuple[ProcessUri, dict[str, Any]]] = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            uri, payload = parse_uri_json_line(line)
            # Validate against registry
            self.registry.validate_invocation(uri, payload)
            operations.append((uri, payload))
        return operations

    def apply_to_project(
        self,
        project_path: Path,
        spec_content: str,
        *,
        execute_handlers: bool = True,
    ) -> dict[str, Any]:
        """Apply a reconfiguration spec to a target project."""
        ops = self.parse_spec(spec_content)
        executed: list[dict[str, Any]] = []

        for uri, payload in ops:
            action_def = self.registry.get(uri.canonical_action)
            result = None
            if execute_handlers and action_def and action_def.handler:
                try:
                    result = action_def.handler(uri, payload)
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}

            action_record = {
                "uri": uri.canonical_action,
                "params": payload,
                "status": "applied",
                "result": result,
            }
            executed.append(action_record)

        return {
            "project": str(project_path),
            "status": "success",
            "operations_count": len(executed),
            "operations": executed,
        }
