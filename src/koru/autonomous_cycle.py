"""
Backward compatibility shim for koru.autonomy.cycle module migration.

This module maintains backward compatibility by re-exporting from the new
autonomy.cycle submodule. Remove this shim after one release.
"""

# Re-export everything from the new module location
import sys

# Also expose the module for test monkeypatching and private function access
from koru.autonomy import cycle as _module_impl  # noqa: F401
from koru.autonomy.cycle import *  # noqa: F401, F403

_current_module = sys.modules[__name__]
for attr in dir(_module_impl):
    if not attr.startswith("__"):
        if not hasattr(_current_module, attr):
            setattr(_current_module, attr, getattr(_module_impl, attr))


# --- Compat re-exports (2026-07-03) -----------------------------------------
# The autonomy/cycle_* modules late-bind these names THROUGH this facade
# (`from koru import autonomous_cycle as _cycle_mod; _cycle_mod.<name>`), and
# tests monkeypatch them here. Removing them breaks cycle_queue_scan /
# cycle_diagnostics / cycle_planning at runtime (AttributeError) — keep this
# block until every late-bound call site and test patch target migrates.
from koru.autonomy.cycle.cycle import (  # noqa: E402
    _escalate_error_stagnation as _escalate_error_stagnation,
)
from koru.autonomy.cycle.cycle import (
    _run_drive_phase as _run_drive_phase,
)
from koru.autonomy.cycle.cycle import (
    _run_post_drive_phase as _run_post_drive_phase,
)
from koru.autonomy.cycle.cycle import _stdio_info as _stdio_info  # noqa: E402
from koru.autonomy.cycle.cycle_chat_activity import (  # noqa: E402
    _skip_due_to_recent_chat_activity as _skip_due_to_recent_chat_activity,
)
from koru.autonomy.cycle.cycle_chat_activity_text import (  # noqa: E402
    extract_needs_input_question as _extract_needs_input_question,
)
from koru.autonomy.cycle.cycle_drive_retry import (  # noqa: E402
    _log_autopilot_result as _log_autopilot_result,
)
from koru.autonomy.cycle.cycle_drive_retry import (
    _reply_chat_input_busy as _reply_chat_input_busy,
)
from koru.autonomy.cycle.cycle_drive_retry import (
    _resolve_autopilot_drive_decision as _resolve_autopilot_drive_decision,
)
from koru.autonomy.cycle.cycle_orchestrator import (  # noqa: E402
    _handle_autopilot_phase as _handle_autopilot_phase,
)
from koru.autonomy.cycle_diagnostics import (  # noqa: E402
    _run_idle_diagnostics as _run_idle_diagnostics,
)
from koru.autonomy.cycle_planning import (  # noqa: E402
    _load_open_tickets_for_planning as _load_open_tickets_for_planning,
)
from koru.autonomy.cycle_planning import (
    _run_phase4_advisory_hooks as _run_phase4_advisory_hooks,
)
from koru.autonomy.cycle_queue_scan import (
    _build_queue_command as _build_queue_command,
)
from koru.autonomy.cycle_queue_scan import (
    _handle_scan_after_idle as _handle_scan_after_idle,
)
from koru.autonomy.cycle_queue_scan import (  # noqa: E402
    _run_code2llm_discovery_after_idle as _run_code2llm_discovery_after_idle,
)
from koru.autonomy.decision_trace import (  # noqa: E402
    load_recent_decisions as load_recent_decisions,
)
from koru.autonomy.planning_llm import (  # noqa: E402
    prioritize_tickets as _llm_prioritize_tickets,
)
from koru.autonomy.planning_llm import (  # noqa: E402
    propose_strategy_tuning as _llm_propose_strategy_tuning,
)
from koru.autonomy.post_run_verify import (  # noqa: E402
    verify_completed_tickets as verify_completed_tickets,
)
from koru.autonomy_strategy.config import (  # noqa: E402
    load_autonomy_strategy as load_autonomy_strategy,
)
from koru.queue import default_human_prompt as _default_human_prompt  # noqa: E402
from koru.queue import run_api_request as _run_api_request  # noqa: E402
from koru.queue import run_llm_request as _run_llm_request  # noqa: E402
from koru.queue import run_planfile_queue_loop as run_planfile_queue_loop  # noqa: E402
from koru.queue import run_process as _run_process  # noqa: E402
from koru.queue import run_shell_command as _run_shell_command  # noqa: E402
from koru.scan import run_scan as run_scan  # noqa: E402

# koru.autonomous imports this facade at module level, so these four cannot
# be imported eagerly (circular import) — resolve them lazily instead.
_LATE_COMPAT_FROM_AUTONOMOUS = (
    "_clear_diagnostic_marker",
    "_create_diagnostic_ticket",
    "_read_wup_health",
    "_run_command_check",
)


def __getattr__(name: str):
    if name in _LATE_COMPAT_FROM_AUTONOMOUS:
        from koru import autonomous as _autonomous_mod

        return getattr(_autonomous_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
