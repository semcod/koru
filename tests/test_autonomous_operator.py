from __future__ import annotations

from types import SimpleNamespace

from koru.autonomous_operator import _plugin_blocker_line, run_operator_pipeline
from koru.autonomous_plugin import plugin_skip_code, plugin_status_decision


def test_run_operator_pipeline_skips_hints_when_disabled() -> None:
  hints = ["koru autonomous: --- co zrobić teraz (operator IDE) ---"]
  emitted: list[str] = []

  run_operator_pipeline(
      SimpleNamespace(operator_pipeline=False, emit_events="text"),
      project=SimpleNamespace(),
      startup_probe=SimpleNamespace(),
      plugin_connected=True,
      mcp_provision_ran=False,
      correlation_id="test",
      format_hints=lambda *_a, **_k: hints,
      run_pipeline=lambda **_kw: (_ for _ in ()).throw(AssertionError("pipeline ran")),
      stdio_info=lambda msg, **_kw: emitted.append(msg),
  )

  assert emitted == []


def test_run_operator_pipeline_emits_hints_when_enabled() -> None:
  hints = ["line-one", "line-two"]
  emitted: list[str] = []
  pipeline_ran = False

  def _run_pipeline(**_kwargs):
      nonlocal pipeline_ran
      pipeline_ran = True

  run_operator_pipeline(
      SimpleNamespace(
          operator_pipeline=True,
          emit_events="text",
          operator_tickets=False,
          operator_ticket_queue="operator",
          operator_ticket_priority="normal",
      ),
      project=SimpleNamespace(),
      startup_probe=SimpleNamespace(),
      plugin_connected=True,
      mcp_provision_ran=False,
      correlation_id="test",
      format_hints=lambda *_a, **_k: hints,
      run_pipeline=_run_pipeline,
      stdio_info=lambda msg, **_kw: emitted.append(msg),
  )

  assert emitted == hints
  assert pipeline_ran is True


def test_plugin_skip_code_classifies_version_mismatch() -> None:
    assert (
        plugin_skip_code(
            "ide=vscodium version=0.1.63 blocked: connected autopilot "
            "plugin version mismatch: connected=0.1.63 expected=0.1.64"
        )
        == "plugin_version_mismatch"
    )


def test_plugin_skip_code_classifies_build_mismatch() -> None:
    assert (
        plugin_skip_code(
            "ide=vscodium version=0.2.7 blocked: connected autopilot "
            "plugin build mismatch: connected=old expected=new"
        )
        == "plugin_version_mismatch"
    )


def test_plugin_skip_code_classifies_empty_plugin_list_as_not_connected() -> None:
    assert plugin_skip_code("daemon status plugin list is empty") == "plugin_not_connected"


def test_plugin_blocker_line_includes_recovery_action() -> None:
    line = _plugin_blocker_line(
        "connected autopilot plugin version mismatch: connected=0.1.63 expected=0.1.64",
        "vscodium",
    )

    assert "blocked_by=plugin_version_mismatch" in line
    assert "ide=vscodium" in line
    assert "reload IDE window" in line


def test_plugin_blocker_line_for_empty_list_is_reload_first() -> None:
    line = _plugin_blocker_line("daemon status plugin list is empty", "vscodium")

    assert "blocked_by=plugin_not_connected" in line
    assert "Developer: Reload Window" in line
    assert "koru: Connect autopilot daemon" in line


def test_plugin_status_decision_uses_stale_rejection_when_plugin_list_empty() -> None:
    ready, reason = plugin_status_decision(
        {
            "plugins": [],
            "rejected_plugins": [
                {
                    "ide": "vscodium",
                    "version": "0.1.77",
                    "expected_version": "0.1.78",
                    "message": (
                        "connected autopilot plugin version mismatch: "
                        "connected=0.1.77 expected=0.1.78"
                    ),
                },
            ],
        },
        "vscodium",
    )

    assert ready is False
    assert "plugin version mismatch" in reason
    assert "connected=0.1.77 expected=0.1.78" in reason
    assert plugin_skip_code(reason) == "plugin_version_mismatch"
