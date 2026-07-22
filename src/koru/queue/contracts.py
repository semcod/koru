"""Capability contracts: the box an actor works in, decided before any model runs.

A contract is project policy, loaded from koru.yaml — never from the ticket.
The ticket may *name* a contract; it cannot write one, and neither can a pack
or an LLM, because anything the model can author is by definition not a limit
on the model. Evaluation happens at every stage boundary (before the LLM,
after the patch arrives, before promotion), and the answer only ever shrinks:
a later check can refuse what an earlier one allowed, never the reverse.

.. code-block:: yaml

    queue:
      contracts:
        local-refactor-r1:
          actor: "bot:koru-refactor"
          allow_paths: ["src/**", "tests/**"]
          deny_paths: [".env", ".git/**", "secrets/**"]
          allow_capabilities:
            - code.patch.propose
            - code.patch.stage
            - code.patch.promote_branch
          max_risk: R1
          max_files: 4
          max_patch_bytes: 50000
          max_attempts: 2
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Capabilities the queue itself distinguishes today.
CAP_PROPOSE = "code.patch.propose"
CAP_STAGE = "code.patch.stage"
CAP_PROMOTE_BRANCH = "code.patch.promote_branch"
CAP_PROMOTE_MAIN = "code.patch.promote_main"

_RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}


@dataclass(frozen=True)
class ContractDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class CapabilityContract:
    """One actor's box. Absent limits mean 'no limit', absent contract means legacy."""

    id: str
    actor: str
    allow_paths: tuple[str, ...] = ()
    deny_paths: tuple[str, ...] = ()
    allow_capabilities: tuple[str, ...] = ()
    max_risk: str = "R1"
    max_files: int | None = None
    max_patch_bytes: int | None = None
    max_attempts: int | None = None
    workspace_roots: tuple[str, ...] = ()

    def evaluate(
        self,
        *,
        actor: str,
        capability: str,
        targets: tuple[str, ...] = (),
        diff: str = "",
        risk_class: str = "R1",
        workspace: Path | None = None,
    ) -> ContractDecision:
        """Judge one intended action. Any single violation refuses the whole."""
        if actor != self.actor:
            return ContractDecision(
                False, f"contract {self.id} is issued to `{self.actor}`, not `{actor}`",
            )
        if capability not in self.allow_capabilities:
            return ContractDecision(
                False, f"contract {self.id} does not allow capability `{capability}`",
            )
        if _RISK_ORDER.get(risk_class, 99) > _RISK_ORDER.get(self.max_risk, -1):
            return ContractDecision(
                False, f"risk {risk_class} exceeds the contract's max_risk {self.max_risk}",
            )
        if workspace is not None and self.workspace_roots:
            real = str(Path(workspace).resolve())
            if not any(
                real == root or real.startswith(root.rstrip("/") + "/")
                for root in (str(Path(r).resolve()) for r in self.workspace_roots)
            ):
                return ContractDecision(
                    False, f"workspace {real} is outside the contract's roots",
                )

        denied = [rel for rel in targets if _matches_any(rel, self.deny_paths)]
        if denied:
            return ContractDecision(
                False, f"the patch touches denied paths: {', '.join(sorted(denied))}",
            )
        if self.allow_paths:
            outside = [rel for rel in targets if not _matches_any(rel, self.allow_paths)]
            if outside:
                return ContractDecision(
                    False,
                    f"the patch reaches outside allowed paths: {', '.join(sorted(outside))}",
                )

        if self.max_files is not None and len(targets) > self.max_files:
            return ContractDecision(
                False, f"the patch touches {len(targets)} files; the contract allows "
                f"{self.max_files}",
            )
        if self.max_patch_bytes is not None and len(diff.encode("utf-8")) > self.max_patch_bytes:
            return ContractDecision(
                False,
                f"the patch is {len(diff.encode('utf-8'))} bytes; the contract allows "
                f"{self.max_patch_bytes}",
            )
        return ContractDecision(True, "within contract")


def contract_for_ticket(project: Path, ticket: dict) -> CapabilityContract | None:
    """The contract this ticket runs under, or ``None`` for legacy tickets.

    The ticket only *names* the contract (``inputs.contract``); the definition
    always comes from koru.yaml. Naming a contract that does not exist is a
    hard error expressed as an unsatisfiable contract, not a silent fallback to
    freedom — a typo must not widen anyone's box.
    """
    name = str((ticket.get("inputs") or {}).get("contract") or "").strip()
    if not name:
        return None
    defined = _contract_definitions(project)
    spec = defined.get(name)
    if not isinstance(spec, dict):
        return CapabilityContract(id=name, actor="", allow_capabilities=())
    return _parse_contract(name, spec)


def _contract_definitions(project: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return {}
    try:
        config = yaml.safe_load((project / "koru.yaml").read_text(encoding="utf-8"))
        contracts = ((config or {}).get("queue") or {}).get("contracts") or {}
    except (OSError, AttributeError, yaml.YAMLError):
        return {}
    return contracts if isinstance(contracts, dict) else {}


def _parse_contract(name: str, spec: dict) -> CapabilityContract:
    def _int_or_none(value) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return CapabilityContract(
        id=name,
        actor=str(spec.get("actor") or ""),
        allow_paths=tuple(str(p) for p in (spec.get("allow_paths") or [])),
        deny_paths=tuple(str(p) for p in (spec.get("deny_paths") or [])),
        allow_capabilities=tuple(str(c) for c in (spec.get("allow_capabilities") or [])),
        max_risk=str(spec.get("max_risk") or "R1"),
        max_files=_int_or_none(spec.get("max_files")),
        max_patch_bytes=_int_or_none(spec.get("max_patch_bytes")),
        max_attempts=_int_or_none(spec.get("max_attempts")),
        workspace_roots=tuple(str(r) for r in ((spec.get("workspace") or {}).get("roots") or [])),
    )


def promotion_capability(mode: str) -> str | None:
    """The extra capability a promotion mode demands beyond staging."""
    return {
        "branch": CAP_PROMOTE_BRANCH,
        "commit": CAP_PROMOTE_MAIN,
    }.get(mode)


def _matches_any(rel: str, patterns: tuple[str, ...]) -> bool:
    return any(_compile(p).match(rel) for p in patterns)


def _compile(pattern: str) -> re.Pattern:
    """Translate a ``**`` glob into a regex, portably across 3.12/3.13.

    ``*`` and ``?`` never cross ``/``; ``**`` crosses everything; ``**/`` also
    matches zero directories. Deterministic on purpose — path policy must not
    depend on the stdlib's glob dialect of the week.
    """
    p = pattern.strip().strip("/")
    out = []
    i = 0
    while i < len(p):
        if p[i : i + 3] == "**/":
            out.append(r"(?:.*/)?")
            i += 3
        elif p[i : i + 2] == "**":
            out.append(r".*")
            i += 2
        elif p[i] == "*":
            out.append(r"[^/]*")
            i += 1
        elif p[i] == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(p[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")
