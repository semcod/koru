# System Architecture Analysis
<!-- generated in 0.00s -->

## Overview

- **Project**: /home/tom/github/semcod/koru
- **Primary Language**: python
- **Languages**: python: 159, shell: 44, yaml: 15, yml: 8, typescript: 6
- **Analysis Mode**: static
- **Total Functions**: 1611
- **Total Classes**: 106
- **Modules**: 248
- **Entry Points**: 566

## Architecture by Module

### plugins.koru-autopilot-vscode.src.extension
- **Functions**: 172
- **Classes**: 2
- **File**: `extension.ts`

### src.koru.autonomous
- **Functions**: 57
- **Classes**: 1
- **File**: `autonomous.py`

### src.koru.autonomous_cycle
- **Functions**: 52
- **Classes**: 2
- **File**: `autonomous_cycle.py`

### src.koru.context
- **Functions**: 49
- **File**: `context.py`

### src.koruide.daemon
- **Functions**: 43
- **Classes**: 2
- **File**: `daemon.py`

### src.koruide.ide
- **Functions**: 41
- **Classes**: 1
- **File**: `ide.py`

### src.koruapi.mcp_server
- **Functions**: 34
- **File**: `mcp_server.py`

### src.koru.autonomy.operator_pipeline
- **Functions**: 30
- **Classes**: 2
- **File**: `operator_pipeline.py`

### src.koru.autopilot.install_manager
- **Functions**: 30
- **Classes**: 2
- **File**: `install_manager.py`

### src.koru.autonomous_startup
- **Functions**: 29
- **Classes**: 1
- **File**: `autonomous_startup.py`

### src.koruide.os_injector
- **Functions**: 28
- **Classes**: 2
- **File**: `os_injector.py`

### services.healing-webhook.app
- **Functions**: 27
- **File**: `app.py`

### src.koru.autonomous_wup
- **Functions**: 27
- **Classes**: 3
- **File**: `autonomous_wup.py`

### src.koru.scan
- **Functions**: 26
- **Classes**: 2
- **File**: `scan.py`

### src.koruide.plugin_installer
- **Functions**: 24
- **Classes**: 1
- **File**: `plugin_installer.py`

### src.koru.mcp_provision
- **Functions**: 24
- **File**: `mcp_provision.py`

### plugins.koru-autopilot-vscode.src.probe-ladder
- **Functions**: 24
- **Classes**: 3
- **File**: `probe-ladder.ts`

### src.koruide.injector
- **Functions**: 23
- **Classes**: 4
- **File**: `injector.py`

### src.koru.doctor
- **Functions**: 23
- **Classes**: 2
- **File**: `doctor.py`

### src.koru.autopilot.cli_command
- **Functions**: 22
- **File**: `cli_command.py`

## Key Entry Points

Main execution flows into the system:

### src.koru.autonomous_parser.build_parser
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_subparsers, sub.add_parser, doctor.add_argument, sub.add_parser, heal.add_argument, heal.add_argument

### src.koru.autonomy.config.AutonomyConfig.from_env
> Create config from environment variables (shell compatibility).
- **Calls**: os.getenv, cls, None.strip, max, Path, os.getenv, os.getenv, src.koru.autonomy.env.env_truthy

### src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
> Fallback: OS injector profile (X11) or :class:`Injector` keyboard sim.
- **Calls**: self.log, src.koruide.ide.resolve_drive_target, self.log, src.koruide.ide.pick_target, self.injector.select_backend, self.log, self._send, self.log

### src.koru.context_render.render_markdown_handoff
> Turn a context dict into a Markdown brief for the operator.

Designed to be pasted into a Cascade/Cursor/aider chat to onboard
the LLM with the policy
- **Calls**: context.get, context.get, context.get, lines.extend, bool, lines.extend, lines.extend, lines.extend

### src.koru.local_manager_state.WorkerRegistry.register
- **Calls**: src.koru.local_manager_state.utc_now, str, str, self._workers.get, self._reconcile_locked, self._reply_locked, payload.get, src.koru.local_manager_state.koru_version

