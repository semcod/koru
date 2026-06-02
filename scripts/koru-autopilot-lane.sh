#!/usr/bin/env bash
set -euo pipefail

if ! command -v koruenv >/dev/null 2>&1; then
	echo "error: koruenv command not found" >&2
	echo "install standalone package first: pip install -e ./packages/koruenv" >&2
	exit 127
fi

exec koruenv "$@"
