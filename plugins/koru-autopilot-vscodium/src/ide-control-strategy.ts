export type SubmitStrategy =
  | "registered-commands"
  | "vscodium-host-submit"
  | "cursor-host-submit"
  | "native-send-only";

export interface IdeControlStrategy {
  ide: string;
  allowGenericPaste: boolean;
  nativeAtomicSend: boolean;
  submitStrategy: SubmitStrategy;
  verifyPostSubmit: boolean;
}

const DEFAULT_STRATEGY: IdeControlStrategy = {
  ide: "unknown",
  allowGenericPaste: true,
  nativeAtomicSend: false,
  submitStrategy: "registered-commands",
  verifyPostSubmit: true,
};

const STRATEGIES: Record<string, IdeControlStrategy> = {
  cursor: {
    ide: "cursor",
    allowGenericPaste: true,
    nativeAtomicSend: false,
    submitStrategy: "cursor-host-submit",
    verifyPostSubmit: true,
  },
  vscode: {
    ide: "vscode",
    allowGenericPaste: true,
    nativeAtomicSend: false,
    submitStrategy: "registered-commands",
    verifyPostSubmit: true,
  },
  vscodium: {
    ide: "vscodium",
    allowGenericPaste: true,
    nativeAtomicSend: false,
    submitStrategy: "vscodium-host-submit",
    verifyPostSubmit: true,
  },
  windsurf: {
    ide: "windsurf",
    allowGenericPaste: false,
    nativeAtomicSend: true,
    submitStrategy: "native-send-only",
    verifyPostSubmit: false,
  },
  antigravity: {
    ide: "antigravity",
    allowGenericPaste: false,
    nativeAtomicSend: true,
    submitStrategy: "native-send-only",
    verifyPostSubmit: false,
  },
};

export function ideControlStrategy(ide: string | undefined): IdeControlStrategy {
  const key = (ide || "").toLowerCase();
  return STRATEGIES[key] || { ...DEFAULT_STRATEGY, ide: key || "unknown" };
}
