# STARTER-558: R-F3.3: Doctor check for duplicate autopilot daemons

model: qwen/qwen3-coder-next

## Prompt

Three koru autopilot daemon processes run from this repo despite --idempotent. Diagnose why idempotency does not reap older daemons and add a doctor/readiness check flagging duplicates per socket/instance.

---
Deliverable: a concrete, ordered action plan with exact shell commands and file paths where applicable, short enough to execute directly. State assumptions explicitly; do not pad.

## Answer

**Assumptions**  
1. `--idempotent` is a custom flag in the koru autopilot daemon (e.g., checks for existing PID or socket).  
2. Daemons are started via a script (e.g., `start.sh`) that *does not* enforce idempotency correctly.  
3. Each daemon binds to a unique socket (e.g., `/run/koru/daemon-<id>.sock`).  
4. No external process manager (e.g., systemd) is managing lifecycle.  
5. `--idempotent` likely checks for *any* running daemon, not *this specific instance*.

---

### **Diagnosis Steps**

1. **Inspect daemon startup script**  
   ```bash
   grep -r "idempotent" . --include="*.sh" --include="*.py" --include="*.go"
   ```
   → Look for logic like `if [ -f /run/koru/daemon.pid ]; then exit 0; fi`.  
   → **Root cause likely**: `--idempotent` checks for *any* daemon PID, not per-socket/per-instance.

2. **Check running processes & sockets**  
   ```bash
   ps aux | grep koru | grep -v grep
   ls -l /run/koru/*.sock 2>/dev/null || echo "No sockets found"
   ss -xlnp | grep koru
   ```
   → If multiple daemons run *and* bind to *different* sockets, `--idempotent` is not instance-aware.

3. **Verify socket binding logic**  
   ```bash
   grep -r "bind.*sock" . --include="*.go" --include="*.py" --include="*.c"
   ```
   → Confirm each daemon binds to a *unique* socket (e.g., `socket_path = f"/run/koru/daemon-{id}.sock"`).

---

### **Fix Plan**

#### **A. Patch `--idempotent` to check *per-socket* existence**
**File**: `src/daemon/main.go` (example; adjust to your language)  
**Change**: Replace global PID check with socket-specific check.

```go
// BEFORE (likely):
if _, err := os.Stat("/run/koru/daemon.pid"); err == nil {
    log.Fatal("Daemon already running (idempotent)")
}

// AFTER:
socketPath := fmt.Sprintf("/run/koru/daemon-%s.sock", instanceID)
if _, err := os.Stat(socketPath); err == nil {
    // Check if socket is *active* (not stale)
    conn, err := net.Dial("unix", socketPath)
    if err == nil {
        conn.Close()
        log.Fatalf("Daemon for instance %s already running", instanceID)
    }
    // Stale socket: remove and proceed
    os.Remove(socketPath)
}
```

#### **B. Ensure socket path is instance-unique**
**File**: `src/daemon/config.go` (or equivalent)  
**Add**:
```go
instanceID := os.Getenv("KORU_INSTANCE_ID") // or parse from --id flag
if instanceID == "" {
    log.Fatal("KORU_INSTANCE_ID must be set")
}
socketPath := fmt.Sprintf("/run/koru/daemon-%s.sock", instanceID)
```

#### **C. Add doctor/readiness check**
**File**: `scripts/doctor.sh` (new file)
```bash
#!/bin/bash
set -e

SOCK_DIR="/run/koru"
DUPLICATES=0

for sock in "$SOCK_DIR"/daemon-*.sock; do
    [ -e "$sock" ] || continue
    # Check if socket is bound by a live process
    if ss -xlnp 2>/dev/null | grep -qF "$sock"; then
        # Count processes bound to this socket
        PIDS=$(ss -xlnp 2>/dev/null | awk -v s="$sock" '$4 == s {print $6}' | tr -d '()' | sort -u)
        if [ $(echo "$PIDS" | wc -l) -gt 1 ]; then
            echo "ERROR: Duplicate daemons on $sock: PIDs $PIDS"
            DUPLICATES=1
        fi
    fi
done

if [ $DUPLICATES -eq 1 ]; then
    echo "DOCTOR: FAIL — duplicate daemons detected"
    exit 1
else
    echo "DOCTOR: PASS — no duplicates"
    exit 0
fi
```

Make executable:
```bash
chmod +x scripts/doctor.sh
```

#### **D. Update startup script to enforce uniqueness**
**File**: `start.sh`  
**Add**:
```bash
#!/bin/bash
set -e

INSTANCE_ID="$1"
[ -z "$INSTANCE_ID" ] && { echo "Usage: $0 <instance_id>"; exit 1; }

export KORU_INSTANCE_ID="$INSTANCE_ID"

# Run doctor check before starting
./scripts/doctor.sh || { echo "Refusing to start: duplicates exist"; exit 1; }

# Start daemon with --idempotent
./bin/koru-daemon --idempotent --socket "/run/koru/daemon-${INSTANCE_ID}.sock"
```

#### **E. Verify fix**
```bash
# Start 3 instances
./start.sh 1 &
./start.sh 2 &
./start.sh 3 &

# Check for duplicates
./scripts/doctor.sh

# Confirm only 3 daemons
ps aux | grep koru | grep -v grep | wc -l
```

---

**Expected outcome**:  
- `--idempotent` now checks *per-socket*, preventing duplicate *per instance*.  
- `doctor.sh` flags duplicates per socket.  
- No stale sockets left behind (cleaned on startup).
