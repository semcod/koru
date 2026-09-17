"""koru queue clean — sweep stale test fixtures out of the planfile queue.

Test sessions accumulate fixture tickets (``test-only``, ``dryrun``,
``synthetic`` …). Without housekeeping they pile up, distract the agent
on every ``koru --context`` call, and gradually erode trust in the
queue. ``koru queue clean`` is the safe, auditable broom.

Safety contract
---------------
1. **Dry-run by default.** No ticket is mutated unless ``--apply`` is
   passed. The dry-run output is the list a human would otherwise
   produce by hand — it must be possible to read it and predict
   exactly what ``--apply`` will do.
2. **Active work is sacred.** Tickets with status ``in_progress`` or
   ``waiting_input`` are never touched unless the operator explicitly
   passes ``--include-active``. Default cleanup considers only
   ``open`` and ``ready`` tickets.
3. **Every closure leaves an audit trail.** Each completed ticket
   receives a single ``KORU-QUEUE-CLEAN`` note carrying the reason and
   matched rules — same parseable shape as ``KORU-GATE-AUTH`` so the
   audit-trail tooling can reuse the existing parser style.

Detection rules
---------------
A ticket is a cleanup candidate when **any** of the following holds:

* its ``labels`` intersect :data:`koru.context.FIXTURE_LABELS`
  (``test-only``, ``dryrun``, ``dry-run``, ``synthetic``, ``auto-close``);
* ``--include-names`` is enabled and the ticket name matches
  :data:`FIXTURE_NAME_PATTERN` (``Test …`` / ``TEST: …``);
* ``--max-age-days N`` is set and the ticket has been open longer than
  that many days (combined with the above — never a sole criterion).
"""

from koru.queue_clean.cleanup import (
    ACTIVE_STATUSES,
    CLEANABLE_STATUSES_DEFAULT,
    FIXTURE_NAME_PATTERN,
    QUEUE_CLEAN_TAG,
    CleanupCandidate,
    CleanupReport,
    _build_close_note,
    _close_ticket,
    _list_tickets,
    clean_queue,
    find_candidates,
)
from koru.queue_clean.legacy_skipped import (
    LEGACY_SKIPPED_MIGRATION_SCHEMA,
    LEGACY_SKIPPED_MIGRATION_TAG,
    MIGRATION_RULE_V1,
    LegacySkippedCandidate,
    LegacySkippedMigrationReport,
    LegacySkippedMigrationRule,
    _build_legacy_skipped_note,
    find_legacy_skipped_candidates,
    load_raw_sprint_tickets,
    migrate_legacy_skipped,
)

__all__ = [
    "ACTIVE_STATUSES",
    "CLEANABLE_STATUSES_DEFAULT",
    "CleanupCandidate",
    "CleanupReport",
    "FIXTURE_NAME_PATTERN",
    "LEGACY_SKIPPED_MIGRATION_SCHEMA",
    "LEGACY_SKIPPED_MIGRATION_TAG",
    "LegacySkippedCandidate",
    "LegacySkippedMigrationReport",
    "LegacySkippedMigrationRule",
    "MIGRATION_RULE_V1",
    "QUEUE_CLEAN_TAG",
    "clean_queue",
    "find_candidates",
    "find_legacy_skipped_candidates",
    "load_raw_sprint_tickets",
    "migrate_legacy_skipped",
    "_build_close_note",
    "_build_legacy_skipped_note",
    "_close_ticket",
    "_list_tickets",
]
