export function chatFocusOperatorHint(ide: string): string {
  const label = ide || "IDE";
  return (
    `Operator: open the ${label} chat panel, click inside the chat input `
    + "(blinking text cursor — not the file editor or terminal), then retry."
  );
}

export function pasteProbeOperatorHint(ide: string): string {
  return (
    `${chatFocusOperatorHint(ide)} `
    + "Clipboard input probes fail when the chat webview is not focused."
  );
}

export function manualSendOperatorHint(ide: string): string {
  const label = ide || "IDE";
  return (
    `Operator: in ${label}, click the chat input and press Enter/Send to submit `
    + "the pending prompt manually."
  );
}
