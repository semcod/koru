# Koru Autonomy Log: `ticket-356`

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-28T20:26:36+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
DSL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ide=auto, backend=test, kind=fallback_prompt)"
DSL: "autopilot: ok (ide=auto, backend=test, kind=fallback_prompt)"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=TEST-001 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=TEST-001 drives=1"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=test)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=test)[0m"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: fallback_prompt (queue=waiting_input ticket=TEST-001)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: fallback_prompt (queue=waiting_input ticket=TEST-001)[0m"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=test) [evidence: backend=test, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=test) [evidence: backend=test, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-28T20:26:37+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

