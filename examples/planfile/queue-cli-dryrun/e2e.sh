#!/bin/bash
# Planfile queue: koru root-mode CLI only (no separate HTTP server).
set -euo pipefail

koru --help >/dev/null

demo="$(mktemp -d)"
trap 'rm -rf "$demo"' EXIT
cd "$demo"
git init -q
koru --init --project . --agent-lane none
koru --doctor --project .

koru --project . --queue --dry-run
planfile --version
