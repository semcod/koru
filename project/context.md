# System Architecture Analysis
<!-- generated in 0.00s -->

## Overview

- **Project**: /home/tom/github/semcod/koru
- **Primary Language**: python
- **Languages**: python: 120, shell: 41, yaml: 16, yml: 8, typescript: 6
- **Analysis Mode**: static
- **Total Functions**: 1037
- **Total Classes**: 89
- **Modules**: 206
- **Entry Points**: 392

## Architecture by Module

### plugins.koru-autopilot-vscode.src.extension
- **Functions**: 102
- **Classes**: 2
- **File**: `extension.ts`

### src.koru.cli
- **Functions**: 52
- **File**: `cli.py`

### src.koru.context
- **Functions**: 43
- **File**: `context.py`

### src.koru.autopilot.cli_command
- **Functions**: 37
- **File**: `cli_command.py`

### src.koru.autonomous
- **Functions**: 37
- **Classes**: 2
- **File**: `autonomous.py`

### src.koruapi.mcp_server
- **Functions**: 32
- **File**: `mcp_server.py`

### src.koruide.daemon
- **Functions**: 29
- **Classes**: 2
- **File**: `daemon.py`

### services.healing-webhook.app
- **Functions**: 27
- **File**: `app.py`

### src.koruide.os_injector
- **Functions**: 24
- **Classes**: 2
- **File**: `os_injector.py`

### plugins.koru-autopilot-vscode.src.probe-ladder
- **Functions**: 24
- **Classes**: 3
- **File**: `probe-ladder.ts`

### src.koruide.ide
- **Functions**: 22
- **Classes**: 1
- **File**: `ide.py`

### src.koru.mcp_provision
- **Functions**: 21
- **File**: `mcp_provision.py`

### src.koru.doctor
- **Functions**: 21
- **Classes**: 2
- **File**: `doctor.py`

### src.koruide.injector
- **Functions**: 20
- **Classes**: 4
- **File**: `injector.py`

### src.koru.bootstrap
- **Functions**: 19
- **Classes**: 2
- **File**: `bootstrap.py`

### plugins.koru-autopilot-vscode.src.socketPath
- **Functions**: 18
- **File**: `socketPath.ts`

### src.koru.scan
- **Functions**: 18
- **Classes**: 2
- **File**: `scan.py`

### src.koru.autonomy.operator_pipeline
- **Functions**: 18
- **Classes**: 2
- **File**: `operator_pipeline.py`

### plugins.koru-autopilot-vscode.src.dispatch-plan.test
- **Functions**: 17
- **File**: `dispatch-plan.test.ts`

### src.korudsl.library
- **Functions**: 16
- **File**: `library.py`

## Key Entry Points

Main execution flows into the system:

### src.koru.autonomous_cycle.run_cycle
- **Calls**: src.koru.autonomous_cycle._drain_autopilot_events, src.koru.run_log.RunLogWriter._emit, src.koru.autonomy.ide_work.resolve_in_progress_stale_minutes, src.koru.autonomy.post_run_verify.load_post_run_verify_config, src.koru.autonomy.post_run_verify.verify_after_ide_work, src.koru.autonomous_cycle._queue_loop_waiting_ticket_label, DiagnosticResult, WupHealthResult

### src.koru.autonomous_parser.build_parser
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_subparsers, sub.add_parser, doctor.add_argument, sub.add_parser, heal.add_argument, heal.add_argument

### src.koru.autonomy.config.AutonomyConfig.from_env
> Create config from environment variables (shell compatibility).
- **Calls**: os.getenv, cls, None.strip, max, Path, os.getenv, os.getenv, src.koru.autonomy.env.env_truthy

### src.koru.queue.runners.run_llm_request
> Call an OpenAI-compatible chat-completion endpoint (default OpenRouter).

Reads ``OPENROUTER_API_KEY`` from the environment when ``endpoint``
points a
- **Calls**: str, str, request.get, messages.append, request.get, os.getenv, os.getenv, urllib.request.Request

### src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
> Fallback: OS injector profile (X11) or :class:`Injector` keyboard sim.
- **Calls**: src.koruide.ide.resolve_drive_target, src.koruide.ide.pick_target, self._send, self.log, self.audit.record, self.log, text.replace, src.koru.ide_runtime.detect_running_ides

### src.koruide.daemon.AutopilotDaemon._handle_plugin_event
- **Calls**: self.log, self._append_event, self.audit.record, None.encode, self._send, time.monotonic, len, self._send

