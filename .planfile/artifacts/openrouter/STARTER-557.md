# STARTER-557: R-F3.2: Safety rails for tillm execute_profile=automation

model: qwen/qwen3-coder-next

## Prompt

Autonomous drive defaults KORU_TILLM_EXECUTE_PROFILE=automation letting the vendor CLI edit files. Add per-project consent/dry-run levels and audit logging of executed profiles.

---
Deliverable: a concrete, ordered action plan with exact shell commands and file paths where applicable, short enough to execute directly. State assumptions explicitly; do not pad.

## Answer

**Assumptions**  
1. Project uses a vendor CLI (e.g., `vendor-cli`) that respects `KORU_TILLM_EXECUTE_PROFILE`.  
2. Files are edited in-place by the CLI (e.g., `config.yaml`, `settings.json`).  
3. Audit log is a single file: `/var/log/koru_audit.log`.  
4. Per-project consent/dry-run levels: `none`, `dry-run`, `consent`, `execute`.  
5. Project root = current working directory; config stored in `.koru/config.json`.  

---

### Action Plan

1. **Create project config structure**  
   ```bash
   mkdir -p .koru && echo '{"level": "dry-run"}' > .koru/config.json
   ```

2. **Create wrapper script `koru-run` (in `$PATH`, e.g., `/usr/local/bin/koru-run`)**  
   ```bash
   cat > /usr/local/bin/koru-run << 'EOF'
   #!/bin/bash
   set -euo pipefail

   PROJECT_ROOT="$(pwd)"
   CONFIG_FILE="$PROJECT_ROOT/.koru/config.json"
   AUDIT_LOG="/var/log/koru_audit.log"

   # Read consent/dry-run level (default: dry-run)
   LEVEL=$(jq -r '.level // "dry-run"' "$CONFIG_FILE" 2>/dev/null || echo "dry-run")

   # Validate level
   case "$LEVEL" in
     none|dry-run|consent|execute) ;;
     *) echo "ERROR: Invalid level '$LEVEL' in $CONFIG_FILE"; exit 1 ;;
   esac

   # Prompt for consent if level=consent
   if [[ "$LEVEL" == "consent" ]]; then
     echo "Profile '$KORU_TILLM_EXECUTE_PROFILE' will be executed. Proceed? [y/N]"
     read -r ans
     [[ "$ans" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
   fi

   # Dry-run: simulate only
   if [[ "$LEVEL" == "dry-run" ]]; then
     echo "[AUDIT] $(date -Iseconds) DRY-RUN profile=$KORU_TILLM_EXECUTE_PROFILE dir=$PROJECT_ROOT" >> "$AUDIT_LOG"
     echo "DRY-RUN: Would run: vendor-cli --profile $KORU_TILLM_EXECUTE_PROFILE"
     exit 0
   fi

   # Execute (level=execute or none)
   if [[ "$LEVEL" == "execute" || "$LEVEL" == "none" ]]; then
     echo "[AUDIT] $(date -Iseconds) EXECUTE profile=$KORU_TILLM_EXECUTE_PROFILE dir=$PROJECT_ROOT" >> "$AUDIT_LOG"
     exec vendor-cli --profile "$KORU_TILLM_EXECUTE_PROFILE"
   fi
   EOF
   chmod +x /usr/local/bin/koru-run
   ```

3. **Set environment variable (e.g., in `.envrc` or shell profile)**  
   ```bash
   echo 'export KORU_TILLM_EXECUTE_PROFILE=automation' >> ~/.bashrc
   ```

4. **Verify audit log permissions**  
   ```bash
   sudo touch /var/log/koru_audit.log && sudo chmod 644 /var/log/koru_audit.log
   ```

5. **Test dry-run**  
   ```bash
   cd /path/to/project && koru-run
   # Expected: prints DRY-RUN line, logs to /var/log/koru_audit.log
   ```

6. **Upgrade to execute (once consented)**  
   ```bash
   jq '.level = "execute"' .koru/config.json > .koru/config.json.tmp && mv .koru/config.json.tmp .koru/config.json
   ```

7. **Run final execution**  
   ```bash
   koru-run
   # Logs execution, runs vendor CLI
   ```

---  
**Audit log format**:  
`[AUDIT] 2024-06-15T10:30:00+00:00 DRY-RUN/EXECUTE profile=automation dir=/path/to/project`
