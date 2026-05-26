"""HTML response builders and shared constants for dashboard quick actions.

Extracted from ``dashboard_routes.py`` (R2) to keep route handlers focused on
HTTP dispatch and to localize HTML markup in a single module.
"""

from __future__ import annotations

from html import escape
from typing import Any

# ---------------------------------------------------------------------------
# Quick-action: create project-discovery ticket
# ---------------------------------------------------------------------------

PROJECT_DISCOVERY_TITLE = "Project discovery: generate code2llm analysis and tickets"

PROJECT_DISCOVERY_DESCRIPTION = (
  "Run a broad project discovery pass because the planfile queue is idle.\n\n"
  "1. Refresh project/code2llm artifacts when stale.\n"
  "2. Ask IDE LLM: 'Co jeszcze zostalo do wykonania? zrob z tego nastepne tickety do planfile.'.\n"
  "3. Review findings and create focused planfile tickets for concrete work.\n"
  "4. Keep broad discovery scoped: stop when runnable tickets exist."
)

PROJECT_DISCOVERY_TICKET_FIELDS: dict[str, str] = {
  "title": PROJECT_DISCOVERY_TITLE,
  "description": PROJECT_DISCOVERY_DESCRIPTION,
  "priority": "high",
  "executor_kind": "human",
  "queue_name": "operator",
  "dedupe_key": "koru:quick-action:create-ticket-for-project",
  "signal": "project_discovery_quick_action",
}

PROJECT_DISCOVERY_PROMPT_QUERY: dict[str, str] = {
  "tab": "tickets",
  "focus": "create-ticket",
  "change": "llm.prompt.create-ticket-for-project",
  "title": PROJECT_DISCOVERY_TITLE,
  "priority": "high",
  "executor_kind": "human",
  "queue_name": "operator",
  "description": PROJECT_DISCOVERY_DESCRIPTION,
}


def render_action_success_html(
  *,
  title: str,
  project: str,
  ticket_id: str,
  name: str,
) -> bytes:
  """Render the HTML response body for a successful quick-action.

  Returns bytes ready to pass to ``_send``.
  """
  body = (
    "<!doctype html><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<title>koru action result</title>"
    "<style>"
    "body{font-family:system-ui,sans-serif;max-width:760px;margin:48px auto;padding:0 20px;"
    "line-height:1.45;color:#17202a} .ok{color:#147a3d;font-weight:700}"
    "code{background:#eef2f7;padding:2px 5px;border-radius:4px}"
    "a{color:#0b5fff}"
    "</style>"
    f"<h1 class='ok'>{escape(title)}</h1>"
    f"<p>Project: <code>{escape(project)}</code></p>"
    f"<p>Ticket: <code>{escape(ticket_id)}</code></p>"
    f"<p>Name: {escape(name)}</p>"
    "<p>This quick action is idempotent: repeated clicks reuse the same active ticket.</p>"
    "<p><a href='/?tab=tickets'>Open tickets</a> · "
    "<a href='/api/context'>Context JSON</a></p>"
  )
  return body.encode("utf-8")


def render_action_error_html(exc: BaseException) -> bytes:
  """Render the HTML response body for a failed quick-action."""
  body = (
    "<!doctype html><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<title>koru action failed</title>"
    "<style>body{font-family:system-ui,sans-serif;max-width:760px;margin:48px auto;padding:0 20px;"
    "line-height:1.45;color:#17202a}.err{color:#b42318;font-weight:700}"
    "pre{white-space:pre-wrap;background:#fff1f0;padding:12px;border-radius:6px}</style>"
    "<h1 class='err'>Action failed</h1>"
    f"<pre>{escape(type(exc).__name__ + ': ' + str(exc))}</pre>"
    "<p><a href='/?tab=tickets'>Open tickets</a></p>"
  )
  return body.encode("utf-8")


def render_create_ticket_success_html(project: str, result: dict[str, Any]) -> bytes:
  """Render success HTML for the create-project-discovery-ticket action."""
  status = "reused" if result.get("reused") else "created"
  ticket_id = str(result.get("ticket_id") or "")
  return render_action_success_html(
    title=f"Ticket {status}: {ticket_id}",
    project=project,
    ticket_id=ticket_id,
    name=str(result.get("name") or ""),
  )


__all__ = [
  "PROJECT_DISCOVERY_TITLE",
  "PROJECT_DISCOVERY_DESCRIPTION",
  "PROJECT_DISCOVERY_TICKET_FIELDS",
  "PROJECT_DISCOVERY_PROMPT_QUERY",
  "render_action_success_html",
  "render_action_error_html",
  "render_create_ticket_success_html",
]
