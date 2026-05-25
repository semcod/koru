# System Architecture Analysis
<!-- generated in 0.01s -->

## Overview

- **Project**: /home/tom/github/semcod/koru
- **Primary Language**: python
- **Languages**: python: 714, md: 89, shell: 50, typescript: 29, yaml: 22
- **Analysis Mode**: static
- **Total Functions**: 5338
- **Total Classes**: 529
- **Modules**: 947
- **Entry Points**: 0

## Architecture by Module

### plugins.koru-autopilot-vscode.src.extension
- **Functions**: 306
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

### plugins.koru-autopilot-vscode.src.probe-ladder.test
- **Functions**: 69
- **File**: `probe-ladder.test.ts`

### koru.autonomous
- **Functions**: 59
- **Classes**: 2
- **File**: `autonomous.py`

### src.koru.autonomous
- **Functions**: 59
- **Classes**: 2
- **File**: `autonomous.py`

### koru.wizard.gui.static.wizard
- **Functions**: 47
- **File**: `wizard.js`

### src.koru.wizard.gui.static.wizard
- **Functions**: 47
- **File**: `wizard.js`

### plugins.koru-autopilot-vscode.src.probe-ladder
- **Functions**: 47
- **Classes**: 3
- **File**: `probe-ladder.ts`

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

### koru.autonomous_cycle_chat_activity
- **Functions**: 39
- **File**: `autonomous_cycle_chat_activity.py`

### koru.autonomous_wup
- **Functions**: 39
- **Classes**: 3
- **File**: `autonomous_wup.py`

### src.koru.autonomous_cycle_chat_activity
- **Functions**: 39
- **File**: `autonomous_cycle_chat_activity.py`

### src.koru.autonomous_wup
- **Functions**: 39
- **Classes**: 3
- **File**: `autonomous_wup.py`

### koruapi.mcp_server
- **Functions**: 35
- **File**: `mcp_server.py`

### src.koruapi.mcp_server
- **Functions**: 35
- **File**: `mcp_server.py`

