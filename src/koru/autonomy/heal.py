"""Auto-repair primitives for Koru autonomy.

Each function applies a *minimal*, *idempotent*, and *reversible* fix to a
specific symptom detected by :mod:`koru.autonomy.environment`. None of these
modify project source code; they only touch ephemeral state (sockets, PID
files, JSON configs that already exist).

Design rules:
  - dry_run=True must NOT mutate the filesystem
  - each repair returns a structured RepairResult so callers can log + telemetry
  - repairs are pure functions of inputs; no hidden state
"""


from dataclasses import dataclass
from typing import Literal

from koru.autonomy.environment import EnvironmentReport, SocketHealth

RepairStatus = Literal["fixed", "skipped", "failed", "dry_run"]


@dataclass(frozen=True)
class RepairResult:
    """Outcome of one self-heal action."""

    action: str
    status: RepairStatus
    detail: str = ""


def remove_stale_socket(
    socket: SocketHealth,
    *,
    dry_run: bool = False,
) -> RepairResult:
    """Delete a socket file that exists but has no listener.

    Safe: only removes when ``stale=True`` (i.e. connect failed). Idempotent:
    repeated calls after the first one return ``skipped``.
    """
    if not socket.stale:
        return RepairResult(
            action="remove_stale_socket",
            status="skipped",
            detail=(
                f"socket {socket.path} is not stale"
                f" (exists={socket.exists}, listening={socket.listening})"
            ),
        )
    if dry_run:
        return RepairResult(
            action="remove_stale_socket",
            status="dry_run",
            detail=f"would unlink {socket.path}",
        )
    try:
        socket.path.unlink()
        return RepairResult(
            action="remove_stale_socket",
            status="fixed",
            detail=f"removed stale socket: {socket.path}",
        )
    except FileNotFoundError:
        return RepairResult(
            action="remove_stale_socket",
            status="skipped",
            detail=f"socket already gone: {socket.path}",
        )
    except OSError as exc:
        return RepairResult(
            action="remove_stale_socket",
            status="failed",
            detail=f"could not remove {socket.path}: {exc}",
        )


def heal_environment(
    report: EnvironmentReport,
    *,
    dry_run: bool = False,
) -> list[RepairResult]:
    """Apply every safe automatic repair indicated by ``report``.

    Currently handles:
      - stale autopilot socket (delete file so daemon restart can re-bind)

    MCP-config repairs are deliberately *not* performed here: writing into a
    user's IDE config dir is invasive and is gated behind explicit ``koru
    init-ide`` / ``task koru:mcp:bootstrap`` commands.
    """
    results: list[RepairResult] = []
    socket = report.autopilot_socket
    if socket is not None and socket.stale:
        results.append(remove_stale_socket(socket, dry_run=dry_run))
    return results


def summarise(results: list[RepairResult]) -> str:
    """One-line summary for logs / telemetry."""
    if not results:
        return "self-heal: nothing to fix"
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    parts = [f"{k}={v}" for k, v in sorted(counts.items())]
    return f"self-heal: {', '.join(parts)}"


__all__ = [
    "RepairResult",
    "RepairStatus",
    "heal_environment",
    "remove_stale_socket",
    "summarise",
]
