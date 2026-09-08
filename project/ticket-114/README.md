# Ticket 114: Separate bounded command output capture

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, GitHub publication, deployment and testing. Deploy the resulting wheel into an isolated local Hillm pilot.

AC-01: Reduce _default_runner complexity below 15 by separating bounded stream capture, preserving byte limits, decoding, stream-specific truncation, deadlines, partial output, retries and process-group cleanup. Validate through Koru and protected publication.

Validation: 22 runner tests passed before and after extraction. Koru-driven checks passed: 81 regressions, Ruff, managed governance, Docker Compose and compileall. Comparable code2llm scans reduce critical findings from 24 to 23; Lizard reduces runner CC from 19 to 13 (capture helper: 7). Wheel built for isolated local deployment.
