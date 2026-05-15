// Mirrors koru Python ``default_socket_path()`` / ``KORU_AUTOPILOT_*`` env.

import * as os from "os";
import * as path from "path";

function slugInstance(raw: string): string {
  const cleaned = raw
    .slice(0, 64)
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || "instance";
}

export function defaultSocketPathFromEnv(): string {
  const explicit = (process.env.KORU_AUTOPILOT_SOCKET || "").trim();
  if (explicit) return path.resolve(explicit);

  const inst = (process.env.KORU_AUTOPILOT_INSTANCE || "").trim();
  const name = inst ? `koru-autopilot-${slugInstance(inst)}.sock` : "koru-autopilot.sock";
  const xdg = process.env.XDG_RUNTIME_DIR;
  if (xdg) return path.join(xdg, name);

  const uid = (process.getuid?.() ?? 0).toString();
  if (name === "koru-autopilot.sock") return `/tmp/koru-autopilot-${uid}.sock`;
  const stem = name.replace(/\.sock$/i, "");
  return `/tmp/${stem}-${uid}.sock`;
}

export function socketCandidatesFromEnv(ideId: string, override?: string): string[] {
  const out: string[] = [];
  const push = (p: string) => {
    const r = path.resolve(p);
    if (!out.includes(r)) out.push(r);
  };

  const ov = (override || "").trim();
  if (ov) push(ov);

  const explicit = (process.env.KORU_AUTOPILOT_SOCKET || "").trim();
  if (explicit) push(explicit);

  // Also try per-IDE instance sockets when env doesn't point there.
  // This matches common autonomous lanes: koru-autopilot-windsurf.sock, etc.
  const xdg = process.env.XDG_RUNTIME_DIR;
  if (xdg) {
    push(path.join(xdg, `koru-autopilot-${ideId}.sock`));
    push(path.join(xdg, "koru-autopilot-windsurf.sock"));
    push(path.join(xdg, "koru-autopilot-vscode.sock"));
    push(path.join(xdg, "koru-autopilot-cursor.sock"));
  } else {
    const uid = (process.getuid?.() ?? 0).toString();
    push(`/tmp/koru-autopilot-${ideId}-${uid}.sock`);
    push(`/tmp/koru-autopilot-windsurf-${uid}.sock`);
    push(`/tmp/koru-autopilot-vscode-${uid}.sock`);
    push(`/tmp/koru-autopilot-cursor-${uid}.sock`);
  }

  // Default "single-instance" socket last. A different project may have a
  // healthy singleton daemon; autonomous lanes should prefer their per-IDE
  // socket when no explicit override/env socket was provided.
  push(defaultSocketPathFromEnv());
  return out;
}
