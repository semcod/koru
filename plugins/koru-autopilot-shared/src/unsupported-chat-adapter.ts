import type { ChatHistoryRow, IdeAdapter, SupportedIde } from "./chat-history-types";

export class UnsupportedAdapter implements IdeAdapter {
  readonly ide: SupportedIde;
  readonly description: string;

  constructor(ide: SupportedIde, description: string) {
    this.ide = ide;
    this.description = description;
  }

  storeAvailable(): boolean {
    return false;
  }

  async fetchNewer(): Promise<ChatHistoryRow[]> {
    return [];
  }
}