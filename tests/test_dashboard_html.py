"""Tests for dashboard HTML response builders."""

from __future__ import annotations

from koruapi.dashboard_html import (
    PROJECT_DISCOVERY_DESCRIPTION,
    PROJECT_DISCOVERY_PROMPT_QUERY,
    PROJECT_DISCOVERY_TICKET_FIELDS,
    PROJECT_DISCOVERY_TITLE,
    render_action_error_html,
    render_action_success_html,
    render_create_ticket_success_html,
)


def test_project_discovery_constants_are_consistent() -> None:
    assert PROJECT_DISCOVERY_TITLE == PROJECT_DISCOVERY_TICKET_FIELDS["title"]
    assert PROJECT_DISCOVERY_TITLE == PROJECT_DISCOVERY_PROMPT_QUERY["title"]
    assert PROJECT_DISCOVERY_DESCRIPTION == PROJECT_DISCOVERY_TICKET_FIELDS["description"]
    assert PROJECT_DISCOVERY_DESCRIPTION == PROJECT_DISCOVERY_PROMPT_QUERY["description"]
    assert PROJECT_DISCOVERY_TICKET_FIELDS["priority"] == "high"
    assert PROJECT_DISCOVERY_TICKET_FIELDS["queue_name"] == "operator"
    assert PROJECT_DISCOVERY_TICKET_FIELDS["dedupe_key"].startswith("koru:quick-action:")


def test_render_action_success_html_contains_fields() -> None:
    html = render_action_success_html(
        title="Ticket created: T-1",
        project="/home/user/proj",
        ticket_id="T-1",
        name="My ticket",
    ).decode("utf-8")
    assert "Ticket created: T-1" in html
    assert "/home/user/proj" in html
    assert "T-1" in html
    assert "My ticket" in html
    assert "<!doctype html>" in html
    assert "text/html" not in html  # body only, not content-type


def test_render_action_success_html_escapes_html_in_inputs() -> None:
    html = render_action_success_html(
        title="<script>alert(1)</script>",
        project="<p>",
        ticket_id="<b>",
        name="<i>",
    ).decode("utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;p&gt;" in html


def test_render_action_error_html_includes_exception_class_and_message() -> None:
    exc = ValueError("bad input")
    html = render_action_error_html(exc).decode("utf-8")
    assert "ValueError" in html
    assert "bad input" in html
    assert "Action failed" in html


def test_render_action_error_html_escapes_exception_message() -> None:
    exc = RuntimeError("<script>alert('xss')</script>")
    html = render_action_error_html(exc).decode("utf-8")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_render_create_ticket_success_html_reused_status() -> None:
    html = render_create_ticket_success_html(
        "/proj",
        {"reused": True, "ticket_id": "T-9", "name": "Existing"},
    ).decode("utf-8")
    assert "Ticket reused: T-9" in html
    assert "T-9" in html
    assert "Existing" in html


def test_render_create_ticket_success_html_created_status() -> None:
    html = render_create_ticket_success_html(
        "/proj",
        {"reused": False, "ticket_id": "T-10", "name": "Fresh"},
    ).decode("utf-8")
    assert "Ticket created: T-10" in html


def test_render_create_ticket_success_html_handles_missing_fields() -> None:
    html = render_create_ticket_success_html("/proj", {}).decode("utf-8")
    # Should still render without crashing on missing optional fields.
    assert "Ticket created:" in html
    assert "/proj" in html
