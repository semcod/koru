import * as vscode from "vscode";

import type { BridgeHandle } from "./autopilot-bridge";

export interface WireBridgeCommandsOptions {
	includeOpenChatCommand?: boolean;
	safeRegisterCommands?: boolean;
	onRegisterCommandError?: (command: string, message: string) => void;
}

function maybeAutoConnect(bridge: BridgeHandle): void {
	const cfg = vscode.workspace.getConfiguration("koruAutopilot");
	if (cfg.get<boolean>("autoConnect", true)) bridge.connect();
}

function registerBridgeCommand(
	context: vscode.ExtensionContext,
	command: string,
	callback: (...args: unknown[]) => unknown,
	options: WireBridgeCommandsOptions,
): void {
	if (!options.safeRegisterCommands) {
		context.subscriptions.push(vscode.commands.registerCommand(command, callback));
		return;
	}
	try {
		context.subscriptions.push(vscode.commands.registerCommand(command, callback));
	} catch (err) {
		const message = err instanceof Error ? err.message : String(err);
		options.onRegisterCommandError?.(command, message);
	}
}

export function wireBridgeCommands(
	context: vscode.ExtensionContext,
	bridge: BridgeHandle,
	options: WireBridgeCommandsOptions = {},
): void {
	registerBridgeCommand(context, "koruAutopilot.connect", () => bridge.connect(), options);
	if (options.includeOpenChatCommand) {
		registerBridgeCommand(context, "koruAutopilot.openChat", () => bridge.openChatFromCommand(), options);
	}
	registerBridgeCommand(context, "koruAutopilot.sendChat", async () => {
		const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
		if (text) await bridge.sendManualChat(text);
	}, options);
	registerBridgeCommand(context, "koruAutopilot.calibrateProbe", () => bridge.calibrateProbe(), options);
	registerBridgeCommand(context, "koruAutopilot.calibrate", () => bridge.calibrateProbe(), options);
	registerBridgeCommand(context, "koruAutopilot.calibrateCompact", () => bridge.calibrateProbe(), options);
	registerBridgeCommand(context, "koruAutopilot.captureSubmitClick", () => bridge.captureSubmitClickPosition(), options);

	context.subscriptions.push(
		vscode.workspace.onDidChangeConfiguration((event) => {
			if (
				event.affectsConfiguration("koruAutopilot.socketPath") ||
				event.affectsConfiguration("koruAutopilot.autoConnect")
			) {
				maybeAutoConnect(bridge);
			}
		}),
	);

	maybeAutoConnect(bridge);
}
