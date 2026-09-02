# ticket-047 — cursor agent log

Layer hotspot scan tickets only referenced `project/analysis.toon.yaml`, so
`run_ticket_hygiene` classified them as junk and would auto-archive valid refactor
backlog items. Resolve source paths from `calls.yaml` module graph.
