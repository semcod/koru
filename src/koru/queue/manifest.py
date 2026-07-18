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

from koru.queue.workspace import current_head, dirty_paths, fingerprint_files

MANIFEST_MISMATCH = "manifest_mismatch"
MANIFEST_NOT_PERSISTED = "manifest_not_persisted"


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
    base_files = {
        rel: (print_.sha256 or ("symlink:" + (print_.symlink_target or "")) if print_.exists else None)
        for rel, print_ in fingerprints.items()
    }
    manifest = {
        "run_id": run_id,
        "ticket_id": ticket.get("id"),
        "base_head": current_head(project),
        "base_files": base_files,
        "workspace_snapshot_sha256": workspace_snapshot_sha256(base_files),
        "dirty_files": sorted(dirty_paths(project, targets)),
        "patch_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "touched_files": sorted(targets),
        "verify_command": verify_command,
        "promotion_mode": mode,
        "attempt": attempt,
        "max_attempts": max_attempts,
    }
    manifest["manifest_hash"] = manifest_hash(manifest)
    return manifest


def workspace_snapshot_sha256(base_files: dict) -> str:
    """Digest of the frozen target-file snapshot (Subactor ``plan_hash`` analogue)."""
    payload = json.dumps(base_files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def manifest_run_directory(project: Path, run_id: str) -> Path:
    """Evidence directory for a single patch run."""
    return project / ".koru" / "runs" / run_id


def persist_manifest(project: Path, manifest: dict) -> Path:
    """Write an immutable manifest for audit and pre-promotion verification."""
    directory = manifest_run_directory(project, manifest["run_id"])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "manifest.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return path


def load_persisted_manifest(project: Path, run_id: str) -> dict | None:
    """Load a previously persisted run manifest, or ``None`` if missing."""
    path = manifest_run_directory(project, run_id) / "manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def persisted_manifest_mismatch(project: Path, manifest: dict) -> str:
    """Describe disagreement between *manifest* and its on-disk copy, or "" if aligned."""
    loaded = load_persisted_manifest(project, manifest["run_id"])
    if loaded is None:
        return "manifest was not persisted for this run"
    if manifest_hash(loaded) != manifest_hash(manifest):
        return "persisted manifest hash mismatch"
    return ""


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


