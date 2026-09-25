"""Human-readable rendering of a standard-fleet report."""

from __future__ import annotations

from koru.standard_fleet.models import StandardFleetReport


def render_report(report: StandardFleetReport, *, show_excluded: bool = False) -> str:
    lines = [
        f"Wellmanifest fleet: {report.repositories} selected / "
        f"{report.discovered or report.repositories + len(report.excluded)} discovered, "
        f"{report.current} current, {len(report.candidates)} stale, "
        f"{len(report.excluded)} excluded",
        f"Standard: {report.standard.version} @ {report.standard.revision}",
    ]
    for candidate in report.candidates:
        blockers = []
        if candidate.dirty:
            blockers.append("dirty")
        if candidate.linked_worktrees:
            blockers.append(f"worktrees={candidate.linked_worktrees}")
        suffix = f" [{', '.join(blockers)}]" if blockers else ""
        lines.append(f"  {candidate.identity}: {', '.join(candidate.reasons)}{suffix}")
    if show_excluded:
        lines.append("Excluded repositories:")
        for item in report.excluded:
            blockers = []
            if item.dirty:
                blockers.append("dirty")
            if item.linked_worktrees:
                blockers.append(f"worktrees={item.linked_worktrees}")
            suffix = f" [{', '.join(blockers)}]" if blockers else ""
            lines.append(f"  {item.identity}: {', '.join(item.reasons)}{suffix} ({item.path})")
    if report.emitted or report.reused or report.emission_errors:
        lines.append(f"Tickets: emitted={report.emitted} reused={report.reused} errors={len(report.emission_errors)}")
    return "\n".join(lines)
