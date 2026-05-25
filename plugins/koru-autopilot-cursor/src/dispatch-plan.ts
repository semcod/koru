export interface EnvelopeLike {
  type: string;
}

export type DispatchPlan =
  | { kind: "injectChat" }
  | { kind: "ack"; info: Record<string, unknown> }
  | { kind: "ignore" }
  | { kind: "ackAndDisconnect"; info: Record<string, unknown> }
  | { kind: "error"; message: string };

export function planDispatch(env: EnvelopeLike): DispatchPlan {
  switch (env.type) {
    case "chat.send":
      return { kind: "injectChat" };
    case "ping":
      return { kind: "ack", info: { pong: true } };
    case "ack":
    case "error":
      return { kind: "ignore" };
    case "shutdown":
      return { kind: "ackAndDisconnect", info: { shutdown: true } };
    default:
      return { kind: "error", message: `unhandled ${env.type}` };
  }
}
