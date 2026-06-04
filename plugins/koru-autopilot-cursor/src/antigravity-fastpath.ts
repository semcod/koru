export const ANTIGRAVITY_SEND_PROMPT_COMMAND = "antigravity.sendPromptToAgentPanel";

export const ANTIGRAVITY_OPEN_COMMANDS = [
  "antigravity.agentSidePanel.focus",
];

export function selectAntigravityOpenCommand(existing: Set<string>): string {
  for (const openCmd of ANTIGRAVITY_OPEN_COMMANDS) {
    if (existing.has(openCmd)) {
      return openCmd;
    }
  }
  return "none";
}

export function canUseAntigravitySendPrompt(existing: Set<string>): boolean {
  return existing.has(ANTIGRAVITY_SEND_PROMPT_COMMAND);
}
