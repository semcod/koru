# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/semcod/koru/src
- **Primary Language**: python
- **Languages**: python: 121
- **Analysis Mode**: static
- **Total Functions**: 878
- **Total Classes**: 80
- **Modules**: 121
- **Entry Points**: 0

## Architecture by Module

### koru.cli
- **Functions**: 52
- **File**: `cli.py`

### koru.context
- **Functions**: 43
- **File**: `context.py`

### koru.autonomous
- **Functions**: 37
- **Classes**: 2
- **File**: `autonomous.py`

### koru.autopilot.cli_command
- **Functions**: 37
- **File**: `cli_command.py`

### koruapi.mcp_server
- **Functions**: 34
- **File**: `mcp_server.py`

### koruide.daemon
- **Functions**: 31
- **Classes**: 2
- **File**: `daemon.py`

### koruide.ide
- **Functions**: 29
- **Classes**: 1
- **File**: `ide.py`

### koruide.os_injector
- **Functions**: 24
- **Classes**: 2
- **File**: `os_injector.py`

### koru.mcp_provision
- **Functions**: 21
- **File**: `mcp_provision.py`

### koru.doctor
- **Functions**: 21
- **Classes**: 2
- **File**: `doctor.py`

### koruide.injector
- **Functions**: 20
- **Classes**: 4
- **File**: `injector.py`

### korudsl.library
- **Functions**: 19
- **File**: `library.py`

### koru.bootstrap
- **Functions**: 19
- **Classes**: 2
- **File**: `bootstrap.py`

### koru.scan
- **Functions**: 18
- **Classes**: 2
- **File**: `scan.py`

### koru.autonomy.operator_pipeline
- **Functions**: 18
- **Classes**: 2
- **File**: `operator_pipeline.py`

### koruide.plugin_installer
- **Functions**: 17
- **Classes**: 1
- **File**: `plugin_installer.py`

### koruapi.dashboard_serve
- **Functions**: 16
- **Classes**: 1
- **File**: `dashboard_serve.py`

### koru.autonomous_cycle
- **Functions**: 16
- **Classes**: 2
- **File**: `autonomous_cycle.py`

### koruapi.invoke_handlers
- **Functions**: 15
- **Classes**: 1
- **File**: `invoke_handlers.py`