### src.koru.cli._topology_main
- **Calls**: None.parse_args, args.project.resolve, src.koru.topology.load_topology, src.koru.topology.load_topology, None.get, None.get, isinstance, scripts.koru-soak-monitor.print

### src.koruapi.server.KoruAPIHandler.do_POST
- **Calls**: urlparse, src.koru.activity_log.activity, int, str, str, None.resolve, src.koruapi.server._json_response, self.rfile.read

### src.koru.autonomous_diagnostics.run_idle_diagnostics
- **Calls**: profile.lower, stdio_info, shutil.which, diagnostic_state_dir.mkdir, make_result, stdio_info, make_result, is_topology_enabled

### src.koru.autonomous_wup._read_wup_health
- **Calls**: health_path.is_file, events_path.is_file, max, max, WupHealthResult, sorted, json.loads, isinstance

### src.koru.queue.runners.run_api_request
> Execute an HTTP API request.
- **Calls**: request.get, urllib.request.Request, float, str, str, None.encode, headers.setdefault, str

### src.koru.autonomous._run_idle_diagnostics
- **Calls**: profile.lower, src.koru.autonomous._stdio_info, shutil.which, diagnostic_state_dir.mkdir, DiagnosticResult, src.koru.autonomous._stdio_info, DiagnosticResult, src.koru.autonomous._is_topology_enabled

### src.koru.autonomy.env.autonomous_environ_doctor_probe
> Return ``(status, detail)`` for ``koru --doctor``; process-global, no I/O.
- **Calls**: os.environ.get, src.koru.autonomy.env.env_truthy, os.environ.get, os.environ.get, src.koru.autonomy.env.env_truthy, None.strip, None.lower, None.strip

### src.koru.autopilot.cli_command._action_session_start
- **Calls**: src.koru.autopilot.cli_command._resolve_session_ides, max, captured.items, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, float, scripts.koru-soak-monitor.print, time.sleep

### src.koru.cli._gc_main
- **Calls**: None.parse_args, frozenset, src.koru.gc.run_gc, src.koru.events.emit_management_event, args.project.resolve, scripts.koru-soak-monitor.print, src.koru.cli._build_gc_parser, s.strip

### src.koruide.daemon.AutopilotDaemon._handle_ack
- **Calls**: bool, src.koruide.protocol.ack, self._send, msg.data.get, None.lower, info.get, relay.encode, msg.data.items

### src.koru.autopilot.cli_command._action_drive
- **Calls**: src.koru.autopilot.cli_command._client, src.koru.autopilot.cli_command._should_fallback_to_direct, scripts.koru-soak-monitor.print, None.strip, None.strip, scripts.koru-soak-monitor.print, src.koru.autopilot.cli_command._run_direct_drive, client.is_running

### src.koru.cli._task_main
- **Calls**: None.parse_args, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, src.koru.events.emit_management_event, src.koru.tools.load_tool_registry, src.koru.tools.find_tool_entry

### src.koru.cli._agent_main
- **Calls**: None.parse_args, args.project.resolve, src.koru.agents.detect_agent_options, None.strip, src.koru.context.build_context, src.koru.context.render_markdown_handoff, src.koru.agents.select_agent, src.koru.agents.launch_agent

### src.koru.cli._agent_backends_main
> List or describe IDE agent backend profiles (``agent_backends``).
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.parse_args, src.koru.agent_backends.iter_agent_backend_profiles, src.koru.agent_backends.get_agent_backend_profile, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print

### src.koru.gate.parse_authorizations
> Extract all gate authorizations recorded on a ticket.

Returns them in insertion order so callers can pick the most
recent one with ``parse_authorizat
- **Calls**: str, out.append, isinstance, note.startswith, json.loads, payload.get, payload.get, isinstance

### src.koruide.daemon.AutopilotDaemon._handle_drive
- **Calls**: msg.data.get, bool, bool, self._plugin_for, self._drive_via_keyboard, self._send, isinstance, msg.data.get

### services.healing-webhook.app.heal_vallm_validate
> Run vallm tier-1 (check) on all files mapped from the alert component.

Cheap pre-flight gate: blocks AI patches if affected files are already
syntact
- **Calls**: services.healing-webhook.app._resolve_affected_files, services.healing-webhook.app._record_action, isinstance, detail.get, services.healing-webhook.app._record_action, services.healing-webhook.app._run_vallm_check, sum, max

### services.healing-webhook.app.probe_failure
> Accept the testql-watchdog probe-failure payload.
- **Calls**: app.post, None.inc, payload.get, log.info, services.healing-webhook.app.create_planfile_ticket, request.json, payload.get, len

