from __future__ import annotations

from koru.autonomy.structured_report import emit_structured_cycle_report


def test_structured_cycle_report_emits_diagnostics_and_plans() -> None:
    emitted: list[tuple[str, str]] = []

    def dummy_activity(category: str, message: str) -> None:
        emitted.append((category, message))

    actions = emit_structured_cycle_report(
        cycle=38,
        queue_status="waiting_input",
        waiting_ticket="PLF-013",
        wup_status="ok",
        diag_status="skipped",
        autopilot_status="skipped(plugin_missing)",
        autopilot_ide="antigravity",
        stagnation_streak=2,
        sleep_seconds=15.0,
        activity_fn=dummy_activity,
    )

    # Verify that the correct headers, DIAG, PLAN, and ACTION categories are present
    categories = [cat for cat, _ in emitted]
    assert "KORUAUTONOMOUS" in categories
    assert "DIAG" in categories
    assert "PLAN" in categories
    assert "ACTION" in categories

    # Verify DIAG lines
    diag_msgs = [msg for cat, msg in emitted if cat == "DIAG"]
    assert any("queue=waiting_input" in msg for msg in diag_msgs)
    assert any("ticket=PLF-013" in msg for msg in diag_msgs)
    assert any("streak=2" in msg for msg in diag_msgs)
    assert any("blocker=plugin_missing" in msg for msg in diag_msgs)
    assert any("ide=antigravity" in msg for msg in diag_msgs)

    # Verify PLAN lines
    plan_msgs = [msg for cat, msg in emitted if cat == "PLAN"]
    assert any("skip drive" in msg for msg in plan_msgs)
    assert any("wait for plugin reconnect" in msg for msg in plan_msgs)

    # Verify ACTION lines contain correct commands/notes
    action_msgs = [msg for cat, msg in emitted if cat == "ACTION"]
    assert any(
        "[manual] Reload antigravity IDE window: ide reload-window antigravity" in msg
        for msg in action_msgs
    )
    assert any(
        "[manual] Connect autopilot plugin for antigravity: ide connect-plugin antigravity"
        in msg
        for msg in action_msgs
    )

    # Verify action objects are built properly
    assert len(actions) > 0
    assert any(a.domain == "ide" and a.verb == "reload-window" for a in actions)