### src.koru.autonomy.operator_pipeline
- **Functions**: 33
- **Classes**: 2
- **File**: `operator_pipeline.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

### plugins.koru-autopilot-vscode.src.extension.AutopilotBridge
- **Methods**: 292
- **Key Methods**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.isConnected, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.sendConsoleLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.resetOperationTrace, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.traceOperation, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.safeLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.currentOperationTrace, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.socketPath, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.cfg, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.override, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect

### plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 19
- **Key Methods**: plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.exec, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, plugins.koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text

### koruide.ides.base.IdeStrategy
> Per-IDE knowledge object.

Subclasses are **pure data + thin helpers** — no global mutable state,
no
- **Methods**: 15
- **Key Methods**: koruide.ides.base.IdeStrategy.id, koruide.ides.base.IdeStrategy.label, koruide.ides.base.IdeStrategy.detection, koruide.ides.base.IdeStrategy.terminal, koruide.ides.base.IdeStrategy.aliases, koruide.ides.base.IdeStrategy.config_home, koruide.ides.base.IdeStrategy.user_settings_path, koruide.ides.base.IdeStrategy.workspace_settings_path, koruide.ides.base.IdeStrategy.state_vscdb_path, koruide.ides.base.IdeStrategy.extensions_metadata_path
- **Inherits**: ABC

### src.koruide.ides.base.IdeStrategy
> Per-IDE knowledge object.

Subclasses are **pure data + thin helpers** — no global mutable state,
no
- **Methods**: 15
- **Key Methods**: src.koruide.ides.base.IdeStrategy.id, src.koruide.ides.base.IdeStrategy.label, src.koruide.ides.base.IdeStrategy.detection, src.koruide.ides.base.IdeStrategy.terminal, src.koruide.ides.base.IdeStrategy.aliases, src.koruide.ides.base.IdeStrategy.config_home, src.koruide.ides.base.IdeStrategy.user_settings_path, src.koruide.ides.base.IdeStrategy.workspace_settings_path, src.koruide.ides.base.IdeStrategy.state_vscdb_path, src.koruide.ides.base.IdeStrategy.extensions_metadata_path
- **Inherits**: ABC

### plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 15
- **Key Methods**: plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.exec, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.r, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.r, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep, plugins.koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fields

### koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 14
- **Key Methods**: koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, koruide.drive_orchestrator.DriveOrchestrator.protocol_plugin_version_policy, koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info, koruide.drive_orchestrator.DriveOrchestrator.should_block_plugin_version

### koruide.daemon.server.AutopilotDaemon
> Selector-based unix-socket broker.
- **Methods**: 14
- **Key Methods**: koruide.daemon.server.AutopilotDaemon.__init__, koruide.daemon.server.AutopilotDaemon.start, koruide.daemon.server.AutopilotDaemon.serve_forever, koruide.daemon.server.AutopilotDaemon.stop, koruide.daemon.server.AutopilotDaemon._shutdown, koruide.daemon.server.AutopilotDaemon._accept, koruide.daemon.server.AutopilotDaemon._on_readable, koruide.daemon.server.AutopilotDaemon._dispatch, koruide.daemon.server.AutopilotDaemon._send, koruide.daemon.server.AutopilotDaemon._drop

### src.koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 14
- **Key Methods**: src.koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, src.koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, src.koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, src.koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, src.koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, src.koruide.drive_orchestrator.DriveOrchestrator.protocol_plugin_version_policy, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info, src.koruide.drive_orchestrator.DriveOrchestrator.should_block_plugin_version

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

### koruide.ides.antigravity.AntigravityStrategy
- **Methods**: 12
- **Key Methods**: koruide.ides.antigravity.AntigravityStrategy.id, koruide.ides.antigravity.AntigravityStrategy.label, koruide.ides.antigravity.AntigravityStrategy.detection, koruide.ides.antigravity.AntigravityStrategy.terminal, koruide.ides.antigravity.AntigravityStrategy.aliases, koruide.ides.antigravity.AntigravityStrategy.config_home, koruide.ides.antigravity.AntigravityStrategy.workspace_settings_path, koruide.ides.antigravity.AntigravityStrategy.extensions_metadata_path, koruide.ides.antigravity.AntigravityStrategy.plugin, koruide.ides.antigravity.AntigravityStrategy.keyboard
- **Inherits**: IdeStrategy

### koruide.ides.windsurf.WindsurfStrategy
- **Methods**: 12
- **Key Methods**: koruide.ides.windsurf.WindsurfStrategy.id, koruide.ides.windsurf.WindsurfStrategy.label, koruide.ides.windsurf.WindsurfStrategy.detection, koruide.ides.windsurf.WindsurfStrategy.terminal, koruide.ides.windsurf.WindsurfStrategy.aliases, koruide.ides.windsurf.WindsurfStrategy.config_home, koruide.ides.windsurf.WindsurfStrategy.workspace_settings_path, koruide.ides.windsurf.WindsurfStrategy.extensions_metadata_path, koruide.ides.windsurf.WindsurfStrategy.plugin, koruide.ides.windsurf.WindsurfStrategy.keyboard
- **Inherits**: IdeStrategy

### koruide.ides.cursor.CursorStrategy
> Strategy for Cursor (VS Code-fork by Anysphere).
- **Methods**: 12
- **Key Methods**: koruide.ides.cursor.CursorStrategy.id, koruide.ides.cursor.CursorStrategy.label, koruide.ides.cursor.CursorStrategy.detection, koruide.ides.cursor.CursorStrategy.terminal, koruide.ides.cursor.CursorStrategy.aliases, koruide.ides.cursor.CursorStrategy.config_home, koruide.ides.cursor.CursorStrategy.workspace_settings_path, koruide.ides.cursor.CursorStrategy.extensions_metadata_path, koruide.ides.cursor.CursorStrategy.plugin, koruide.ides.cursor.CursorStrategy.keyboard
- **Inherits**: IdeStrategy

### koruide.ides.vscode.VscodeStrategy
- **Methods**: 12
- **Key Methods**: koruide.ides.vscode.VscodeStrategy.id, koruide.ides.vscode.VscodeStrategy.label, koruide.ides.vscode.VscodeStrategy.detection, koruide.ides.vscode.VscodeStrategy.terminal, koruide.ides.vscode.VscodeStrategy.aliases, koruide.ides.vscode.VscodeStrategy.config_home, koruide.ides.vscode.VscodeStrategy.workspace_settings_path, koruide.ides.vscode.VscodeStrategy.extensions_metadata_path, koruide.ides.vscode.VscodeStrategy.plugin, koruide.ides.vscode.VscodeStrategy.keyboard
- **Inherits**: IdeStrategy

### src.koruide.ides.antigravity.AntigravityStrategy
- **Methods**: 12
- **Key Methods**: src.koruide.ides.antigravity.AntigravityStrategy.id, src.koruide.ides.antigravity.AntigravityStrategy.label, src.koruide.ides.antigravity.AntigravityStrategy.detection, src.koruide.ides.antigravity.AntigravityStrategy.terminal, src.koruide.ides.antigravity.AntigravityStrategy.aliases, src.koruide.ides.antigravity.AntigravityStrategy.config_home, src.koruide.ides.antigravity.AntigravityStrategy.workspace_settings_path, src.koruide.ides.antigravity.AntigravityStrategy.extensions_metadata_path, src.koruide.ides.antigravity.AntigravityStrategy.plugin, src.koruide.ides.antigravity.AntigravityStrategy.keyboard
- **Inherits**: IdeStrategy

### src.koruide.ides.windsurf.WindsurfStrategy
- **Methods**: 12
- **Key Methods**: src.koruide.ides.windsurf.WindsurfStrategy.id, src.koruide.ides.windsurf.WindsurfStrategy.label, src.koruide.ides.windsurf.WindsurfStrategy.detection, src.koruide.ides.windsurf.WindsurfStrategy.terminal, src.koruide.ides.windsurf.WindsurfStrategy.aliases, src.koruide.ides.windsurf.WindsurfStrategy.config_home, src.koruide.ides.windsurf.WindsurfStrategy.workspace_settings_path, src.koruide.ides.windsurf.WindsurfStrategy.extensions_metadata_path, src.koruide.ides.windsurf.WindsurfStrategy.plugin, src.koruide.ides.windsurf.WindsurfStrategy.keyboard
- **Inherits**: IdeStrategy

### src.koruide.ides.cursor.CursorStrategy
> Strategy for Cursor (VS Code-fork by Anysphere).
- **Methods**: 12
- **Key Methods**: src.koruide.ides.cursor.CursorStrategy.id, src.koruide.ides.cursor.CursorStrategy.label, src.koruide.ides.cursor.CursorStrategy.detection, src.koruide.ides.cursor.CursorStrategy.terminal, src.koruide.ides.cursor.CursorStrategy.aliases, src.koruide.ides.cursor.CursorStrategy.config_home, src.koruide.ides.cursor.CursorStrategy.workspace_settings_path, src.koruide.ides.cursor.CursorStrategy.extensions_metadata_path, src.koruide.ides.cursor.CursorStrategy.plugin, src.koruide.ides.cursor.CursorStrategy.keyboard
- **Inherits**: IdeStrategy

### src.koruide.ides.vscode.VscodeStrategy
- **Methods**: 12
- **Key Methods**: src.koruide.ides.vscode.VscodeStrategy.id, src.koruide.ides.vscode.VscodeStrategy.label, src.koruide.ides.vscode.VscodeStrategy.detection, src.koruide.ides.vscode.VscodeStrategy.terminal, src.koruide.ides.vscode.VscodeStrategy.aliases, src.koruide.ides.vscode.VscodeStrategy.config_home, src.koruide.ides.vscode.VscodeStrategy.workspace_settings_path, src.koruide.ides.vscode.VscodeStrategy.extensions_metadata_path, src.koruide.ides.vscode.VscodeStrategy.plugin, src.koruide.ides.vscode.VscodeStrategy.keyboard
- **Inherits**: IdeStrategy

### koruide.ides.vscodium.VscodiumStrategy
- **Methods**: 11
- **Key Methods**: koruide.ides.vscodium.VscodiumStrategy.id, koruide.ides.vscodium.VscodiumStrategy.label, koruide.ides.vscodium.VscodiumStrategy.detection, koruide.ides.vscodium.VscodiumStrategy.aliases, koruide.ides.vscodium.VscodiumStrategy.config_home, koruide.ides.vscodium.VscodiumStrategy.workspace_settings_path, koruide.ides.vscodium.VscodiumStrategy.extensions_metadata_path, koruide.ides.vscodium.VscodiumStrategy.plugin, koruide.ides.vscodium.VscodiumStrategy.keyboard, koruide.ides.vscodium.VscodiumStrategy.editor_cli_candidates
- **Inherits**: IdeStrategy

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

### koruide.chat_history._parse_line
- **Output to**: line.strip, json.loads, isinstance, ChatEvent, float

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `koruapi.dashboard_routes.build_dashboard_handler` - 237 calls
- `src.koruapi.dashboard_routes.build_dashboard_handler` - 237 calls
- `koru.wizard.gui.app.create_app` - 96 calls
- `src.koru.wizard.gui.app.create_app` - 96 calls
- `koru.autonomous_parser.build_parser` - 71 calls
- `src.koru.autonomous_parser.build_parser` - 71 calls
- `koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `src.koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `koru.context_render.render_markdown_handoff` - 47 calls
- `src.koru.context_render.render_markdown_handoff` - 47 calls
- `koru.policy.load_policy` - 43 calls
- `src.koru.policy.load_policy` - 43 calls
- `src.koru.autonomous_cycle.run_cycle` - 40 calls
- `koru.git_cli.build_parser` - 39 calls
- `src.koru.git_cli.build_parser` - 39 calls
- `koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `src.koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `koru.ide_doctor_cli.build_parser` - 33 calls
- `koru.cli_topology.topology_main` - 33 calls
- `src.koru.ide_doctor_cli.build_parser` - 33 calls
- `src.koru.cli_topology.topology_main` - 33 calls
- `koruobserve.lifecycle.observe_up` - 32 calls
- `src.koruobserve.lifecycle.observe_up` - 32 calls
- `koruapi.mcp_server.tool_run_ticket` - 31 calls
- `src.koruapi.mcp_server.tool_run_ticket` - 31 calls
- `koru.queue.runners.run_api_request` - 30 calls
- `koruapi.dashboard_tickets.create_ticket_from_dashboard` - 30 calls
- `koruide.daemon.handlers.handle_drive` - 30 calls
- `src.koruide.daemon.handlers.handle_drive` - 30 calls
- `src.koru.queue.runners.run_api_request` - 30 calls
- `src.koruapi.dashboard_tickets.create_ticket_from_dashboard` - 30 calls
- `koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `src.koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `koruide.plugin_installer.resolve_extension_vsix` - 28 calls
- `koru.cli_queue.render_clean_report_text` - 28 calls
- `src.koruide.plugin_installer.resolve_extension_vsix` - 28 calls
- `src.koru.cli_queue.render_clean_report_text` - 28 calls
- `koru.doctor.render_text` - 27 calls
- `koru.autonomy.ide_work.build_ide_work_prompt` - 27 calls
- `src.koru.doctor.render_text` - 27 calls

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