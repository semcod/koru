// koru autopilot — shared bridge helpers
//
// IDE-agnostic helper functions for VS Code family plugins.

import { buildSubmitCommands } from "../probe-ladder";

const DISALLOWED_FOCUS_OPEN_COMMANDS = new Set([
  "workbench.action.chat.openagent",
  "workbench.action.chat.openask",
]);

const UNSAFE_VSCODE_FOCUS_OPEN_COMMANDS = new Set([
  "workbench.action.openchat",
  "workbench.action.openquickchat",
  "workbench.action.chat.open",
  "workbench.action.chat.openinnewwindow",
  "workbench.action.chat.opensessioninnewwindow",
  "workbench.action.quickchat.openinchatview",
  "workbench.panel.chat",
  "workbench.panel.chat.view.copilot.focus",
  "workbench.panel.aichat.view.copilot.focus",
]);

export function isAllowedFocusOpenCommand(command: unknown): command is string {
  return (
    typeof command === "string" &&
    command.trim().length > 0 &&
    !DISALLOWED_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase())
  );
}

export function sanitizeFocusOpenCommand(command: unknown): string | undefined {
  if (!isAllowedFocusOpenCommand(command)) {
    return undefined;
  }
  return command.trim();
}

export function sanitizeFocusOpenCandidates(commands: readonly string[]): string[] {
  return commands.filter(isAllowedFocusOpenCommand);
}

export function filterUnsafeFocusOpenForIde(commands: readonly string[], ide: string): string[] {
  if (ide !== "vscode" && ide !== "vscodium") {
    return [...commands];
  }
  return commands.filter((command) => !UNSAFE_VSCODE_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase()));
}

export function isSpecificChatInputFocusCommand(command: string | undefined): boolean {
  if (!command) {
    return false;
  }
  const normalized = command.toLowerCase();
  return normalized.includes("chat") || normalized.includes("composer") || normalized.includes("cascade");
}

const TOGGLING_FOCUS_OPEN_COMMANDS: ReadonlySet<string> = new Set([
  "composer.openaspane",
  "workbench.action.toggleauxiliarybar",
  "workbench.action.togglepanel",
  "workbench.action.togglesidebar",
  "workbench.view.chat.toggle",
]);

export function isTogglingFocusOpenCommand(command: string | undefined): boolean {
  if (!command) {
    return false;
  }
  return TOGGLING_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase());
}

export function isVSCodiumSafeSubmitCommand(command: string): boolean {
  const normalized = command.trim().toLowerCase();
  if (buildSubmitCommands("vscodium").includes(command)) {
    return true;
  }
  return normalized.startsWith("workbench.action.chat.");
}

export function filterVSCodiumSubmitCandidates(commands: string[]): string[] {
  return commands.filter(isVSCodiumSafeSubmitCommand);
}

export function isHostClipboardPasteCommand(command: string | undefined): boolean {
  return Boolean(command && command.includes("host-clipboard"));
}
