# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/semcod/koru
- **Primary Language**: python
- **Languages**: python: 896, md: 115, typescript: 79, yaml: 65, shell: 49
- **Analysis Mode**: static
- **Total Functions**: 30318
- **Total Classes**: 685
- **Modules**: 1255
- **Entry Points**: 0

## Architecture by Module

### code2llm_output.map.toon
- **Functions**: 67223
- **File**: `map.toon.yaml`

### batch_1.SUMD
- **Functions**: 4386
- **Classes**: 1
- **File**: `SUMD.md`

### project.map.toon
- **Functions**: 4386
- **File**: `map.toon.yaml`

### project.src_part4.map.toon
- **Functions**: 2552
- **File**: `map.toon.yaml`

### project.src_part3.map.toon
- **Functions**: 2549
- **File**: `map.toon.yaml`

### project.src_part2.map.toon
- **Functions**: 2546
- **File**: `map.toon.yaml`

### project.src.map.toon
- **Functions**: 2544
- **File**: `map.toon.yaml`

### plugins.koru-autopilot-cursor.src.extension
- **Functions**: 396
- **Classes**: 2
- **File**: `extension.ts`

### plugins.koru-autopilot-vscodium.src.extension
- **Functions**: 389
- **Classes**: 1
- **File**: `extension.ts`

### plugins.koru-autopilot-antigravity.src.extension
- **Functions**: 373
- **Classes**: 2
- **File**: `extension.ts`

### plugins.koru-autopilot-windsurf.src.extension
- **Functions**: 373
- **Classes**: 2
- **File**: `extension.ts`

### plugins.koru-autopilot-vscode.src.extension
- **Functions**: 373
- **Classes**: 1
- **File**: `extension.ts`

### koru.doctor
- **Functions**: 71
- **Classes**: 2
- **File**: `doctor.py`

### src.koru.doctor
- **Functions**: 71
- **Classes**: 2
- **File**: `doctor.py`

### koru.autonomous
- **Functions**: 62
- **File**: `autonomous.py`

### src.koru.autonomous
- **Functions**: 62
- **File**: `autonomous.py`

### plugins.koru-autopilot-vscodium.src.probe-ladder
- **Functions**: 53
- **Classes**: 3
- **File**: `probe-ladder.ts`

### plugins.koru-autopilot-vscode.src.probe-ladder
- **Functions**: 49
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koru.autonomous_loop_runner
- **Functions**: 48
- **Classes**: 1
- **File**: `autonomous_loop_runner.py`

