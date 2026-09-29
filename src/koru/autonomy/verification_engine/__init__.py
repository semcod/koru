"""Post-drive verification engine for autonomous cycles.

Collects evidence from multiple sources (git, tests, chat history, file
modifications) and produces a structured ``Verdict`` that the decision
arbiter can act on.  Phase 1 of ADR AUTO-002: zero LLM cost, pure
heuristics.
"""

import subprocess  # noqa: F401  (kept for patch-target compatibility)

from koru.autonomy.verification_engine.budget import (
    _drive_budget_counts as _drive_budget_counts,
)
from koru.autonomy.verification_engine.budget import (
    _drive_budget_db as _drive_budget_db,
)
from koru.autonomy.verification_engine.budget import (
    drive_budget_exhausted as drive_budget_exhausted,
)
from koru.autonomy.verification_engine.budget import (
    record_unsuccessful_drive as record_unsuccessful_drive,
)
from koru.autonomy.verification_engine.budget import (
    reserve_drive_attempt as reserve_drive_attempt,
)
from koru.autonomy.verification_engine.collectors import (
    absorbed_foreign_paths,
    collect_chat_evidence,
    collect_evidence,
    collect_git_diff_between,
    collect_git_evidence,
    collect_test_evidence,
    take_snapshot,
)
from koru.autonomy.verification_engine.git_utils import (
    _extract_leading_int as _extract_leading_int,
)
from koru.autonomy.verification_engine.git_utils import (
    _git_head as _git_head,
)
from koru.autonomy.verification_engine.git_utils import (
    _workspace_delta as _workspace_delta,
)
from koru.autonomy.verification_engine.git_utils import (
    _workspace_fingerprints as _workspace_fingerprints,
)
from koru.autonomy.verification_engine.models import (
    ChatEvidence,
    Evidence,
    FileEvidence,
    GitEvidence,
    Snapshot,
    TestEvidence,
    Verdict,
    VerdictOutcome,
)
from koru.autonomy.verification_engine.verdict import assess_verdict

__all__ = [
    "ChatEvidence",
    "Evidence",
    "FileEvidence",
    "GitEvidence",
    "Snapshot",
    "TestEvidence",
    "Verdict",
    "VerdictOutcome",
    "absorbed_foreign_paths",
    "assess_verdict",
    "collect_chat_evidence",
    "collect_evidence",
    "collect_git_diff_between",
    "collect_git_evidence",
    "collect_test_evidence",
    "take_snapshot",
]
