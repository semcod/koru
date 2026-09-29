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

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://chat/test-message
category: CHAT
```

```yaml
NL: "test message"
DSL: "test message «hello world»"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://info/koru-autonomous
category: INFO
```

```yaml
NL: " koru autonomous: stopped after SIGTERM (WUP watcher stopped)"
DSL: " koru autonomous: stopped after SIGTERM (WUP watcher stopped)"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://chat/test-message
category: CHAT
```

```yaml
NL: "test message"
DSL: "test message «hello world»"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue=idle waiting=STARTER-219 url=http://127.0.0.1:8765/ cmd=`koru auto` path=/tmp/koru/test.sock"
DSL: "queue=idle waiting=STARTER-219 url=http://127.0.0.1:8765/ cmd=`koru auto` path=/tmp/koru/test.sock"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue=idle waiting=STARTER-219"
DSL: "queue=idle waiting=STARTER-219"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://chat/test-message
category: CHAT
```

```yaml
NL: "test message"
DSL: "test message «hello»"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://chat/first
category: CHAT
```

```yaml
NL: "first"
DSL: "first"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://chat/second
category: CHAT
```

```yaml
NL: "second"
DSL: "second"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://chat/trigger
category: CHAT
```

```yaml
NL: "trigger"
DSL: "trigger"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://chat/trigger
category: CHAT
```

```yaml
NL: "trigger"
DSL: "trigger"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://warn/coś-poszło-nie-tak
category: WARN
```

```yaml
NL: "coś poszło nie tak"
DSL: "coś poszło nie tak"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://warn/brak-profilu
category: WARN
```

```yaml
NL: "brak profilu"
DSL: "brak profilu «koru autopilot calibrate --ide jetbrains»"
```

### Activity (`2026-09-29T07:39:24+00:00`)

```yaml
uri: koru://warn/plain-warning
category: WARN
```

```yaml
NL: "plain warning"
DSL: "plain warning"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://run/koru-scan-apply-queue
category: RUN
```

```yaml
NL: "koru scan --apply (queue idle → intake scan)"
DSL: "koru scan --apply (queue idle → intake scan)"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/nxdo-discovery-skipped
category: INFO
```

```yaml
NL: "  nxdo discovery skipped: no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)"
DSL: "  nxdo discovery skipped: no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped, scan_idle_applied=0][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped, scan_idle_applied=0][0m"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:25+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VSCodium"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VSCodium"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscodium auto` from VSCodium's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscodium, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscodium auto` from VSCodium's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscodium, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VSCodium ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VSCodium ."
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscodium auto` or open VSCodium's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscodium auto` or open VSCodium's integrated terminal."
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscodium and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscodium and restart."
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=7 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=7 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/7/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/7/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 7: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 7: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:39:26+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://run/koru-scan-apply-queue
category: RUN
```

```yaml
NL: "koru scan --apply (queue idle → intake scan)"
DSL: "koru scan --apply (queue idle → intake scan)"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/nxdo-discovery-skipped
category: INFO
```

```yaml
NL: "  nxdo discovery skipped: no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)"
DSL: "  nxdo discovery skipped: no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped, scan_idle_applied=0][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped, scan_idle_applied=0][0m"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:27+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:28+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:39:28+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/koru-scan-after-idle
category: INFO
```

```yaml
NL: "- koru scan after idle skipped (min-interval 60.0s, ~30s remaining)"
DSL: "- koru scan after idle skipped (min-interval 60.0s, ~30s remaining)"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 2: skip:idle_no_ticket (queue=idle streak=1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 2: skip:idle_no_ticket (queue=idle streak=1)[0m"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:29+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://run/koru-scan-apply-queue
category: RUN
```

```yaml
NL: "koru scan --apply (queue idle → intake scan)"
DSL: "koru scan --apply (queue idle → intake scan)"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/nxdo-discovery-skipped
category: INFO
```

```yaml
NL: "  nxdo discovery skipped: no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)"
DSL: "  nxdo discovery skipped: no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=3 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=3 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ide=auto, backend=test, kind=drive_prompt)"
DSL: "autopilot: ok (ide=auto, backend=test, kind=drive_prompt)"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=- drives=0"
DSL: "  verdict: unknown (confidence=0.00) ticket=- drives=0"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: run_discovery (reason='queue idle, no open tickets', confidence=0.00)"
DSL: "decision: run_discovery (reason='queue idle, no open tickets', confidence=0.00)"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=test)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=test)[0m"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: drive_prompt (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: drive_prompt (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=test) [evidence: backend=test, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=test) [evidence: backend=test, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:30+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:39:31+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:39:31+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:39:31+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:39:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://chat/autopilot-skipped-idle-streak-1
category: CHAT
```

```yaml
NL: "autopilot skipped (idle_streak_1>=1)"
DSL: "autopilot skipped (idle_streak_1>=1)"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(idle_streak)"
DSL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(idle_streak)"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 2: skip:idle_streak (queue=idle streak=1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 2: skip:idle_streak (queue=idle streak=1)[0m"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_streak, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_streak, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle for 1 consecutive cycles[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle for 1 consecutive cycles[0m"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: let idle backoff drain before next drive[0m"
DSL: "    [33mDSL:[0m [34mnext: let idle backoff drain before next drive[0m"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_streak] Queue stayed idle for too many consecutive cycles; the loop is backing off. — queue idle for 1 consecutive cycles"
DSL: "  [33mdecision:[0m because[idle_streak] Queue stayed idle for too many consecutive cycles; the loop is backing off. — queue idle for 1 consecutive cycles"
```

### Activity (`2026-09-29T07:39:32+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
DSL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:39:36+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/plugin-niedostępny-dla-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
DSL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-local-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0"
DSL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/3-socket-daemona
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
DSL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/4-ustaw-w-shellu
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
DSL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/5-wayland
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
DSL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/6-na-waylandzie-nie
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
DSL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/7-kalibracja-os-injectora
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
DSL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/8-test-semantyczny
category: KORUAUTONOMOUS
```

```yaml
NL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
DSL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
```

### Activity (`2026-09-29T07:39:40+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:39:41+00:00`)

```yaml
uri: koru://run/koru-scan-apply-semcod-artifacts
category: RUN
```

```yaml
NL: "koru scan --apply --semcod-artifacts"
DSL: "koru scan --apply --semcod-artifacts"
```

### Activity (`2026-09-29T07:39:41+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:39:41+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:39:41+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:39:41+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:41+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
```

### Activity (`2026-09-29T07:39:41+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=1"
DSL: "next 1/3 stop now; reached max-cycles=1"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_overri0"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=1; stopping"
DSL: "reached max-cycles=1; stopping"
```

### Activity (`2026-09-29T07:39:42+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
DSL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:39:44+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:39:45+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:39:45+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:39:45+00:00`)

```yaml
uri: koru://autonomous/plugin-niedostępny-dla-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
DSL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-local-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0"
DSL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_invali0"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/3-socket-daemona
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
DSL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/4-ustaw-w-shellu
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
DSL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/5-wayland
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
DSL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/6-na-waylandzie-nie
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
DSL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/7-kalibracja-os-injectora
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
DSL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/8-test-semantyczny
category: KORUAUTONOMOUS
```

```yaml
NL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
DSL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0"
```

### Activity (`2026-09-29T07:39:46+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=1"
DSL: "next 1/3 stop now; reached max-cycles=1"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_ticket_sources_env_invali0"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=1; stopping"
DSL: "reached max-cycles=1; stopping"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://auto/onboarding/start-wizard
category: KORUAUTO ONBOARDING
```

```yaml
NL: "start (wizard)"
DSL: "start (wizard)"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://ticket/utworzono-plf-001-quality
category: TICKET
```

```yaml
NL: "utworzono PLF-001 (Quality: redukcja CC w hotspotach) kolejka=default executor=human"
DSL: "utworzono PLF-001 (Quality: redukcja CC w hotspotach) kolejka=default executor=human «Quality: redukcja CC w hotspotach  `project/analysis.toon.yaml` zawiera listę funkcji z CC>15. Wybierz top 5, wydziel sub-funkcje, dodaj testy regresji.»"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://auto/onboarding/created-ticket-plf-001-quality
category: KORUAUTO ONBOARDING
```

```yaml
NL: "created ticket PLF-001 (Quality: redukcja CC w hotspotach)"
DSL: "created ticket PLF-001 (Quality: redukcja CC w hotspotach)"
```

### Activity (`2026-09-29T07:39:47+00:00`)

```yaml
uri: koru://auto/stopping-1-prior-managed
category: KORUAUTO
```

```yaml
NL: "stopping 1 prior managed process(es) (koru autonomous/auto, wup watch)"
DSL: "stopping 1 prior managed process(es) (koru autonomous/auto, wup watch)"
```

### Activity (`2026-09-29T07:39:48+00:00`)

```yaml
uri: koru://autonomous/another-managed-process-is
category: KORUAUTONOMOUS
```

```yaml
NL: "another managed process is already running for this project; use --replace-existing to stop it first or --allow-duplicate to run anyway."
DSL: "another managed process is already running for this project; use --replace-existing to stop it first or --allow-duplicate to run anyway."
```

### Activity (`2026-09-29T07:39:48+00:00`)

```yaml
uri: koru://info/existing-autonomous-loop-pid
category: INFO
```

```yaml
NL: "  existing autonomous-loop pid=123: koru autonomous up --project /tmp/pytest-of-tom/pytest-33/test_guard_existing_autonomous0"
DSL: "  existing autonomous-loop pid=123: koru autonomous up --project /tmp/pytest-of-tom/pytest-33/test_guard_existing_autonomous0"
```

### Activity (`2026-09-29T07:39:48+00:00`)

```yaml
uri: koru://autonomous/keeping-existing-processes-not
category: KORUAUTONOMOUS
```

```yaml
NL: "keeping existing process(es); not starting a duplicate. Use --allow-duplicate to override."
DSL: "keeping existing process(es); not starting a duplicate. Use --allow-duplicate to override."
```

### Activity (`2026-09-29T07:39:48+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
DSL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:39:49+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/plugin-niedostępny-dla-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
DSL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-local-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0"
DSL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_autonomous_jsonl_keyboard0"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/3-socket-daemona
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
DSL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/4-ustaw-w-shellu
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
DSL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/5-wayland
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
DSL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/6-na-waylandzie-nie
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
DSL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/7-kalibracja-os-injectora
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
DSL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/8-test-semantyczny
category: KORUAUTONOMOUS
```

```yaml
NL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
DSL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://run/koru-scan-apply-semcod-artifacts
category: RUN
```

```yaml
NL: "koru scan --apply --semcod-artifacts"
DSL: "koru scan --apply --semcod-artifacts"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:39:51+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=1.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=1.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 wait 1s; queue is idle — no eligible work in the current queue. Open tickets may wait for an operator, dependencies or another queue; autopilot drive is suppressed"
DSL: "next 1/3 wait 1s; queue is idle — no eligible work in the current queue. Open tickets may wait for an operator, dependencies or another queue; autopilot drive is suppressed"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 strategy detail→general: planfile ticket queue first; when no work is eligible, idle scan is disabled unless explicitly requested"
DSL: "next 2/3 strategy detail→general: planfile ticket queue first; when no work is eligible, idle scan is disabled unless explicitly requested"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 quick links: create discovery ticket http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0 ; tickets http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0 ; optional signal scan: `koru scan --apply` (preserves project history)"
DSL: "next 3/3 quick links: create discovery ticket http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0 ; tickets http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0 ; optional signal scan: `koru scan --apply` (preserves project history)"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_jsonl_keyboard0"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://info/koru-autonomous
category: INFO
```

```yaml
NL: " koru autonomous: interrupted (Ctrl+C)"
DSL: " koru autonomous: interrupted (Ctrl+C)"
```

### Activity (`2026-09-29T07:39:52+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=cursor (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
DSL: "lane=cursor (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=cursor (from lane, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=cursor (from lane, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot-cursor-main.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot-cursor-main.sock"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/czekam-na-plugin-jeśli
category: KORUAUTONOMOUS
```

```yaml
NL: "[?] czekam na plugin — jeśli poniżej nie ma [ok], wykonaj kroki 1–6"
DSL: "[?] czekam na plugin — jeśli poniżej nie ma [ok], wykonaj kroki 1–6"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-cursor-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz cursor z root = /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0"
DSL: "1) Otwórz cursor z root = /tmp/pytest-of-tom/pytest-33/test_autonomous_main_prepends_0"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/3-autopilot
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Autopilot: Command Palette → „koru: Connect autopilot daemon” (pasek: koru: on)"
DSL: "3) Autopilot: Command Palette → „koru: Connect autopilot daemon” (pasek: koru: on)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/jeśli-komendy-nie-ma
category: KORUAUTONOMOUS
```

```yaml
NL: "   Jeśli komendy nie ma albo plugin list jest pusty po instalacji VSIX: Developer: Reload Window / restart IDE"
DSL: "   Jeśli komendy nie ma albo plugin list jest pusty po instalacji VSIX: Developer: Reload Window / restart IDE"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/4-socket-wtyczki
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Socket wtyczki = /run/user/1000/koru-autopilot-cursor-main.sock (~/.config/Cursor/User/settings.json: koruAutopilot.socketPath)"
DSL: "4) Socket wtyczki = /run/user/1000/koru-autopilot-cursor-main.sock (~/.config/Cursor/User/settings.json: koruAutopilot.socketPath)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/5-ten-sam-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Ten sam socket w shellu: export KORU_AUTOPILOT_INSTANCE=cursor"
DSL: "5) Ten sam socket w shellu: export KORU_AUTOPILOT_INSTANCE=cursor"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/6-diagnostyka-mostu
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Diagnostyka mostu: koru ide doctor --ide cursor --fix"
DSL: "6) Diagnostyka mostu: koru ide doctor --ide cursor --fix"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/7-test
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Test: koru autopilot status --ide cursor --explain → plugins niepuste; potem koru autopilot drive --ide cursor --require-plugin 'probe test'"
DSL: "7) Test: koru autopilot status --ide cursor --explain → plugins niepuste; potem koru autopilot drive --ide cursor --require-plugin 'probe test'"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/7a-przed-drive
category: KORUAUTONOMOUS
```

```yaml
NL: "7a) Przed drive: kliknij w pole czatu cursor (mrugający kursor w input, nie w edytorze pliku)"
DSL: "7a) Przed drive: kliknij w pole czatu cursor (mrugający kursor w input, nie w edytorze pliku)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/8-opcjonalnie-command-palette
category: KORUAUTONOMOUS
```

```yaml
NL: "8) (opcjonalnie) Command Palette → „koru: Calibrate chat probe ladder” (po ustawieniu fokusu w polu czatu; submit na Wayland)"
DSL: "8) (opcjonalnie) Command Palette → „koru: Calibrate chat probe ladder” (po ustawieniu fokusu w polu czatu; submit na Wayland)"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://autonomous/docs
category: KORUAUTONOMOUS
```

```yaml
NL: "--- docs: <project>/docs/autonomy-ide-cursor.md (sekcja „Po starcie”) ---"
DSL: "--- docs: <project>/docs/autonomy-ide-cursor.md (sekcja „Po starcie”) ---"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:39:53+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Cursor (lane=cursor)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Cursor (lane=cursor)"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru cursor auto` from Cursor's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=cursor, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru cursor auto` from Cursor's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=cursor, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Cursor (cursor)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Cursor (cursor)."
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru cursor auto` or open Cursor's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru cursor auto` or open Cursor's integrated terminal."
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=cursor and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=cursor and restart."
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=1"
DSL: "next 1/3 stop now; reached max-cycles=1"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_autonomous_main_prepends_0"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=1; stopping"
DSL: "reached max-cycles=1; stopping"
```

### Activity (`2026-09-29T07:39:54+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
DSL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:39:56+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/plugin-niedostępny-dla-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
DSL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-local-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0"
DSL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_queue_onl0"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/3-socket-daemona
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
DSL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/4-ustaw-w-shellu
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
DSL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/5-wayland
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
DSL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/6-na-waylandzie-nie
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
DSL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/7-kalibracja-os-injectora
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
DSL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/8-test-semantyczny
category: KORUAUTONOMOUS
```

```yaml
NL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
DSL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:39:58+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=1"
DSL: "next 1/3 stop now; reached max-cycles=1"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_queue_onl0"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=1; stopping"
DSL: "reached max-cycles=1; stopping"
```

### Activity (`2026-09-29T07:39:59+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=none (from cli:none, cli --agent-lane=none)"
DSL: "lane=none (from cli:none, cli --agent-lane=none)"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:40:00+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/plugin-niedostępny-dla-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "[i] plugin niedostępny dla ide=auto — używam ścieżki keyboard/OS-injector"
DSL: "[i] plugin niedostępny dla ide=auto — używam ścieżki keyboard/OS-injector"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-auto-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz auto z root = /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0"
DSL: "1) Otwórz auto z root = /tmp/pytest-of-tom/pytest-33/test_safe_up_uses_queue_diagno0"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/3-socket-daemona
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Socket daemona = /run/user/1000/koru-autopilot.sock"
DSL: "3) Socket daemona = /run/user/1000/koru-autopilot.sock"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/4-ustaw-w-shellu
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=auto"
DSL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=auto"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/5-wayland
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide auto (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance auto --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide auto; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
DSL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide auto (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance auto --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide auto; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/6-na-waylandzie-nie
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
DSL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/7-kalibracja-os-injectora
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=auto"
DSL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=auto"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/8-test-semantyczny
category: KORUAUTONOMOUS
```

```yaml
NL: "8) Test semantyczny: koru autopilot drive --ide auto 'probe test'"
DSL: "8) Test semantyczny: koru autopilot drive --ide auto 'probe test'"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:40:02+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=ok wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=ok wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=ok, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=ok, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=ok autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=ok autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0"
```

### Activity (`2026-09-29T07:40:03+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=1"
DSL: "next 1/3 stop now; reached max-cycles=1"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_safe_up_uses_queue_diagno0"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=1; stopping"
DSL: "reached max-cycles=1; stopping"
```

### Activity (`2026-09-29T07:40:04+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
DSL: "lane=local (from env:KORU_AUTOPILOT_INSTANCE, cli --agent-lane=auto)"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=local (from lane, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:40:06+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/plugin-niedostępny-dla-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
DSL: "[i] plugin niedostępny dla ide=local — używam ścieżki keyboard/OS-injector"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-local-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0"
DSL: "1) Otwórz local z root = /tmp/pytest-of-tom/pytest-33/test_up_single_cycle_all_sourc0"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/3-socket-daemona
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
DSL: "3) Socket daemona = /run/user/1000/koru-autopilot-local.sock"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/4-ustaw-w-shellu
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
DSL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=local"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/5-wayland
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
DSL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide local (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance local --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide local; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/6-na-waylandzie-nie
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
DSL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/7-kalibracja-os-injectora
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
DSL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=local"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/8-test-semantyczny
category: KORUAUTONOMOUS
```

```yaml
NL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
DSL: "8) Test semantyczny: koru autopilot drive --ide local 'probe test'"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://run/koru-scan-apply-semcod-artifacts
category: RUN
```

```yaml
NL: "koru scan --apply --semcod-artifacts"
DSL: "koru scan --apply --semcod-artifacts"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:09+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:10+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:10+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is local (lane=local)"
```

### Activity (`2026-09-29T07:40:10+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru local auto` from local's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=local, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:10+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets local (local)."
```

### Activity (`2026-09-29T07:40:10+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru local auto` or open local's integrated terminal."
```

### Activity (`2026-09-29T07:40:10+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=local and restart."
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=1"
DSL: "next 1/3 stop now; reached max-cycles=1"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_single_cycle_all_sourc0"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=1; stopping"
DSL: "reached max-cycles=1; stopping"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/unsupported
category: INFO
```

```yaml
NL: "unsupported"
DSL: "unsupported"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://autonomous/autopilot-plugin-unsupported
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot plugin unsupported for ide=jetbrains; na Waylandzie wymagane jest vdisplay/photo-VQL z potwierdzonym targetem; ślepy keyboard/OS-injector jest blokowany"
DSL: "autopilot plugin unsupported for ide=jetbrains; na Waylandzie wymagane jest vdisplay/photo-VQL z potwierdzonym targetem; ślepy keyboard/OS-injector jest blokowany"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:40:11+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
DSL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
```

### Activity (`2026-09-29T07:40:12+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ide=auto, backend=test, kind=fallback_prompt)"
DSL: "autopilot: ok (ide=auto, backend=test, kind=fallback_prompt)"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=TEST-001 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=TEST-001 drives=1"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=test)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=test)[0m"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: fallback_prompt (queue=waiting_input ticket=TEST-001)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: fallback_prompt (queue=waiting_input ticket=TEST-001)[0m"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=test) [evidence: backend=test, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=test) [evidence: backend=test, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
```

### Activity (`2026-09-29T07:40:13+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
DSL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ticket=PLF-999, ide=windsurf, backend=plugin, kind=ticket_prompt)"
DSL: "autopilot: ok (ticket=PLF-999, ide=windsurf, backend=plugin, kind=ticket_prompt)"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=PLF-999 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=PLF-999 drives=1"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=plugin)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=plugin)[0m"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: ticket_prompt (queue=waiting_input ticket=PLF-999)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: ticket_prompt (queue=waiting_input ticket=PLF-999)[0m"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
```

### Activity (`2026-09-29T07:40:14+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
DSL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ide=vscode, backend=plugin, kind=escalation_prompt)"
DSL: "autopilot: ok (ide=vscode, backend=plugin, kind=escalation_prompt)"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=PLF-1305 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=PLF-1305 drives=1"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=4 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=4 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/4/decision/submit_verified(backend=plugin)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/4/decision/submit_verified(backend=plugin)[0m"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 4: escalation_prompt (queue=waiting_input ticket=PLF-1305)[0m"
DSL: "    [33mNL:[0m  [32mCykl 4: escalation_prompt (queue=waiting_input ticket=PLF-1305)[0m"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:15+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
DSL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
```

### Activity (`2026-09-29T07:40:16+00:00`)

```yaml
uri: koru://info/autopilot-auto-llm-ready
category: INFO
```

```yaml
NL: "- autopilot auto llm-ready: added label to PLF-1317"
DSL: "- autopilot auto llm-ready: added label to PLF-1317"
```

### Activity (`2026-09-29T07:40:17+00:00`)

```yaml
uri: koru://info/autopilot-not-skipped-auto
category: INFO
```

```yaml
NL: "- autopilot not skipped (auto llm-ready, streak=2)"
DSL: "- autopilot not skipped (auto llm-ready, streak=2)"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ticket=PLF-1317, ide=vscode, backend=plugin, kind=ticket_prompt)"
DSL: "autopilot: ok (ticket=PLF-1317, ide=vscode, backend=plugin, kind=ticket_prompt)"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=PLF-1317 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=PLF-1317 drives=1"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=3 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=3 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/3/decision/submit_verified(backend=plugin)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/3/decision/submit_verified(backend=plugin)[0m"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 3: ticket_prompt (queue=waiting_input ticket=PLF-1317 streak=2)[0m"
DSL: "    [33mNL:[0m  [32mCykl 3: ticket_prompt (queue=waiting_input ticket=PLF-1317 streak=2)[0m"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:18+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
DSL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
```

### Activity (`2026-09-29T07:40:19+00:00`)

```yaml
uri: koru://info/autopilot-not-skipped-auto
category: INFO
```

```yaml
NL: "- autopilot not skipped (auto llm-ready, streak=1)"
DSL: "- autopilot not skipped (auto llm-ready, streak=1)"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ticket=PLF-1321, ide=vscode, backend=plugin, kind=ticket_prompt)"
DSL: "autopilot: ok (ticket=PLF-1321, ide=vscode, backend=plugin, kind=ticket_prompt)"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=PLF-1321 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=PLF-1321 drives=1"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=2 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=2 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/2/decision/submit_verified(backend=plugin)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/2/decision/submit_verified(backend=plugin)[0m"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 2: ticket_prompt (queue=waiting_input ticket=PLF-1321 streak=1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 2: ticket_prompt (queue=waiting_input ticket=PLF-1321 streak=1)[0m"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=plugin) [evidence: backend=plugin, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:20+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code (lane=vscode)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code (lane=vscode)"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code (vscode)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code (vscode)."
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
DSL: "- pre-drive: control route → ide_plugin_socket (verified): connected IDE plugin acknowledges every write"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://chat/autopilot-skipped-recent-chat-activity-last
category: CHAT
```

```yaml
NL: "autopilot skipped (recent_chat_activity last=message.sent age=31s cooldown=300s ticket=PLF-2001)"
DSL: "autopilot skipped (recent_chat_activity last=message.sent age=31s cooldown=300s ticket=PLF-2001)"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=3 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped(chat_activity)"
DSL: "cycle=3 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped(chat_activity)"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/3/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/3/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 3: skip:chat_activity (queue=waiting_input ticket=PLF-2001 streak=1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 3: skip:chat_activity (queue=waiting_input ticket=PLF-2001 streak=1)[0m"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=chat_activity, diagnostics=skipped, wup=skipped, chat_event=message.sent][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=chat_activity, diagnostics=skipped, wup=skipped, chat_event=message.sent][0m"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: recent_chat_activity last=message.sent age=31s cooldown=300s ticket=PLF-2001[0m"
DSL: "    [33mNL:[0m  [32mPowód: recent_chat_activity last=message.sent age=31s cooldown=300s ticket=PLF-2001[0m"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for chat cooldown to expire[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for chat cooldown to expire[0m"
```

### Activity (`2026-09-29T07:40:21+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[chat_activity] Recent chat activity (drive ack / user message) is still inside the cooldown window; pasting now would clobber the user. — recent_chat_activity last=message.sent age=31s cooldown=300s ticket=PLF-2001"
DSL: "  [33mdecision:[0m because[chat_activity] Recent chat activity (drive ack / user message) is still inside the cooldown window; pasting now would clobber the user. — recent_chat_activity last=message.sent age=31s cooldown=300s ticket=PLF-2001"
```

### Activity (`2026-09-29T07:40:22+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=auto outcome=stop transport=unknown phase=submit_unverified attempt=1 reason=submit_unverified_not_retryable evidence=\"kind=stop; warn=-; sleep=0.0; max_attempts=5\" next=\"do not paste again; surface root cause to operator\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=auto outcome=stop transport=unknown phase=submit_unverified attempt=1 reason=submit_unverified_not_retryable evidence=\"kind=stop; warn=-; sleep=0.0; max_attempts=5\" next=\"do not paste again; surface root cause to operator\""
```

### Activity (`2026-09-29T07:40:23+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:23+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=windsurf outcome=retry transport=plugin phase=- attempt=1 reason=\"no connected plugin\" evidence=\"kind=retry_plugin; warn=plugin; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=windsurf outcome=retry transport=plugin phase=- attempt=1 reason=\"no connected plugin\" evidence=\"kind=retry_plugin; warn=plugin; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: aborting retry loop — identical failure repeated (attempt 2/3, signature unchanged)"
DSL: "autopilot: aborting retry loop — identical failure repeated (attempt 2/3, signature unchanged)"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: failed (no connected plugin, kind=drive_prompt)"
DSL: "autopilot: failed (no connected plugin, kind=drive_prompt)"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
DSL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
DSL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, backend=plugin, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, backend=plugin, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
DSL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
DSL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:24+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=windsurf outcome=retry transport=unknown phase=plugin_error attempt=1 reason=\"chat input is not focused\" evidence=\"kind=retry_focus; warn=focus; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=windsurf outcome=retry transport=unknown phase=plugin_error attempt=1 reason=\"chat input is not focused\" evidence=\"kind=retry_focus; warn=focus; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: aborting retry loop — identical failure repeated (attempt 2/3, signature unchanged)"
DSL: "autopilot: aborting retry loop — identical failure repeated (attempt 2/3, signature unchanged)"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: failed (chat input is not focused, kind=drive_prompt)"
DSL: "autopilot: failed (chat input is not focused, kind=drive_prompt)"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
DSL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
DSL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
```

### Activity (`2026-09-29T07:40:25+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
DSL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
DSL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
```

### Activity (`2026-09-29T07:40:26+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=windsurf outcome=retry transport=unknown phase=plugin_error attempt=1 reason=\"chat opened but paste command failed (fast path failed)\" evidence=\"kind=retry_plugin; warn=plugin; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=windsurf outcome=retry transport=unknown phase=plugin_error attempt=1 reason=\"chat opened but paste command failed (fast path failed)\" evidence=\"kind=retry_plugin; warn=plugin; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: aborting retry loop — identical failure repeated (attempt 2/3, signature unchanged)"
DSL: "autopilot: aborting retry loop — identical failure repeated (attempt 2/3, signature unchanged)"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: failed (chat opened but paste command failed (fast path failed), kind=drive_prompt)"
DSL: "autopilot: failed (chat opened but paste command failed (fast path failed), kind=drive_prompt)"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
DSL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
DSL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
DSL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
DSL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=vscode outcome=stop transport=unknown phase=- attempt=1 reason=\"no connected autopilot plugin for ide=vscode\" evidence=\"kind=stop; warn=-; sleep=0.0; max_attempts=3\" next=\"do not paste again; surface root cause to operator\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=vscode outcome=stop transport=unknown phase=- attempt=1 reason=\"no connected autopilot plugin for ide=vscode\" evidence=\"kind=stop; warn=-; sleep=0.0; max_attempts=3\" next=\"do not paste again; surface root cause to operator\""
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: failed (no connected autopilot plugin for ide=vscode, kind=drive_prompt)"
DSL: "autopilot: failed (no connected autopilot plugin for ide=vscode, kind=drive_prompt)"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
DSL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
DSL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
DSL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
DSL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
```

### Activity (`2026-09-29T07:40:27+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:28+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:28+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:28+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=jetbrains outcome=stop transport=semantic_required phase=- attempt=1 reason=\"refusing blind keyboard/OS-injector fallback on Wayland for JetBrains after vdisplay/imgl did not confirm the target\" evidence=\"kind=semantic_required; warn=semantic_required; sleep=0.0; max_attempts=3\" next=\"do not paste again; surface root cause to operator\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=jetbrains outcome=stop transport=semantic_required phase=- attempt=1 reason=\"refusing blind keyboard/OS-injector fallback on Wayland for JetBrains after vdisplay/imgl did not confirm the target\" evidence=\"kind=semantic_required; warn=semantic_required; sleep=0.0; max_attempts=3\" next=\"do not paste again; surface root cause to operator\""
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: failed (refusing blind keyboard/OS-injector fallback on Wayland for JetBrains after vdisplay/imgl did not confirm the target, kind=drive_prompt)"
DSL: "autopilot: failed (refusing blind keyboard/OS-injector fallback on Wayland for JetBrains after vdisplay/imgl did not confirm the target, kind=drive_prompt)"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
DSL: "  verdict: degraded (confidence=1.00) ticket=- drives=0"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
DSL: "decision: escalate_ticket (reason='tests degraded after drive: failed', confidence=1.00)"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=failed"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_unverified[0m"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: drive_failed (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, backend=semantic_required, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_unverified [evidence: blocked_by=failed, backend=semantic_required, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
DSL: "    [33mDSL:[0m [34mnext: retry next cycle (cached winner discarded)[0m"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
DSL: "  [33mdecision:[0m because[failed] Drive ran but the plugin reported a failure."
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:31+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=vscode outcome=stop transport=unknown phase=plugin_error attempt=1 reason=focus_open_candidates_empty evidence=\"kind=stop_manual_focus; warn=manual_focus; sleep=0.0; max_attempts=3\" next=\"do not paste again; surface root cause to operator\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=vscode outcome=stop transport=unknown phase=plugin_error attempt=1 reason=focus_open_candidates_empty evidence=\"kind=stop_manual_focus; warn=manual_focus; sleep=0.0; max_attempts=3\" next=\"do not paste again; surface root cause to operator\""
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://chat/manual-focus-required-no
category: CHAT
```

```yaml
NL: "manual focus required; no automatic retry"
DSL: "manual focus required; no automatic retry"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: skipped(manual_focus) (chat input is not focused/open; focus_open_candidates=(none), kind=drive_prompt)"
DSL: "autopilot: skipped(manual_focus) (chat input is not focused/open; focus_open_candidates=(none), kind=drive_prompt)"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(manual_focus)"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(manual_focus)"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:32+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:manual_focus (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:manual_focus (queue=idle)[0m"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=manual_focus, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=manual_focus, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: operator must foreground the chat surface[0m"
DSL: "    [33mDSL:[0m [34mnext: operator must foreground the chat surface[0m"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[manual_focus] Plugin ran the submit step but reports the chat surface needs manual focus (webview not foregrounded)."
DSL: "  [33mdecision:[0m because[manual_focus] Plugin ran the submit step but reports the chat surface needs manual focus (webview not foregrounded)."
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → vdisplay_verified_injection (verified): vdisplay confirms the target region visually before typing"
DSL: "- pre-drive: control route → vdisplay_verified_injection (verified): vdisplay confirms the target region visually before typing"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://info/pre-drive-readiness
category: INFO
```

```yaml
NL: "- pre-drive readiness: queue is waiting_input but autopilot plugin is not connected (daemon status plugin list is empty); drive will be skipped until plugin reconnects"
DSL: "- pre-drive readiness: queue is waiting_input but autopilot plugin is not connected (daemon status plugin list is empty); drive will be skipped until plugin reconnects"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://chat/autopilot-skipped-plugin-not-connected
category: CHAT
```

```yaml
NL: "autopilot skipped (plugin_not_connected: daemon status plugin list is empty)"
DSL: "autopilot skipped (plugin_not_connected: daemon status plugin list is empty)"
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://autonomous/event
category: KORUAUTONOMOUS
```

```yaml
NL: "→ VSIX plugin is not connected to the daemon socket. In the IDE: Command Palette → `Developer: Reload Window`, then `koru: Connect autopilot daemon` (status bar should show koru: on). Check: `koru autopilot status --explain`."
DSL: "→ VSIX plugin is not connected to the daemon socket. In the IDE: Command Palette → `Developer: Reload Window`, then `koru: Connect autopilot daemon` (status bar should show koru: on). Check: `koru autopilot status --explain`."
```

### Activity (`2026-09-29T07:40:33+00:00`)

```yaml
uri: koru://autonomous/event
category: KORUAUTONOMOUS
```

```yaml
NL: "→ autopilot recovery: automatic reload failed (command-palette reload disabled by default; set KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD=1 to allow visible keyboard UI automation, or set KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to opt in to the CLI reuse-window fallback)"
DSL: "→ autopilot recovery: automatic reload failed (command-palette reload disabled by default; set KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD=1 to allow visible keyboard UI automation, or set KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to opt in to the CLI reuse-window fallback)"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://autonomous/event
category: KORUAUTONOMOUS
```

```yaml
NL: "→ autopilot recovery: still not connected (daemon status plugin list is empty)"
DSL: "→ autopilot recovery: still not connected (daemon status plugin list is empty)"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped(plugin_not_connected)"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped(plugin_not_connected)"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:plugin_not_connected (queue=waiting_input ticket=PLF-1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:plugin_not_connected (queue=waiting_input ticket=PLF-1)[0m"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=plugin_not_connected, diagnostics=skipped, wup=skipped, plugin_reason=daemon status plugin list is empty][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=plugin_not_connected, diagnostics=skipped, wup=skipped, plugin_reason=daemon status plugin list is empty][0m"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: daemon status plugin list is empty[0m"
DSL: "    [33mNL:[0m  [32mPowód: daemon status plugin list is empty[0m"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for plugin reconnect (manual reload may be needed)[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for plugin reconnect (manual reload may be needed)[0m"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[plugin_not_connected] Autopilot needs a connected VSIX plugin but no compatible live session is attached to the daemon yet. Reload the IDE window, then connect the IDE plugin. — daemon status plugin list is empty"
DSL: "  [33mdecision:[0m because[plugin_not_connected] Autopilot needs a connected VSIX plugin but no compatible live session is attached to the daemon yet. Reload the IDE window, then connect the IDE plugin. — daemon status plugin list is empty"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is VS Code"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru vscode auto` from VS Code's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=vscode, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets VS Code ."
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru vscode auto` or open VS Code's integrated terminal."
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=vscode and restart."
```

### Activity (`2026-09-29T07:40:45+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → vdisplay_verified_injection (verified): vdisplay confirms the target region visually before typing"
DSL: "- pre-drive: control route → vdisplay_verified_injection (verified): vdisplay confirms the target region visually before typing"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ticket=PLF-1, ide=vscode, backend=stub, kind=ticket_prompt)"
DSL: "autopilot: ok (ticket=PLF-1, ide=vscode, backend=stub, kind=ticket_prompt)"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=PLF-1 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=PLF-1 drives=1"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=stub)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=stub)[0m"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: ticket_prompt (queue=waiting_input ticket=PLF-1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: ticket_prompt (queue=waiting_input ticket=PLF-1)[0m"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=stub) [evidence: backend=stub, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=stub) [evidence: backend=stub, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:49+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: control route → vdisplay_verified_injection (verified): vdisplay confirms the target region visually before typing"
DSL: "- pre-drive: control route → vdisplay_verified_injection (verified): vdisplay confirms the target region visually before typing"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ticket=PLF-1, ide=jetbrains, backend=stub, kind=ticket_prompt)"
DSL: "autopilot: ok (ticket=PLF-1, ide=jetbrains, backend=stub, kind=ticket_prompt)"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=PLF-1 drives=1"
DSL: "  verdict: unknown (confidence=0.00) ticket=PLF-1 drives=1"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
DSL: "decision: drive_ticket (reason='ticket waiting for input', confidence=0.00)"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=stub)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=stub)[0m"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: ticket_prompt (queue=waiting_input ticket=PLF-1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: ticket_prompt (queue=waiting_input ticket=PLF-1)[0m"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=stub) [evidence: backend=stub, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=stub) [evidence: backend=stub, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:40:50+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_keeps_running_on_waiti0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_keeps_running_on_waiti0"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_up_keeps_running_on_waiti0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_up_keeps_running_on_waiti0"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=none (from cli:none, cli --agent-lane=none)"
DSL: "lane=none (from cli:none, cli --agent-lane=none)"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:40:51+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_keeps_running_on_waiti0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_keeps_running_on_waiti0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
DSL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:unknown (queue=waiting_input)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:unknown (queue=waiting_input)[0m"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
DSL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
DSL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=waiting_input waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s"
DSL: "summary cycle=1 queue=waiting_input waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 wait 0s; keep current waiting ticket none scoped"
DSL: "next 1/3 wait 0s; keep current waiting ticket none scoped"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 rerun planfile queue (max 50) and check whether none moved"
DSL: "next 2/3 rerun planfile queue (max 50) and check whether none moved"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 if queue becomes idle, run scan/discovery; if still waiting, use chat events/reflection before any redrive"
DSL: "next 3/3 if queue becomes idle, run scan/discovery; if still waiting, use chat events/reflection before any redrive"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:52+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
DSL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=2 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=2 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 2: skip:unknown (queue=waiting_input streak=1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 2: skip:unknown (queue=waiting_input streak=1)[0m"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
DSL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
DSL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=2 queue=waiting_input waiting=- streak=1 diagnostics=skipped autopilot=skipped sleep=0.0s"
DSL: "summary cycle=2 queue=waiting_input waiting=- streak=1 diagnostics=skipped autopilot=skipped sleep=0.0s"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 wait 0s; keep current waiting ticket none scoped"
DSL: "next 1/3 wait 0s; keep current waiting ticket none scoped"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 rerun planfile queue (max 50) and check whether none moved"
DSL: "next 2/3 rerun planfile queue (max 50) and check whether none moved"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 if queue becomes idle, run scan/discovery; if still waiting, use chat events/reflection before any redrive"
DSL: "next 3/3 if queue becomes idle, run scan/discovery; if still waiting, use chat events/reflection before any redrive"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:53+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
DSL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=3 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=3 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/3/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/3/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 3: skip:unknown (queue=waiting_input streak=2)[0m"
DSL: "    [33mNL:[0m  [32mCykl 3: skip:unknown (queue=waiting_input streak=2)[0m"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
DSL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
DSL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=3 queue=waiting_input waiting=- streak=2 diagnostics=skipped autopilot=skipped sleep=0.0s"
DSL: "summary cycle=3 queue=waiting_input waiting=- streak=2 diagnostics=skipped autopilot=skipped sleep=0.0s"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=3"
DSL: "next 1/3 stop now; reached max-cycles=3"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=waiting_input waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=waiting_input waiting=none"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=3; stopping"
DSL: "reached max-cycles=3; stopping"
```

### Activity (`2026-09-29T07:40:54+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:40:55+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0"
```

### Activity (`2026-09-29T07:40:55+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:40:55+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0"
```

### Activity (`2026-09-29T07:40:55+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:40:55+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:40:55+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:40:55+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=none (from cli:none, cli --agent-lane=none)"
DSL: "lane=none (from cli:none, cli --agent-lane=none)"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/strict-plugin
category: KORUAUTONOMOUS
```

```yaml
NL: "strict plugin version/ack policy enabled by default"
DSL: "strict plugin version/ack policy enabled by default"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket-decision
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket decision: lane=auto ide=auto source=env:KORU_AUTOPILOT_SOCKET path=/run/user/1000/koru-autopilot.sock"
DSL: "autopilot socket decision: lane=auto ide=auto source=env:KORU_AUTOPILOT_SOCKET path=/run/user/1000/koru-autopilot.sock"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autopilot/socket-decision
category: AUTOPILOT
```

```yaml
NL: "socket decision"
DSL: "socket decision"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/fail-daemon-version-mismatch
category: KORUAUTONOMOUS
```

```yaml
NL: "[FAIL] daemon_version_mismatch: daemon did not report version; expected 0.1.461"
DSL: "[FAIL] daemon_version_mismatch: daemon did not report version; expected 0.1.461"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/fix
category: KORUAUTONOMOUS
```

```yaml
NL: "fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
DSL: "fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/fail-plugin-workspace-mismatch
category: KORUAUTONOMOUS
```

```yaml
NL: "[FAIL] plugin_workspace_mismatch: connected plugin has no workspaceFolders"
DSL: "[FAIL] plugin_workspace_mismatch: connected plugin has no workspaceFolders"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/fix
category: KORUAUTONOMOUS
```

```yaml
NL: "fix → open /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0 in auto, then 'koru: Connect autopilot daemon'"
DSL: "fix → open /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0 in auto, then 'koru: Connect autopilot daemon'"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/primary-fix
category: KORUAUTONOMOUS
```

```yaml
NL: "primary fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
DSL: "primary fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_stops_on_waiting_input0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/skipped
category: INFO
```

```yaml
NL: "skipped"
DSL: "skipped"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/autopilot-skipped-this-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot skipped this cycle; ide=auto requires a compatible connected plugin"
DSL: "autopilot skipped this cycle; ide=auto requires a compatible connected plugin"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
DSL: "- pre-drive: no viable control route — ide_plugin_socket: no IDE plugin connected for auto; vdisplay_verified_injection: no chat calibration for 'auto' in ide-os-injector.json; xdotool_injection: requires an x11 session (current: wayland); wtype_injection: compositor does not support the virtual keyboard protocol; ydotool_guarded_injection: focused window cannot be identified on this compositor; ydotool_blind_injection: blind typing needs the explicit KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1 opt-in (GNOME Wayland exposes no focus introspection)"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/pre-drive-readiness
category: INFO
```

```yaml
NL: "- pre-drive readiness: queue is waiting_input but autopilot plugin is not connected (ide=auto version=- blocked: connected autopilot plugin protocol missing: minimum=1; install the current VSIX, reload the IDE window, then run `koru: Connect autopilot daemon`.); drive will be skipped until plugin reconnects"
DSL: "- pre-drive readiness: queue is waiting_input but autopilot plugin is not connected (ide=auto version=- blocked: connected autopilot plugin protocol missing: minimum=1; install the current VSIX, reload the IDE window, then run `koru: Connect autopilot daemon`.); drive will be skipped until plugin reconnects"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=waiting_input diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:unknown (queue=waiting_input)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:unknown (queue=waiting_input)[0m"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
DSL: "    [33mDSL:[0m [34mnext: keep waiting ticket scoped; rerun queue next cycle[0m"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
DSL: "  [33mdecision:[0m because[unknown] No structured reason recorded for this cycle."
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=waiting_input waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s"
DSL: "summary cycle=1 queue=waiting_input waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; queue is waiting for operator input on none"
DSL: "next 1/3 stop now; queue is waiting for operator input on none"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 operator should mark none done/input/fail through planfile"
DSL: "next 2/3 operator should mark none done/input/fail through planfile"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will resume from the updated queue state"
DSL: "next 3/3 next koru auto run will resume from the updated queue state"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/queue-is-waiting-input-stopping
category: KORUAUTONOMOUS
```

```yaml
NL: "queue is waiting_input; stopping until human/manual ticket recovery marks it ready or done"
DSL: "queue is waiting_input; stopping until human/manual ticket recovery marks it ready or done"
```

### Activity (`2026-09-29T07:40:56+00:00`)

```yaml
uri: koru://autonomous/nfo-structured-log
category: KORUAUTONOMOUS
```

```yaml
NL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
DSL: "nfo structured log -> /tmp/pytest-of-tom/pytest-33/test_ticket_sources_env_overri0/.planfile/.koru/nfo-events.jsonl"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/init-done
category: KORUAUTONOMOUS
```

```yaml
NL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0"
DSL: "init done at /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/version
category: KORUAUTONOMOUS
```

```yaml
NL: "koru 0.1.461 (python 3.13.12)"
DSL: "koru 0.1.461 (python 3.13.12)"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/project-root
category: KORUAUTONOMOUS
```

```yaml
NL: "project /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0"
DSL: "project /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/session
category: KORUAUTONOMOUS
```

```yaml
NL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
DSL: "session=wayland TERM_PROGRAM=- XDG_RUNTIME_DIR=/run/user/1000"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/running-ides
category: KORUAUTONOMOUS
```

```yaml
NL: "running IDEs: (none detected)"
DSL: "running IDEs: (none detected)"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/terminal-hint
category: KORUAUTONOMOUS
```

```yaml
NL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
DSL: "terminal hint → jetbrains (kind=integrated, source=env:TERMINAL_EMULATOR)"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/lane
category: KORUAUTONOMOUS
```

```yaml
NL: "lane=none (from cli:none, cli --agent-lane=none)"
DSL: "lane=none (from cli:none, cli --agent-lane=none)"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/autopilot-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
DSL: "autopilot IDE=auto (from router:auto, cli --autopilot-ide=auto)"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
DSL: "autopilot socket → /run/user/1000/koru-autopilot.sock"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/strict-plugin
category: KORUAUTONOMOUS
```

```yaml
NL: "strict plugin version/ack policy enabled by default"
DSL: "strict plugin version/ack policy enabled by default"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket-decision
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket decision: lane=auto ide=auto source=env:KORU_AUTOPILOT_SOCKET path=/tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/koru-autopilot-test.sock"
DSL: "autopilot socket decision: lane=auto ide=auto source=env:KORU_AUTOPILOT_SOCKET path=/tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/koru-autopilot-test.sock"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autopilot/socket-decision
category: AUTOPILOT
```

```yaml
NL: "socket decision"
DSL: "socket decision"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/fail-daemon-version-mismatch
category: KORUAUTONOMOUS
```

```yaml
NL: "[FAIL] daemon_version_mismatch: daemon did not report version; expected 0.1.461"
DSL: "[FAIL] daemon_version_mismatch: daemon did not report version; expected 0.1.461"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/fix
category: KORUAUTONOMOUS
```

```yaml
NL: "fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
DSL: "fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/socket-probe-stale-with-status
category: KORUAUTONOMOUS
```

```yaml
NL: "[WARN] socket_probe_stale_with_status: socket probe reports no listener at /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/koru-autopilot-test.sock, but daemon status is available; keeping socket in place"
DSL: "[WARN] socket_probe_stale_with_status: socket probe reports no listener at /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/koru-autopilot-test.sock, but daemon status is available; keeping socket in place"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/fail-plugin-workspace-mismatch
category: KORUAUTONOMOUS
```

```yaml
NL: "[FAIL] plugin_workspace_mismatch: connected plugin has no workspaceFolders"
DSL: "[FAIL] plugin_workspace_mismatch: connected plugin has no workspaceFolders"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/fix
category: KORUAUTONOMOUS
```

```yaml
NL: "fix → open /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0 in auto, then 'koru: Connect autopilot daemon'"
DSL: "fix → open /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0 in auto, then 'koru: Connect autopilot daemon'"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/primary-fix
category: KORUAUTONOMOUS
```

```yaml
NL: "primary fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
DSL: "primary fix → KORU_AUTOPILOT_INSTANCE=auto koru autopilot shutdown && koru auto"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/env2llm-registry-refreshed-1
category: KORUAUTONOMOUS
```

```yaml
NL: "env2llm registry refreshed (1 commands) -> ?"
DSL: "env2llm registry refreshed (1 commands) -> ?"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://autonomous/mcp-bootstrap-added-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/.cursor/mcp.json"
DSL: "mcp bootstrap added ide=cursor -> /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/.cursor/mcp.json"
```

### Activity (`2026-09-29T07:40:58+00:00`)

```yaml
uri: koru://info/skipped
category: INFO
```

```yaml
NL: "skipped"
DSL: "skipped"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://info/event
category: INFO
```

```yaml
NL: ""
DSL: ""
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/co-zrobić-teraz-operator
category: KORUAUTONOMOUS
```

```yaml
NL: "--- co zrobić teraz (operator IDE) ---"
DSL: "--- co zrobić teraz (operator IDE) ---"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/plugin-niedostępny-dla-ide
category: KORUAUTONOMOUS
```

```yaml
NL: "[i] plugin niedostępny dla ide=auto — używam ścieżki keyboard/OS-injector"
DSL: "[i] plugin niedostępny dla ide=auto — używam ścieżki keyboard/OS-injector"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/1-otwórz-auto-z
category: KORUAUTONOMOUS
```

```yaml
NL: "1) Otwórz auto z root = /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0"
DSL: "1) Otwórz auto z root = /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/2-mcp
category: KORUAUTONOMOUS
```

```yaml
NL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
DSL: "2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/3-socket-daemona
category: KORUAUTONOMOUS
```

```yaml
NL: "3) Socket daemona = /run/user/1000/koru-autopilot.sock"
DSL: "3) Socket daemona = /run/user/1000/koru-autopilot.sock"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/4-ustaw-w-shellu
category: KORUAUTONOMOUS
```

```yaml
NL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=auto"
DSL: "4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE=auto"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/5-wayland
category: KORUAUTONOMOUS
```

```yaml
NL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide auto (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance auto --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide auto; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
DSL: "5) Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide auto (starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, select HDMI-1, keep the tab open); lower-level: vdisplay services up --instance auto --source HDMI-1 --open-browser-bridge; vdisplay services status --source HDMI-1; set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives; koru autopilot prepare-vdisplay --ide auto; manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; fallback keeper: vdisplay agent screencast start --force, then verify with vdisplay agent screencast probe --via-agent --source HDMI-1; blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/6-na-waylandzie-nie
category: KORUAUTONOMOUS
```

```yaml
NL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
DSL: "6) Na Waylandzie nie używaj ślepego OS injectora dla JetBrains; daemon odmówi, jeśli vdisplay/imgl nie potwierdzi celu."
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/7-kalibracja-os-injectora
category: KORUAUTONOMOUS
```

```yaml
NL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=auto"
DSL: "7) Kalibracja OS injectora (ostateczny fallback): task koru:ide-os:calibrate IDE=auto"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/8-test-semantyczny
category: KORUAUTONOMOUS
```

```yaml
NL: "8) Test semantyczny: koru autopilot drive --ide auto 'probe test'"
DSL: "8) Test semantyczny: koru autopilot drive --ide auto 'probe test'"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/9-dashboard
category: KORUAUTONOMOUS
```

```yaml
NL: "9) Dashboard: task koru:server → http://localhost:8765/"
DSL: "9) Dashboard: task koru:server → http://localhost:8765/"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://autonomous/autopilot-skipped-this-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot skipped this cycle; ide=auto requires a compatible connected plugin"
DSL: "autopilot skipped this cycle; ide=auto requires a compatible connected plugin"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:40:59+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [FAIL] socket_lane_mismatch: socket koru-autopilot-test.sock is lane 'test', but configured instance is 'auto'"
DSL: "- pre-drive: [FAIL] socket_lane_mismatch: socket koru-autopilot-test.sock is lane 'test', but configured instance is 'auto'"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → koru autopilot shutdown && koru auto"
DSL: "- pre-drive: fix → koru autopilot shutdown && koru auto"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: primary fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: primary fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=1 queue=idle waiting=- streak=0 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 wait 0s; queue is idle — no eligible work in the current queue. Open tickets may wait for an operator, dependencies or another queue; autopilot drive is suppressed"
DSL: "next 1/3 wait 0s; queue is idle — no eligible work in the current queue. Open tickets may wait for an operator, dependencies or another queue; autopilot drive is suppressed"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 strategy detail→general: planfile ticket queue first; when no work is eligible, idle scan is disabled unless explicitly requested"
DSL: "next 2/3 strategy detail→general: planfile ticket queue first; when no work is eligible, idle scan is disabled unless explicitly requested"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 quick links: create discovery ticket http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; tickets http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; optional signal scan: `koru scan --apply` (preserves project history)"
DSL: "next 3/3 quick links: create discovery ticket http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; tickets http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; optional signal scan: `koru scan --apply` (preserves project history)"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/autopilot-socket-missing
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot socket missing at /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/koru-autopilot-test.sock; restarting or taking over daemon…"
DSL: "autopilot socket missing at /tmp/pytest-of-tom/pytest-33/test_up_restarts_autopilot_whe0/koru-autopilot-test.sock; restarting or taking over daemon…"
```

### Activity (`2026-09-29T07:41:00+00:00`)

```yaml
uri: koru://autonomous/autopilot-skipped-this-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "autopilot skipped this cycle; ide=auto requires a compatible connected plugin"
DSL: "autopilot skipped this cycle; ide=auto requires a compatible connected plugin"
```

### Activity (`2026-09-29T07:41:01+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50 --queue-name default"
DSL: "koru --queue --loop --max-iterations 50 --queue-name default"
```

### Activity (`2026-09-29T07:41:01+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto (lane=auto)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto (auto)."
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [FAIL] socket_lane_mismatch: socket koru-autopilot-test.sock is lane 'test', but configured instance is 'auto'"
DSL: "- pre-drive: [FAIL] socket_lane_mismatch: socket koru-autopilot-test.sock is lane 'test', but configured instance is 'auto'"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → koru autopilot shutdown && koru auto"
DSL: "- pre-drive: fix → koru autopilot shutdown && koru auto"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: primary fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: primary fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 2: skip:idle_no_ticket (queue=idle streak=1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 2: skip:idle_no_ticket (queue=idle streak=1)[0m"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/summary-cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "summary cycle=2 queue=idle waiting=- streak=1 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
DSL: "summary cycle=2 queue=idle waiting=- streak=1 diagnostics=skipped autopilot=skipped sleep=0.0s planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0 ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 1/3 stop now; reached max-cycles=2"
DSL: "next 1/3 stop now; reached max-cycles=2"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
DSL: "next 2/3 preserve checkpoint with queue=idle waiting=none"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/next
category: KORUAUTONOMOUS
```

```yaml
NL: "next 3/3 next koru auto run will continue from the saved checkpoint"
DSL: "next 3/3 next koru auto run will continue from the saved checkpoint"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/action-show-decision-trace
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
DSL: "action [show decision trace] `koru replay 'trace show-decisions --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/action-show-interfaces-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
DSL: "action [show interfaces] `koru replay 'trace show-interfaces --url=http://127.0.0.1:8765'`"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/action-inspect-tickets
category: KORUAUTONOMOUS
```

```yaml
NL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
DSL: "action [inspect tickets] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_up_restarts_autopilot_whe0"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/action-scan-signals-koru
category: KORUAUTONOMOUS
```

```yaml
NL: "action [scan signals] `koru replay 'scan force'`"
DSL: "action [scan signals] `koru replay 'scan force'`"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/reached-max-cycles
category: KORUAUTONOMOUS
```

```yaml
NL: "reached max-cycles=2; stopping"
DSL: "reached max-cycles=2; stopping"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/idle-diagnostics-disabled-profile
category: KORUAUTONOMOUS
```

```yaml
NL: "idle diagnostics disabled (profile=off)"
DSL: "idle diagnostics disabled (profile=off)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/queue-idle
category: KORUAUTONOMOUS
```

```yaml
NL: "queue idle -> running semcod diagnostics (profile=quick)"
DSL: "queue idle -> running semcod diagnostics (profile=quick)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/auto-diag-tworzę-ticket-dla
category: TICKET
```

```yaml
NL: "[AUTO-DIAG] tworzę ticket dla regix"
DSL: "[AUTO-DIAG] tworzę ticket dla regix «[AUTO-DIAG] regix needs attention in cycle 1. queue_status=idle. Check: regix compare HEAD --local --format rich. Investigate and fix regression, stale quality artifact, or broken diagnostic gate.»"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/utworzono-plf-001-auto-diag-regix
category: TICKET
```

```yaml
NL: "utworzono PLF-001 ([AUTO-DIAG] regix needs attention in cycle 1. queue_status=idle. Check: regix compare HEAD --local --format rich. Inv...) kolejka=diag executor=human"
DSL: "utworzono PLF-001 ([AUTO-DIAG] regix needs attention in cycle 1. queue_status=idle. Check: regix compare HEAD --local --format rich. Inv...) kolejka=diag executor=human «[AUTO-DIAG] regix needs attention in cycle 1. queue_status=idle. Check: regix compare HEAD --local --format rich. Investigate and fix regression, stale quality artifact, or broken diagnostic gate.»"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/auto-diag-regix
category: TICKET
```

```yaml
NL: "[AUTO-DIAG] regix → PLF-001 (queue=diag)"
DSL: "[AUTO-DIAG] regix → PLF-001 (queue=diag)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/created-diagnostic-ticket-plf-001
category: INFO
```

```yaml
NL: "+ created diagnostic ticket PLF-001 for regix (queue=diag)"
DSL: "+ created diagnostic ticket PLF-001 for regix (queue=diag)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/wup-watch-already-running
category: KORUAUTONOMOUS
```

```yaml
NL: "WUP watch already running (service-health.json updated 0s ago) — skipping duplicate spawn"
DSL: "WUP watch already running (service-health.json updated 0s ago) — skipping duplicate spawn"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/wup-watch
category: INFO
```

```yaml
NL: "+ wup watch /tmp/pytest-of-tom/pytest-33/test_start_wup_watch_spawns_wh0 --deps deps.json --cpu-throttle 0.8 --debounce 2 --cooldown 300 --mode testql --scenarios-dir testql-scenarios --testql-bin testql --track-dir .wup/tracks --quick-limit 3"
DSL: "+ wup watch /tmp/pytest-of-tom/pytest-33/test_start_wup_watch_spawns_wh0 --deps deps.json --cpu-throttle 0.8 --debounce 2 --cooldown 300 --mode testql --scenarios-dir testql-scenarios --testql-bin testql --track-dir .wup/tracks --quick-limit 3"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/started-wup-watcher-pid
category: KORUAUTONOMOUS
```

```yaml
NL: "started WUP watcher pid=321 mode=testql"
DSL: "started WUP watcher pid=321 mode=testql"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/wup-watch
category: INFO
```

```yaml
NL: "+ wup watch /tmp/pytest-of-tom/pytest-33/test_start_wup_watch_passes_pl0 --deps deps.json --cpu-throttle 0.8 --debounce 2 --cooldown 300 --mode testql --scenarios-dir testql-scenarios --testql-bin testql --track-dir .wup/tracks --quick-limit 3"
DSL: "+ wup watch /tmp/pytest-of-tom/pytest-33/test_start_wup_watch_passes_pl0 --deps deps.json --cpu-throttle 0.8 --debounce 2 --cooldown 300 --mode testql --scenarios-dir testql-scenarios --testql-bin testql --track-dir .wup/tracks --quick-limit 3"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/started-wup-watcher-pid
category: KORUAUTONOMOUS
```

```yaml
NL: "started WUP watcher pid=123 mode=testql"
DSL: "started WUP watcher pid=123 mode=testql"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/docker-compose-f-docker-composeyml
category: INFO
```

```yaml
NL: "+ docker compose -f docker-compose.yml --profile simulator up -d firmware"
DSL: "+ docker compose -f docker-compose.yml --profile simulator up -d firmware"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://autonomous/wup-compose-service-ready
category: KORUAUTONOMOUS
```

```yaml
NL: "WUP compose service ready: firmware"
DSL: "WUP compose service ready: firmware"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/auto-diag-tworzę-ticket-dla
category: TICKET
```

```yaml
NL: "[AUTO-DIAG] tworzę ticket dla wup-api"
DSL: "[AUTO-DIAG] tworzę ticket dla wup-api «[AUTO-DIAG] wup-api needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=api stage=quick message=TestQL scenario failed track=.wup/tracks/api.json. Investigate and fix regression, stale quality artifact, or broken diagnostic gate.»"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/utworzono-plf-001-auto-diag-wup-api
category: TICKET
```

```yaml
NL: "utworzono PLF-001 ([AUTO-DIAG] wup-api needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=api stage=quick message=...) kolejka=default executor=human"
DSL: "utworzono PLF-001 ([AUTO-DIAG] wup-api needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=api stage=quick message=...) kolejka=default executor=human «[AUTO-DIAG] wup-api needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=api stage=quick message=TestQL scenario failed track=.wup/tracks/api.json. Investigate and fix regression, stale quality artifact, or broken diagnostic gate.»"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/auto-diag-wup-api
category: TICKET
```

```yaml
NL: "[AUTO-DIAG] wup-api → PLF-001 (queue=default)"
DSL: "[AUTO-DIAG] wup-api → PLF-001 (queue=default)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/created-diagnostic-ticket-plf-001
category: INFO
```

```yaml
NL: "+ created diagnostic ticket PLF-001 for wup-api (queue=default)"
DSL: "+ created diagnostic ticket PLF-001 for wup-api (queue=default)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/auto-diag-tworzę-ticket-dla
category: TICKET
```

```yaml
NL: "[AUTO-DIAG] tworzę ticket dla wup-src/koru"
DSL: "[AUTO-DIAG] tworzę ticket dla wup-src/koru «[AUTO-DIAG] wup-src/koru needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=src/koru stage=quick message=cli-koru.testql.toon.yaml track=/tmp/track.json. Investigate and fix regression, stale quality artifact, or broken diagnostic gate.»"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/utworzono-plf-001-auto-diag
category: TICKET
```

```yaml
NL: "utworzono PLF-001 ([AUTO-DIAG] wup-src/koru needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=src/koru stage=quic...) kolejka=default executor=human"
DSL: "utworzono PLF-001 ([AUTO-DIAG] wup-src/koru needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=src/koru stage=quic...) kolejka=default executor=human «[AUTO-DIAG] wup-src/koru needs attention in cycle 0. queue_status=wup_failure. Check: WUP service=src/koru stage=quick message=cli-koru.testql.toon.yaml track=/tmp/track.json. Investigate and fix regression, stale quality artifact, or broken diagnostic gate.»"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/auto-diag
category: TICKET
```

```yaml
NL: "[AUTO-DIAG] wup-src/koru → PLF-001 (queue=default)"
DSL: "[AUTO-DIAG] wup-src/koru → PLF-001 (queue=default)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://info/created-diagnostic-ticket-plf-001
category: INFO
```

```yaml
NL: "+ created diagnostic ticket PLF-001 for wup-src/koru (queue=default)"
DSL: "+ created diagnostic ticket PLF-001 for wup-src/koru (queue=default)"
```

### Activity (`2026-09-29T07:41:02+00:00`)

```yaml
uri: koru://ticket/utworzono-plf-001-auto-diag-wup-koru-core
category: TICKET
```

```yaml
NL: "utworzono PLF-001 ([AUTO-DIAG] wup-koru-core needs attention in cycle 0. queue_status=wup_failure. Check: old failure.) kolejka=default executor=human"
DSL: "utworzono PLF-001 ([AUTO-DIAG] wup-koru-core needs attention in cycle 0. queue_status=wup_failure. Check: old failure.) kolejka=default executor=human «[AUTO-DIAG] wup-koru-core needs attention in cycle 0. queue_status=wup_failure. Check: old failure.»"
```

### Activity (`2026-09-29T07:41:03+00:00`)

```yaml
uri: koru://config/using-shell-client-aider
category: KORUCONFIG
```

```yaml
NL: "using shell client 'aider' from KORU_TILLM_CLIENT/URIRUN_KORU_IDE."
DSL: "using shell client 'aider' from KORU_TILLM_CLIENT/URIRUN_KORU_IDE."
```

### Activity (`2026-09-29T07:41:04+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=- attempt=1 reason=\"chat input is not focused/open\" evidence=\"kind=retry_focus; warn=focus; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=- attempt=1 reason=\"chat input is not focused/open\" evidence=\"kind=retry_focus; warn=focus; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
```

### Activity (`2026-09-29T07:41:04+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=- attempt=2 reason=\"submit could not be verified\" evidence=\"kind=retry_submit; warn=submit; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=- attempt=2 reason=\"submit could not be verified\" evidence=\"kind=retry_submit; warn=submit; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
```

### Activity (`2026-09-29T07:41:04+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=- attempt=1 reason=\"submit could not be verified A\" evidence=\"kind=retry_submit; warn=submit; sleep=5.0; max_attempts=2\" next=\"retry after policy sleep\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=- attempt=1 reason=\"submit could not be verified A\" evidence=\"kind=retry_submit; warn=submit; sleep=5.0; max_attempts=2\" next=\"retry after policy sleep\""
```

### Activity (`2026-09-29T07:41:04+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=stop transport=unknown phase=- attempt=2 reason=\"submit could not be verified B\" evidence=\"kind=stop; warn=-; sleep=0.0; max_attempts=2\" next=\"do not paste again; surface root cause to operator\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=stop transport=unknown phase=- attempt=2 reason=\"submit could not be verified B\" evidence=\"kind=stop; warn=-; sleep=0.0; max_attempts=2\" next=\"do not paste again; surface root cause to operator\""
```

### Activity (`2026-09-29T07:41:04+00:00`)

```yaml
uri: koru://integration/drive.retry_decision
category: INTEGRATION
```

```yaml
NL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=focus_failed attempt=1 reason=\"chat input is not focused/open\" evidence=\"kind=retry_focus; warn=focus; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
DSL: "koru.integration.v1 action=drive.retry_decision intent=\"decide whether another IDE interaction is safe\" actor=autonomous-loop target=cursor outcome=retry transport=unknown phase=focus_failed attempt=1 reason=\"chat input is not focused/open\" evidence=\"kind=retry_focus; warn=focus; sleep=5.0; max_attempts=3\" next=\"retry after policy sleep\""
```

### Activity (`2026-09-29T07:41:04+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 50"
DSL: "koru --queue --loop --max-iterations 50"
```

### Activity (`2026-09-29T07:41:04+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle"
```

### Activity (`2026-09-29T07:41:05+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:05+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Cursor"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Cursor"
```

### Activity (`2026-09-29T07:41:05+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru cursor auto` from Cursor's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=cursor, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru cursor auto` from Cursor's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=cursor, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:05+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Cursor ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Cursor ."
```

### Activity (`2026-09-29T07:41:05+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru cursor auto` or open Cursor's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru cursor auto` or open Cursor's integrated terminal."
```

### Activity (`2026-09-29T07:41:05+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=cursor and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=cursor and restart."
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: ok (ide=cursor, backend=gillm, kind=drive_prompt)"
DSL: "autopilot: ok (ide=cursor, backend=gillm, kind=drive_prompt)"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://info/verdict
category: INFO
```

```yaml
NL: "  verdict: unknown (confidence=0.00) ticket=- drives=0"
DSL: "  verdict: unknown (confidence=0.00) ticket=- drives=0"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://decision/decision
category: DECISION
```

```yaml
NL: "decision: run_discovery (reason='queue idle, no open tickets', confidence=0.00)"
DSL: "decision: run_discovery (reason='queue idle, no open tickets', confidence=0.00)"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=ok"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=ok"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=gillm)[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/submit_verified(backend=gillm)[0m"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: idle_ticket_prompt (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: idle_ticket_prompt (queue=idle)[0m"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: submit_verified(backend=gillm) [evidence: backend=gillm, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: submit_verified(backend=gillm) [evidence: backend=gillm, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
DSL: "    [33mDSL:[0m [34mnext: wait for IDE response, then advance queue[0m"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://info/autonomia-nie-wykonuje-zadania
category: INFO
```

```yaml
NL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Fhome%2Ftom%2Fgithub%2Fsemcod%2Fkoru%2Fproject ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Fhome%2Ftom%2Fgithub%2Fsemcod%2Fkoru%2Fproject"
DSL: "autonomia nie wykonuje zadania: brak zadania gotowego w bieżącej kolejce   → Otwarte zadania mogą czekać na operatora, zależności albo inną kolejkę. Sprawdź przyczynę oczekiwania w Planfile; skan i discovery zależą od konfiguracji lub jawnego polecenia operatora. Nowe zadanie dla nowej pracy: http://127.0.0.1:8765/llm/prompt/create-ticket-for-project?project=%2Fhome%2Ftom%2Fgithub%2Fsemcod%2Fkoru%2Fproject ; lista ticketów: http://127.0.0.1:8765/?tab=tickets&project=%2Fhome%2Ftom%2Fgithub%2Fsemcod%2Fkoru%2Fproject"
```

### Activity (`2026-09-29T07:41:16+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Fhome%2Ftom%2Fgithub%2Fsemcod%2Fkoru%2Fproject   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Fhome%2Ftom%2Fgithub%2Fsemcod%2Fkoru%2Fproject   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:41:17+00:00`)

```yaml
uri: koru://autonomous/create_ticket
category: KORUAUTONOMOUS
```

```yaml
NL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_idle_scan_quick_action_re0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
DSL: "action [create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Fpytest-of-tom%2Fpytest-33%2Ftest_idle_scan_quick_action_re0   → brak zadania gotowego w bieżącej kolejce; sprawdź zależności i zadania operatora, a nowe zadanie utwórz dla nowej pracy"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://autopilot/socket-decision
category: AUTOPILOT
```

```yaml
NL: "socket decision"
DSL: "socket decision"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://autopilot/socket-decision
category: AUTOPILOT
```

```yaml
NL: "socket decision"
DSL: "socket decision"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://autopilot/agent-unavailable-daemon-and
category: AUTOPILOT
```

```yaml
NL: "agent unavailable; daemon and plugin startup skipped"
DSL: "agent unavailable; daemon and plugin startup skipped"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://autopilot/action-off-daemon-and
category: AUTOPILOT
```

```yaml
NL: "action off; daemon and plugin startup skipped"
DSL: "action off; daemon and plugin startup skipped"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://run/koru-scan-apply
category: RUN
```

```yaml
NL: "koru scan --apply"
DSL: "koru scan --apply"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:41:28+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://run/koru-scan-apply
category: RUN
```

```yaml
NL: "koru scan --apply"
DSL: "koru scan --apply"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:41:29+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://run/koru-scan-apply
category: RUN
```

```yaml
NL: "koru scan --apply"
DSL: "koru scan --apply"
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:41:30+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://run/koru-scan-apply
category: RUN
```

```yaml
NL: "koru scan --apply"
DSL: "koru scan --apply"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:41:31+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is auto"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru auto auto` from auto's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=auto, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets auto ."
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru auto auto` or open auto's integrated terminal."
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=auto and restart."
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
DSL: "    [33mDSL:[0m [34mnext: run idle scan / intake strategy[0m"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://run/koru-scan-apply
category: RUN
```

```yaml
NL: "koru scan --apply"
DSL: "koru scan --apply"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:41:32+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:41:33+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
```

### Activity (`2026-09-29T07:41:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
```

### Activity (`2026-09-29T07:41:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
```

### Activity (`2026-09-29T07:41:33+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
```

### Activity (`2026-09-29T07:41:34+00:00`)

```yaml
uri: koru://chat/autopilot-skipped-idle-no-ticket
category: CHAT
```

```yaml
NL: "autopilot skipped (idle_no_ticket): no eligible ticket in the current queue; open work may be held → nothing to paste into the IDE chat. Drive is suppressed to avoid clobbering the user's input with stale prompts."
DSL: "autopilot skipped (idle_no_ticket): no eligible ticket in the current queue; open work may be held → nothing to paste into the IDE chat. Drive is suppressed to avoid clobbering the user's input with stale prompts."
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://autonomous/planfile-snapshot
category: KORUAUTONOMOUS
```

```yaml
NL: "planfile snapshot: planfile: 0 tickets in current sprint"
DSL: "planfile snapshot: planfile: 0 tickets in current sprint"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/next-cycle-rechecks-the
category: INFO
```

```yaml
NL: "  next cycle rechecks the configured queue; scan/discovery runs only when enabled. Inspect operator holds and dependencies before creating more work."
DSL: "  next cycle rechecks the configured queue; scan/discovery runs only when enabled. Inspect operator holds and dependencies before creating more work."
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/quick-actions
category: INFO
```

```yaml
NL: "  quick actions: create discovery ticket http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Ftmph1majcwn ; tickets http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Ftmph1majcwn ; optional signal scan: `koru scan --apply` (preserves project history)."
DSL: "  quick actions: create discovery ticket http://127.0.0.1:8765/llm/action/create-ticket-for-project?project=%2Ftmp%2Ftmph1majcwn ; tickets http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Ftmph1majcwn ; optional signal scan: `koru scan --apply` (preserves project history)."
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://chat/autopilot
category: CHAT
```

```yaml
NL: "autopilot: failed (no eligible ticket in the current queue, kind=skipped(idle_no_ticket))"
DSL: "autopilot: failed (no eligible ticket in the current queue, kind=skipped(idle_no_ticket))"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(idle_no_ticket)"
DSL: "cycle=1 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(idle_no_ticket)"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/1/decision/no_op[0m"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
DSL: "    [33mNL:[0m  [32mCykl 1: skip:idle_no_ticket (queue=idle)[0m"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_no_ticket, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle AND zero open planfile tickets[0m"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: scan / reopen done ticket / `koru --ticket`[0m"
DSL: "    [33mDSL:[0m [34mnext: scan / reopen done ticket / `koru --ticket`[0m"
```

### Activity (`2026-09-29T07:41:35+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
DSL: "  [33mdecision:[0m because[idle_no_ticket] No eligible ticket in the current queue can be driven; open work may be held. Drive is suppressed so the user's chat input isn't clobbered with stale prompts. — queue idle AND zero open planfile tickets"
```

### Activity (`2026-09-29T07:41:36+00:00`)

```yaml
uri: koru://run/koru-scan-apply
category: RUN
```

```yaml
NL: "koru scan --apply"
DSL: "koru scan --apply"
```

### Activity (`2026-09-29T07:41:36+00:00`)

```yaml
uri: koru://scan/scan
category: SCAN
```

```yaml
NL: "scan: suggestions=0 applied=0 skipped=0"
DSL: "scan: suggestions=0 applied=0 skipped=0"
```

### Activity (`2026-09-29T07:41:36+00:00`)

```yaml
uri: koru://run/koru-queue-loop-max-iterations
category: RUN
```

```yaml
NL: "koru --queue --loop --max-iterations 1"
DSL: "koru --queue --loop --max-iterations 1"
```

### Activity (`2026-09-29T07:41:36+00:00`)

```yaml
uri: koru://queue/queue
category: QUEUE
```

```yaml
NL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
DSL: "queue: iterations=1 completed=0 failed=0 waiting=0 last_status=idle waiting_ticket=none"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/monag-backlog-promotion-error
category: INFO
```

```yaml
NL: "  monag backlog promotion error: monag resume did not report this project"
DSL: "  monag backlog promotion error: monag resume did not report this project"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
DSL: "- pre-drive: [WARN] terminal_lane_mismatch: terminal host is jetbrains (integrated IDE terminal), but autopilot target is Windsurf"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
DSL: "- pre-drive: fix → run `coru windsurf auto` from Windsurf's integrated terminal, or export KORU_AUTOPILOT_INSTANCE=windsurf, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: This shell is inside JetBrains IDE, but autopilot lane targets Windsurf ."
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Run `coru windsurf auto` or open Windsurf's integrated terminal."
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/pre-drive
category: INFO
```

```yaml
NL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
DSL: "- pre-drive: [WARN] terminal_lane_operator_hint: Or export KORU_AUTOPILOT_INSTANCE=windsurf and restart."
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://chat/autopilot-skipped-idle-streak-1
category: CHAT
```

```yaml
NL: "autopilot skipped (idle_streak_1>=1)"
DSL: "autopilot skipped (idle_streak_1>=1)"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://autonomous/cycle
category: KORUAUTONOMOUS
```

```yaml
NL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(idle_streak)"
DSL: "cycle=2 queue=idle diagnostics=skipped wup=skipped autopilot=skipped(idle_streak)"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/35muri
category: INFO
```

```yaml
NL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
DSL: "  [35muri:[0m [36mkoru://cycle/2/decision/no_op[0m"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mCykl 2: skip:idle_streak (queue=idle streak=1)[0m"
DSL: "    [33mNL:[0m  [32mCykl 2: skip:idle_streak (queue=idle streak=1)[0m"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_streak, diagnostics=skipped, wup=skipped][0m"
DSL: "    [33mDSL:[0m [34maction: no_op [evidence: blocked_by=idle_streak, diagnostics=skipped, wup=skipped][0m"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/33mnl
category: INFO
```

```yaml
NL: "    [33mNL:[0m  [32mPowód: queue idle for 1 consecutive cycles[0m"
DSL: "    [33mNL:[0m  [32mPowód: queue idle for 1 consecutive cycles[0m"
```

### Activity (`2026-09-29T07:41:37+00:00`)

```yaml
uri: koru://info/33mdsl
category: INFO
```

```yaml
NL: "    [33mDSL:[0m [34mnext: let idle backoff drain before next drive[0m"
DSL: "    [33mDSL:[0m [34mnext: let idle backoff drain before next drive[0m"
```

### Activity (`2026-09-29T07:41:38+00:00`)

```yaml
uri: koru://info/33mdecision
category: INFO
```

```yaml
NL: "  [33mdecision:[0m because[idle_streak] Queue stayed idle for too many consecutive cycles; the loop is backing off. — queue idle for 1 consecutive cycles"
DSL: "  [33mdecision:[0m because[idle_streak] Queue stayed idle for too many consecutive cycles; the loop is backing off. — queue idle for 1 consecutive cycles"
```

### Activity (`2026-09-29T07:44:34+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:44:58+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:48:19+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:51:00+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:52:03+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:54:39+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:55:35+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:56:12+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T07:56:46+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T08:00:31+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T08:03:03+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

### Activity (`2026-09-29T10:18:54+00:00`)

```yaml
uri: koru://mcp/starting-stdio-mcp-server
category: MCP
```

```yaml
NL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
DSL: "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)"
```

