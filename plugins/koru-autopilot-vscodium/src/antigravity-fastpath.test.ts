import {
  ANTIGRAVITY_SEND_PROMPT_COMMAND,
  canUseAntigravitySendPrompt,
  selectAntigravityOpenCommand,
} from "./antigravity-fastpath";

function assert(condition: unknown, message: string): void {
  if (!condition) {
    throw new Error(`antigravity-fastpath test failed: ${message}`);
  }
}

function testSelectAntigravityOpenCommandPrefersNativeOpenOrder(): void {
  const existing = new Set<string>([
    "antigravity.agentSidePanel.focus",
    "antigravity.agentSidePanel.open",
    "antigravity.openAgent",
  ]);
  const cmd = selectAntigravityOpenCommand(existing);
  assert(cmd === "antigravity.openAgent", "should prefer antigravity.openAgent when available");
}

function testSelectAntigravityOpenCommandReturnsNoneWhenMissing(): void {
  const existing = new Set<string>(["workbench.action.chat.focusInput"]);
  const cmd = selectAntigravityOpenCommand(existing);
  assert(cmd === "none", "should return none when no Antigravity open command is present");
}

function testCanUseAntigravitySendPromptAfterRefresh(): void {
  const beforeOpen = new Set<string>(["antigravity.openAgent"]);
  const afterOpen = new Set<string>(["antigravity.openAgent", ANTIGRAVITY_SEND_PROMPT_COMMAND]);
  assert(!canUseAntigravitySendPrompt(beforeOpen), "send command may be unavailable before panel open");
  assert(canUseAntigravitySendPrompt(afterOpen), "send command should be accepted after command registry refresh");
}

testSelectAntigravityOpenCommandPrefersNativeOpenOrder();
testSelectAntigravityOpenCommandReturnsNoneWhenMissing();
testCanUseAntigravitySendPromptAfterRefresh();
console.log("antigravity-fastpath tests: ok");
