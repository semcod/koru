#!/usr/bin/env python3
"""Capture and verify bounded work-continuity checkpoints.

The local registry is a recoverable cache outside the tracked checkout. A
controller that promises cross-machine durability must persist the emitted
checkpoint in its protected receipt store. A checkpoint is never authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit


CHECKPOINT_SCHEMA = "new-project.work-continuity/v1"
REGISTRY_SCHEMA = "new-project.work-continuity-registry/v1"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TICKET_RE = re.compile(r"^ticket-[0-9]{3,}$")
WORKSTREAM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
WORKTREE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
REPOSITORY_RE = re.compile(r"^repository:[A-Za-z0-9][A-Za-z0-9._/-]{0,500}$")
CRITERION_RE = re.compile(r"^AC-[0-9]{2,}$")
REFERENCE_RE = re.compile(
    r"^(artifact|authorization|decision|knowledge|receipt):"
    r"[a-z0-9][a-z0-9._:/-]{0,510}$"
)
IDEMPOTENCY_RE = re.compile(r"^idempotency:[a-z0-9][a-z0-9._-]{0,127}$")
PHASES = {"analysis", "plan", "tools", "edit", "validation", "publication", "blocked"}
NEXT_ACTIONS = {"observe", "edit", "validate", "publish", "reconcile", "wait"}
EFFECT_KINDS = {
    "push", "pull-request", "validation", "merge", "release", "external-coordination"
}
EFFECT_STATES = {"planned", "in-flight", "failed"}


class ContinuityError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise ContinuityError(code, message)


def load_json(path: Path) -> Any:
    try:
        if path.stat().st_size > 1024 * 1024:
            fail("GOV-CONTINUITY-001", f"continuity document is too large: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    except ContinuityError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail("GOV-CONTINUITY-001", f"cannot read continuity document {path}: {exc}")


def exact_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        fail("GOV-CONTINUITY-001", f"{label} fields are invalid")
    return value


def string(value: Any, label: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        fail("GOV-CONTINUITY-001", f"{label} must be a bounded non-empty string")
    if any(ord(character) < 32 for character in value):
        fail("GOV-CONTINUITY-001", f"{label} contains control characters")
    return value


def reference(value: Any, label: str, *, kind: str | None = None) -> str:
    result = string(value, label)
    match = REFERENCE_RE.fullmatch(result)
    if match is None or (kind is not None and match.group(1) != kind):
        fail("GOV-CONTINUITY-001", f"{label} is not an allowed opaque {kind or 'evidence'} reference")
    return result


def sha(value: Any, label: str, expression: re.Pattern[str]) -> str:
    if not isinstance(value, str) or expression.fullmatch(value) is None:
        fail("GOV-CONTINUITY-001", f"{label} has an invalid digest")
    return value


def unique_strings(value: Any, label: str, expression: re.Pattern[str], maximum: int = 128) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        fail("GOV-CONTINUITY-001", f"{label} must be a bounded array")
    if any(not isinstance(item, str) or expression.fullmatch(item) is None for item in value):
        fail("GOV-CONTINUITY-001", f"{label} contains an invalid item")
    if len(value) != len(set(value)):
        fail("GOV-CONTINUITY-001", f"{label} contains duplicates")
    return value


def git_ref(value: Any, label: str) -> str:
    result = string(value, label, maximum=255)
    invalid = (
        result.startswith(("/", "."))
        or result.endswith(("/", ".", ".lock"))
        or any(token in result for token in ("..", "//", "@{", "\\", " "))
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", result) is None
    )
    if invalid:
        fail("GOV-CONTINUITY-001", f"{label} is not a safe Git ref")
    return result


def timestamp(value: Any) -> str:
    result = string(value, "recordedAt", maximum=64)
    if not result.endswith("Z"):
        fail("GOV-CONTINUITY-001", "recordedAt must be UTC and end with Z")
    try:
        parsed = datetime.fromisoformat(result[:-1] + "+00:00")
    except ValueError:
        fail("GOV-CONTINUITY-001", "recordedAt is not an RFC 3339 timestamp")
    if parsed.tzinfo != timezone.utc:
        fail("GOV-CONTINUITY-001", "recordedAt must use UTC")
    return result


def validate_workspace(value: Any) -> dict[str, Any]:
    workspace = exact_object(
        value,
        {"state", "statusSha256", "snapshotRef", "snapshotSha256", "secretScanReceipt"},
        "workspace",
    )
    if workspace["state"] not in {"clean", "snapshotted"}:
        fail("GOV-CONTINUITY-001", "workspace state must be clean or snapshotted")
    sha(workspace["statusSha256"], "workspace.statusSha256", SHA256_RE)
    if workspace["state"] == "clean":
        if workspace["statusSha256"] != EMPTY_SHA256:
            fail("GOV-CONTINUITY-001", "clean workspace must bind the empty status digest")
        if any(
            workspace[field] is not None
            for field in ("snapshotRef", "snapshotSha256", "secretScanReceipt")
        ):
            fail("GOV-CONTINUITY-001", "clean workspace cannot claim a snapshot")
    else:
        reference(workspace["snapshotRef"], "workspace.snapshotRef", kind="artifact")
        sha(workspace["snapshotSha256"], "workspace.snapshotSha256", SHA256_RE)
        reference(workspace["secretScanReceipt"], "workspace.secretScanReceipt", kind="receipt")
        if workspace["statusSha256"] == EMPTY_SHA256:
            fail("GOV-CONTINUITY-001", "snapshotted workspace must bind a non-empty status digest")
    return workspace


def validate_lease(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    lease = exact_object(value, {"leaseRef", "leaseRevision", "fencingToken"}, "lease")
    reference(lease["leaseRef"], "lease.leaseRef", kind="receipt")
    for field in ("leaseRevision", "fencingToken"):
        if not isinstance(lease[field], int) or isinstance(lease[field], bool) or lease[field] < 1:
            fail("GOV-CONTINUITY-001", f"lease.{field} must be a positive integer")
    return lease


def validate_pending_effect(value: Any, index: int) -> dict[str, Any]:
    effect = exact_object(
        value, {"kind", "state", "idempotencyKey", "effectRef"}, f"pendingEffects[{index}]"
    )
    if effect["kind"] not in EFFECT_KINDS or effect["state"] not in EFFECT_STATES:
        fail("GOV-CONTINUITY-001", f"pendingEffects[{index}] uses an unsupported enum")
    if not isinstance(effect["idempotencyKey"], str) or IDEMPOTENCY_RE.fullmatch(effect["idempotencyKey"]) is None:
        fail("GOV-CONTINUITY-001", f"pendingEffects[{index}].idempotencyKey is invalid")
    if effect["effectRef"] is not None:
        reference(effect["effectRef"], f"pendingEffects[{index}].effectRef")
    return effect


def validate_checkpoint(value: Any) -> dict[str, Any]:
    fields = {
        "schema", "authority", "checkpointRef", "previousCheckpointRef", "sequence",
        "repositoryRef", "ticket", "workstream", "intentRef", "intentSha256",
        "scopeSha256", "targetBranch", "branchRef", "headSha", "worktreeId", "phase",
        "authorizationRef", "lease", "workspace", "completedCriteria",
        "remainingCriteria", "evidenceRefs", "pendingEffects", "nextAction", "recordedAt",
    }
    checkpoint = exact_object(value, fields, "checkpoint")
    if checkpoint["schema"] != CHECKPOINT_SCHEMA or checkpoint["authority"] != "advisory-projection":
        fail("GOV-CONTINUITY-001", "checkpoint schema or authority is invalid")
    reference(checkpoint["checkpointRef"], "checkpointRef", kind="receipt")
    if checkpoint["previousCheckpointRef"] is not None:
        reference(checkpoint["previousCheckpointRef"], "previousCheckpointRef", kind="receipt")
    sequence = checkpoint["sequence"]
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        fail("GOV-CONTINUITY-001", "sequence must be a positive integer")
    if (sequence == 1) != (checkpoint["previousCheckpointRef"] is None):
        fail("GOV-CONTINUITY-002", "checkpoint sequence and previous reference do not agree")
    repository = string(checkpoint["repositoryRef"], "repositoryRef")
    if REPOSITORY_RE.fullmatch(repository) is None or ".." in repository or "//" in repository:
        fail("GOV-CONTINUITY-001", "repositoryRef is not a credential-free repository identity")
    if not isinstance(checkpoint["ticket"], str) or TICKET_RE.fullmatch(checkpoint["ticket"]) is None:
        fail("GOV-CONTINUITY-001", "ticket is invalid")
    if not isinstance(checkpoint["workstream"], str) or WORKSTREAM_RE.fullmatch(checkpoint["workstream"]) is None:
        fail("GOV-CONTINUITY-001", "workstream is invalid")
    reference(checkpoint["intentRef"], "intentRef", kind="artifact")
    sha(checkpoint["intentSha256"], "intentSha256", SHA256_RE)
    sha(checkpoint["scopeSha256"], "scopeSha256", SHA256_RE)
    git_ref(checkpoint["targetBranch"], "targetBranch")
    git_ref(checkpoint["branchRef"], "branchRef")
    sha(checkpoint["headSha"], "headSha", SHA1_RE)
    if not isinstance(checkpoint["worktreeId"], str) or WORKTREE_RE.fullmatch(checkpoint["worktreeId"]) is None:
        fail("GOV-CONTINUITY-001", "worktreeId is invalid")
    if checkpoint["phase"] not in PHASES:
        fail("GOV-CONTINUITY-001", "phase is invalid")
    reference(checkpoint["authorizationRef"], "authorizationRef", kind="authorization")
    validate_lease(checkpoint["lease"])
    validate_workspace(checkpoint["workspace"])
    completed = unique_strings(checkpoint["completedCriteria"], "completedCriteria", CRITERION_RE)
    remaining = unique_strings(checkpoint["remainingCriteria"], "remainingCriteria", CRITERION_RE)
    if set(completed) & set(remaining):
        fail("GOV-CONTINUITY-001", "completed and remaining criteria overlap")
    evidence = checkpoint["evidenceRefs"]
    if not isinstance(evidence, list) or len(evidence) > 128:
        fail("GOV-CONTINUITY-001", "evidenceRefs must be a bounded array")
    for index, item in enumerate(evidence):
        reference(item, f"evidenceRefs[{index}]")
    if len(evidence) != len(set(evidence)):
        fail("GOV-CONTINUITY-001", "evidenceRefs contains duplicates")
    effects = checkpoint["pendingEffects"]
    if not isinstance(effects, list) or len(effects) > 32:
        fail("GOV-CONTINUITY-001", "pendingEffects must be a bounded array")
    validated_effects = [validate_pending_effect(item, index) for index, item in enumerate(effects)]
    keys = [item["idempotencyKey"] for item in validated_effects]
    if len(keys) != len(set(keys)):
        fail("GOV-CONTINUITY-001", "pending effect idempotency keys must be unique")
    next_action = exact_object(checkpoint["nextAction"], {"kind", "criterion"}, "nextAction")
    if next_action["kind"] not in NEXT_ACTIONS:
        fail("GOV-CONTINUITY-001", "nextAction.kind is invalid")
    if next_action["criterion"] is not None and (
        not isinstance(next_action["criterion"], str)
        or CRITERION_RE.fullmatch(next_action["criterion"]) is None
    ):
        fail("GOV-CONTINUITY-001", "nextAction.criterion is invalid")
    if next_action["criterion"] is not None and next_action["criterion"] not in remaining:
        fail("GOV-CONTINUITY-001", "next action criterion must remain unfinished")
    timestamp(checkpoint["recordedAt"])
    digest_payload = dict(checkpoint)
    digest_payload.pop("checkpointRef")
    expected_ref = (
        f"receipt:continuity.{checkpoint['ticket']}.{sequence}."
        f"{canonical_digest(digest_payload)}"
    )
    if checkpoint["checkpointRef"] != expected_ref:
        fail("GOV-CONTINUITY-002", "checkpoint reference does not bind its canonical content")
    return checkpoint


def validate_registry(value: Any) -> dict[str, Any]:
    registry = exact_object(value, {"schema", "repositoryRef", "checkpoints"}, "registry")
    if registry["schema"] != REGISTRY_SCHEMA:
        fail("GOV-CONTINUITY-001", "registry schema is invalid")
    repository = string(registry["repositoryRef"], "registry.repositoryRef")
    if REPOSITORY_RE.fullmatch(repository) is None or ".." in repository or "//" in repository:
        fail("GOV-CONTINUITY-001", "registry repositoryRef is invalid")
    checkpoints = registry["checkpoints"]
    if not isinstance(checkpoints, list):
        fail("GOV-CONTINUITY-001", "registry checkpoints must be an array")
    seen: dict[str, dict[str, Any]] = {}
    latest: dict[str, dict[str, Any]] = {}
    for item in checkpoints:
        checkpoint = validate_checkpoint(item)
        if checkpoint["repositoryRef"] != repository:
            fail("GOV-CONTINUITY-002", "checkpoint belongs to another repository")
        checkpoint_ref = checkpoint["checkpointRef"]
        if checkpoint_ref in seen:
            fail("GOV-CONTINUITY-002", "checkpoint reference is not append-only unique")
        prior = latest.get(checkpoint["ticket"])
        expected_sequence = 1 if prior is None else prior["sequence"] + 1
        expected_previous = None if prior is None else prior["checkpointRef"]
        if checkpoint["sequence"] != expected_sequence or checkpoint["previousCheckpointRef"] != expected_previous:
            fail("GOV-CONTINUITY-002", f"checkpoint chain for {checkpoint['ticket']} is not monotonic")
        seen[checkpoint_ref] = checkpoint
        latest[checkpoint["ticket"]] = checkpoint
    return registry


def validate_document(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("schema") == CHECKPOINT_SCHEMA:
        return validate_checkpoint(value)
    if isinstance(value, dict) and value.get("schema") == REGISTRY_SCHEMA:
        return validate_registry(value)
    fail("GOV-CONTINUITY-001", "unsupported continuity schema")


def git(root: Path, *arguments: str, binary: bool = False) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail("GOV-CONTINUITY-003", f"cannot observe Git state for {arguments[0]}: {exc}")
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def repository_ref(root: Path) -> str:
    """Return a transport-independent identity without URL credentials."""
    value = git(root, "config", "--get", "remote.origin.url")
    assert isinstance(value, str)
    origin = string(value, "repository origin")
    host = ""
    repository_path = ""
    if "://" in origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"git", "http", "https", "ssh"} or not parsed.hostname:
            fail("GOV-CONTINUITY-001", "repository origin uses an unsupported transport")
        try:
            port = parsed.port
        except ValueError:
            fail("GOV-CONTINUITY-001", "repository origin has an invalid port")
        host = parsed.hostname if port is None else f"{parsed.hostname}.port-{port}"
        repository_path = parsed.path
    else:
        match = re.fullmatch(r"(?:[^@/:]+@)?([^/:]+):(.+)", origin)
        if match is None:
            fail("GOV-CONTINUITY-001", "repository origin must name a remote host and path")
        host, repository_path = match.groups()
    repository_path = repository_path.lstrip("/")
    if repository_path.endswith(".git"):
        repository_path = repository_path[:-4]
    identity = f"repository:{host.lower()}/{repository_path}"
    if REPOSITORY_RE.fullmatch(identity) is None or ".." in identity or "//" in identity:
        fail("GOV-CONTINUITY-001", "repository origin cannot be normalized safely")
    return identity


def default_registry(root: Path) -> Path:
    value = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    assert isinstance(value, str)
    return Path(value) / "new-project" / "work-continuity.json"


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def intent_state(root: Path, ticket: str) -> tuple[dict[str, Any], str, str, str]:
    path = root / "project" / ticket / "intent.json"
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail("GOV-CONTINUITY-003", f"cannot resolve active ticket intent: {exc}")
    if not isinstance(value, dict) or value.get("ticket") != ticket:
        fail("GOV-CONTINUITY-003", "ticket intent identity does not match")
    workstream = value.get("workstream")
    if not isinstance(workstream, str) or WORKSTREAM_RE.fullmatch(workstream) is None:
        fail("GOV-CONTINUITY-003", "ticket intent workstream is invalid")
    delivery = value.get("delivery")
    target_branch = delivery.get("targetBranch") if isinstance(delivery, dict) else None
    git_ref(target_branch, "intent target branch")
    scope = {
        "ticket": value.get("ticket"),
        "workstream": value.get("workstream"),
        "allowedPaths": value.get("allowedPaths"),
        "forbiddenPaths": value.get("forbiddenPaths"),
        "dependsOn": value.get("dependsOn"),
        "conflictsWith": value.get("conflictsWith"),
        "integrationTicket": value.get("integrationTicket"),
        "targetBranch": target_branch,
    }
    return value, hashlib.sha256(raw).hexdigest(), canonical_digest(scope), target_branch


def read_registry(path: Path, repository: str) -> dict[str, Any]:
    if not path.exists():
        return {"schema": REGISTRY_SCHEMA, "repositoryRef": repository, "checkpoints": []}
    registry = validate_registry(load_json(path))
    if registry["repositoryRef"] != repository:
        fail("GOV-CONTINUITY-002", "continuity registry belongs to another repository")
    return registry


def append_checkpoint(registry: dict[str, Any], checkpoint: dict[str, Any]) -> bool:
    for existing in registry["checkpoints"]:
        if existing["checkpointRef"] == checkpoint["checkpointRef"]:
            if existing != checkpoint:
                fail("GOV-CONTINUITY-002", "checkpoint reference already binds different content")
            return False
    prior = None
    for existing in registry["checkpoints"]:
        if existing["ticket"] == checkpoint["ticket"]:
            prior = existing
    expected_sequence = 1 if prior is None else prior["sequence"] + 1
    expected_previous = None if prior is None else prior["checkpointRef"]
    if checkpoint["sequence"] != expected_sequence or checkpoint["previousCheckpointRef"] != expected_previous:
        fail("GOV-CONTINUITY-002", "new checkpoint does not extend the latest ticket chain")
    registry["checkpoints"].append(checkpoint)
    validate_registry(registry)
    return True


def write_registry(path: Path, registry: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="work-continuity.", suffix=".json", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(registry, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        try:
            directory_descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError:
            # Windows and some network filesystems do not expose directory fsync.
            pass
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_pending(value: str) -> dict[str, Any]:
    fields = value.split(",", 3)
    if len(fields) not in {3, 4}:
        fail("GOV-CONTINUITY-001", "--pending expects kind,state,idempotencyKey[,effectRef]")
    return {
        "kind": fields[0],
        "state": fields[1],
        "idempotencyKey": fields[2],
        "effectRef": fields[3] if len(fields) == 4 and fields[3] else None,
    }


def capture(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    repository = repository_ref(root)
    registry_path = args.registry.resolve() if args.registry else default_registry(root)
    registry = read_registry(registry_path, repository)
    intent, intent_digest, scope_digest, target_branch = intent_state(root, args.ticket)
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    head = git(root, "rev-parse", "HEAD")
    status_bytes = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True)
    assert isinstance(branch, str) and isinstance(head, str) and isinstance(status_bytes, bytes)
    status_digest = hashlib.sha256(status_bytes).hexdigest()
    if status_bytes:
        if any(
            value is None
            for value in (args.snapshot_ref, args.snapshot_sha256, args.snapshot_secret_scan_receipt)
        ):
            fail(
                "GOV-CONTINUITY-001",
                "dirty workspace needs an externally stored, secret-scanned snapshot reference and digest",
            )
        workspace = {
            "state": "snapshotted",
            "statusSha256": status_digest,
            "snapshotRef": args.snapshot_ref,
            "snapshotSha256": args.snapshot_sha256,
            "secretScanReceipt": args.snapshot_secret_scan_receipt,
        }
    else:
        if any(
            value is not None
            for value in (args.snapshot_ref, args.snapshot_sha256, args.snapshot_secret_scan_receipt)
        ):
            fail("GOV-CONTINUITY-001", "clean workspace cannot claim a snapshot")
        workspace = {
            "state": "clean",
            "statusSha256": EMPTY_SHA256,
            "snapshotRef": None,
            "snapshotSha256": None,
            "secretScanReceipt": None,
        }
    prior = next(
        (item for item in reversed(registry["checkpoints"]) if item["ticket"] == args.ticket),
        None,
    )
    sequence = 1 if prior is None else prior["sequence"] + 1
    lease = None
    lease_values = (args.lease_ref, args.lease_revision, args.fencing_token)
    if any(value is not None for value in lease_values):
        if not all(value is not None for value in lease_values):
            fail("GOV-CONTINUITY-001", "lease reference, revision and fencing token must be supplied together")
        lease = {
            "leaseRef": args.lease_ref,
            "leaseRevision": args.lease_revision,
            "fencingToken": args.fencing_token,
        }
    checkpoint: dict[str, Any] = {
        "schema": CHECKPOINT_SCHEMA,
        "authority": "advisory-projection",
        "checkpointRef": "receipt:pending",
        "previousCheckpointRef": None if prior is None else prior["checkpointRef"],
        "sequence": sequence,
        "repositoryRef": repository,
        "ticket": args.ticket,
        "workstream": intent["workstream"],
        "intentRef": f"artifact:intent/{args.ticket}/{intent_digest}",
        "intentSha256": intent_digest,
        "scopeSha256": scope_digest,
        "targetBranch": target_branch,
        "branchRef": branch,
        "headSha": head,
        "worktreeId": args.worktree_id,
        "phase": args.phase,
        "authorizationRef": args.authorization_ref,
        "lease": lease,
        "workspace": workspace,
        "completedCriteria": args.completed,
        "remainingCriteria": args.remaining,
        "evidenceRefs": args.evidence,
        "pendingEffects": [parse_pending(value) for value in args.pending],
        "nextAction": {"kind": args.next_action, "criterion": args.next_criterion},
        "recordedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    digest_payload = dict(checkpoint)
    digest_payload.pop("checkpointRef")
    checkpoint["checkpointRef"] = (
        f"receipt:continuity.{args.ticket}.{sequence}.{canonical_digest(digest_payload)}"
    )
    validate_checkpoint(checkpoint)
    append_checkpoint(registry, checkpoint)
    write_registry(registry_path, registry)
    return checkpoint


def record(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    repository = repository_ref(root)
    registry_path = args.registry.resolve() if args.registry else default_registry(root)
    checkpoint = validate_checkpoint(load_json(args.checkpoint))
    if checkpoint["repositoryRef"] != repository:
        fail("GOV-CONTINUITY-002", "checkpoint belongs to another repository")
    registry = read_registry(registry_path, repository)
    changed = append_checkpoint(registry, checkpoint)
    if changed:
        write_registry(registry_path, registry)
    return {"status": "recorded" if changed else "already-recorded", "checkpoint": checkpoint}


def latest_checkpoint(registry: dict[str, Any], ticket: str) -> dict[str, Any]:
    for checkpoint in reversed(registry["checkpoints"]):
        if checkpoint["ticket"] == ticket:
            return checkpoint
    fail("GOV-CONTINUITY-002", f"no continuity checkpoint exists for {ticket}")


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    repository = repository_ref(root)
    registry_path = args.registry.resolve() if args.registry else default_registry(root)
    registry = read_registry(registry_path, repository)
    return latest_checkpoint(registry, args.ticket)


def verify_checkpoint(root: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    observations: dict[str, Any] = {}
    observations["repositoryRef"] = repository_ref(root)
    observations["branchRef"] = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    observations["headSha"] = git(root, "rev-parse", "HEAD")
    _, intent_digest, scope_digest, target_branch = intent_state(root, checkpoint["ticket"])
    observations["intentSha256"] = intent_digest
    observations["scopeSha256"] = scope_digest
    observations["targetBranch"] = target_branch
    status_bytes = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True)
    assert isinstance(status_bytes, bytes)
    observations["statusSha256"] = hashlib.sha256(status_bytes).hexdigest()
    expected = {
        "repositoryRef": checkpoint["repositoryRef"],
        "branchRef": checkpoint["branchRef"],
        "headSha": checkpoint["headSha"],
        "intentSha256": checkpoint["intentSha256"],
        "scopeSha256": checkpoint["scopeSha256"],
        "targetBranch": checkpoint["targetBranch"],
        "statusSha256": checkpoint["workspace"]["statusSha256"],
    }
    mismatches = {
        field: {"expected": expected[field], "observed": observations[field]}
        for field in expected
        if expected[field] != observations[field]
    }
    if mismatches:
        fail("GOV-CONTINUITY-003", "checkpoint diverges from current repository observation: " + ", ".join(mismatches))
    return {
        "status": "matches-observed-state",
        "checkpointRef": checkpoint["checkpointRef"],
        "authority": "advisory-projection",
        "authorityVerified": False,
        "leaseMustBeRevalidated": checkpoint["lease"] is not None,
    }


def verify(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    if args.checkpoint:
        checkpoint = validate_checkpoint(load_json(args.checkpoint))
    else:
        checkpoint = resolve(args)
    return verify_checkpoint(root, checkpoint)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate a checkpoint or registry")
    validate_parser.add_argument("document", type=Path)

    capture_parser = subparsers.add_parser("capture", help="capture and append the current repository state")
    capture_parser.add_argument("--root", type=Path, default=Path.cwd())
    capture_parser.add_argument("--registry", type=Path)
    capture_parser.add_argument("--ticket", required=True)
    capture_parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    capture_parser.add_argument("--worktree-id", required=True)
    capture_parser.add_argument("--authorization-ref", required=True)
    capture_parser.add_argument("--lease-ref")
    capture_parser.add_argument("--lease-revision", type=int)
    capture_parser.add_argument("--fencing-token", type=int)
    capture_parser.add_argument("--snapshot-ref")
    capture_parser.add_argument("--snapshot-sha256")
    capture_parser.add_argument("--snapshot-secret-scan-receipt")
    capture_parser.add_argument("--completed", action="append", default=[])
    capture_parser.add_argument("--remaining", action="append", default=[])
    capture_parser.add_argument("--evidence", action="append", default=[])
    capture_parser.add_argument("--pending", action="append", default=[])
    capture_parser.add_argument("--next-action", choices=sorted(NEXT_ACTIONS), required=True)
    capture_parser.add_argument("--next-criterion")

    record_parser = subparsers.add_parser("record", help="append a restored checkpoint to the local cache")
    record_parser.add_argument("--root", type=Path, default=Path.cwd())
    record_parser.add_argument("--registry", type=Path)
    record_parser.add_argument("--checkpoint", type=Path, required=True)

    resolve_parser = subparsers.add_parser("resolve", help="resolve the latest checkpoint for a ticket")
    resolve_parser.add_argument("--root", type=Path, default=Path.cwd())
    resolve_parser.add_argument("--registry", type=Path)
    resolve_parser.add_argument("--ticket", required=True)

    verify_parser = subparsers.add_parser("verify", help="compare a checkpoint with current observable state")
    verify_parser.add_argument("--root", type=Path, default=Path.cwd())
    verify_parser.add_argument("--registry", type=Path)
    source = verify_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--checkpoint", type=Path)
    source.add_argument("--ticket")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "validate":
            document = validate_document(load_json(args.document))
            output: Any = {"status": "valid", "schema": document["schema"]}
        elif args.command == "capture":
            output = capture(args)
        elif args.command == "record":
            output = record(args)
        elif args.command == "resolve":
            output = resolve(args)
        else:
            output = verify(args)
        print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except ContinuityError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return 3 if exc.code == "GOV-CONTINUITY-003" else 2


if __name__ == "__main__":
    raise SystemExit(main())
