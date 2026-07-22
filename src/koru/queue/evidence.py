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

import hashlib
import json
from pathlib import Path

from koru.queue.manifest import manifest_run_directory, persist_run_artifact
from koru.queue.patch_mode import redact_secrets


def _sha256_of(value: object) -> str:
    """Canonical-JSON sha256 — the same convention the ProposalEnvelope uses."""
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _runtime_versions() -> dict:
    """What produced this bundle — needed to reproduce a run months later."""
    try:
        from koru import __version__ as koru_version
    except Exception:  # noqa: BLE001 — version lookup must never break evidence
        koru_version = "unknown"
    try:
        from koru.proposal_envelope import SCHEMA_VERSION as proposal_schema
    except Exception:  # noqa: BLE001
        proposal_schema = "unknown"
    return {
        "koru": koru_version,
        "proposal_schema": proposal_schema,
        "evidence_schema": SCHEMA_VERSION,
    }

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


def provenance_from_result(result: object) -> dict | None:
    """LLM provenance carried by the agent reply, or ``None`` for other lanes.

    The tillm shell lane keeps the full drive payload on ``LlmRunResult.raw``:
    ``provider`` is the one that actually served the request and
    ``provider_attempts`` the configured fallback queue. When the winner is
    not the queue's first choice the fallback is recorded here too, so the
    bundle alone answers *who proposed this change and why that provider* —
    without consulting loop logs. Provenance is context, never authority.
    """
    raw = getattr(result, "raw", None)
    raw = raw if isinstance(raw, dict) else {}
    provider = str(raw.get("provider") or "").strip() or None
    model = str(raw.get("model") or getattr(result, "model", "") or "").strip() or None
    attempts = [
        str(item).strip()
        for item in (raw.get("provider_attempts") or ())
        if str(item).strip()
    ]
    if not (provider or model or attempts):
        return None
    provenance: dict = {
        "provider": provider,
        "model": model,
        "provider_attempts": attempts or None,
    }
    if provider and attempts and attempts[0] != provider:
        skipped = attempts[: attempts.index(provider)] if provider in attempts else attempts[:1]
        provenance["fallback"] = (
            f"{' → '.join(skipped)} unavailable/exhausted; served by {provider}"
        )
    return provenance


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
    provenance: dict | None = None,
    bindings: dict | None = None,
    authorization: dict | None = None,
) -> dict:
    """Assemble the canonical bundle for a finished run.

    The verdict is computed by the transaction layer from outcomes — never by
    an LLM, whose text has no authority here. ``manifest=None`` is legitimate
    only for refusals that fired before the plan was frozen — there was nothing
    to pin because nothing was going to change. Every path that mutates has a
    manifest, and the bundle carries its hash so the two artifacts vouch for
    each other.
    """
    manifest_hash = (manifest or {}).get("manifest_hash")
    # The ladder's lower rungs, computed at assembly so they cannot disagree
    # with the fields they summarise. ``verification_hash`` pins what gate ran
    # and how it ended; ``execution_binding_hash`` ties proposal → manifest →
    # verification → delivery into one value an auditor can recompute.
    verification_hash = _sha256_of(verify) if verify else None
    execution_binding_hash = _sha256_of(
        {
            "proposal_sha256": (bindings or {}).get("proposal_sha256"),
            "manifest_hash": manifest_hash,
            "verification_hash": verification_hash,
            "grant_jti": (authorization or {}).get("jti"),
            "promotion": promotion,
            "verdict": verdict,
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "ticket_id": ticket.get("id"),
        "actor": actor,
        "provenance": provenance,
        # Top of the hash ladder: the ProposalEnvelope's verified hashes.
        # ``None`` means the legacy bare-diff contract, whose ladder starts
        # at patch_sha256/manifest_hash instead.
        "bindings": bindings,
        # Under which authority the mutation ran: contract flag, grant ``jti``
        # and the capabilities it covered. ``None`` = legacy unenforced run —
        # visible as such, matching the journal's missing ``authorized`` event.
        "authorization": authorization,
        "verification_hash": verification_hash,
        "execution_binding_hash": execution_binding_hash,
        "versions": _runtime_versions(),
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
