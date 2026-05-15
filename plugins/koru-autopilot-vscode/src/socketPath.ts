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
  if (ov) {
    push(ov);
    return out;
  }

  const explicit = (process.env.KORU_AUTOPILOT_SOCKET || "").trim();
  if (explicit) {
    push(explicit);
    return out;
  }

  // Try only this editor's lane plus the singleton socket. Falling through to
  // other IDE sockets can attach a VS Code window to a stale Windsurf daemon.
  const xdg = process.env.XDG_RUNTIME_DIR;
  if (xdg) {
    push(path.join(xdg, `koru-autopilot-${ideId}.sock`));
    push(path.join(xdg, "koru-autopilot.sock"));
  } else {
    const uid = (process.getuid?.() ?? 0).toString();
    push(`/tmp/koru-autopilot-${ideId}-${uid}.sock`);
    push(`/tmp/koru-autopilot-${uid}.sock`);
  }
  return out;
}
