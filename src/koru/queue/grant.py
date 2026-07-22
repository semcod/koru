"""Signed execution grants: a mutation needs a cryptographic yes, not a flag.

A grant is a short-lived Ed25519-signed statement from local control that one
specific run may perform one specific mutation: it binds the run id, the frozen
manifest hash, the patch hash, the workspace, the actor and the capabilities.
The executor holds only the *public* key, so nothing an LLM writes — and
nothing that leaks into a ticket — can mint permission to mutate.

Issuance can only happen after the manifest freeze, because the grant signs the
manifest hash; that ordering is the point of the autonomy loop
(``manifest freeze → signed grant → worktree``). Verification is pure and
injectable; replay protection lives next door in :mod:`grant_store`.

Token format is deliberately not JWT: ``base64url(payload).base64url(sig)``
with exactly one algorithm, so there is no ``alg`` header to confuse.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

GRANT_VERSION = 1
DEFAULT_ISSUER = "koru-local-control"
DEFAULT_AUDIENCE = "koru-queue-executor"
DEFAULT_TTL_S = 600


def generate_keypair() -> tuple[bytes, bytes]:
    """A fresh Ed25519 keypair as raw bytes: (private, public).

    The private half belongs to local control only; executors get the public
    half. Separate keys per environment, rotated by ``kid``.
    """
    private = Ed25519PrivateKey.generate()
    return (
        private.private_bytes_raw(),
        private.public_key().public_bytes_raw(),
    )


@dataclass(frozen=True)
class GrantBindings:
    """What the executor is about to do — every field must match the grant.

    ``capability`` is the one permission this mutation needs; the grant must
    list it. A grant may carry several, a check needs exactly one.
    """

    run_id: str
    workspace: Path
    manifest_hash: str
    patch_sha256: str
    actor: str
    capability: str
    promotion_mode: str
    base_head: str = ""
    audience: str = DEFAULT_AUDIENCE
    issuer: str = DEFAULT_ISSUER


@dataclass(frozen=True)
class GrantDecision:
    """The verdict on a token, with the reason a refusal can be acted on."""

    allowed: bool
    reason: str
    payload: dict = field(default_factory=dict)

    @property
    def jti(self) -> str:
        return str(self.payload.get("jti") or "")


def issue_grant(
    private_key_raw: bytes,
    *,
    run_id: str,
    ticket_id: str,
    actor: str,
    workspace: Path,
    base_head: str,
    manifest_hash: str,
    patch_sha256: str,
    capabilities: tuple[str, ...],
    promotion_mode: str,
    risk_class: str = "R1",
    issuer: str = DEFAULT_ISSUER,
    audience: str = DEFAULT_AUDIENCE,
    kid: str = "local-1",
    ttl_s: int = DEFAULT_TTL_S,
    now: datetime | None = None,
) -> str:
    """Sign a one-mutation permission. Only local control can call this usefully."""
    issued_at = now or datetime.now(UTC)
    payload = {
        "version": GRANT_VERSION,
        "issuer": issuer,
        "audience": audience,
        "kid": kid,
        "jti": uuid4().hex,
        "run_id": run_id,
        "ticket_id": ticket_id,
        "actor": actor,
        "workspace_realpath": str(Path(workspace).resolve()),
        "base_head": base_head,
        "manifest_hash": manifest_hash,
        "patch_sha256": patch_sha256,
        "capabilities": sorted(capabilities),
        "risk_class": risk_class,
        "promotion_mode": promotion_mode,
        "expires_at": (issued_at + timedelta(seconds=ttl_s)).isoformat(),
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = Ed25519PrivateKey.from_private_bytes(private_key_raw).sign(body)
    return f"{_b64(body)}.{_b64(signature)}"


def verify_grant(
    public_key_raw: bytes,
    token: str,
    bindings: GrantBindings,
    *,
    now: datetime | None = None,
) -> GrantDecision:
    """Check the signature first, then every binding. Any mismatch refuses.

    The order matters: nothing in the payload is even *read* as data until the
    signature over it has been verified, so a forged token gets no influence
    over the error path either.
    """
    try:
        body_b64, sig_b64 = token.split(".")
        body = _unb64(body_b64)
        signature = _unb64(sig_b64)
    except (ValueError, TypeError):
        return GrantDecision(False, "grant token is malformed")

    try:
        Ed25519PublicKey.from_public_bytes(public_key_raw).verify(signature, body)
    except (InvalidSignature, ValueError):
        return GrantDecision(False, "grant signature is invalid")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return GrantDecision(False, "grant payload is not valid JSON")

    if payload.get("version") != GRANT_VERSION:
        return GrantDecision(False, f"grant version {payload.get('version')!r} is not supported")
    if payload.get("issuer") != bindings.issuer:
        return GrantDecision(False, "grant issuer does not match this environment", payload)
    if payload.get("audience") != bindings.audience:
        # A staging grant presented to a production executor dies here.
        return GrantDecision(False, "grant audience does not match this executor", payload)

    moment = now or datetime.now(UTC)
    try:
        expires_at = datetime.fromisoformat(str(payload.get("expires_at")))
    except (TypeError, ValueError):
        return GrantDecision(False, "grant carries no readable expiry", payload)
    if moment >= expires_at:
        return GrantDecision(False, "grant has expired", payload)

    checks = (
        ("run_id", payload.get("run_id"), bindings.run_id),
        ("workspace", payload.get("workspace_realpath"), str(Path(bindings.workspace).resolve())),
        ("manifest_hash", payload.get("manifest_hash"), bindings.manifest_hash),
        ("patch_sha256", payload.get("patch_sha256"), bindings.patch_sha256),
        ("actor", payload.get("actor"), bindings.actor),
        ("promotion_mode", payload.get("promotion_mode"), bindings.promotion_mode),
    )
    for name, granted, actual in checks:
        if granted != actual:
            return GrantDecision(
                False, f"grant {name} does not match what is about to run", payload,
            )
    if bindings.base_head and payload.get("base_head") != bindings.base_head:
        return GrantDecision(False, "grant base_head does not match what is about to run", payload)

    if bindings.capability not in (payload.get("capabilities") or []):
        return GrantDecision(
            False, f"grant does not carry capability `{bindings.capability}`", payload,
        )

    return GrantDecision(True, "grant valid", payload)


def mutations_enabled() -> bool:
    """The master kill switch. Nothing overrides an absent yes."""
    return (os.environ.get("KORU_MUTATIONS_ENABLED") or "").strip() == "1"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