### src.koru.autonomous_cycle.run_cycle
- **Calls**: src.koru.autonomous_cycle._initialize_cycle_telemetry, src.koru.autonomous_cycle._heal_stale_socket, src.koru.autonomous_cycle._handle_autopilot_events, src.koru.run_log.RunLogWriter._emit, src.koru.autonomous_cycle._handle_queue_hygiene, src.koru.autonomous_cycle._handle_post_run_verify_ide, src.koru.autonomous_cycle._handle_scan_phase, src.koru.autonomous_cycle._handle_queue_loop_phase

### src.koru.cli._topology_main
- **Calls**: None.parse_args, args.project.resolve, src.koru.topology.load_topology, src.koru.topology_cli.apply_topology_mutations, src.koru.topology.load_topology, None.get, None.get, isinstance

### src.koru.cli_topology.topology_main
- **Calls**: None.parse_args, args.project.resolve, src.koru.topology.load_topology, src.koru.topology_cli.apply_topology_mutations, src.koru.topology.load_topology, None.get, None.get, isinstance

### src.koru.queue.runners.run_api_request
> Execute an HTTP API request.
- **Calls**: request.get, urllib.request.Request, float, str, str, None.encode, headers.setdefault, str

### src.koruide.daemon.AutopilotDaemon._drive_via_plugin
> Forward a drive request to a connected plugin for that IDE.
- **Calls**: self.log, DriveOrchestrator.plugin_version_info, self.log, version_info.get, DriveOrchestrator.should_block_plugin_version, self._send, time.monotonic, self.log

### src.koru.autonomy.env.autonomous_environ_doctor_probe
> Return ``(status, detail)`` for ``koru --doctor``; process-global, no I/O.
- **Calls**: os.environ.get, src.koru.autonomy.env.env_truthy, os.environ.get, os.environ.get, src.koru.autonomy.env.env_truthy, None.strip, None.lower, None.strip

### src.koruide.daemon.AutopilotDaemon._handle_drive
- **Calls**: msg.data.get, bool, bool, self.log, self._plugin_for, self.log, self._drive_via_keyboard, self._send

### src.koru.autopilot.cli_command._action_drive
- **Calls**: src.koru.autopilot.cli_command._client, src.koru.autopilot.cli_command._should_fallback_to_direct, scripts.koru-soak-monitor.print, None.strip, None.strip, scripts.koru-soak-monitor.print, src.koru.autopilot.cli_command._run_direct_drive, client.is_running

### src.koru.cli._task_main
- **Calls**: None.parse_args, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, src.koru.events.emit_management_event, src.koru.tools.load_tool_registry, src.koru.tools.find_tool_entry

### src.koru.cli._agent_backends_main
> List or describe IDE agent backend profiles (``agent_backends``).
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.parse_args, src.koru.agent_backends.iter_agent_backend_profiles, src.koru.agent_backends.get_agent_backend_profile, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print

### src.koru.gate.parse_authorizations
> Extract all gate authorizations recorded on a ticket.

Returns them in insertion order so callers can pick the most
recent one with ``parse_authorizat
- **Calls**: str, out.append, isinstance, note.startswith, json.loads, payload.get, payload.get, isinstance

### services.healing-webhook.app.heal_vallm_validate
> Run vallm tier-1 (check) on all files mapped from the alert component.

Cheap pre-flight gate: blocks AI patches if affected files are already
syntact
- **Calls**: services.healing-webhook.app._resolve_affected_files, services.healing-webhook.app._record_action, isinstance, detail.get, services.healing-webhook.app._record_action, services.healing-webhook.app._run_vallm_check, sum, max

### services.healing-webhook.app.probe_failure
> Accept the testql-watchdog probe-failure payload.
- **Calls**: app.post, None.inc, payload.get, log.info, services.healing-webhook.app.create_planfile_ticket, request.json, payload.get, len

### src.koru.doctor.render_text
> Human-readable rendering — fixed-width status column.
- **Calls**: lines.append, lines.append, max, report.summary, sum, counts.get, counts.get, counts.get

