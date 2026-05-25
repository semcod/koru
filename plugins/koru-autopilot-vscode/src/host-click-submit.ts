export type ScreenPoint = { x: number; y: number };
export type WindowGeometry = { x: number; y: number; width: number; height: number };

export function parseXdotoolGeometryShell(text: string): WindowGeometry | null {
  const values: Record<string, number> = {};
  for (const rawLine of text.split(/\r?\n/)) {
    const match = rawLine.match(/^([A-Z]+)=(-?\d+)$/);
    if (!match) {
      continue;
    }
    values[match[1]] = Number.parseInt(match[2], 10);
  }
  const x = values.X;
  const y = values.Y;
  const width = values.WIDTH;
  const height = values.HEIGHT;
  if (![x, y, width, height].every((value) => Number.isFinite(value))) {
    return null;
  }
  if (width < 160 || height < 160) {
    return null;
  }
  return { x, y, width, height };
}

export function bottomRightSubmitPoint(
  geometry: WindowGeometry,
  insetX = 42,
  insetY = 52
): ScreenPoint {
  return {
    x: Math.max(geometry.x + 1, geometry.x + geometry.width - insetX),
    y: Math.max(geometry.y + 1, geometry.y + geometry.height - insetY),
  };
}
