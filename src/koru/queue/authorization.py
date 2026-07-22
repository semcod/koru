"""Composing contract and grant into the transaction's one authorization hook.

The transaction calls the authorizer once, after the manifest freeze and before
any mutation. What the authorizer checks depends on what the project turned on:

- a ticket naming a contract gets contract evaluation (paths, size, capability,
  risk) against the frozen plan;
- with ``KORU_QUEUE_REQUIRE_GRANT=1`` a signed grant is additionally minted by
  local control (this process holds the private key), verified against the
  frozen bindings with the executor's public key, and its ``jti`` claimed —
  so the full signature/binding/replay path runs even while issuer and
  executor share a process, and splitting them later changes wiring, not law;
- grant enforcement also demands ``KORU_MUTATIONS_ENABLED=1`` — the master
  kill switch that nothing overrides.

No configuration → no authorizer → the transaction behaves as before. Policy
narrows; its absence must not change history.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from koru.queue.contracts import (
    CAP_STAGE,
    contract_for_ticket,
    promotion_capability,
)
from koru.queue.grant import (
    GrantBindings,
    generate_keypair,
    issue_grant,
    mutations_enabled,
    verify_grant,
)
from koru.queue.grant_store import claim_jti
from koru.queue.patch_mode import POLICY_DENIED, PatchOutcome
from koru.queue.transaction.result import PatchPlan

Authorizer = Callable[[PatchPlan, dict], PatchOutcome | None]


def grant_required() -> bool:
    return (os.environ.get("KORU_QUEUE_REQUIRE_GRANT") or "").strip() == "1"


def build_authorizer(project: Path, ticket: dict, actor: str) -> Authorizer | None:
    """The authorization this ticket runs under, or ``None`` for legacy runs.

    The returned callable keeps the ``(plan, manifest) → outcome`` seam tests
    stub, and additionally exposes ``authorize.record`` — a dict the last call
    filled with what was actually granted (``jti``, capabilities, promotion
    mode). Evidence reads it so the bundle can answer "under which grant"
    without widening the Authorizer signature.
    """
    contract = contract_for_ticket(project, ticket)
    needs_grant = grant_required()
    if contract is None and not needs_grant:
        return None

    record: dict = {}

    def authorize(plan: PatchPlan, manifest: dict) -> PatchOutcome | None:
        record.clear()
        if contract is not None:
            capability = CAP_STAGE
            decision = contract.evaluate(
                actor=actor,
                capability=capability,
                targets=plan.targets,
                diff=plan.diff,
                risk_class=str((ticket.get("inputs") or {}).get("risk_class") or "R1"),
                workspace=plan.project,
            )
            if not decision.allowed:
                return PatchOutcome(code=POLICY_DENIED, message=decision.reason)
            extra = promotion_capability(plan.mode)
            if extra is not None:
                promotion = contract.evaluate(actor=actor, capability=extra)
                if not promotion.allowed:
                    return PatchOutcome(code=POLICY_DENIED, message=promotion.reason)
            record["contract"] = True
        if needs_grant:
            return _grant_gate(project, plan, manifest, actor, record)
        return None

    authorize.record = record  # type: ignore[attr-defined]
    return authorize


def _grant_gate(
    project: Path,
    plan: PatchPlan,
    manifest: dict,
    actor: str,
    record: dict | None = None,
) -> PatchOutcome | None:
    """KORU_MUTATIONS_ENABLED + valid signature + bindings + unspent jti = yes."""
    if not mutations_enabled():
        return PatchOutcome(
            code=POLICY_DENIED,
            message=(
                "grant enforcement is on but KORU_MUTATIONS_ENABLED is not 1 — "
                "the master mutation switch overrides everything, including a "
                "valid grant."
            ),
        )
    private, public = _local_keys(project)
    capabilities = [CAP_STAGE]
    extra = promotion_capability(plan.mode)
    if extra:
        capabilities.append(extra)
    token = issue_grant(
        private,
        run_id=plan.run_id,
        ticket_id=plan.ticket_id,
        actor=actor,
        workspace=plan.project,
        base_head=str(manifest.get("base_head") or ""),
        manifest_hash=str(manifest.get("manifest_hash") or ""),
        patch_sha256=str(manifest.get("patch_sha256") or ""),
        capabilities=tuple(capabilities),
        promotion_mode=plan.mode,
    )
    decision = verify_grant(
        public,
        token,
        GrantBindings(
            run_id=plan.run_id,
            workspace=plan.project,
            manifest_hash=str(manifest.get("manifest_hash") or ""),
            patch_sha256=str(manifest.get("patch_sha256") or ""),
            actor=actor,
            capability=CAP_STAGE,
            promotion_mode=plan.mode,
            base_head=str(manifest.get("base_head") or ""),
        ),
    )
    if not decision.allowed:
        return PatchOutcome(code=POLICY_DENIED, message=f"grant refused: {decision.reason}")
    claim = claim_jti(
        project,
        decision.jti,
        run_id=plan.run_id,
        manifest_hash=str(manifest.get("manifest_hash") or ""),
    )
    if not claim.ok:
        return PatchOutcome(code=POLICY_DENIED, message=f"grant replay refused: {claim.reason}")
    if record is not None:
        record.update(
            {
                "jti": decision.jti,
                "capabilities": list(capabilities),
                "promotion_mode": plan.mode,
            }
        )
    return None


def _local_keys(project: Path) -> tuple[bytes, bytes]:
    """Local control's keypair, created on first use with owner-only access."""
    keys_dir = project / ".koru" / "keys"
    private_path = keys_dir / "local-control.ed25519"
    public_path = keys_dir / "local-control.ed25519.pub"
    if private_path.is_file() and public_path.is_file():
        return private_path.read_bytes(), public_path.read_bytes()
    keys_dir.mkdir(parents=True, exist_ok=True)
    private, public = generate_keypair()
    private_path.touch(mode=0o600)
    private_path.write_bytes(private)
    private_path.chmod(0o600)
    public_path.write_bytes(public)
    return private, public
