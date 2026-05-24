# System Architecture Analysis
<!-- generated in 0.02s -->

## Overview

- **Project**: /home/tom/github/semcod/koru
- **Primary Language**: python
- **Languages**: python: 649, md: 84, shell: 50, yaml: 22, typescript: 18
- **Analysis Mode**: static
- **Total Functions**: 4738
- **Total Classes**: 468
- **Modules**: 863
- **Entry Points**: 0

## Architecture by Module

### plugins.koru-autopilot-vscode.src.extension
- **Functions**: 263
- **Classes**: 2
- **File**: `extension.ts`

### koru.doctor
- **Functions**: 91
- **Classes**: 2
- **File**: `doctor.py`

### src.koru.doctor
- **Functions**: 91
- **Classes**: 2
- **File**: `doctor.py`

### koru.autonomous_cycle
- **Functions**: 73
- **Classes**: 1
- **File**: `autonomous_cycle.py`

### src.koru.autonomous_cycle
- **Functions**: 73
- **Classes**: 1
- **File**: `autonomous_cycle.py`

### plugins.koru-autopilot-vscode.src.probe-ladder.test
- **Functions**: 64
- **File**: `probe-ladder.test.ts`

### koru.autonomous
- **Functions**: 56
- **Classes**: 1
- **File**: `autonomous.py`

### src.koru.autonomous
- **Functions**: 56
- **Classes**: 1
- **File**: `autonomous.py`

### koru.wizard.gui.static.wizard
- **Functions**: 47
- **File**: `wizard.js`

### src.koru.wizard.gui.static.wizard
- **Functions**: 47
- **File**: `wizard.js`

### koruide.ide
- **Functions**: 44
- **Classes**: 1
- **File**: `ide.py`

### src.koruide.ide
- **Functions**: 44
- **Classes**: 1
- **File**: `ide.py`

### koru.cli_cleaned
- **Functions**: 41
- **File**: `cli_cleaned.py`

### src.koru.cli_cleaned
- **Functions**: 41
- **File**: `cli_cleaned.py`

### src.koru.autonomous_wup
- **Functions**: 39
- **Classes**: 3
- **File**: `autonomous_wup.py`

### plugins.koru-autopilot-vscode.src.probe-ladder
- **Functions**: 39
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koruapi.mcp_server
- **Functions**: 35
- **File**: `mcp_server.py`

### koruide.daemon.handlers
- **Functions**: 32
- **File**: `handlers.py`

### koru.autonomous_startup
- **Functions**: 32
- **Classes**: 3
- **File**: `autonomous_startup.py`