### src.koru.autonomous_loop_runner
- **Functions**: 48
- **Classes**: 1
- **File**: `autonomous_loop_runner.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

### plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge
- **Methods**: 382
- **Key Methods**: plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.isConnected, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.sendConsoleLog, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.resetOperationTrace, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.value, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.commands, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.server, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.traceOperation, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.safeLog, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.emitLiveDsl, plugins.koru-autopilot-vscodium.src.extension.AutopilotBridge.seq

### plugins.koru-autopilot-cursor.src.extension.AutopilotBridge
- **Methods**: 381
- **Key Methods**: plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.isConnected, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.sendConsoleLog, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.resetOperationTrace, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.value, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.commands, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.server, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.traceOperation, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.safeLog, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.emitLiveDsl, plugins.koru-autopilot-cursor.src.extension.AutopilotBridge.seq

### plugins.koru-autopilot-vscode.src.extension.AutopilotBridge
- **Methods**: 367
- **Key Methods**: plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.isConnected, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.sendConsoleLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.resetOperationTrace, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.value, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.commands, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.server, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.traceOperation, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.safeLog, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.emitLiveDsl, plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.seq

### plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge
- **Methods**: 358
- **Key Methods**: plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.isConnected, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.sendConsoleLog, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.resetOperationTrace, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.value, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.commands, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.server, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.traceOperation, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.safeLog, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.emitLiveDsl, plugins.koru-autopilot-antigravity.src.extension.AutopilotBridge.seq

### plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge
- **Methods**: 358
- **Key Methods**: plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.isConnected, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.sendConsoleLog, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.resetOperationTrace, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.value, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.commands, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.server, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.traceOperation, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.safeLog, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.emitLiveDsl, plugins.koru-autopilot-windsurf.src.extension.AutopilotBridge.seq

### koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 22
- **Key Methods**: koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, koruide.drive_orchestrator.DriveOrchestrator.is_poisoned_submit_ack, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, koruide.drive_orchestrator.DriveOrchestrator.protocol_plugin_version_policy, koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info

### src.koruide.drive_orchestrator.DriveOrchestrator
> Pure helpers used by the autopilot daemon.
- **Methods**: 22
- **Key Methods**: src.koruide.drive_orchestrator.DriveOrchestrator.plugin_required_message, src.koruide.drive_orchestrator.DriveOrchestrator.should_try_os_fallback, src.koruide.drive_orchestrator.DriveOrchestrator.build_message_sent_info, src.koruide.drive_orchestrator.DriveOrchestrator.annotate_plugin_ack, src.koruide.drive_orchestrator.DriveOrchestrator.is_poisoned_submit_ack, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_ack_required, src.koruide.drive_orchestrator.DriveOrchestrator.expected_plugin_version, src.koruide.drive_orchestrator.DriveOrchestrator.strict_plugin_version_required, src.koruide.drive_orchestrator.DriveOrchestrator.protocol_plugin_version_policy, src.koruide.drive_orchestrator.DriveOrchestrator.plugin_version_info

### plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 17
- **Key Methods**: plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, plugins.koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.trimmed

### plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 16
- **Key Methods**: plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.latestBubbleRowid, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.r, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.n, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.r, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, plugins.koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep

### src.koruide.injector.Injector
> Pick the best available backend and type text through it.

Parameters
----------
session:
    Overri
- **Methods**: 15
- **Key Methods**: src.koruide.injector.Injector.probe, src.koruide.injector.Injector._candidate_backends, src.koruide.injector.Injector._forced_backend_candidates, src.koruide.injector.Injector._available_backend_candidates, src.koruide.injector.Injector.select_backend, src.koruide.injector.Injector._type_with_backend, src.koruide.injector.Injector._type_text_backends, src.koruide.injector.Injector._log_type_text_request, src.koruide.injector.Injector._dry_run_type_text_result, src.koruide.injector.Injector._try_type_text_backends

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

### koruide.daemon.server.AutopilotDaemon
> Selector-based unix-socket broker.
- **Methods**: 14
- **Key Methods**: koruide.daemon.server.AutopilotDaemon.__init__, koruide.daemon.server.AutopilotDaemon.start, koruide.daemon.server.AutopilotDaemon.serve_forever, koruide.daemon.server.AutopilotDaemon.stop, koruide.daemon.server.AutopilotDaemon._shutdown, koruide.daemon.server.AutopilotDaemon._accept, koruide.daemon.server.AutopilotDaemon._on_readable, koruide.daemon.server.AutopilotDaemon._dispatch, koruide.daemon.server.AutopilotDaemon._send, koruide.daemon.server.AutopilotDaemon._drop

### src.koruide.daemon.server.AutopilotDaemon
> Selector-based unix-socket broker.
- **Methods**: 14
- **Key Methods**: src.koruide.daemon.server.AutopilotDaemon.__init__, src.koruide.daemon.server.AutopilotDaemon.start, src.koruide.daemon.server.AutopilotDaemon.serve_forever, src.koruide.daemon.server.AutopilotDaemon.stop, src.koruide.daemon.server.AutopilotDaemon._shutdown, src.koruide.daemon.server.AutopilotDaemon._accept, src.koruide.daemon.server.AutopilotDaemon._on_readable, src.koruide.daemon.server.AutopilotDaemon._dispatch, src.koruide.daemon.server.AutopilotDaemon._send, src.koruide.daemon.server.AutopilotDaemon._drop

### korullm.strategies.base.LlmStrategy
> Per-LLM knowledge object.
- **Methods**: 12
- **Key Methods**: korullm.strategies.base.LlmStrategy.id, korullm.strategies.base.LlmStrategy.label, korullm.strategies.base.LlmStrategy.matches_environment, korullm.strategies.base.LlmStrategy.capabilities, korullm.strategies.base.LlmStrategy.assess_drive_failure, korullm.strategies.base.LlmStrategy.idle_marker_patterns, korullm.strategies.base.LlmStrategy.prompt_envelope, korullm.strategies.base.LlmStrategy._reply_message, korullm.strategies.base.LlmStrategy._reply_verification, korullm.strategies.base.LlmStrategy._reply_reason
- **Inherits**: ABC

### koru.deployment_events.analyzer.DeploymentEventAnalyzer
> Analyzer for deployment event history with reflection capabilities.
- **Methods**: 12
- **Key Methods**: koru.deployment_events.analyzer.DeploymentEventAnalyzer.__init__, koru.deployment_events.analyzer.DeploymentEventAnalyzer.add_events, koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_type, koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_source, koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_correlation, koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_time_range, koru.deployment_events.analyzer.DeploymentEventAnalyzer.get_errors, koru.deployment_events.analyzer.DeploymentEventAnalyzer.get_plugin_events, koru.deployment_events.analyzer.DeploymentEventAnalyzer.get_deployment_summary, koru.deployment_events.analyzer.DeploymentEventAnalyzer.analyze_deployment_flow

### src.korullm.strategies.base.LlmStrategy
> Per-LLM knowledge object.
- **Methods**: 12
- **Key Methods**: src.korullm.strategies.base.LlmStrategy.id, src.korullm.strategies.base.LlmStrategy.label, src.korullm.strategies.base.LlmStrategy.matches_environment, src.korullm.strategies.base.LlmStrategy.capabilities, src.korullm.strategies.base.LlmStrategy.assess_drive_failure, src.korullm.strategies.base.LlmStrategy.idle_marker_patterns, src.korullm.strategies.base.LlmStrategy.prompt_envelope, src.korullm.strategies.base.LlmStrategy._reply_message, src.korullm.strategies.base.LlmStrategy._reply_verification, src.korullm.strategies.base.LlmStrategy._reply_reason
- **Inherits**: ABC

### src.koru.deployment_events.analyzer.DeploymentEventAnalyzer
> Analyzer for deployment event history with reflection capabilities.
- **Methods**: 12
- **Key Methods**: src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.__init__, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.add_events, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_type, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_source, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_correlation, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.filter_by_time_range, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.get_errors, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.get_plugin_events, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.get_deployment_summary, src.koru.deployment_events.analyzer.DeploymentEventAnalyzer.analyze_deployment_flow

### koruide.ides.cursor.CursorStrategy
> Strategy for Cursor (VS Code-fork by Anysphere).
- **Methods**: 11
- **Key Methods**: koruide.ides.cursor.CursorStrategy.id, koruide.ides.cursor.CursorStrategy.label, koruide.ides.cursor.CursorStrategy.config_folder_name, koruide.ides.cursor.CursorStrategy.workspace_settings_folder_name, koruide.ides.cursor.CursorStrategy.detection, koruide.ides.cursor.CursorStrategy.terminal, koruide.ides.cursor.CursorStrategy.aliases, koruide.ides.cursor.CursorStrategy.extensions_metadata_path, koruide.ides.cursor.CursorStrategy.plugin, koruide.ides.cursor.CursorStrategy.editor_cli_candidates
- **Inherits**: VscodeFamilyStrategy

### src.koruide.ides.cursor.CursorStrategy
> Strategy for Cursor (VS Code-fork by Anysphere).
- **Methods**: 11
- **Key Methods**: src.koruide.ides.cursor.CursorStrategy.id, src.koruide.ides.cursor.CursorStrategy.label, src.koruide.ides.cursor.CursorStrategy.config_folder_name, src.koruide.ides.cursor.CursorStrategy.workspace_settings_folder_name, src.koruide.ides.cursor.CursorStrategy.detection, src.koruide.ides.cursor.CursorStrategy.terminal, src.koruide.ides.cursor.CursorStrategy.aliases, src.koruide.ides.cursor.CursorStrategy.extensions_metadata_path, src.koruide.ides.cursor.CursorStrategy.plugin, src.koruide.ides.cursor.CursorStrategy.editor_cli_candidates
- **Inherits**: VscodeFamilyStrategy

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

### koruide.ide._ide_id_from_process
> Map a single process to a known IDE id, if any.
- **Output to**: koruide.ide._read_comm, koruide.ide._read_cmdline, _IDE_SIGNATURES.items, koruide.ide._matches

### koruide.audit._JSONFormatter.format
- **Output to**: record.getMessage

### koruide.audit._isoformat_utc
- **Output to**: int, int, time.gmtime, time.time, time.strftime

### koru.agent_backends._parse_lane
- **Output to**: raw.get, raw.get, raw.get, raw.get, raw.get

### koru.agent_backends.validate_agent_integration_config
> Return human-readable validation errors (empty list when OK).
- **Output to**: config.lanes.items, errors.append, koru.agent_backends.get_agent_backend_profile, errors.append

### koru.autonomous_processes._process_cwd
- **Output to**: proc_cwd.resolve, Path, str

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `src.koru.autonomy.config.AutonomyConfig.from_env` - 50 calls
- `koru.context_render.render_markdown_handoff` - 47 calls
- `src.koru.context_render.render_markdown_handoff` - 47 calls
- `koru.ide_doctor_cli.build_parser` - 44 calls
- `src.koru.ide_doctor_cli.build_parser` - 44 calls
- `koru.policy.load_policy` - 43 calls
- `src.koru.policy.load_policy` - 43 calls
- `src.koru.git_cli.build_parser` - 39 calls
- `koru.queue.runners.run_api_request` - 39 calls
- `src.koru.queue.runners.run_api_request` - 39 calls
- `koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `src.koru.local_manager_state.WorkerRegistry.register` - 37 calls
- `koru.autopilot.cli_trace.action_trace` - 36 calls
- `src.koru.autopilot.cli_trace.action_trace` - 36 calls
- `koru.autopilot.commands.drive.action_drive` - 35 calls
- `src.koru.autopilot.commands.drive.action_drive` - 35 calls
- `koruide.command_scenario.validate_ide_command_scenario` - 34 calls
- `src.koruide.command_scenario.validate_ide_command_scenario` - 34 calls
- `koru.cli_topology.topology_main` - 33 calls
- `src.koru.cli_topology.topology_main` - 33 calls
- `koruobserve.lifecycle.observe_up` - 32 calls
- `koruide.daemon.handlers_drive.handle_drive` - 32 calls
- `src.koruobserve.lifecycle.observe_up` - 32 calls
- `src.koruide.daemon.handlers_drive.handle_drive` - 32 calls
- `koruapi.mcp_server.tool_run_ticket` - 31 calls
- `src.koruapi.mcp_server.tool_run_ticket` - 31 calls
- `koru.autonomy.phases.scan_phase.handle_scan_after_idle` - 30 calls
- `koru.deployment_events.models.DeploymentEvent.from_dict` - 30 calls
- `src.koru.autonomy.phases.scan_phase.handle_scan_after_idle` - 30 calls
- `src.koru.deployment_events.models.DeploymentEvent.from_dict` - 30 calls
- `koru.ide_client.LegacyAutopilotClientAdapter.drive` - 29 calls
- `koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `koru.ide_adapters.bridge.evaluate_bridge` - 29 calls
- `koru.observability_dsl.parse_observability_dsl` - 29 calls
- `src.koru.autonomy.env.autonomous_environ_doctor_probe` - 29 calls
- `src.koru.ide_adapters.bridge.evaluate_bridge` - 29 calls
- `src.koru.observability_dsl.parse_observability_dsl` - 29 calls
- `koru.control_commands.control_command_replay_plan` - 28 calls
- `koru.cli_queue.render_clean_report_text` - 28 calls

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