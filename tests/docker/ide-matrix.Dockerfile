ARG BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

FROM ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa AS uv
FROM ${BASE_IMAGE}

COPY --from=uv /uv /uvx /bin/

ARG SYSTEM_ID=unknown
ENV KORU_MATRIX_SYSTEM=${SYSTEM_ID}
ENV UV_PROJECT_ENVIRONMENT=/opt/koru-venv \
    UV_PYTHON=python3.12 \
    VIRTUAL_ENV=/opt/koru-venv \
    PATH="/opt/koru-venv/bin:/usr/local/bin:${PATH}" \
    PYTHONPATH=/app/src:/app/packages/coru/src:/app/packages/koruide/src

WORKDIR /app

RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            bash ca-certificates curl git jq; \
        if ! command -v python3.12 >/dev/null 2>&1; then \
            apt-get install -y --no-install-recommends python3 python3-venv; \
        fi; \
        rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
        apk add --no-cache bash ca-certificates curl git jq; \
    elif command -v dnf >/dev/null 2>&1; then \
        dnf install -y bash ca-certificates curl git jq python3.12; \
        dnf clean all; \
    else \
        echo "unsupported base image: no apt-get/apk/dnf" >&2; \
        exit 1; \
    fi; \
    python3.12 --version

COPY pyproject.toml uv.lock README.md LICENSE VERSION ./

RUN uv lock --check --no-sources \
    && uv sync --frozen --no-editable --no-install-project

COPY src/ ./src/
COPY packages/ ./packages/
COPY tests/ ./tests/
COPY plugins/koru-autopilot-vscode/package*.json ./plugins/koru-autopilot-vscode/
COPY plugins/koru-autopilot-vscode/src/ ./plugins/koru-autopilot-vscode/src/
COPY plugins/koru-autopilot-vscodium/package.json ./plugins/koru-autopilot-vscodium/package.json
COPY plugins/koru-autopilot-vscodium/src/ ./plugins/koru-autopilot-vscodium/src/
COPY plugins/koru-autopilot-shared/package.json ./plugins/koru-autopilot-shared/package.json
COPY plugins/koru-autopilot-shared/src/ ./plugins/koru-autopilot-shared/src/
COPY scripts/docker-ide-matrix-entrypoint.sh ./scripts/docker-ide-matrix-entrypoint.sh
COPY .github/workflows/native-ide-matrix.yml ./.github/workflows/native-ide-matrix.yml
COPY scripts/docker-ide-matrix-entrypoint.sh /usr/local/bin/koru-docker-ide-matrix-entrypoint.sh

RUN set -eux; \
    uv sync --frozen --no-editable; \
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

# The matrix is a hermetic runtime smoke, not a Git checkout. Ignore the
# repository-level pytest plugin and skip calibrated desktop profiles so the
# direct dry-run produces a machine-readable payload for the entrypoint check.
ENV PYTEST_ADDOPTS="-c /dev/null" \
    KORU_OS_INJECTOR=0

ENTRYPOINT ["koru-docker-ide-matrix-entrypoint.sh"]