### src.koru.autopilot.install_plugin_cli.action_install_plugin_jetbrains
- **Calls**: proc.stdout.strip, proc.stderr.strip, src.koru.autopilot.install_plugin_cli._render_jetbrains_success, resolve_plugin_dir, resolve_gradle, subprocess.run, src.koru.autopilot.install_plugin_cli._render_jetbrains_failure, resolve_artifact

### src.koruapi.cli.main
- **Calls**: src.koruapi.cli._build_parser, parser.parse_known_args, args.project.resolve, sys.stdout.write, src.koru.activity_log.activity, src.koru.activity_log.activity, sys.stdout.write, api_serve

### src.koru.local_manager_state.ActionQueue.claim
- **Calls**: src.koru.local_manager_state.utc_now, max, None.replace, set, set, min, src.koru.local_manager_state.normalize_capabilities, int

### src.koru.local_manager_state.WorkerRegistry.heartbeat
- **Calls**: str, self.register, self._workers.get, dict, self.register, isinstance, src.koru.local_manager_state.utc_now, self._reconcile_locked

### src.koruide.daemon.AutopilotDaemon._on_readable
- **Calls**: client.buf.extend, client.sock.recv, self.log, self._drop, len, self._send, self._drop, client.buf.partition

### services.healing-webhook.app.alertmanager_webhook
> Accept the Alertmanager webhook payload (v4).
- **Calls**: app.post, payload.get, request.json, alert.get, labels.get, labels.get, labels.get, alert.get

### src.koruapi.dashboard_serve.serve
> Start the dashboard server and block until Ctrl-C.

Returns the process exit code (0 on clean shutdown).
- **Calls**: src.koruapi.dashboard_serve.write_serve_endpoint_file, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, scripts.koru-soak-monitor.print, src.koru.events.emit_management_event, src.koruapi.dashboard_serve.bind_serve_server, scripts.koru-soak-monitor.print, None.start

### src.koru.autopilot.daemon_cli.action_daemon
- **Calls**: src.koru.autopilot.daemon_cli._daemon_already_running, src.koru.autopilot.daemon_cli._start_local_manager, AuditLog, AutopilotDaemon, src.koru.autopilot.local_manager.start_autopilot_manager_heartbeat, default_socket_fn, args.project.resolve, scripts.koru-soak-monitor.print

### src.korudsl.cli.main
- **Calls**: None.parse_args, src.korudsl.cli._read_input, src.korudsl.transform.library_from_any, src.korudsl.cli._read_input, src.korudsl.transform.library_from_any, src.korudsl.transform.library_to_any, src.korudsl.cli._read_input, src.korudsl.transform.dsl_roundtrip_report

### src.koru.agent_backends.load_agent_integration_config
> Load ``ide_integration`` from ``<project>/koru.yaml`` if present.
- **Calls**: data.get, block.get, block.get, raw_lanes.items, AgentIntegrationConfig, path.is_file, isinstance, isinstance

### src.koru.dev_sync.dev_main
- **Calls**: argparse.ArgumentParser, parser.add_subparsers, sub.add_parser, sync.add_argument, sync.add_argument, sync.add_argument, sync.add_argument, parser.parse_args

## Process Flows

Key execution flows identified:

### Flow 1: build_parser
```
build_parser [src.koru.autonomous_parser]
```

### Flow 2: from_env
```
from_env [src.koru.autonomy.config.AutonomyConfig]
```

### Flow 3: _drive_via_keyboard
```
_drive_via_keyboard [src.koruide.daemon.AutopilotDaemon]
  └─ →> resolve_drive_target
      └─> normalize_ide_id
      └─> detect_running_ides
          └─> _iter_proc_pids
  └─ →> pick_target
      └─> normalize_ide_id
      └─> normalize_ide_id
```

### Flow 4: render_markdown_handoff
```
render_markdown_handoff [src.koru.context_render]
```

### Flow 5: register
```
register [src.koru.local_manager_state.WorkerRegistry]
  └─ →> utc_now
```

### Flow 6: run_cycle
```
run_cycle [src.koru.autonomous_cycle]
  └─> _initialize_cycle_telemetry
  └─> _heal_stale_socket
      └─ →> probe_socket_health
      └─ →> default_socket_path
          └─> _autopilot_socket_basename
  └─ →> _emit
      └─ →> print
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
  └─ →> apply_topology_mutations
      └─ →> print
      └─ →> print
```

