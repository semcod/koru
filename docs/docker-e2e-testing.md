# Docker & E2E testing for koru

How containerized tests are organized, how to run them, what they install,
and what they **do not** cover (including noVNC / full desktop GUI).

## TL;DR

| Layer | What it validates | Real tools? | How to run |
| ----- | ----------------- | ----------- | ---------- |
| Unit / critical | Core Python logic | Host venv | `task test:fast` / `scripts/koru-pytest.sh --critical` |
| Shell queue e2e | `koru --queue` ↔ planfile | planfile on PATH | `task test:e2e` / `bash tests/e2e/smoke.sh` |
| Docker image e2e | Image builds; `koru --help` / `--doctor` in container | Minimal pip toolchain | `task test:docker` |
| Docker IDE matrix | OS × IDE **smoke** (drive dry-run, fake plugins) | **Stubs** for IDE/input | `task test:docker:ide-matrix` |
| Capture smoke | headless + Xvfb screenshot path | mss/scrot/Xvfb | `docker/capture/run.sh` |
| Examples Docker | Nested scenarios under `examples/**/run-docker.sh` | Per-example `EXTRA_PIP` | `bash examples/run-e2e.sh` |
| **noVNC lab** | Browser XFCE desktop + koru mount | xdotool, optional koru extras | `docker compose -f docker/novnc/docker-compose.yml up` |

Default `pytest` **deselects** slow Docker tests (`addopts` / markers).
Docker suites must be requested explicitly.

## Inventory

### 1. Shell e2e (`tests/e2e/`)

Documents: [`tests/e2e/README.md`](../tests/e2e/README.md).

```bash
# planfile must be installed (floor: >=0.1.100, same as pyproject extras)
pip install -e ".[planfile,dev]"
# or: task install:tools

task test:e2e            # smoke queue lifecycle
task test:e2e:bootstrap  # flat pipeline bootstrap
task test:e2e:all
# or:
bash tests/e2e/smoke.sh
bash tests/e2e/bootstrap.sh
bash tests/e2e/init.sh
```

**Installs / requires:** `planfile` CLI, `python3`, `git`. Does **not** install
IDEs, vdisplay, playwright, regix, etc.

### 2. Docker image + compose (`tests/test_docker_e2e.py`)

```bash
task test:docker
# equivalent:
scripts/koru-pytest.sh --serial tests/test_docker_e2e.py -v -m ""
```

Uses root [`Dockerfile`](../Dockerfile) (multi-stage: `base` / `development` /
`test` / `production`) and [`docker-compose.yml`](../docker-compose.yml)
profiles `test` / `dev` / `deps`.

**What the image installs (production stage):**

- System: `git`, `curl`, `docker.io`, `jq`
- Python: `pip install -e ".[planfile,api,desktop]"` plus aligned toolchain pins
  (see Dockerfile)
- Entry: `koru` CLI

**What it does *not* install by default:** real IDE binaries, noVNC, vdisplay
agent stack, playwright browsers, JetBrains, ydotool device access, full
semcod gate suite (`regix`/`vallm` optional via deps profile images).

Compose `deps` profile expects external images (`semcod/planfile`,
`semcod/regix`, `semcod/testql`) which may be private — tests skip if pull
fails.

### 3. Docker OS × IDE matrix (`scripts/docker-ide-matrix.sh`)

```bash
task test:docker:ide-matrix
# subset:
KORU_DOCKER_SYSTEMS=debian-slim KORU_DOCKER_IDES=vscode,cursor \
  bash scripts/docker-ide-matrix.sh
```

- Image: [`tests/docker/ide-matrix.Dockerfile`](../tests/docker/ide-matrix.Dockerfile)
- Entrypoint: [`scripts/docker-ide-matrix-entrypoint.sh`](../scripts/docker-ide-matrix-entrypoint.sh)

**Inside the matrix image:**

| Component | Reality |
| --------- | ------- |
| `pip install -e .` + pytest | Real koru source |
| `code` / `cursor` / `windsurf` / `pycharm` / … | **Fake shell stubs** that print fake extension lists |
| `wtype` / `xdotool` / `ydotool` | **Fake stubs** (`exit 0`) |
| `wl-copy` / `xclip` | Fake clipboard |
| Autopilot drive | `--direct --dry-run` only |

This validates **lane routing and CLI contracts** across base OS images, not
real IDE plugins or host input injection.

### 4. Capture smoke (Xvfb, not noVNC)

```bash
docker/capture/run.sh           # headless + x11 targets
docker/capture/run.sh x11
```

- Dockerfile: [`docker/capture/Dockerfile`](../docker/capture/Dockerfile)
- X11 target runs **Xvfb** + `scrot` + `mss` — useful for `koruvision` capture
  providers.
- Explicitly **out of scope:** Wayland-in-Docker / cage / grim / **noVNC**.

Pytest: `tests/test_docker_capture.py` (when present) wraps the same idea.