### src.koruide.injector.Injector._type_with_backend
- **Calls**: src.koruide.injector._extra_enter_count, self._call, self._call, range, self._call, self._call, self._press_wtype, range

### src.koru.doctor.render_text
> Human-readable rendering — fixed-width status column.
- **Calls**: lines.append, lines.append, max, report.summary, sum, counts.get, counts.get, counts.get

### src.koruapi.cli.main
- **Calls**: src.koruapi.cli._build_parser, parser.parse_known_args, args.project.resolve, sys.stdout.write, src.koru.activity_log.activity, src.koru.activity_log.activity, sys.stdout.write, api_serve

### services.healing-webhook.app.alertmanager_webhook
> Accept the Alertmanager webhook payload (v4).
- **Calls**: app.post, payload.get, request.json, alert.get, labels.get, labels.get, labels.get, alert.get

### src.koruide.daemon.AutopilotDaemon._on_readable
- **Calls**: client.buf.extend, client.sock.recv, self._drop, len, self._send, self._drop, client.buf.partition, bytearray

### src.koru.agent_backends.load_agent_integration_config
> Load ``ide_integration`` from ``<project>/koru.yaml`` if present.
- **Calls**: data.get, block.get, block.get, raw_lanes.items, AgentIntegrationConfig, path.is_file, isinstance, isinstance

## Process Flows

Key execution flows identified:

### Flow 1: run_cycle
```
run_cycle [src.koru.autonomous_cycle]
  └─> _drain_autopilot_events
      └─> _autopilot_event_path
  └─ →> _emit
      └─ →> print
  └─ →> resolve_in_progress_stale_minutes
      └─ →> load_koru_project_pipeline
          └─> project_pipeline_path
```

### Flow 2: build_parser
```
build_parser [src.koru.autonomous_parser]
```

### Flow 3: from_env
```
from_env [src.koru.autonomy.config.AutonomyConfig]
```

### Flow 4: run_llm_request
```
run_llm_request [src.koru.queue.runners]
```

### Flow 5: _drive_via_keyboard
```
_drive_via_keyboard [src.koruide.daemon.AutopilotDaemon]
  └─ →> resolve_drive_target
      └─> detect_running_ides
          └─> _iter_proc_pids
          └─> _read_comm
  └─ →> pick_target
      └─> detect_terminal_host_ide_id
          └─> _vscode_family_env_present
      └─> focused_ide
```

### Flow 6: _handle_plugin_event
```
_handle_plugin_event [src.koruide.daemon.AutopilotDaemon]
```

### Flow 7: _topology_main
```
_topology_main [src.koru.cli]
  └─ →> load_topology
      └─> topology_path
      └─> _read_yaml
      └─ →> detect_semcod_tools
  └─ →> load_topology
      └─> topology_path
      └─> _read_yaml
      └─ →> detect_semcod_tools
```

### Flow 8: do_POST
```
do_POST [src.koruapi.server.KoruAPIHandler]
  └─ →> activity
      └─> _out_stream
      └─> activity_enabled
      └─ →> print
```

### Flow 9: run_idle_diagnostics
```
run_idle_diagnostics [src.koru.autonomous_diagnostics]
```

### Flow 10: _read_wup_health
```
_read_wup_health [src.koru.autonomous_wup]
```

## Key Classes

### plugins.koru-autopilot-vscode.src.extension.AutopilotBridge
- **Methods**: 100
- **Key Methods**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.socketPath, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.tryConnectNext, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.p, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.debugLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.sock

### src.koruide.daemon.AutopilotDaemon
> Selector-based unix-socket broker.

Parameters
----------
socket_path:
    Where to bind. Defaults t
- **Methods**: 24
- **Key Methods**: src.koruide.daemon.AutopilotDaemon.__init__, src.koruide.daemon.AutopilotDaemon.start, src.koruide.daemon.AutopilotDaemon.serve_forever, src.koruide.daemon.AutopilotDaemon.stop, src.koruide.daemon.AutopilotDaemon._shutdown, src.koruide.daemon.AutopilotDaemon._accept, src.koruide.daemon.AutopilotDaemon._on_readable, src.koruide.daemon.AutopilotDaemon._dispatch, src.koruide.daemon.AutopilotDaemon._send, src.koruide.daemon.AutopilotDaemon._drop

