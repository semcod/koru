"""The frozen plan a run is judged against.

A manifest records what the workspace looked like when a patch was accepted:
the base commit, the exact content of every file it touches, and the hash of
the patch itself. Promotion and retries both re-check it, so a run can prove
the world did not move underneath a verification that took minutes — which is
the difference between refusing a stale change and silently overwriting
someone else's work.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from koru.queue.workspace import current_head, fingerprint_files

MANIFEST_MISMATCH = "manifest_mismatch"


def build_manifest(
    project: Path,
    *,
    run_id: str,
    ticket: dict,
    diff: str,
    targets: tuple[str, ...],
    verify_command: str,
    mode: str,
    attempt: int,
    max_attempts: int,
) -> dict:
    """Freeze what this run is allowed to do, and against what.

    Recorded before anything is staged so promotion can prove the world did not
    move underneath it. Deliberately carries no timestamp: the hash must depend
    only on the decision, so the same inputs always produce the same manifest.
    """
    fingerprints = fingerprint_files(project, targets)
    manifest = {
        "run_id": run_id,
        "ticket_id": ticket.get("id"),
        "base_head": current_head(project),
        "base_files": {
            rel: (print_.sha256 or ("symlink:" + (print_.symlink_target or "")) if print_.exists else None)
            for rel, print_ in fingerprints.items()
        },
        "patch_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "touched_files": sorted(targets),
        "verify_command": verify_command,
        "promotion_mode": mode,
        "attempt": attempt,
        "max_attempts": max_attempts,
    }
    manifest["manifest_hash"] = manifest_hash(manifest)
    return manifest


def manifest_hash(manifest: dict) -> str:
    """Canonical hash of a manifest, ignoring any hash already recorded on it."""
    payload = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()


def manifest_drift(project: Path, manifest: dict) -> str:
    """Describe how the workspace diverged from the manifest, or "" if it has not.

    Checks the commit *and* the file contents, because the change that matters
    most here — another session editing a target file — need not be committed
    to invalidate the plan.
    """
    if manifest.get("base_head") and current_head(project) != manifest["base_head"]:
        return f"HEAD moved from {str(manifest['base_head'])[:12]} to {current_head(project)[:12]}"
    recorded: dict = manifest.get("base_files") or {}
    current = fingerprint_files(project, tuple(recorded))
    drifted = sorted(
        rel
        for rel, digest in recorded.items()
        if (current[rel].sha256 if current[rel].exists else None) != digest
    )
    return f"changed on disk: {', '.join(drifted)}" if drifted else ""