### koru.topology
- **Functions**: 15
- **Classes**: 1
- **File**: `topology.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

### koruide.daemon.AutopilotDaemon
> Selector-based unix-socket broker.

Parameters
----------
socket_path:
    Where to bind. Defaults t
- **Methods**: 26
- **Key Methods**: koruide.daemon.AutopilotDaemon.__init__, koruide.daemon.AutopilotDaemon.start, koruide.daemon.AutopilotDaemon.serve_forever, koruide.daemon.AutopilotDaemon.stop, koruide.daemon.AutopilotDaemon._shutdown, koruide.daemon.AutopilotDaemon._accept, koruide.daemon.AutopilotDaemon._on_readable, koruide.daemon.AutopilotDaemon._dispatch, koruide.daemon.AutopilotDaemon._send, koruide.daemon.AutopilotDaemon._drop

### koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 9
- **Key Methods**: koruide.injector.Injector.probe, koruide.injector.Injector._candidate_backends, koruide.injector.Injector.select_backend, koruide.injector.Injector._type_with_backend, koruide.injector.Injector.type_text, koruide.injector.Injector.submit_only, koruide.injector.Injector._probe_one, koruide.injector.Injector._call, koruide.injector.Injector._press_wtype

### koruide.client.KoruIDEClient
> Connect, send one message, read one reply, disconnect.
- **Methods**: 7
- **Key Methods**: koruide.client.KoruIDEClient.__init__, koruide.client.KoruIDEClient._connect, koruide.client.KoruIDEClient.request, koruide.client.KoruIDEClient.is_running, koruide.client.KoruIDEClient.drive, koruide.client.KoruIDEClient.status, koruide.client.KoruIDEClient.shutdown

### koru.ide_client.IDEControlClient
> Minimal interface `koru` runtime code expects from an IDE client.
- **Methods**: 4
- **Key Methods**: koru.ide_client.IDEControlClient.is_running, koru.ide_client.IDEControlClient.drive, koru.ide_client.IDEControlClient.status, koru.ide_client.IDEControlClient.shutdown
- **Inherits**: Protocol

### koru.ide_client.LegacyAutopilotClientAdapter
> Expose legacy :class:`AutopilotClient` through :class:`IDEControlClient`.
- **Methods**: 4
- **Key Methods**: koru.ide_client.LegacyAutopilotClientAdapter.is_running, koru.ide_client.LegacyAutopilotClientAdapter.drive, koru.ide_client.LegacyAutopilotClientAdapter.status, koru.ide_client.LegacyAutopilotClientAdapter.shutdown

### koru.doctor.DoctorReport
> Aggregate result of ``run_diagnostics``.
- **Methods**: 4
- **Key Methods**: koru.doctor.DoctorReport.has_failures, koru.doctor.DoctorReport.has_warnings, koru.doctor.DoctorReport.summary, koru.doctor.DoctorReport.to_dict

### koru.run_log.RunLogWriter
> Append-only JSONL writer with best-effort durability.

The constructor does not open the file — that
- **Methods**: 4
- **Key Methods**: koru.run_log.RunLogWriter._emit, koru.run_log.RunLogWriter.write_header, koru.run_log.RunLogWriter.write_iteration, koru.run_log.RunLogWriter.write_footer

### koruapi.server.KoruAPIHandler
- **Methods**: 3
- **Key Methods**: koruapi.server.KoruAPIHandler.log_message, koruapi.server.KoruAPIHandler.do_GET, koruapi.server.KoruAPIHandler.do_POST
- **Inherits**: BaseHTTPRequestHandler

### koruide.audit.AuditLog
> Append-only audit log for autopilot events.

Construct once at daemon start; call :meth:`record` for
- **Methods**: 3
- **Key Methods**: koruide.audit.AuditLog.__init__, koruide.audit.AuditLog.record, koruide.audit.AuditLog.close

### koru.local_service._EventBuffer
> Thread-safe ring of recent event records (oldest dropped at maxlen).
- **Methods**: 3
- **Key Methods**: koru.local_service._EventBuffer.__init__, koru.local_service._EventBuffer.append, koru.local_service._EventBuffer.snapshot

### koruide.protocol.Message
- **Methods**: 2
- **Key Methods**: koruide.protocol.Message.to_dict, koruide.protocol.Message.encode

### koru.autonomy.environment.EnvironmentReport
> Snapshot of the autonomy-relevant environment.

Designed to be cheap (<200 ms) so it can be called o
- **Methods**: 2
- **Key Methods**: koru.autonomy.environment.EnvironmentReport.installed_ides, koru.autonomy.environment.EnvironmentReport.mcp_enabled_ides

### koru.queue.types.QueueLoopResult
> Aggregate result of draining the planfile queue with run_planfile_queue_loop.
- **Methods**: 2
- **Key Methods**: koru.queue.types.QueueLoopResult.ticket_id, koru.queue.types.QueueLoopResult.summary

### koruide.config.AutopilotConfig
> In-memory view of ``autopilot.toml`` (or defaults).
- **Methods**: 1
- **Key Methods**: koruide.config.AutopilotConfig.submit_key_for

### koruide.ide.RunningIDE
> A single IDE process discovered on the system.
- **Methods**: 1
- **Key Methods**: koruide.ide.RunningIDE.to_dict

### koruide.injector.BackendStatus
> Result of probing a single backend.
- **Methods**: 1
- **Key Methods**: koruide.injector.BackendStatus.to_dict

### koruide.injector.InjectionResult
- **Methods**: 1
- **Key Methods**: koruide.injector.InjectionResult.to_dict

### koruide.audit._JSONFormatter
> Emit ``record.msg`` verbatim — we hand it in pre-serialised.
- **Methods**: 1
- **Key Methods**: koruide.audit._JSONFormatter.format
- **Inherits**: logging.Formatter

### koruide.plugin_installer.PluginInstallResult
- **Methods**: 1
- **Key Methods**: koruide.plugin_installer.PluginInstallResult.to_dict

### koru.gate.GateAuthorization
> Parsed gate-authorization record extracted from a ticket note.
- **Methods**: 1
- **Key Methods**: koru.gate.GateAuthorization.to_note

## Data Transformation Functions

Key functions that process and transform data:

### korudsl.cli._build_parser
- **Output to**: argparse.ArgumentParser, parser.add_subparsers, sub.add_parser, to_lib.add_argument, to_lib.add_argument

### korudsl.library.convert_goals_json_to_library
> Convert legacy goals JSON to OQL library.
- **Output to**: korudsl.library.ensure_library_structure, isinstance, isinstance, isinstance, json.loads

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

### koru.watch._format_ticket_event
- **Output to**: str, str, ticket.get, execution.get, execution.get

### koru.watch.format_queue_event
> Return a compact human-readable line for a planfile WebSocket event.
- **Output to**: str, koru.watch._format_ticket_event, koru.watch._format_connected_event, koru.watch._format_management_event, event.get

### koru.gate.parse_authorizations
> Extract all gate authorizations recorded on a ticket.

Returns them in insertion order so callers ca
- **Output to**: str, out.append, isinstance, note.startswith, json.loads

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `koru.autonomous_cycle.run_cycle` - 168 calls
- `koru.autonomous_parser.build_parser` - 65 calls
- `koru.agents.detect_agent_options` - 61 calls
- `koru.queue.runner.run_next_planfile_task` - 57 calls
- `koru.autonomy.env.apply_autoloop_env_to_args` - 53 calls
- `koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `koru.context.render_markdown_handoff` - 47 calls
- `koru.tasks.create_nl_task` - 47 calls
- `koru.queue.runners.run_llm_request` - 46 calls
- `koru.policy.load_policy` - 43 calls
- `koruapi.mcp_server.tool_run_ticket` - 33 calls
- `koru.autonomy.post_run_verify.load_post_run_verify_config` - 31 calls
- `koru.queue.runners.run_api_request` - 30 calls
- `koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `koru.tools.detect_tools` - 25 calls
- `koru.scan.scan_pytest_collect` - 24 calls
- `koru.autonomy.operator_pipeline.run_startup_operator_pipeline` - 23 calls
- `koru.autonomy.ide_work.build_ide_work_prompt` - 23 calls
- `koruapi.dashboard_serve.apply_topology_post_update` - 22 calls
- `koru.gate.parse_authorizations` - 22 calls
- `koru.init.init_project` - 22 calls
- `koru.agents.detect_project_environment` - 22 calls
- `koruide.protocol.decode` - 21 calls
- `koru.autonomous_startup.build_startup_probe` - 21 calls
- `koru.tools.build_tool_task_scaffold` - 21 calls
- `koru.doctor.render_text` - 21 calls
- `koru.gc.collect_gc_candidates` - 21 calls
- `koruapi.cli.main` - 20 calls
- `koruide.os_injector.inject_with_profile` - 20 calls
- `koru.tools.render_tools_detect_text` - 20 calls
- `korudsl.cli.main` - 18 calls
- `koruapi.dashboard_serve.serve` - 18 calls
- `koruide.plugin_installer.resolve_extension_vsix` - 18 calls
- `koru.agent_backends.load_agent_integration_config` - 18 calls
- `koru.loop.run_closed_loop` - 18 calls
- `koru.init_host_environment.build_host_environment_report` - 18 calls
- `koru.mcp_provision.ensure_koru_mcp_not_disabled` - 17 calls
- `koru.autonomy.environment.probe_ide_presence` - 17 calls
- `koruapi.mcp_server.tool_propose_edits` - 16 calls
- `koru.autonomous_diagnostics.build_idle_checks` - 16 calls

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