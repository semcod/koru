export interface BridgeHandle {
  connect(): void;
  disconnect(): void;
  sendManualChat(text: string): Promise<void>;
  openChatFromCommand(): Promise<void>;
  calibrateProbe(): Promise<void>;
  captureSubmitClickPosition(): Promise<void>;
}
