# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/semcod/koru
- **Primary Language**: python
- **Languages**: python: 301, md: 86, shell: 50, yaml: 38, yml: 8
- **Analysis Mode**: static
- **Total Functions**: 7504
- **Total Classes**: 199
- **Modules**: 507
- **Entry Points**: 0

## Architecture by Module

### code2llm_output.map.toon
- **Functions**: 21416
- **File**: `map.toon.yaml`

### scripts_services.SUMD
- **Functions**: 1838
- **File**: `SUMD.md`

### project.map.toon
- **Functions**: 1237
- **File**: `map.toon.yaml`

### plugins.koru-autopilot-vscode.src.extension
- **Functions**: 117
- **Classes**: 2
- **File**: `extension.ts`

### koru.autonomous
- **Functions**: 65
- **Classes**: 4
- **File**: `autonomous.py`

### src.koru.autonomous
- **Functions**: 65
- **Classes**: 4
- **File**: `autonomous.py`

### koru.context
- **Functions**: 49
- **File**: `context.py`

### src.koru.context
- **Functions**: 49
- **File**: `context.py`

### koru.autonomous_cycle
- **Functions**: 39
- **Classes**: 2
- **File**: `autonomous_cycle.py`

### src.koru.autonomous_cycle
- **Functions**: 39
- **Classes**: 2
- **File**: `autonomous_cycle.py`

### koruide.ide
- **Functions**: 36
- **Classes**: 1
- **File**: `ide.py`

### src.koruide.ide
- **Functions**: 36
- **Classes**: 1
- **File**: `ide.py`

### koruide.daemon
- **Functions**: 35
- **Classes**: 2
- **File**: `daemon.py`

### src.koruide.daemon
- **Functions**: 35
- **Classes**: 2
- **File**: `daemon.py`

### koruapi.mcp_server
- **Functions**: 34
- **File**: `mcp_server.py`

### src.koruapi.mcp_server
- **Functions**: 34
- **File**: `mcp_server.py`

### services.healing-webhook.app
- **Functions**: 27
- **File**: `app.py`

### koru.autopilot.install_manager
- **Functions**: 26
- **Classes**: 2
- **File**: `install_manager.py`

### src.koru.autonomy.operator_pipeline
- **Functions**: 26
- **Classes**: 2
- **File**: `operator_pipeline.py`

