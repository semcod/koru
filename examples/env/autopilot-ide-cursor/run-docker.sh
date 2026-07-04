#!/usr/bin/env bash
# Build and run the isolated Docker smoke for this example only.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
docker compose -f "$HERE/docker-compose.yml" build
docker compose -f "$HERE/docker-compose.yml" run --rm e2e