### Flow 8: topology_main
```
topology_main [src.koru.cli_topology]
  └─ →> load_topology
      └─> topology_path
      └─> _read_yaml
      └─ →> detect_semcod_tools
  └─ →> load_topology
      └─> topology_path
      └─> _read_yaml
      └─ →> detect_semcod_tools
  └─ →> apply_topology_mutations
      └─ →> print
      └─ →> print
```

### Flow 9: run_api_request
```
run_api_request [src.koru.queue.runners]
```

### Flow 10: _drive_via_plugin
```
_drive_via_plugin [src.koruide.daemon.AutopilotDaemon]
```

## Key Classes

### plugins.koru-autopilot-vscode.src.extension.AutopilotBridge
- **Methods**: 170
- **Key Methods**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.socketPath, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.tryConnectNext, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.p, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.debugLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.sock

### src.koruide.daemon.AutopilotDaemon
> Selector-based unix-socket broker.

Parameters
----------
socket_path:
    Where to bind. Defaults t
- **Methods**: 36
- **Key Methods**: src.koruide.daemon.AutopilotDaemon.__init__, src.koruide.daemon.AutopilotDaemon.start, src.koruide.daemon.AutopilotDaemon.serve_forever, src.koruide.daemon.AutopilotDaemon.stop, src.koruide.daemon.AutopilotDaemon._shutdown, src.koruide.daemon.AutopilotDaemon._accept, src.koruide.daemon.AutopilotDaemon._on_readable, src.koruide.daemon.AutopilotDaemon._dispatch, src.koruide.daemon.AutopilotDaemon._send, src.koruide.daemon.AutopilotDaemon._drop

### src.koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 12
- **Key Methods**: src.koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, src.koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, src.koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, src.koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, src.koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info, src.koruide.drive_orchestrator.DriveOrchestrator.should_block_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_block_message

### src.koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 12
- **Key Methods**: src.koruide.injector.Injector.probe, src.koruide.injector.Injector._candidate_backends, src.koruide.injector.Injector.select_backend, src.koruide.injector.Injector._type_with_xdotool, src.koruide.injector.Injector._type_with_wtype, src.koruide.injector.Injector._type_with_ydotool, src.koruide.injector.Injector._type_with_backend, src.koruide.injector.Injector.type_text, src.koruide.injector.Injector.submit_only, src.koruide.injector.Injector._probe_one

### src.koruide.client.KoruIDEClient
> Connect, send one message, read one reply, disconnect.
- **Methods**: 7
- **Key Methods**: src.koruide.client.KoruIDEClient.__init__, src.koruide.client.KoruIDEClient._connect, src.koruide.client.KoruIDEClient.request, src.koruide.client.KoruIDEClient.is_running, src.koruide.client.KoruIDEClient.drive, src.koruide.client.KoruIDEClient.status, src.koruide.client.KoruIDEClient.shutdown

### src.koru.local_manager_client.LocalManagerClient
> Tiny JSON-over-HTTP client for ``koru local-serve``.
- **Methods**: 7
- **Key Methods**: src.koru.local_manager_client.LocalManagerClient.from_env, src.koru.local_manager_client.LocalManagerClient.enabled, src.koru.local_manager_client.LocalManagerClient.post, src.koru.local_manager_client.LocalManagerClient.register_worker, src.koru.local_manager_client.LocalManagerClient.heartbeat_worker, src.koru.local_manager_client.LocalManagerClient.claim_action, src.koru.local_manager_client.LocalManagerClient.complete_action

### src.koru.local_manager_state.WorkerRegistry
> Registry and lifecycle policy for versioned koru workers.
- **Methods**: 6
- **Key Methods**: src.koru.local_manager_state.WorkerRegistry.__init__, src.koru.local_manager_state.WorkerRegistry.register, src.koru.local_manager_state.WorkerRegistry.heartbeat, src.koru.local_manager_state.WorkerRegistry._reconcile_locked, src.koru.local_manager_state.WorkerRegistry._reply_locked, src.koru.local_manager_state.WorkerRegistry.snapshot