### src.koruide.daemon.handlers
- **Functions**: 32
- **File**: `handlers.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

### plugins.koru-autopilot-vscode.src.extension.AutopilotBridge
- **Methods**: 253
- **Key Methods**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.isConnected, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.sendConsoleLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.socketPath, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.tryConnectNext, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.p

### plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 19
- **Key Methods**: plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.exec, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text

### plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 15
- **Key Methods**: plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.exec, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.r, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.r, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fields

### koruide.daemon.server.AutopilotDaemon
> Selector-based unix-socket broker.
- **Methods**: 14
- **Key Methods**: koruide.daemon.server.AutopilotDaemon.__init__, koruide.daemon.server.AutopilotDaemon.start, koruide.daemon.server.AutopilotDaemon.serve_forever, koruide.daemon.server.AutopilotDaemon.stop, koruide.daemon.server.AutopilotDaemon._shutdown, koruide.daemon.server.AutopilotDaemon._accept, koruide.daemon.server.AutopilotDaemon._on_readable, koruide.daemon.server.AutopilotDaemon._dispatch, koruide.daemon.server.AutopilotDaemon._send, koruide.daemon.server.AutopilotDaemon._drop

### src.koruide.daemon.server.AutopilotDaemon
> Selector-based unix-socket broker.
- **Methods**: 14
- **Key Methods**: src.koruide.daemon.server.AutopilotDaemon.__init__, src.koruide.daemon.server.AutopilotDaemon.start, src.koruide.daemon.server.AutopilotDaemon.serve_forever, src.koruide.daemon.server.AutopilotDaemon.stop, src.koruide.daemon.server.AutopilotDaemon._shutdown, src.koruide.daemon.server.AutopilotDaemon._accept, src.koruide.daemon.server.AutopilotDaemon._on_readable, src.koruide.daemon.server.AutopilotDaemon._dispatch, src.koruide.daemon.server.AutopilotDaemon._send, src.koruide.daemon.server.AutopilotDaemon._drop

### koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 13
- **Key Methods**: koruide.injector.Injector.probe, koruide.injector.Injector._candidate_backends, koruide.injector.Injector.select_backend, koruide.injector.Injector._type_with_backend, koruide.injector.Injector._type_text_backends, koruide.injector.Injector._log_type_text_request, koruide.injector.Injector._dry_run_type_text_result, koruide.injector.Injector._try_type_text_backends, koruide.injector.Injector._all_type_backends_failed, koruide.injector.Injector.type_text

### src.koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 13
- **Key Methods**: src.koruide.injector.Injector.probe, src.koruide.injector.Injector._candidate_backends, src.koruide.injector.Injector.select_backend, src.koruide.injector.Injector._type_with_backend, src.koruide.injector.Injector._type_text_backends, src.koruide.injector.Injector._log_type_text_request, src.koruide.injector.Injector._dry_run_type_text_result, src.koruide.injector.Injector._try_type_text_backends, src.koruide.injector.Injector._all_type_backends_failed, src.koruide.injector.Injector.type_text

### koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 12
- **Key Methods**: koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info, koruide.drive_orchestrator.DriveOrchestrator.should_block_plugin_version, koruide.drive_orchestrator.DriveOrchestrator.plugin_version_block_message

### src.koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 12
- **Key Methods**: src.koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, src.koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, src.koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, src.koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, src.koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info, src.koruide.drive_orchestrator.DriveOrchestrator.should_block_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_block_message

### plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher
- **Methods**: 11
- **Key Methods**: plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.currentCursor, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.adapterDescription, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.setCursor, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.start, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.tick, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.stop, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.clearInterval, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.pollOnce, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.cursorAdvances, plugins.koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.a

### koruide.client.KoruIDEClient
> Connect, send one message, read one reply, disconnect.
- **Methods**: 7
- **Key Methods**: koruide.client.KoruIDEClient.__init__, koruide.client.KoruIDEClient._connect, koruide.client.KoruIDEClient.request, koruide.client.KoruIDEClient.is_running, koruide.client.KoruIDEClient.drive, koruide.client.KoruIDEClient.status, koruide.client.KoruIDEClient.shutdown

### koru.local_manager_client.LocalManagerClient
> Tiny JSON-over-HTTP client for ``koru local-serve``.
- **Methods**: 7
- **Key Methods**: koru.local_manager_client.LocalManagerClient.from_env, koru.local_manager_client.LocalManagerClient.enabled, koru.local_manager_client.LocalManagerClient.post, koru.local_manager_client.LocalManagerClient.register_worker, koru.local_manager_client.LocalManagerClient.heartbeat_worker, koru.local_manager_client.LocalManagerClient.claim_action, koru.local_manager_client.LocalManagerClient.complete_action

### koru.remote.client.KoruRemoteClient
> SDK for controlling and monitoring remote Koru nodes and active IDEs.
- **Methods**: 7
- **Key Methods**: koru.remote.client.KoruRemoteClient.__init__, koru.remote.client.KoruRemoteClient._request, koru.remote.client.KoruRemoteClient.get_status, koru.remote.client.KoruRemoteClient.get_logs, koru.remote.client.KoruRemoteClient.send_drive_command, koru.remote.client.KoruRemoteClient.list_running_ides, koru.remote.client.KoruRemoteClient.list_connected_plugins

### src.koruide.client.KoruIDEClient
> Connect, send one message, read one reply, disconnect.
- **Methods**: 7
- **Key Methods**: src.koruide.client.KoruIDEClient.__init__, src.koruide.client.KoruIDEClient._connect, src.koruide.client.KoruIDEClient.request, src.koruide.client.KoruIDEClient.is_running, src.koruide.client.KoruIDEClient.drive, src.koruide.client.KoruIDEClient.status, src.koruide.client.KoruIDEClient.shutdown

### src.koru.local_manager_client.LocalManagerClient
> Tiny JSON-over-HTTP client for ``koru local-serve``.
- **Methods**: 7
- **Key Methods**: src.koru.local_manager_client.LocalManagerClient.from_env, src.koru.local_manager_client.LocalManagerClient.enabled, src.koru.local_manager_client.LocalManagerClient.post, src.koru.local_manager_client.LocalManagerClient.register_worker, src.koru.local_manager_client.LocalManagerClient.heartbeat_worker, src.koru.local_manager_client.LocalManagerClient.claim_action, src.koru.local_manager_client.LocalManagerClient.complete_action

### src.koru.remote.client.KoruRemoteClient
> SDK for controlling and monitoring remote Koru nodes and active IDEs.
- **Methods**: 7
- **Key Methods**: src.koru.remote.client.KoruRemoteClient.__init__, src.koru.remote.client.KoruRemoteClient._request, src.koru.remote.client.KoruRemoteClient.get_status, src.koru.remote.client.KoruRemoteClient.get_logs, src.koru.remote.client.KoruRemoteClient.send_drive_command, src.koru.remote.client.KoruRemoteClient.list_running_ides, src.koru.remote.client.KoruRemoteClient.list_connected_plugins

### koru.local_manager_state.WorkerRegistry
> Registry and lifecycle policy for versioned koru workers.
- **Methods**: 6
- **Key Methods**: koru.local_manager_state.WorkerRegistry.__init__, koru.local_manager_state.WorkerRegistry.register, koru.local_manager_state.WorkerRegistry.heartbeat, koru.local_manager_state.WorkerRegistry._reconcile_locked, koru.local_manager_state.WorkerRegistry._reply_locked, koru.local_manager_state.WorkerRegistry.snapshot

### koru.bounded_contexts.local_manager.application.LocalManagerCommandService
> Handles state-changing local-manager operations.
- **Methods**: 6
- **Key Methods**: koru.bounded_contexts.local_manager.application.LocalManagerCommandService.__init__, koru.bounded_contexts.local_manager.application.LocalManagerCommandService.enqueue, koru.bounded_contexts.local_manager.application.LocalManagerCommandService.claim, koru.bounded_contexts.local_manager.application.LocalManagerCommandService.complete, koru.bounded_contexts.local_manager.application.LocalManagerCommandService.register_worker, koru.bounded_contexts.local_manager.application.LocalManagerCommandService.heartbeat_worker

### koru.wizard.prompters.StdinPrompter
> Default prompter: prints prompt + options, reads a single line from stdin.

Supports a ``?`` prefix 
- **Methods**: 6
- **Key Methods**: koru.wizard.prompters.StdinPrompter.__init__, koru.wizard.prompters.StdinPrompter._print, koru.wizard.prompters.StdinPrompter._render_prompt, koru.wizard.prompters.StdinPrompter._show_help, koru.wizard.prompters.StdinPrompter.ask_choice, koru.wizard.prompters.StdinPrompter.ask_yes_no
- **Inherits**: Prompter

### src.koru.local_manager_state.WorkerRegistry
> Registry and lifecycle policy for versioned koru workers.
- **Methods**: 6
- **Key Methods**: src.koru.local_manager_state.WorkerRegistry.__init__, src.koru.local_manager_state.WorkerRegistry.register, src.koru.local_manager_state.WorkerRegistry.heartbeat, src.koru.local_manager_state.WorkerRegistry._reconcile_locked, src.koru.local_manager_state.WorkerRegistry._reply_locked, src.koru.local_manager_state.WorkerRegistry.snapshot

## Data Transformation Functions

Key functions that process and transform data:

### koruobserve.lifecycle._stop_orphan_observe_processes
> SIGTERM stale observe children when pidfiles are missing (e.g. after crash).
- **Output to**: needles.items, koruobserve.lifecycle._pids_matching_koru_cmdline, None.unlink, contextlib.suppress, os.kill

### koruobserve.cli_parser.build_observe_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_subparsers, sub.add_parser, koruobserve.cli_parser._add_subproject

### korudsl.cli._build_parser
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_subparsers, sub.add_parser, to_lib.add_argument

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
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_subparsers, sub.add_parser

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

### koruvision.cli_parser._add_capture_subparser
- **Output to**: sub.add_parser, once.add_argument, koruvision.cli_parser.register_mesh_publish_args

### koruvision.cli_parser._add_agent_subparser
- **Output to**: sub.add_parser, agent.add_argument, agent.add_argument, agent.add_argument, koruvision.cli_parser.register_mesh_publish_args

### koruvision.cli_parser.build_vision_parser
> Build the ``koru vision`` argparse tree (capture + agent subcommands).
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_subparsers, koruvision.cli_parser._add_capture_subparser, koruvision.cli_parser._add_agent_subparser

### koruvision.providers.portal_screencast._run_screencast_subprocess
- **Output to**: subprocess.run, RuntimeError

### koruvision.providers.portal_screencast._parse_screencast_stdout
- **Output to**: stdout.strip, RuntimeError, json.loads, RuntimeError, dict

### koruvision.providers.browser_getdisplay._decode_browser_png_upload
- **Output to**: body.get, body.get, ValueError, base64.b64decode, payload.startswith

### korumesh.cli_parser.build_mesh_parser
- **Output to**: argparse.ArgumentParser, parser.add_subparsers, sub.add_parser, relay.add_argument, relay.add_argument

### korumesh.dashboard_parse.parse_mime_params
> Return ``(base_mime, params)`` from a mime string with ``;`` separators.
- **Output to**: piece.strip, piece.split, value.strip, mime.split, piece.strip

### src.koruide.chat_history._parse_line
- **Output to**: line.strip, json.loads, isinstance, ChatEvent, float

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `koruapi.dashboard_routes.build_dashboard_handler` - 207 calls
- `koru.wizard.gui.app.create_app` - 96 calls
- `src.koru.wizard.gui.app.create_app` - 96 calls
- `koru.autonomous_parser.build_parser` - 71 calls
- `src.koru.autonomous_parser.build_parser` - 71 calls
- `koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `src.koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `koru.context_render.render_markdown_handoff` - 47 calls
- `koru.policy.load_policy` - 43 calls
- `src.koru.policy.load_policy` - 43 calls
- `koru.git_cli.build_parser` - 39 calls
- `src.koru.git_cli.build_parser` - 39 calls
- `koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `src.koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `koru.autonomous_cycle.run_cycle` - 33 calls
- `koru.cli_topology.topology_main` - 33 calls
- `src.koru.autonomous_cycle.run_cycle` - 33 calls
- `src.koru.cli_topology.topology_main` - 33 calls
- `koruobserve.lifecycle.observe_up` - 32 calls
- `src.koruobserve.lifecycle.observe_up` - 32 calls
- `koruapi.mcp_server.tool_run_ticket` - 31 calls
- `koru.queue.runners.run_api_request` - 30 calls
- `src.koru.queue.runners.run_api_request` - 30 calls
- `koruide.daemon.handlers.handle_drive` - 29 calls
- `koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `src.koruide.daemon.handlers.handle_drive` - 29 calls
- `src.koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `koruide.plugin_installer.resolve_extension_vsix` - 28 calls
- `koru.cli_queue.render_clean_report_text` - 28 calls
- `src.koruide.plugin_installer.resolve_extension_vsix` - 28 calls
- `src.koru.cli_queue.render_clean_report_text` - 28 calls
- `koru.doctor.render_text` - 27 calls
- `src.koru.doctor.render_text` - 27 calls
- `koru.autonomous_daemon.start_or_reuse_daemon` - 26 calls
- `koru.autonomous_runtime.setup_autonomous_session` - 26 calls
- `src.koru.autonomous_daemon.start_or_reuse_daemon` - 26 calls
- `src.koru.autonomous_runtime.setup_autonomous_session` - 26 calls
- `services.healing-webhook.ticket_builder.build_ticket_payload` - 25 calls
- `koru.configurator.render_shell_exports` - 24 calls
- `koru.scan.scan_pytest_collect` - 24 calls

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