### src.koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 9
- **Key Methods**: src.koruide.injector.Injector.probe, src.koruide.injector.Injector._candidate_backends, src.koruide.injector.Injector.select_backend, src.koruide.injector.Injector._type_with_backend, src.koruide.injector.Injector.type_text, src.koruide.injector.Injector.submit_only, src.koruide.injector.Injector._probe_one, src.koruide.injector.Injector._call, src.koruide.injector.Injector._press_wtype

### src.koruide.client.KoruIDEClient
> Connect, send one message, read one reply, disconnect.
- **Methods**: 7
- **Key Methods**: src.koruide.client.KoruIDEClient.__init__, src.koruide.client.KoruIDEClient._connect, src.koruide.client.KoruIDEClient.request, src.koruide.client.KoruIDEClient.is_running, src.koruide.client.KoruIDEClient.drive, src.koruide.client.KoruIDEClient.status, src.koruide.client.KoruIDEClient.shutdown

### src.koru.doctor.DoctorReport
> Aggregate result of ``run_diagnostics``.
- **Methods**: 4
- **Key Methods**: src.koru.doctor.DoctorReport.has_failures, src.koru.doctor.DoctorReport.has_warnings, src.koru.doctor.DoctorReport.summary, src.koru.doctor.DoctorReport.to_dict

### src.koru.run_log.RunLogWriter
> Append-only JSONL writer with best-effort durability.

The constructor does not open the file — that
- **Methods**: 4
- **Key Methods**: src.koru.run_log.RunLogWriter._emit, src.koru.run_log.RunLogWriter.write_header, src.koru.run_log.RunLogWriter.write_iteration, src.koru.run_log.RunLogWriter.write_footer

### src.koru.ide_client.IDEControlClient
> Minimal interface `koru` runtime code expects from an IDE client.
- **Methods**: 4
- **Key Methods**: src.koru.ide_client.IDEControlClient.is_running, src.koru.ide_client.IDEControlClient.drive, src.koru.ide_client.IDEControlClient.status, src.koru.ide_client.IDEControlClient.shutdown
- **Inherits**: Protocol

### src.koru.ide_client.LegacyAutopilotClientAdapter
> Expose legacy :class:`AutopilotClient` through :class:`IDEControlClient`.
- **Methods**: 4
- **Key Methods**: src.koru.ide_client.LegacyAutopilotClientAdapter.is_running, src.koru.ide_client.LegacyAutopilotClientAdapter.drive, src.koru.ide_client.LegacyAutopilotClientAdapter.status, src.koru.ide_client.LegacyAutopilotClientAdapter.shutdown

### src.koru.autopilot.audit.AuditLog
> Append-only audit log for autopilot events.

Construct once at daemon start; call :meth:`record` for
- **Methods**: 3
- **Key Methods**: src.koru.autopilot.audit.AuditLog.__init__, src.koru.autopilot.audit.AuditLog.record, src.koru.autopilot.audit.AuditLog.close

### src.koru.local_service._EventBuffer
> Thread-safe ring of recent event records (oldest dropped at maxlen).
- **Methods**: 3
- **Key Methods**: src.koru.local_service._EventBuffer.__init__, src.koru.local_service._EventBuffer.append, src.koru.local_service._EventBuffer.snapshot

### src.koruapi.server.KoruAPIHandler
- **Methods**: 3
- **Key Methods**: src.koruapi.server.KoruAPIHandler.log_message, src.koruapi.server.KoruAPIHandler.do_GET, src.koruapi.server.KoruAPIHandler.do_POST
- **Inherits**: BaseHTTPRequestHandler

### src.koruide.protocol.Message
- **Methods**: 2
- **Key Methods**: src.koruide.protocol.Message.to_dict, src.koruide.protocol.Message.encode

### src.koru.autonomy.environment.EnvironmentReport
> Snapshot of the autonomy-relevant environment.

Designed to be cheap (<200 ms) so it can be called o
- **Methods**: 2
- **Key Methods**: src.koru.autonomy.environment.EnvironmentReport.installed_ides, src.koru.autonomy.environment.EnvironmentReport.mcp_enabled_ides

### src.koru.queue.types.QueueLoopResult
> Aggregate result of draining the planfile queue with run_planfile_queue_loop.
- **Methods**: 2
- **Key Methods**: src.koru.queue.types.QueueLoopResult.ticket_id, src.koru.queue.types.QueueLoopResult.summary

### src.koruide.config.AutopilotConfig
> In-memory view of ``autopilot.toml`` (or defaults).
- **Methods**: 1
- **Key Methods**: src.koruide.config.AutopilotConfig.submit_key_for