### 5. Examples E2E (`examples/**/run-docker.sh`)

```bash
bash examples/run-e2e.sh
# single example:
cd examples/ci/headless-autonomous-jsonl && ./run-docker.sh
```

Image helper: [`examples/docker/koru-e2e.Dockerfile`](../examples/docker/koru-e2e.Dockerfile)

- Base: `pip install -e .` + `planfile`, `uvicorn`, `fastapi`, `wup`
- `ARG EXTRA_PIP=...` per example (e.g. `nlp2uri`, `testql`)
- Not a full “every koru tool” image

### 6. Headless CI style

See GitHub workflows under `.github/workflows/` (native IDE matrix, etc.) and
`examples/ci/`. These are mostly **headless JSONL / autonomous** paths, not
graphical desktops.

## Dependency floors (keep Dockerfiles in sync)

Canonical floors live in [`pyproject.toml`](../pyproject.toml):

| Package | Floor (extras / notes) |
| ------- | ---------------------- |
| Python | `>=3.12,<3.14` |
| planfile | `>=0.1.100` (`[planfile]`, `[desktop]`, uv `dev` group) |
| testql | `>=1.2.55` |
| tillm | `>=0.1.35` (core) |
| gillm | `>=0.1.9` (core) |
| vdisplay | `>=0.1.54` (public screen-truth helpers) |
| nlp2uri | `>=0.4.7` |
| env2llm | `>=0.1.10` |
| playwright | `>=1.40` via `[browser]` only |

Full toolchain (optional on host):

```bash
task install:tools
# planfile wup testql regix redup vallm … (see Taskfile install:tools)
```

**Local venv audit (example):** after `uv sync` / `pip install -e ".[dev]"`,
expect `planfile`, `vdisplay`, `tillm`, `gillm` present. Optional gates
(`regix`, `redup`, `vallm`, `wup`, `playwright`, `mss`) may be missing until
`task install:tools` or the matching extra is installed — that is expected,
not a silent core failure.

## Gaps & honest limits

### noVNC

**Minimal lab (new):** [`docker/novnc/`](../docker/novnc/) — XFCE + TigerVNC +
noVNC, browser on port **6080**, bind-mounts the repo for editable koru install.

```bash
docker compose -f docker/novnc/docker-compose.yml up --build -d
# http://127.0.0.1:6080/vnc.html?autoconnect=true
docker exec -it koru-novnc bash /home/koru/smoke-desktop.sh
```

This is an **X11 smoke lab**, not a full Wayland/JetBrains photo-VQL substitute.
Real desktop drive: host + vdisplay ([`photo-vql-jetbrains-wayland.md`](./photo-vql-jetbrains-wayland.md)).

Related elsewhere in the monorepo:

- `semcod/nlp2cmd` — fuller noVNC demos
- `semcod/proxym` — VM console noVNC docs

### “Every tool koru might use”

Koru orchestrates many optional tools. **No single Docker image installs all of
them.** Closest options:

| Goal | Install |
| ---- | ------- |
| Queue + planfile | `koru[planfile]` |
| Desktop / envmap | `koru[desktop]` |
| Browser TestQL | `koru[browser]` + `playwright install chromium` |
| Photo-VQL | `koru[vdisplay]` (+ Pillow/pytesseract as in uv `dev`) |
| Quality gates | `task install:tools` (regix, redup, vallm, …) |
| IDE matrix CI | fake stubs only |

### What works today

| Suite | Expected status |
| ----- | --------------- |
| Critical unit tests | Green on host (`task test:fast`) |
| Shell e2e | Green if planfile ≥ 0.1.100 on PATH |
| Docker e2e | Needs Docker daemon; slow; may skip private images |
| IDE matrix | Green with stubs; **not** real IDE proof |
| Capture X11 | Green with Docker + Xvfb target |
| noVNC GUI e2e | **Absent** |

## Recommended local checklist

```bash
# 1. Core correctness
pip install -e ".[dev,planfile,vdisplay]"
task test:fast

# 2. Queue e2e
bash tests/e2e/smoke.sh

# 3. Container image contract
task test:docker

# 4. Cross-OS IDE routing smoke (optional, heavy)
KORU_DOCKER_SYSTEMS=debian-slim KORU_DOCKER_IDES=vscode bash scripts/docker-ide-matrix.sh

# 5. Capture providers (optional)
docker/capture/run.sh headless
```

## Related docs

- [`docs/pipeline-design.md`](./pipeline-design.md) — product pipeline stages
- [`docs/photo-vql-jetbrains-wayland.md`](./photo-vql-jetbrains-wayland.md) — real desktop drive
- [`docs/autopilot-quickstart.md`](./autopilot-quickstart.md) — host autopilot
- [`tests/e2e/README.md`](../tests/e2e/README.md) — shell queue e2e
- [`examples/README.md`](../examples/README.md) — example scenarios
