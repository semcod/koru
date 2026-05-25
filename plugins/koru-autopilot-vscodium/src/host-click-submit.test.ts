import {
  bottomRightSubmitPoint,
  parseXdotoolGeometryShell,
} from "./host-click-submit";

function assert(cond: boolean, msg: string): void {
  if (!cond) {
    throw new Error(msg);
  }
}

function testParseXdotoolGeometryShell(): void {
  const geometry = parseXdotoolGeometryShell(
    "WINDOW=123\nX=10\nY=20\nWIDTH=1000\nHEIGHT=700\nSCREEN=0\n"
  );
  if (geometry === null) {
    throw new Error("geometry should parse");
  }
  assert(geometry.x === 10, "x");
  assert(geometry.y === 20, "y");
  assert(geometry.width === 1000, "width");
  assert(geometry.height === 700, "height");
}

function testRejectsTinyOrIncompleteGeometry(): void {
  assert(parseXdotoolGeometryShell("X=0\nY=0\nWIDTH=20\nHEIGHT=20\n") === null, "tiny");
  assert(parseXdotoolGeometryShell("X=0\nWIDTH=900\nHEIGHT=600\n") === null, "missing y");
}

function testBottomRightSubmitPoint(): void {
  const point = bottomRightSubmitPoint({ x: 10, y: 20, width: 1000, height: 700 });
  assert(point.x === 968, `x=${point.x}`);
  assert(point.y === 668, `y=${point.y}`);
}

testParseXdotoolGeometryShell();
testRejectsTinyOrIncompleteGeometry();
testBottomRightSubmitPoint();
console.log("host-click-submit tests: ok");