### src.koruide.injector.BackendStatus
> Result of probing a single backend.
- **Methods**: 1
- **Key Methods**: src.koruide.injector.BackendStatus.to_dict

### src.koruide.injector.InjectionResult
- **Methods**: 1
- **Key Methods**: src.koruide.injector.InjectionResult.to_dict

### src.koru.autopilot.audit._JSONFormatter
> Emit ``record.msg`` verbatim — we hand it in pre-serialised.
- **Methods**: 1
- **Key Methods**: src.koru.autopilot.audit._JSONFormatter.format
- **Inherits**: logging.Formatter

### src.koru.gate.GateAuthorization
> Parsed gate-authorization record extracted from a ticket note.
- **Methods**: 1
- **Key Methods**: src.koru.gate.GateAuthorization.to_note

### src.koru.bootstrap.ValidationError
- **Methods**: 1
- **Key Methods**: src.koru.bootstrap.ValidationError.__str__

## Data Transformation Functions

Key functions that process and transform data:

### services.healing-webhook.app._run_vallm_validate
> Full pipeline including LLM-as-judge (tier 2). Slower; uses LLM API key.
- **Output to**: cmd.extend, subprocess.run, None.set, None.inc, _json.loads

### services.healing-webhook.app.heal_vallm_validate
> Run vallm tier-1 (check) on all files mapped from the alert component.

Cheap pre-flight gate: block
- **Output to**: services.healing-webhook.app._resolve_affected_files, services.healing-webhook.app._record_action, isinstance, detail.get, services.healing-webhook.app._record_action

### services.healing-webhook.app._parse_redup_summary
> Parse redup-check.sh JSON payload into summary dict.
- **Output to**: payload.get, int, int, sorted, s.get

### services.healing-webhook.ticket_builder._format_paths
- **Output to**: None.join

### services.healing-webhook.ticket_builder._format_acceptance
- **Output to**: None.join

### src.koruide.protocol.Message.encode
- **Output to**: None.encode, json.dumps, self.to_dict

### src.koruide.protocol.decode
- **Output to**: isinstance, text.strip, obj.get, obj.get, src.koruide.protocol._filter_extras

### src.koru.autopilot.audit._JSONFormatter.format
- **Output to**: record.getMessage

### src.koru.autopilot.audit._isoformat_utc
- **Output to**: int, int, time.gmtime, time.time, time.strftime

### src.koru.agent_backends._parse_lane
- **Output to**: raw.get, raw.get, raw.get, raw.get, raw.get

### src.koru.agent_backends.validate_agent_integration_config
> Return human-readable validation errors (empty list when OK).
- **Output to**: config.lanes.items, errors.append, src.koru.agent_backends.get_agent_backend_profile, errors.append

### src.koru.watch.format_queue_event
> Return a compact human-readable line for a planfile WebSocket event.
- **Output to**: str, str, str, ticket.get, execution.get

### src.koru.gate.parse_authorizations
> Extract all gate authorizations recorded on a ticket.

Returns them in insertion order so callers ca
- **Output to**: str, out.append, isinstance, note.startswith, json.loads

### src.koru.bootstrap._validate_id
> Validate task id field.
- **Output to**: str, errors.append, errors.append, task.get, ValidationError

### src.koru.bootstrap._validate_name
> Validate task name/title field.
- **Output to**: str, task.get, task.get, task.get, ValidationError

### src.koru.bootstrap._validate_status
> Validate task status field.
- **Output to**: str, task.get, task.get, ValidationError, sorted

### src.koru.bootstrap._validate_priority
> Validate task priority field.
- **Output to**: str, task.get, isinstance, task.get, ValidationError

### src.koru.bootstrap._validate_executor
> Validate task executor field.
- **Output to**: str, task.get, executor.get, executor.get, isinstance

### src.koru.bootstrap._validate_execution_state
> Validate task execution.state field.
- **Output to**: str, execution.get, task.get, task.get, ValidationError

### src.koru.bootstrap._validate_blocked_by
> Validate task blocked_by field.
- **Output to**: str, task.get, isinstance, task.get, ValidationError

### src.koru.bootstrap._validate_task
> Validate a single task. Returns a list of errors.
- **Output to**: errors.extend, any, errors.extend, errors.extend, errors.extend

### src.koru.bootstrap._validate_cross_task_dependencies
> Validate cross-task dependencies (blocked_by references and cycles).
- **Output to**: src.koru.bootstrap._detect_cycle, str, str, errors.append, t.get