### src.koru.local_manager_client.LocalManagerSession
> Small lifecycle session for one CLI worker invocation.
- **Methods**: 5
- **Key Methods**: src.koru.local_manager_client.LocalManagerSession.enabled, src.koru.local_manager_client.LocalManagerSession.start, src.koru.local_manager_client.LocalManagerSession.heartbeat, src.koru.local_manager_client.LocalManagerSession.should_stop, src.koru.local_manager_client.LocalManagerSession.complete

### src.koru.local_manager_state.ActionQueue
> Single in-process queue for local koru actions with simple leases.
- **Methods**: 5
- **Key Methods**: src.koru.local_manager_state.ActionQueue.__init__, src.koru.local_manager_state.ActionQueue.enqueue, src.koru.local_manager_state.ActionQueue.claim, src.koru.local_manager_state.ActionQueue.complete, src.koru.local_manager_state.ActionQueue.snapshot

### src.koruide.plugin_router.PluginRouter
> Select, enumerate and deduplicate connected plugin sessions.
- **Methods**: 4
- **Key Methods**: src.koruide.plugin_router.PluginRouter.__init__, src.koruide.plugin_router.PluginRouter.plugin_for, src.koruide.plugin_router.PluginRouter.drop_stale_plugins, src.koruide.plugin_router.PluginRouter.status_rows

### src.koru.ide_client.IDEControlClient
> Minimal interface `koru` runtime code expects from an IDE client.
- **Methods**: 4
- **Key Methods**: src.koru.ide_client.IDEControlClient.is_running, src.koru.ide_client.IDEControlClient.drive, src.koru.ide_client.IDEControlClient.status, src.koru.ide_client.IDEControlClient.shutdown
- **Inherits**: Protocol

### src.koru.ide_client.LegacyAutopilotClientAdapter
> Expose legacy :class:`AutopilotClient` through :class:`IDEControlClient`.
- **Methods**: 4
- **Key Methods**: src.koru.ide_client.LegacyAutopilotClientAdapter.is_running, src.koru.ide_client.LegacyAutopilotClientAdapter.drive, src.koru.ide_client.LegacyAutopilotClientAdapter.status, src.koru.ide_client.LegacyAutopilotClientAdapter.shutdown

### src.koru.init.InitReport
> Summary of what ``init_project`` actually changed on disk.
- **Methods**: 4
- **Key Methods**: src.koru.init.InitReport._env_bit, src.koru.init.InitReport._lane_summary, src.koru.init.InitReport._init_summary, src.koru.init.InitReport.summary

### src.koru.doctor.DoctorReport
> Aggregate result of ``run_diagnostics``.
- **Methods**: 4
- **Key Methods**: src.koru.doctor.DoctorReport.has_failures, src.koru.doctor.DoctorReport.has_warnings, src.koru.doctor.DoctorReport.summary, src.koru.doctor.DoctorReport.to_dict

### src.koru.run_log.RunLogWriter
> Append-only JSONL writer with best-effort durability.

The constructor does not open the file — that
- **Methods**: 4
- **Key Methods**: src.koru.run_log.RunLogWriter._emit, src.koru.run_log.RunLogWriter.write_header, src.koru.run_log.RunLogWriter.write_iteration, src.koru.run_log.RunLogWriter.write_footer

### src.koruapi.server.KoruAPIHandler
- **Methods**: 3
- **Key Methods**: src.koruapi.server.KoruAPIHandler.log_message, src.koruapi.server.KoruAPIHandler.do_GET, src.koruapi.server.KoruAPIHandler.do_POST
- **Inherits**: BaseHTTPRequestHandler

### src.koruide.audit.AuditLog
> Append-only audit log for autopilot events.

Construct once at daemon start; call :meth:`record` for
- **Methods**: 3
- **Key Methods**: src.koruide.audit.AuditLog.__init__, src.koruide.audit.AuditLog.record, src.koruide.audit.AuditLog.close

### src.koru.local_manager_state.EventBuffer
> Thread-safe ring of recent event records (oldest dropped at maxlen).
- **Methods**: 3
- **Key Methods**: src.koru.local_manager_state.EventBuffer.__init__, src.koru.local_manager_state.EventBuffer.append, src.koru.local_manager_state.EventBuffer.snapshot

