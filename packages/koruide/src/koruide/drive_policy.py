"""Plugin drive policy helpers (ACK gates, version checks, fallback rules).

``DriveOrchestrator`` is the legacy name kept for backwards compatibility.
New code should import :class:`DrivePolicy` instead.
"""

from koruide.drive_orchestrator import DriveOrchestrator as DrivePolicy

DriveOrchestrator = DrivePolicy

__all__ = ["DrivePolicy", "DriveOrchestrator"]
