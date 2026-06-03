function normalizeBubbleText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}


export function cursorBubbleTextMatchesPrompt(
  bubbleText: string,
  originalText: string,
): { matched: boolean; mode: "tail" | "head" | "middle" | "none" } {
  const bubble = normalizeBubbleText(bubbleText);
  const prompt = normalizeBubbleText(originalText);
  if (!bubble || !prompt) {
    return { matched: false, mode: "none" };
  }

  const tail = prompt.slice(-40);
  if (tail.length >= 16 && bubble.includes(tail)) {
    return { matched: true, mode: "tail" };
  }

  const head = prompt.slice(0, 80);
  if (head.length >= 24 && bubble.includes(head)) {
    return { matched: true, mode: "head" };
  }

  if (prompt.length >= 120) {
    const midStart = Math.floor((prompt.length - 40) / 2);
    const middle = prompt.slice(midStart, midStart + 40);
    if (middle.length >= 16 && bubble.includes(middle)) {
      return { matched: true, mode: "middle" };
    }
  }

  return { matched: false, mode: "none" };
}
