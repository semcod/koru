ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

ARG SYSTEM_ID=unknown
ENV KORU_MATRIX_SYSTEM=${SYSTEM_ID}
ENV VIRTUAL_ENV=/opt/koru-venv
ENV PATH="/opt/koru-venv/bin:/usr/local/bin:${PATH}"
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            bash ca-certificates curl git jq python3 python3-pip python3-venv; \
        rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
        apk add --no-cache bash ca-certificates curl git jq python3 py3-pip; \
    elif command -v dnf >/dev/null 2>&1; then \
        dnf install -y bash ca-certificates curl git jq python3 python3-pip; \
        dnf clean all; \
    else \
        echo "unsupported base image: no apt-get/apk/dnf" >&2; \
        exit 1; \
    fi; \
    python3 -m venv /opt/koru-venv; \
    python -m pip install --upgrade pip setuptools wheel

COPY pyproject.toml README.md LICENSE VERSION ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY plugins/koru-autopilot-vscode/package*.json ./plugins/koru-autopilot-vscode/
COPY plugins/koru-autopilot-vscode/src/ ./plugins/koru-autopilot-vscode/src/
COPY scripts/docker-ide-matrix-entrypoint.sh ./scripts/docker-ide-matrix-entrypoint.sh
COPY .github/workflows/native-ide-matrix.yml ./.github/workflows/native-ide-matrix.yml
COPY scripts/docker-ide-matrix-entrypoint.sh /usr/local/bin/koru-docker-ide-matrix-entrypoint.sh

RUN set -eux; \
    python -m pip install -e . pytest; \
    chmod +x /usr/local/bin/koru-docker-ide-matrix-entrypoint.sh; \
    for tool in wtype xdotool ydotool; do \
        printf '#!/bin/sh\nexit 0\n' > "/usr/local/bin/${tool}"; \
        chmod +x "/usr/local/bin/${tool}"; \
    done; \
    for tool in wl-copy wl-paste xclip xsel; do \
        printf '%s\n' '#!/bin/sh' \
            'case "${0##*/}" in' \
            '  wl-paste|xclip|xsel) printf "%s" "${KORU_FAKE_HOST_CLIPBOARD:-previous-user-clipboard}" ;;' \
            '  *) cat >/dev/null ;;' \
            'esac' \
            'exit 0' > "/usr/local/bin/${tool}"; \
        chmod +x "/usr/local/bin/${tool}"; \
    done; \
    for tool in code code-insiders code-oss codium vscodium cursor windsurf zed pycharm idea; do \
        printf '%s\n' '#!/bin/sh' \
            'case " $* " in' \
            '  *" --list-extensions --show-versions "*) echo "semcod.koru-autopilot-vscode@${KORU_FAKE_EXTENSION_VERSION:-0.0.0}" ;;' \
            '  *" --list-extensions "*) echo "semcod.koru-autopilot-vscode" ;;' \
            '  *) echo "fake-${0##*/}" ;;' \
            'esac' \
            'exit 0' > "/usr/local/bin/${tool}"; \
        chmod +x "/usr/local/bin/${tool}"; \
    done

ENTRYPOINT ["koru-docker-ide-matrix-entrypoint.sh"]