### src.koruide.protocol.Message
- **Methods**: 2
- **Key Methods**: src.koruide.protocol.Message.to_dict, src.koruide.protocol.Message.encode

### src.koru.autonomy.environment.EnvironmentReport
> Snapshot of the autonomy-relevant environment.

Designed to be cheap (<200 ms) so it can be called o
- **Methods**: 2
- **Key Methods**: src.koru.autonomy.environment.EnvironmentReport.installed_ides, src.koru.autonomy.environment.EnvironmentReport.mcp_enabled_ides

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

### src.korudsl.cli._build_parser
- **Output to**: argparse.ArgumentParser, parser.add_subparsers, sub.add_parser, to_lib.add_argument, to_lib.add_argument

### src.korudsl.library.convert_goals_json_to_library
> Convert legacy goals JSON to OQL library.
- **Output to**: src.korudsl.library.ensure_library_structure, isinstance, isinstance, isinstance, json.loads

### src.koruapi.runtime_insights._classify_process
- **Output to**: None.lower, None.lower, src.koruapi.runtime_insights._looks_project_related, any, str

### src.koruapi.runtime_insights._top_processes
- **Output to**: sorted, out.append, src.koruapi.runtime_insights._classify_process, src.koruapi.runtime_insights._looks_project_related, int

### src.koruapi.dashboard.build_serve_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### src.koruapi.cli._build_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_subparsers, sub.add_parser, sub.add_parser

### src.koruapi.cli._parse_body
- **Output to**: raw.startswith, json.loads, json.loads, None.read_text, Path

### src.koruapi.local.build_local_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument

### src.koruapi.server._parse_invoke_request
- **Output to**: str, str, None.resolve, body.get, str

### src.koruapi.mcp_server._get_process_memory_mb
> Get process memory usage in MB.
- **Output to**: psutil.Process, process.memory_info

### src.koruapi.mcp_server._monitor_subprocess_oom
> Monitor subprocess for OOM conditions.

Returns (should_kill, logs) tuple.
- **Output to**: proc.poll, src.koruapi.mcp_server._get_process_memory_mb, time.sleep, logs.append, logs.append

### src.koruapi.mcp_server._parse_tickets_json
> Parse planfile ticket list JSON output.
- **Output to**: stdout.strip, isinstance, isinstance, json.loads, isinstance

### src.koruapi.mcp_server._serialize_mcp_ticket
- **Output to**: ticket.get, ticket.get, ticket.get, ticket.get, ticket.get

### src.koruapi.mcp_server._collect_process_logs
- **Output to**: logs.extend, logs.extend, None.split, None.split, result.stdout.strip

### src.koruide.protocol.Message.encode
- **Output to**: None.encode, json.dumps, self.to_dict

### src.koruide.protocol.decode
- **Output to**: isinstance, text.strip, obj.get, obj.get, src.koruide.protocol._filter_extras

### src.koruide.audit._JSONFormatter.format
- **Output to**: record.getMessage

### src.koruide.audit._isoformat_utc
- **Output to**: int, int, time.gmtime, time.time, time.strftime

### src.koruide.plugin_installer._parse_extension_version
- **Output to**: output.splitlines, line.strip, None.startswith, EXTENSION_ID.lower, item.lower

### src.koruide.plugin_installer.format_plugin_install_result
> Human-friendly single-line status for autonomous startup.
- **Output to**: None.join

## Behavioral Patterns

### state_machine_EventBuffer
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: src.koru.local_manager_state.EventBuffer.__init__, src.koru.local_manager_state.EventBuffer.append, src.koru.local_manager_state.EventBuffer.snapshot

### state_machine_ActionQueue
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: src.koru.local_manager_state.ActionQueue.__init__, src.koru.local_manager_state.ActionQueue.enqueue, src.koru.local_manager_state.ActionQueue.claim, src.koru.local_manager_state.ActionQueue.complete, src.koru.local_manager_state.ActionQueue.snapshot

