"""LLM-ready ticket builder — converts alerts into planfile tickets.

Design goal
-----------
Every ticket produced here must be *directly actionable* by **any** coding
agent — Windsurf, Cursor, Claude Code, aider, GitHub Copilot Workspace, or
a plain chat with Gemini/GPT — without further priming. That means each
ticket carries:

  1. Self-contained *Context* block (affected files, git SHA, stack names).
  2. Deterministic *Reproduction* steps (copy-pasteable commands).
  3. Machine-checkable *Acceptance criteria* (curl exit codes, testql paths).
  4. Explicit *Constraints* (do NOT change X, must preserve Y).
  5. A ready-made *Prompt* section an agent can quote verbatim.

The `planfile ticket create` CLI stores every field we care about in
`description` (markdown). When an LLM reads `planfile ticket show PLF-123`
it already has everything needed to make the fix; no back-and-forth.
"""

from __future__ import annotations

import subprocess
import textwrap
from typing import Any

LLM_READY_TEMPLATE = """\
## 🚨 Context

- **Alert:** {alertname}
- **Severity:** {severity}
- **Component:** {component}
- **Stack:** c2004 monorepo (FastAPI backend + Vue/Vite frontend + connect-* microservices)
- **Repo:** {repo}
- **Commit:** `{commit}`
- **Detected at:** {timestamp}
- **Source:** {source}

{summary}

## 🔁 Reproduction

```bash
{reproduction}
```

Expected → HTTP 200 / `probe_success=1`.
Observed → `{observed}`.

## 📂 Likely-affected areas

{affected_paths}

## ✅ Acceptance criteria

Agent must leave the repo green against **all** of the following:

{acceptance_block}

## 🔒 Constraints

- Do NOT modify generated code (`**/*_pb2*.py`, `**/__generated__/**`, `archive/**`, `_archive/**`).
- Do NOT bump dependencies in `*/requirements*.txt` without evidence the bug is in the library.
- Do NOT disable tests or weaken assertions to pass the gate.
- Keep changes under ~80 lines; larger diffs must be split into multiple tickets.
- Always write a short regression test that would have caught this alert.

## 🤖 Prompt (LLM-agnostic — copy/paste verbatim)

> You are assigned the following ticket. Produce a minimal patch that satisfies every acceptance criterion.
>
> {prompt_body}
>
> Workflow:
> 1. Read the files listed in “Likely-affected areas”.
> 2. Reproduce the failure using the `Reproduction` block.
> 3. Propose a patch; stay within the constraints.
> 4. Run `task monitor:probe` to confirm the acceptance criteria pass.
> 5. Summarise the root cause in 3 sentences for the PR description.

## 📎 Raw alert payload

```json
{raw_payload}
```
"""


def _git_commit(repo: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return out.decode().strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _infer_paths(component: str, labels: dict[str, str]) -> list[str]:
    """Map alert component → most likely source directories for an LLM to read first."""
    if "instance" in labels and "localhost:8202" in labels["instance"]:
        return ["firmware/", "oqlos/api/"]
    if "instance" in labels and "localhost:8100" in labels["instance"]:
        return ["frontend/src/"]
    if "instance" in labels and "localhost:810" in labels["instance"]:
        # connect-* backend family
        return [
            "connect-*/backend/",
            "backend/api/routes/v3/",
            "packages/backend-shared-py/src/shared/",
        ]
    mapping = {
        "backend": [
            "backend/api/routes/",
            "backend/app/",
            "packages/backend-shared-py/src/shared/",
        ],
        "endpoint": [
            "backend/api/routes/",
            "connect-*/backend/",
        ],
        "infrastructure": ["docker-compose.yml", "docker-compose.dev.yml"],
    }
    return mapping.get(component, ["backend/", "connect-*/backend/"])


def _format_paths(paths: list[str]) -> str:
    return "\n".join(f"- `{p}`" for p in paths)


def _default_acceptance(instance: str | None) -> list[str]:
    probes = [
        "GET http://localhost:8101/api/v3/health → 200",
        "`task monitor:probe` exits 0",
        "`task test` passes for affected sub-packages",
        "`redsl gate check` returns exit code 0",
    ]
    if instance:
        probes.insert(0, f"GET {instance} → 200 (was {instance} failing)")
    return probes


def _format_acceptance(items: list[str]) -> str:
    return "\n".join(f"- [ ] {x}" for x in items)


def _reproduction_for(labels: dict[str, str], failures: list[dict] | None = None) -> str:
    lines: list[str] = ["task monitor:probe"]
    instance = labels.get("instance")
    if instance:
        lines.append(f"curl -sS -m 4 -o /dev/null -w '%{{http_code}}\\n' '{instance}'")
    for f in (failures or [])[:5]:
        if f.get("endpoint"):
            lines.append(
                f"curl -sS -m 4 -o /dev/null -w '%{{http_code}}\\n' '{f['endpoint']}'"
            )
    return "\n".join(lines)


def build_ticket_payload(alert: dict[str, Any], *, repo: str, source: str = "healing-webhook") -> dict:
    """Convert an Alertmanager alert (or probe failure) into planfile ticket kwargs."""
    labels: dict[str, str] = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    alertname = labels.get("alertname") or alert.get("alertname") or "UnknownAlert"
    severity = labels.get("severity", "error")
    component = labels.get("component", "unknown")
    instance = labels.get("instance")
    summary = annotations.get("summary") or annotations.get("description") or "(no summary)"
    observed = annotations.get("observed") or alert.get("status") or "failing"
    timestamp = alert.get("startsAt") or alert.get("timestamp") or ""

    affected_paths = _format_paths(_infer_paths(component, labels))
    acceptance = _default_acceptance(instance)
    reproduction = _reproduction_for(labels, alert.get("failures"))

    prompt_body = textwrap.shorten(
        f"Alert {alertname} fired: {summary}. Component={component}, "
        f"severity={severity}. Root-cause the failure and land a minimal, "
        f"tested patch that satisfies every acceptance criterion.",
        width=480,
        placeholder="…",
    )

    description = LLM_READY_TEMPLATE.format(
        alertname=alertname,
        severity=severity,
        component=component,
        repo=repo,
        commit=_git_commit(repo),
        timestamp=timestamp,
        source=source,
        summary=f"**Summary:** {summary}",
        reproduction=reproduction,
        observed=observed,
        affected_paths=affected_paths,
        acceptance_block=_format_acceptance(acceptance),
        prompt_body=prompt_body,
        raw_payload=str(alert)[:1500],
    )

    priority = {"critical": "critical", "error": "high", "warning": "normal"}.get(severity, "normal")
    name = f"[{source}] {alertname}: {summary[:80]}"

    labels_out = sorted(
        {
            source,
            "auto-generated",
            "llm-ready",
            f"severity:{severity}",
            f"component:{component}",
        }
    )

    return {
        "name": name,
        "priority": priority,
        "source": source,
        "labels": labels_out,
        "description": description,
    }