### src.koru.bootstrap.validate_flat_pipeline
> Validate a flat pipeline. Returns a list of errors (empty == valid).
- **Output to**: set, errors.extend, src.koru.bootstrap._validate_task, errors.extend, task.get

### src.koru.queue_clean._parse_age_days
> Best-effort parse of a ticket's age in days from ``created_at``.
- **Output to**: max, ticket.get, ticket.get, datetime.fromisoformat, created.replace

### src.koru.gc._parse_ts
> Best-effort ISO-8601 timestamp parse.
- **Output to**: datetime.fromisoformat, raw.replace

## Behavioral Patterns

### state_machine_AutopilotBridge
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.socketPath, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.koru.autonomous_cycle.run_cycle` - 168 calls
- `src.koruapi.invoke.invoke_integration` - 70 calls
- `src.koru.autonomous_parser.build_parser` - 65 calls
- `src.koru.agents.detect_agent_options` - 61 calls
- `src.koru.queue.runner.run_next_planfile_task` - 57 calls
- `src.koru.autonomy.env.apply_autoloop_env_to_args` - 53 calls
- `src.koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `src.koru.context.render_markdown_handoff` - 47 calls
- `src.koru.tasks.create_nl_task` - 47 calls
- `src.koru.queue.runners.run_llm_request` - 46 calls
- `src.koru.policy.load_policy` - 43 calls
- `src.koru.watch.format_queue_event` - 35 calls
- `src.koruapi.mcp_server.tool_run_ticket` - 33 calls
- `src.koruapi.server.KoruAPIHandler.do_POST` - 33 calls
- `src.koruide.plugin_installer.install_plugin_for_ide` - 32 calls
- `src.koru.autonomy.post_run_verify.load_post_run_verify_config` - 31 calls
- `scripts.planfile-sync-todo.do_from_todo` - 31 calls
- `src.koru.autonomous_diagnostics.run_idle_diagnostics` - 30 calls
- `src.koru.queue.runners.run_api_request` - 30 calls
- `src.koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `src.korudsl.library.library_to_dsl` - 26 calls
- `services.healing-webhook.ticket_builder.build_ticket_payload` - 25 calls
- `src.koru.tools.detect_tools` - 25 calls
- `src.koru.scan.scan_pytest_collect` - 24 calls
- `src.koru.autonomy.ide_work.build_ide_work_prompt` - 23 calls
- `src.koru.autonomy.operator_pipeline.run_startup_operator_pipeline` - 23 calls
- `src.koru.gate.parse_authorizations` - 22 calls
- `src.koru.init.init_project` - 22 calls
- `src.koru.agents.detect_project_environment` - 22 calls
- `src.koruide.ide.detect_terminal_host_ide_id` - 22 calls
- `services.healing-webhook.app.heal_vallm_validate` - 21 calls
- `services.healing-webhook.app.probe_failure` - 21 calls
- `src.koruide.protocol.decode` - 21 calls
- `src.koru.tools.build_tool_task_scaffold` - 21 calls
- `src.koru.doctor.render_text` - 21 calls
- `src.koru.gc.collect_gc_candidates` - 21 calls
- `src.koru.autonomous_startup.build_startup_probe` - 21 calls
- `src.koru.tools.render_tools_detect_text` - 20 calls
- `scripts.planfile-sync-todo.do_from_planfile` - 20 calls
- `src.koruapi.cli.main` - 20 calls

## System Interactions

How components interact:

```mermaid
graph TD
    run_cycle --> _drain_autopilot_eve
    run_cycle --> _emit
    run_cycle --> resolve_in_progress_
    run_cycle --> load_post_run_verify
    run_cycle --> verify_after_ide_wor
    build_parser --> ArgumentParser
    build_parser --> add_argument
    build_parser --> add_subparsers
    build_parser --> add_parser
    from_env --> getenv
    from_env --> cls
    from_env --> strip
    from_env --> max
    from_env --> Path
    run_llm_request --> str
    run_llm_request --> get
    run_llm_request --> append
    _drive_via_keyboard --> resolve_drive_target
    _drive_via_keyboard --> pick_target
    _drive_via_keyboard --> _send
    _drive_via_keyboard --> log
    _drive_via_keyboard --> record
    _handle_plugin_event --> log
    _handle_plugin_event --> _append_event
    _handle_plugin_event --> record
    _handle_plugin_event --> encode
    _handle_plugin_event --> _send
    _topology_main --> parse_args
    _topology_main --> resolve
    _topology_main --> load_topology
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.