### state_machine_WorkerRegistry
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: src.koru.local_manager_state.WorkerRegistry.__init__, src.koru.local_manager_state.WorkerRegistry.register, src.koru.local_manager_state.WorkerRegistry.heartbeat, src.koru.local_manager_state.WorkerRegistry._reconcile_locked, src.koru.local_manager_state.WorkerRegistry._reply_locked

### state_machine_AutopilotBridge
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.socketPath, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.koru.autonomous_parser.build_parser` - 65 calls
- `src.koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `src.koru.context.render_markdown_handoff` - 47 calls
- `src.koru.context_render.render_markdown_handoff` - 47 calls
- `src.koru.policy.load_policy` - 43 calls
- `src.koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `src.koruapi.mcp_server.tool_run_ticket` - 33 calls
- `src.koru.autonomous_cycle.run_cycle` - 33 calls
- `src.koru.cli_topology.topology_main` - 32 calls
- `src.koru.queue.runners.run_api_request` - 30 calls
- `src.koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `src.koru.cli_queue.render_clean_report_text` - 28 calls
- `src.koru.tasks.create_nl_task` - 28 calls
- `src.koru.autonomous_plugin.plugin_status_decision` - 26 calls
- `src.koru.autonomous_daemon.start_or_reuse_daemon` - 26 calls
- `services.healing-webhook.ticket_builder.build_ticket_payload` - 25 calls
- `src.koru.scan.scan_pytest_collect` - 24 calls
- `src.koru.autopilot.install_manager.collect_install_manager_report` - 24 calls
- `src.koru.init.init_project` - 23 calls
- `src.koru.autonomy.ide_work.build_ide_work_prompt` - 23 calls
- `src.koruapi.topology_post.apply_topology_post_update` - 22 calls
- `src.koruide.plugin_installer.resolve_extension_vsix` - 22 calls
- `src.koru.gate.parse_authorizations` - 22 calls
- `src.koru.agents.detect_project_environment` - 22 calls
- `src.koru.queue.runner.run_next_planfile_task` - 22 calls
- `services.healing-webhook.app.heal_vallm_validate` - 21 calls
- `services.healing-webhook.app.probe_failure` - 21 calls
- `src.koruide.protocol.decode` - 21 calls
- `src.koru.doctor.render_text` - 21 calls
- `src.koru.gc.collect_gc_candidates` - 21 calls
- `src.koru.queue_cli_helpers.run_queue_loop_mode` - 21 calls
- `src.koru.context_render.render_active_ticket` - 21 calls
- `src.koru.agents.detect_agent_options` - 21 calls
- `src.koru.autopilot.install_plugin_cli.action_install_plugin_jetbrains` - 21 calls
- `src.koruapi.cli.main` - 20 calls
- `src.koru.autonomous_diagnostics.build_idle_checks` - 20 calls
- `src.koru.tools.render_tools_detect_text` - 20 calls
- `src.koru.context_render.render_autonomy_loop_brief` - 20 calls
- `src.koru.local_manager_state.ActionQueue.claim` - 20 calls
- `src.koru.local_manager_state.WorkerRegistry.heartbeat` - 20 calls

## System Interactions

How components interact:

```mermaid
graph TD
    build_parser --> ArgumentParser
    build_parser --> add_argument
    build_parser --> add_subparsers
    build_parser --> add_parser
    from_env --> getenv
    from_env --> cls
    from_env --> strip
    from_env --> max
    from_env --> Path
    _drive_via_keyboard --> log
    _drive_via_keyboard --> resolve_drive_target
    _drive_via_keyboard --> pick_target
    _drive_via_keyboard --> select_backend
    render_markdown_hand --> get
    render_markdown_hand --> extend
    render_markdown_hand --> bool
    register --> utc_now
    register --> str
    register --> get
    register --> _reconcile_locked
    run_cycle --> _initialize_cycle_te
    run_cycle --> _heal_stale_socket
    run_cycle --> _handle_autopilot_ev
    run_cycle --> _emit
    run_cycle --> _handle_queue_hygien
    _topology_main --> parse_args
    _topology_main --> resolve
    _topology_main --> load_topology
    _topology_main --> apply_topology_mutat
    topology_main --> parse_args
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.