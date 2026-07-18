"""The one artifact that proves what a patch run did: the evidence bundle.

A run's ticket can be marked done by code paths far from the transaction, long
after the worktree is gone. The bundle is the durable answer to "on what
grounds?" — one JSON file per run recording the frozen plan, every patch
attempt with its hash, the gate that ran and how the result was delivered.
Completion is *gated* on it: a landed patch without a valid bundle blocks the
ticket, because a success nobody can audit is indistinguishable from a failure
nobody noticed.
"""

from __future__ import annotations

import json
from pathlib import Path

from koru.queue.manifest import manifest_run_directory, persist_run_artifact
from koru.queue.patch_mode import redact_secrets

#: How a run ended. ``verified`` — landed with a green gate; ``applied`` —
#: landed with no gate to run; ``artifact`` — delivered as a reviewable file;
#: ``refused`` — the transaction said no and the workspace shows it.
VERDICT_VERIFIED = "verified"
VERDICT_APPLIED = "applied"
VERDICT_ARTIFACT = "artifact"
VERDICT_REFUSED = "refused"

_VERDICTS = frozenset({VERDICT_VERIFIED, VERDICT_APPLIED, VERDICT_ARTIFACT, VERDICT_REFUSED})

#: Bumped when the bundle's shape changes incompatibly; auditors key on it.
SCHEMA_VERSION = 1

_REQUIRED_KEYS = (
    "schema_version",
    "run_id",
    "ticket_id",
    "manifest_hash",
    "base_head",
    "workspace_snapshot",
    "patch_attempts",
    "verify",
    "promotion",
    "cleanup",
    "verdict",
)


def patch_attempt_record(
    attempt: int,
    *,
    patch_sha256: str | None,
    outcome_code: str | None,
    message: str = "",
    retryable: bool = False,
) -> dict:
    """One attempt as evidence. ``outcome_code=None`` means the patch landed.

    The message is redacted before it is written: verify output quotes file
    contents, and evidence outlives the run on disk.
    """
    return {
        "attempt": attempt,
        "patch_sha256": patch_sha256,
        "outcome": outcome_code or "landed",
        "retryable": retryable,
        "message": redact_secrets(message, limit=600),
    }


def build_evidence_bundle(
    *,
    run_id: str,
    ticket: dict,
    manifest: dict | None,
    patch_attempts: list[dict],
    verify: dict,
    promotion: dict,
    verdict: str,
    actor: str | None = None,
) -> dict:
    """Assemble the canonical bundle for a finished run.

    The verdict is computed by the transaction layer from outcomes — never by
    an LLM, whose text has no authority here. ``manifest=None`` is legitimate
    only for refusals that fired before the plan was frozen — there was nothing
    to pin because nothing was going to change. Every path that mutates has a
    manifest, and the bundle carries its hash so the two artifacts vouch for
    each other.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "ticket_id": ticket.get("id"),
        "actor": actor,
        "manifest_hash": (manifest or {}).get("manifest_hash"),
        "base_head": (manifest or {}).get("base_head"),
        "workspace_snapshot": (manifest or {}).get("workspace_snapshot_sha256"),
        "targets": sorted((manifest or {}).get("touched_files") or []),
        "patch_attempts": patch_attempts,
        "verify": verify,
        "promotion": promotion,
        "cleanup": {"worktree_removed": bool(promotion.get("isolated"))},
        "verdict": verdict,
    }


def persist_evidence(project: Path, bundle: dict) -> Path:
    """Write the bundle where the manifest already lives, atomically."""
    return persist_run_artifact(project, bundle["run_id"], "evidence.json", bundle)


def load_evidence(project: Path, run_id: str) -> dict | None:
    path = manifest_run_directory(project, run_id) / "evidence.json"
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def completion_gap(project: Path, bundle: dict | None) -> str | None:
    """Why this run may not close its ticket, or ``None`` when it may.

    Judged from the *persisted* copy, not the in-memory dict: the promise is
    that an auditor can reconstruct the run from disk, so disk is what gates.
    """
    if bundle is None:
        return "no evidence bundle was produced for this run"
    persisted = load_evidence(project, str(bundle.get("run_id") or ""))
    if persisted is None:
        return "the evidence bundle was not persisted"
    missing = [key for key in _REQUIRED_KEYS if key not in persisted]
    if missing:
        return f"evidence bundle is missing: {', '.join(missing)}"
    if persisted.get("verdict") not in _VERDICTS:
        return f"evidence bundle carries unknown verdict {persisted.get('verdict')!r}"
    if not persisted.get("patch_attempts"):
        return "evidence bundle records no patch attempts"
    if persisted["verdict"] in {VERDICT_VERIFIED, VERDICT_APPLIED, VERDICT_ARTIFACT} and not (
        persisted.get("manifest_hash") and persisted.get("workspace_snapshot")
    ):
        return "evidence bundle claims success but carries no frozen manifest"
    return None
