import * as os from "os";
import * as path from "path";

import type { SupportedIde } from "./chat-history-types";

/** Return the per-IDE ``User`` base directory (parent of ``globalStorage``). */
export function ideUserDir(ide: SupportedIde): string {
  const home = os.homedir();
  const folderByIde: Record<SupportedIde, string> = {
    cursor: "Cursor",
    vscode: "Code",
    vscodium: "VSCodium",
    windsurf: "Windsurf",
    antigravity: "Antigravity",
  };
  const name = folderByIde[ide];
  if (process.platform === "darwin") {
    return path.join(home, "Library", "Application Support", name, "User");
  }
  if (process.platform === "win32") {
    const appdata = process.env.APPDATA || path.join(home, "AppData", "Roaming");
    return path.join(appdata, name, "User");
  }
  return path.join(home, ".config", name, "User");
}

export function defaultGlobalStateDbPath(ide: SupportedIde): string {
  return path.join(ideUserDir(ide), "globalStorage", "state.vscdb");
}