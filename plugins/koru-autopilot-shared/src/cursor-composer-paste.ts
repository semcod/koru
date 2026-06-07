export const CURSOR_COMPOSER_PROMPT_PASTE_COMMANDS = [
  "composer.startComposerPrompt2",
  "composer.startComposerPrompt",
] as const;

export const CURSOR_COMPOSER_SAFE_PASTE_COMMANDS = [
  "workbench.action.chat.typeText",
  "workbench.action.chat.insertText",
  "cursor.action.chat.typeText",
] as const;

export function isGlassTypedPasteCommand(command: string): boolean {
  return /(?:type|insert)text/i.test(command);
}

export function resolveCursorComposerPasteCandidates(existing: Set<string>): {
  glassUi: boolean;
  promptPastes: string[];
  safePastes: string[];
} {
  const glassUi = existing.has("glass.focusInput");
  let promptPastes = CURSOR_COMPOSER_PROMPT_PASTE_COMMANDS.filter((cmd) => existing.has(cmd));
  if (glassUi && promptPastes.length === 0) {
    promptPastes = [...CURSOR_COMPOSER_PROMPT_PASTE_COMMANDS];
  }
  let safePastes = CURSOR_COMPOSER_SAFE_PASTE_COMMANDS.filter((cmd) => existing.has(cmd));
  if (glassUi) {
    safePastes = safePastes.filter((cmd) => !isGlassTypedPasteCommand(cmd));
  }
  return { glassUi, promptPastes, safePastes };
}
