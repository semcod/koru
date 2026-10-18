"""Everything decided before a single byte of the workspace changes.

Preflight answers two questions: is this diff even usable, and is the workspace
in a state where the requested promotion is safe? Both are answered from data
that already exists, so a refusal here costs nothing and leaves nothing to undo.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from koru.proposal_envelope import (
    ProposalValidationError,
    looks_like_proposal_envelope,
    parse_proposal_envelope,
)
from koru.queue.patch_mode import (
    NO_PATCH_EMITTED,
    PATCH_INTRODUCES_SYMLINK,
    PROMOTION_COMMIT,
    PROMOTION_REFUSED_DIRTY_REPO,
    UNSAFE_DIRTY_WORKSPACE,
    PatchOutcome,
    build_manifest,
    diff_target_files,
    dirty_paths,
    extract_unified_diff,
    persist_manifest,
    promotion_mode,
    repository_is_clean,
    symlink_creations,
    symlinks_allowed,
    worktree_enabled,
)
from koru.queue.transaction.result import PatchPlan
from koru.queue.types import CommandResult


def extract_patch(
    result: CommandResult,
    *,
    project: Path | str | None = None,
    known_files: Iterable[str] | None = None,
) -> tuple[str | None, dict | None, PatchOutcome | None]:
    """Pull the unified diff out of an agent reply, or explain what came instead.

    The agent's exit code only says it produced *an answer*; whether that answer
    contained an applicable patch is a separate question. When the reply is a
    ProposalEnvelope, its verified hash bindings travel along as the second
    element — that is the top of the run's hash ladder
    (``input_hash → proposal_sha256 → plan → manifest``), and evidence wants it.
    """
    resolved_project = project if project is not None else getattr(result, "project", None)
    resolved_files = known_files if known_files is not None else getattr(result, "known_files", None)
    artifact = result.stdout
    bindings: dict | None = None
    if looks_like_proposal_envelope(artifact):
        try:
            envelope = parse_proposal_envelope(artifact)
        except ProposalValidationError as exc:
            return None, None, PatchOutcome(
                code=NO_PATCH_EMITTED,
                message=f"agent returned an invalid ProposalEnvelope: {exc}",
                retryable=exc.retryable,
            )
        if envelope.artifact_kind != "unified_diff":
            return None, None, PatchOutcome(
                code=NO_PATCH_EMITTED,
                message=(
                    "patch mode requires a unified_diff artifact, but the "
                    f"ProposalEnvelope contains {envelope.artifact_kind!r}"
                ),
                retryable=True,
            )
        artifact = str(envelope.artifact_content)
        bindings = {
            "intent_pack": {
                "id": envelope.intent_pack_id,
                "version": envelope.intent_pack_version,
            },
            "input_hash": envelope.input_hash,
            "prompt_schema_hash": envelope.prompt_schema_hash,
            "artifact_sha256": envelope.artifact_sha256,
            "proposal_sha256": envelope.proposal_sha256,
        }

    diff = extract_unified_diff(artifact, project=resolved_project, known_files=resolved_files)
    if diff is not None:
        return diff, bindings, None
    head = (result.stdout or "").strip().splitlines()
    summary = head[0][:200] if head else "(empty reply)"
    return None, None, PatchOutcome(
        code=NO_PATCH_EMITTED,
        message=(
            "agent returned no valid unified-diff artifact, so nothing could be applied. "
            f"First line of the reply: {summary}"
        ),
        retryable=True,
    )


PATCH_DESTRUCTIVE_TRUNCATION = "patch_destructive_truncation"
PATCH_INTRODUCES_ANTIPATTERN = "patch_introduces_antipattern"

_DIFF_FILE_RE = re.compile(r"^\+\+\+\s+(?:b/)?(\S+)")
_REMOVED_TOP_DEF_RE = re.compile(r"^-(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_ADDED_TOP_DEF_RE = re.compile(r"^\+(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_SPLIT_OR_DELETE_KEYWORDS = (
    "split",
    "delete",
    "remove",
    "extract",
    "decompose",
    "drop",
    "deprecate",
)
_LOOP_ANTIPATTERN_RE = re.compile(
    r"\b(?:subprocess\.(?:run|Popen|check_output|call)|sqlite3\.connect|yaml\.safe_load)\s*\("
)


def _is_test_path(rel_path: str) -> bool:
    norm = rel_path.replace("\\", "/").strip("/")
    parts = norm.split("/")
    filename = parts[-1] if parts else ""
    return (
        "tests" in parts
        or "test" in parts
        or filename.startswith("test_")
        or filename.endswith("_test.py")
    )


def screen_patch_quality(
    project: Path | None,
    ticket: dict | None,
    diff: str,
) -> PatchOutcome | None:
    """Reject patches that accidentally truncate modules or introduce severe anti-patterns."""
    if os.environ.get("KORU_DISABLE_PATCH_QUALITY_GATE") == "1":
        return None

    ticket_text = ""
    if isinstance(ticket, dict):
        ticket_text = " ".join(
            str(ticket.get(k) or "")
            for k in ("title", "description", "summary", "goal", "prompt")
        ).lower()
    allows_removal = any(kw in ticket_text for kw in _SPLIT_OR_DELETE_KEYWORDS)

    current_file: str | None = None
    removed_defs_by_file: dict[str, list[str]] = {}
    all_added_defs: set[str] = set()
    deleted_lines_by_file: dict[str, int] = {}
    added_lines_by_file: dict[str, int] = {}
    active_loop_indent: int | None = None

    for raw_line in diff.splitlines():
        m_file = _DIFF_FILE_RE.match(raw_line)
        if m_file:
            target = m_file.group(1)
            current_file = None if target == "/dev/null" else target
            active_loop_indent = None
            continue
        if raw_line.startswith("@@"):
            active_loop_indent = None
            continue
        if not current_file or not current_file.endswith(".py"):
            continue

        if raw_line.startswith("-") and not raw_line.startswith("---"):
            deleted_lines_by_file[current_file] = deleted_lines_by_file.get(current_file, 0) + 1
            m_rem = _REMOVED_TOP_DEF_RE.match(raw_line)
            if m_rem:
                sym = m_rem.group(1)
                if not sym.startswith("_"):
                    removed_defs_by_file.setdefault(current_file, []).append(sym)
        elif raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_lines_by_file[current_file] = added_lines_by_file.get(current_file, 0) + 1
            m_add = _ADDED_TOP_DEF_RE.match(raw_line)
            if m_add:
                all_added_defs.add(m_add.group(1))

            if not _is_test_path(current_file):
                code_line = raw_line[1:]
                stripped = code_line.lstrip()
                if not stripped or stripped.startswith("#"):
                    continue
                indent = len(code_line) - len(stripped)

                # PERF-AUDIT-SQLITE-002: with sqlite3.connect(...) without closing(...)
                if (
                    stripped.startswith("with ")
                    and "sqlite3.connect(" in stripped
                    and "closing(" not in stripped
                ):
                    return PatchOutcome(
                        code=PATCH_INTRODUCES_ANTIPATTERN,
                        message=(
                            f"patch in {current_file} uses `with sqlite3.connect(...)` which "
                            "does not close the SQLite connection on exit (PERF-AUDIT-SQLITE-002); "
                            "wrap it in `contextlib.closing(sqlite3.connect(...))`."
                        ),
                        retryable=True,
                    )

                if active_loop_indent is not None and indent <= active_loop_indent:
                    active_loop_indent = None
                if stripped.startswith(("for ", "async for ", "while ")) and stripped.endswith(":"):
                    active_loop_indent = indent
                elif active_loop_indent is not None and indent > active_loop_indent:
                    m_anti = _LOOP_ANTIPATTERN_RE.search(stripped)
                    if m_anti:
                        return PatchOutcome(
                            code=PATCH_INTRODUCES_ANTIPATTERN,
                            message=(
                                f"patch in {current_file} introduces `{m_anti.group(0)}...)` "
                                "directly inside a loop (PERF-AUDIT); hoist, batch, or cache "
                                "the operation outside the loop."
                            ),
                            retryable=True,
                        )

    if not allows_removal:
        for file_path, rem_syms in removed_defs_by_file.items():
            missing = [s for s in rem_syms if s not in all_added_defs]
            if len(missing) >= 3:
                sample = ", ".join(missing[:6])
                return PatchOutcome(
                    code=PATCH_DESTRUCTIVE_TRUNCATION,
                    message=(
                        f"patch destructively removes {len(missing)} public top-level "
                        f"symbols from {file_path} ({sample}) without re-adding them. "
                        "Preserve existing functions/classes and emit only targeted hunks."
                    ),
                    retryable=True,
                )
        for file_path, del_count in deleted_lines_by_file.items():
            add_count = added_lines_by_file.get(file_path, 0)
            if del_count >= 80 and add_count < 10:
                return PatchOutcome(
                    code=PATCH_DESTRUCTIVE_TRUNCATION,
                    message=(
                        f"patch deletes {del_count} lines and adds only {add_count} lines "
                        f"in {file_path}, which indicates accidental file truncation. "
                        "Preserve existing code outside the targeted change."
                    ),
                    retryable=True,
                )
    return None


def screen_diff_contents(diff: str) -> PatchOutcome | None:
    """Refuse diffs whose content is unsafe regardless of where they apply.

    ``git apply`` blocks ``../`` traversal but not a link pointing anywhere on
    the filesystem, which would let a scoped patch reach outside its workspace.
    """
    if not symlink_creations(diff) or symlinks_allowed():
        return None
    return PatchOutcome(
        code=PATCH_INTRODUCES_SYMLINK,
        message=(
            "the patch creates a symlink, which would let it point outside the "
            "workspace it is scoped to. Set KORU_QUEUE_ALLOW_SYMLINKS=1 if this "
            "project legitimately needs agent-authored symlinks."
        ),
    )


def build_patch_plan(
    project: Path,
    ticket: dict,
    diff: str,
    manifest: dict | None = None,
    proposal: dict | None = None,
) -> PatchPlan:
    """Resolve, once, every fact the later phases decide on.

    Targets are read before the gate: a profile that takes file arguments
    renders against exactly the files this diff touches.
    """
    from koru.queue.verify.resolver import resolve_verify

    repaired = extract_unified_diff(
        diff,
        project=project,
        known_files=ticket.get("files") if isinstance(ticket, dict) else None,
    )
    if repaired:
        diff = repaired

    targets = diff_target_files(project, diff)
    resolution = resolve_verify(project, ticket, targets)
    return PatchPlan(
        project=project,
        ticket=ticket,
        diff=diff,
        targets=targets,
        verify_command=resolution.command,
        mode=promotion_mode(ticket),
        run_id=manifest["run_id"] if manifest else uuid4().hex[:12],
        isolated=bool(resolution.command) and worktree_enabled(project),
        verify_source=resolution.source,
        verify_error=resolution.error,
        proposal=proposal,
    )


def run_patch_preflight(
    project: Path,
    result: CommandResult,
    ticket: dict,
    manifest: dict | None = None,
) -> tuple[PatchPlan | None, PatchOutcome | None]:
    """Extract, repair/synthesize, screen, and plan a patch against *project*."""
    diff, proposal, refusal = extract_patch(
        result,
        project=project,
        known_files=ticket.get("files") if isinstance(ticket, dict) else None,
    )
    if diff is None or refusal is not None:
        return None, refusal
    refusal = screen_diff_contents(diff)
    if refusal is not None:
        return None, refusal
    refusal = screen_patch_quality(project, ticket, diff)
    if refusal is not None:
        return None, refusal
    return build_patch_plan(project, ticket, diff, manifest, proposal=proposal), None


def screen_promotion_preconditions(plan: PatchPlan) -> PatchOutcome | None:
    """Refuse a promotion the workspace cannot honour cleanly."""
    if plan.mode != PROMOTION_COMMIT or repository_is_clean(plan.project):
        return None
    return PatchOutcome(
        code=PROMOTION_REFUSED_DIRTY_REPO,
        message=(
            "promotion_mode=commit requires a clean repository so the commit "
            "contains only this patch, but the working tree has uncommitted "
            "changes. Commit or stash them, or use promotion_mode=branch."
        ),
    )


def screen_direct_apply(plan: PatchPlan) -> PatchOutcome | None:
    """Refuse to patch dirty files in place, where rollback would lose work.

    Without isolation the only rollback is ``git checkout --``, which restores
    from the index and would destroy any pre-existing unstaged edit. Refusing
    beats promising a rollback that silently discards the user's work.
    """
    dirty = dirty_paths(plan.project, plan.targets)
    if not dirty:
        return None
    return PatchOutcome(
        code=UNSAFE_DIRTY_WORKSPACE,
        message=(
            "refusing to apply the patch directly: "
            f"{', '.join(dirty)} already carry uncommitted changes, and a "
            "rollback would discard them. Commit or stash them, or enable "
            "worktree isolation (KORU_QUEUE_WORKTREE=1)."
        ),
    )


class ManifestFreeze:
    """The plan pinned to disk, built once and re-persisted on demand.

    The manifest records the base commit and the exact content of every target,
    so promotion can prove the world did not move underneath a verification that
    took minutes. It is built lazily because some modes never need one, and only
    ever built *once* — a second build would pin a workspace that has since been
    patched, which is precisely the drift it exists to detect.
    """

    def __init__(self, plan: PatchPlan, manifest: dict | None = None) -> None:
        self._plan = plan
        self._manifest = manifest

    @property
    def manifest(self) -> dict | None:
        return self._manifest

    def freeze(self) -> dict:
        """Pin the plan if it is not pinned yet, then write it out.

        Always a first attempt: a retry does not come through here at all, it
        arrives with the manifest ``patch_retry`` already pinned and passed in.
        """
        if self._manifest is None:
            self._manifest = build_manifest(
                self._plan.project,
                run_id=self._plan.run_id,
                ticket=self._plan.ticket,
                diff=self._plan.diff,
                targets=self._plan.targets,
                verify_command=self._plan.verify_command,
                mode=self._plan.mode,
                attempt=1,
                max_attempts=1,
            )
        persist_manifest(self._plan.project, self._manifest)
        return self._manifest
