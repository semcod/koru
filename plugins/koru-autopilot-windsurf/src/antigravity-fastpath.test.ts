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
  ]);
  const cmd = selectAntigravityOpenCommand(existing);
  assert(
    cmd === "antigravity.agentSidePanel.focus",
    "should prefer antigravity.agentSidePanel.focus when available"
  );
}

function testSelectAntigravityOpenCommandReturnsNoneWhenMissing(): void {
  const existing = new Set<string>(["workbench.action.chat.focusInput"]);
  const cmd = selectAntigravityOpenCommand(existing);
  assert(cmd === "none", "should return none when no Antigravity open command is present");
}

function testCanUseAntigravitySendPromptAfterRefresh(): void {
  const beforeOpen = new Set<string>(["antigravity.agentSidePanel.focus"]);
  const afterOpen = new Set<string>([ANTIGRAVITY_SEND_PROMPT_COMMAND]);
  assert(!canUseAntigravitySendPrompt(beforeOpen), "send command may be unavailable before panel open");
  assert(canUseAntigravitySendPrompt(afterOpen), "send command should be accepted after command registry refresh");
}

testSelectAntigravityOpenCommandPrefersNativeOpenOrder();
testSelectAntigravityOpenCommandReturnsNoneWhenMissing();
testCanUseAntigravitySendPromptAfterRefresh();
console.log("antigravity-fastpath tests: ok");
