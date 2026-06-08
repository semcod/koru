#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m grpc_tools.protoc -I "$ROOT/proto" --python_out="$ROOT/src" \
  "$ROOT/proto/dsl2coru/v1/command.proto" \
  "$ROOT/proto/dsl2coru/v1/result.proto"
