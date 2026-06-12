#!/usr/bin/env bash
# Probe OpenRouter vision chat detection on the latest jetbrains capture.
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true

if [[ -f .env && -z "${OPENROUTER_API_KEY:-}" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${OPENROUTER_API_KEY:?Set OPENROUTER_API_KEY (or add to koru/.env)}"

export VDISPLAY_VISION_CHAT_DETECT="${VDISPLAY_VISION_CHAT_DETECT:-1}"
export VDISPLAY_VISION_LLM_ENABLED="${VDISPLAY_VISION_LLM_ENABLED:-1}"
export VDISPLAY_VISION_LLM_MODE="${VDISPLAY_VISION_LLM_MODE:-both}"
# OpenRouter vision model (override if needed):
export VDISPLAY_VISION_LLM="${VDISPLAY_VISION_LLM:-google/gemini-3.1-flash-image-preview}"

exec koru autopilot diagnose-vdisplay --ide "${1:-jetbrains}"