### src.koru.autopilot.install_manager
- **Functions**: 26
- **Classes**: 2
- **File**: `install_manager.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

### plugins.koru-autopilot-vscode.src.extension.AutopilotBridge
- **Methods**: 115
- **Key Methods**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.socketPath, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.tryConnectNext, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.p, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.debugLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.sock

### koruide.daemon.AutopilotDaemon
> Selector-based unix-socket broker.

Parameters
----------
socket_path:
    Where to bind. Defaults t
- **Methods**: 28
- **Key Methods**: koruide.daemon.AutopilotDaemon.__init__, koruide.daemon.AutopilotDaemon.start, koruide.daemon.AutopilotDaemon.serve_forever, koruide.daemon.AutopilotDaemon.stop, koruide.daemon.AutopilotDaemon._shutdown, koruide.daemon.AutopilotDaemon._accept, koruide.daemon.AutopilotDaemon._on_readable, koruide.daemon.AutopilotDaemon._dispatch, koruide.daemon.AutopilotDaemon._send, koruide.daemon.AutopilotDaemon._drop

### src.koruide.daemon.AutopilotDaemon
> Selector-based unix-socket broker.

Parameters
----------
socket_path:
    Where to bind. Defaults t
- **Methods**: 28
- **Key Methods**: src.koruide.daemon.AutopilotDaemon.__init__, src.koruide.daemon.AutopilotDaemon.start, src.koruide.daemon.AutopilotDaemon.serve_forever, src.koruide.daemon.AutopilotDaemon.stop, src.koruide.daemon.AutopilotDaemon._shutdown, src.koruide.daemon.AutopilotDaemon._accept, src.koruide.daemon.AutopilotDaemon._on_readable, src.koruide.daemon.AutopilotDaemon._dispatch, src.koruide.daemon.AutopilotDaemon._send, src.koruide.daemon.AutopilotDaemon._drop

### koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 12
- **Key Methods**: koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info, koruide.drive_orchestrator.DriveOrchestrator.should_block_plugin_version, koruide.drive_orchestrator.DriveOrchestrator.plugin_version_block_message

### src.koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 12
- **Key Methods**: src.koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, src.koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, src.koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, src.koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, src.koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info, src.koruide.drive_orchestrator.DriveOrchestrator.should_block_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_block_message

### koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 9
- **Key Methods**: koruide.injector.Injector.probe, koruide.injector.Injector._candidate_backends, koruide.injector.Injector.select_backend, koruide.injector.Injector._type_with_backend, koruide.injector.Injector.type_text, koruide.injector.Injector.submit_only, koruide.injector.Injector._probe_one, koruide.injector.Injector._call, koruide.injector.Injector._press_wtype

### src.koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 9
- **Key Methods**: src.koruide.injector.Injector.probe, src.koruide.injector.Injector._candidate_backends, src.koruide.injector.Injector.select_backend, src.koruide.injector.Injector._type_with_backend, src.koruide.injector.Injector.type_text, src.koruide.injector.Injector.submit_only, src.koruide.injector.Injector._probe_one, src.koruide.injector.Injector._call, src.koruide.injector.Injector._press_wtype

### koruide.client.KoruIDEClient
> Connect, send one message, read one reply, disconnect.
- **Methods**: 7
- **Key Methods**: koruide.client.KoruIDEClient.__init__, koruide.client.KoruIDEClient._connect, koruide.client.KoruIDEClient.request, koruide.client.KoruIDEClient.is_running, koruide.client.KoruIDEClient.drive, koruide.client.KoruIDEClient.status, koruide.client.KoruIDEClient.shutdown

### koru.local_manager_client.LocalManagerClient
> Tiny JSON-over-HTTP client for ``koru local-serve``.
- **Methods**: 7
- **Key Methods**: koru.local_manager_client.LocalManagerClient.from_env, koru.local_manager_client.LocalManagerClient.enabled, koru.local_manager_client.LocalManagerClient.post, koru.local_manager_client.LocalManagerClient.register_worker, koru.local_manager_client.LocalManagerClient.heartbeat_worker, koru.local_manager_client.LocalManagerClient.claim_action, koru.local_manager_client.LocalManagerClient.complete_action

### src.koruide.client.KoruIDEClient
> Connect, send one message, read one reply, disconnect.
- **Methods**: 7
- **Key Methods**: src.koruide.client.KoruIDEClient.__init__, src.koruide.client.KoruIDEClient._connect, src.koruide.client.KoruIDEClient.request, src.koruide.client.KoruIDEClient.is_running, src.koruide.client.KoruIDEClient.drive, src.koruide.client.KoruIDEClient.status, src.koruide.client.KoruIDEClient.shutdown

### src.koru.local_manager_client.LocalManagerClient
> Tiny JSON-over-HTTP client for ``koru local-serve``.
- **Methods**: 7
- **Key Methods**: src.koru.local_manager_client.LocalManagerClient.from_env, src.koru.local_manager_client.LocalManagerClient.enabled, src.koru.local_manager_client.LocalManagerClient.post, src.koru.local_manager_client.LocalManagerClient.register_worker, src.koru.local_manager_client.LocalManagerClient.heartbeat_worker, src.koru.local_manager_client.LocalManagerClient.claim_action, src.koru.local_manager_client.LocalManagerClient.complete_action

### koru.local_manager_state.WorkerRegistry
> Registry and lifecycle policy for versioned koru workers.
- **Methods**: 6
- **Key Methods**: koru.local_manager_state.WorkerRegistry.__init__, koru.local_manager_state.WorkerRegistry.register, koru.local_manager_state.WorkerRegistry.heartbeat, koru.local_manager_state.WorkerRegistry._reconcile_locked, koru.local_manager_state.WorkerRegistry._reply_locked, koru.local_manager_state.WorkerRegistry.snapshot

### src.koru.local_manager_state.WorkerRegistry
> Registry and lifecycle policy for versioned koru workers.
- **Methods**: 6
- **Key Methods**: src.koru.local_manager_state.WorkerRegistry.__init__, src.koru.local_manager_state.WorkerRegistry.register, src.koru.local_manager_state.WorkerRegistry.heartbeat, src.koru.local_manager_state.WorkerRegistry._reconcile_locked, src.koru.local_manager_state.WorkerRegistry._reply_locked, src.koru.local_manager_state.WorkerRegistry.snapshot

### koru.local_manager_client.LocalManagerSession
> Small lifecycle session for one CLI worker invocation.
- **Methods**: 5
- **Key Methods**: koru.local_manager_client.LocalManagerSession.enabled, koru.local_manager_client.LocalManagerSession.start, koru.local_manager_client.LocalManagerSession.heartbeat, koru.local_manager_client.LocalManagerSession.should_stop, koru.local_manager_client.LocalManagerSession.complete

### koru.local_manager_state.ActionQueue
> Single in-process queue for local koru actions with simple leases.
- **Methods**: 5
- **Key Methods**: koru.local_manager_state.ActionQueue.__init__, koru.local_manager_state.ActionQueue.enqueue, koru.local_manager_state.ActionQueue.claim, koru.local_manager_state.ActionQueue.complete, koru.local_manager_state.ActionQueue.snapshot

### src.koru.local_manager_client.LocalManagerSession
> Small lifecycle session for one CLI worker invocation.
- **Methods**: 5
- **Key Methods**: src.koru.local_manager_client.LocalManagerSession.enabled, src.koru.local_manager_client.LocalManagerSession.start, src.koru.local_manager_client.LocalManagerSession.heartbeat, src.koru.local_manager_client.LocalManagerSession.should_stop, src.koru.local_manager_client.LocalManagerSession.complete

### src.koru.local_manager_state.ActionQueue
> Single in-process queue for local koru actions with simple leases.
- **Methods**: 5
- **Key Methods**: src.koru.local_manager_state.ActionQueue.__init__, src.koru.local_manager_state.ActionQueue.enqueue, src.koru.local_manager_state.ActionQueue.claim, src.koru.local_manager_state.ActionQueue.complete, src.koru.local_manager_state.ActionQueue.snapshot

### koruide.plugin_router.PluginRouter
> Select, enumerate and deduplicate connected plugin sessions.
- **Methods**: 4
- **Key Methods**: koruide.plugin_router.PluginRouter.__init__, koruide.plugin_router.PluginRouter.plugin_for, koruide.plugin_router.PluginRouter.drop_stale_plugins, koruide.plugin_router.PluginRouter.status_rows

### koru.ide_client.IDEControlClient
> Minimal interface `koru` runtime code expects from an IDE client.
- **Methods**: 4
- **Key Methods**: koru.ide_client.IDEControlClient.is_running, koru.ide_client.IDEControlClient.drive, koru.ide_client.IDEControlClient.status, koru.ide_client.IDEControlClient.shutdown
- **Inherits**: Protocol

### koru.ide_client.LegacyAutopilotClientAdapter
> Expose legacy :class:`AutopilotClient` through :class:`IDEControlClient`.
- **Methods**: 4
- **Key Methods**: koru.ide_client.LegacyAutopilotClientAdapter.is_running, koru.ide_client.LegacyAutopilotClientAdapter.drive, koru.ide_client.LegacyAutopilotClientAdapter.status, koru.ide_client.LegacyAutopilotClientAdapter.shutdown

## Data Transformation Functions

Key functions that process and transform data:

### korudsl.cli._build_parser
- **Output to**: argparse.ArgumentParser, parser.add_subparsers, sub.add_parser, to_lib.add_argument, to_lib.add_argument

### korudsl.library.convert_goals_json_to_library
> Convert legacy goals JSON to OQL library.
- **Output to**: korudsl.library.ensure_library_structure, isinstance, isinstance, isinstance, json.loads

### koruapi.runtime_insights._classify_process
- **Output to**: None.lower, None.lower, koruapi.runtime_insights._looks_project_related, any, str

### koruapi.runtime_insights._top_processes
- **Output to**: sorted, out.append, koruapi.runtime_insights._classify_process, koruapi.runtime_insights._looks_project_related, int

### koruapi.dashboard.build_serve_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### koruapi.cli._build_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_subparsers, sub.add_parser, sub.add_parser

### koruapi.cli._parse_body
- **Output to**: raw.startswith, json.loads, json.loads, None.read_text, Path

### koruapi.local.build_local_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument

### koruapi.server._parse_invoke_request
- **Output to**: str, str, None.resolve, body.get, str

### koruapi.mcp_server._get_process_memory_mb
> Get process memory usage in MB.
- **Output to**: psutil.Process, process.memory_info

### koruapi.mcp_server._monitor_subprocess_oom
> Monitor subprocess for OOM conditions.

Returns (should_kill, logs) tuple.
- **Output to**: proc.poll, koruapi.mcp_server._get_process_memory_mb, time.sleep, logs.append, logs.append

### koruapi.mcp_server._parse_tickets_json
> Parse planfile ticket list JSON output.
- **Output to**: stdout.strip, isinstance, isinstance, json.loads, isinstance

### koruapi.mcp_server._serialize_mcp_ticket
- **Output to**: ticket.get, ticket.get, ticket.get, ticket.get, ticket.get

### koruapi.mcp_server._collect_process_logs
- **Output to**: logs.extend, logs.extend, None.split, None.split, result.stdout.strip

### koruide.protocol.Message.encode
- **Output to**: None.encode, json.dumps, self.to_dict

### koruide.protocol.decode
- **Output to**: isinstance, text.strip, obj.get, obj.get, koruide.protocol._filter_extras

### koruide.ide._ide_id_from_process
> Map a single process to a known IDE id, if any.
- **Output to**: koruide.ide._read_comm, koruide.ide._read_cmdline, _IDE_SIGNATURES.items, koruide.ide._matches

### koruide.audit._JSONFormatter.format
- **Output to**: record.getMessage

### koruide.audit._isoformat_utc
- **Output to**: int, int, time.gmtime, time.time, time.strftime

### koruide.plugin_installer._parse_extension_version
- **Output to**: output.splitlines, line.strip, None.startswith, EXTENSION_ID.lower, item.lower

### koruide.plugin_installer.format_plugin_install_result
> Human-friendly single-line status for autonomous startup.
- **Output to**: None.join

### koru.agent_backends._parse_lane
- **Output to**: raw.get, raw.get, raw.get, raw.get, raw.get

### koru.agent_backends.validate_agent_integration_config
> Return human-readable validation errors (empty list when OK).
- **Output to**: config.lanes.items, errors.append, koru.agent_backends.get_agent_backend_profile, errors.append

### koru.watch._format_connected_event

### koru.watch._format_management_event
- **Output to**: str, str, event.get, event.get, None.join

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `koru.autonomous_parser.build_parser` - 65 calls
- `src.koru.autonomous_parser.build_parser` - 65 calls
- `koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `src.koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `koru.context.render_markdown_handoff` - 47 calls
- `koru.context_render.render_markdown_handoff` - 47 calls
- `src.koru.context.render_markdown_handoff` - 47 calls
- `src.koru.context_render.render_markdown_handoff` - 47 calls
- `koru.policy.load_policy` - 43 calls
- `src.koru.policy.load_policy` - 43 calls
- `koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `src.koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `koruapi.mcp_server.tool_run_ticket` - 33 calls
- `koru.autonomous_cycle.run_cycle` - 33 calls
- `src.koruapi.mcp_server.tool_run_ticket` - 33 calls
- `src.koru.autonomous_cycle.run_cycle` - 33 calls
- `koru.cli_topology.topology_main` - 32 calls
- `src.koru.cli_topology.topology_main` - 32 calls
- `koru.queue.runners.run_api_request` - 30 calls
- `src.koru.queue.runners.run_api_request` - 30 calls
- `koru.autonomous_startup.build_startup_probe` - 29 calls
- `koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `koru.autopilot.daemon_cli.action_daemon` - 29 calls
- `src.koru.autonomous_startup.build_startup_probe` - 29 calls
- `src.koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `src.koru.autopilot.daemon_cli.action_daemon` - 29 calls
- `koru.cli_queue.render_clean_report_text` - 28 calls
- `koru.tasks.create_nl_task` - 28 calls
- `src.koru.cli_queue.render_clean_report_text` - 28 calls
- `src.koru.tasks.create_nl_task` - 28 calls
- `koru.scan.scan_pytest_collect` - 24 calls
- `koru.autopilot.install_manager.collect_install_manager_report` - 24 calls
- `src.koru.scan.scan_pytest_collect` - 24 calls
- `src.koru.autopilot.install_manager.collect_install_manager_report` - 24 calls
- `koruide.os_injector.inject_with_profile` - 23 calls
- `koru.init.init_project` - 23 calls
- `koru.autonomy.ide_work.build_ide_work_prompt` - 23 calls
- `src.koruide.os_injector.inject_with_profile` - 23 calls
- `src.koru.init.init_project` - 23 calls
- `src.koru.autonomy.ide_work.build_ide_work_prompt` - 23 calls

## System Interactions

How components interact:

```mermaid
graph TD
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.