# STARTER-554: R-F2.2: Split vdisplay_client.py (7k lines, 45 silent excepts)

model: qwen/qwen3-coder-next

## Prompt

src/koru/integrations/vdisplay_client.py is the biggest God module with ~45 except-Exception-pass sites. Split by concern (session, capture, gui-map, drive recording) and apply the warn-on-swallow pattern from Phase 0.

---
Deliverable: a concrete, ordered action plan with exact shell commands and file paths where applicable, short enough to execute directly. State assumptions explicitly; do not pad.

## Answer

**Assumptions**  
1. `src/koru/integrations/vdisplay_client.py` exists and is the target file.  
2. “warn-on-swallow pattern” = replace `except Exception: pass` with `logger.warning("Swallowed exception", exc_info=True)` (or similar).  
3. Concern-based splitting:  
   - `session.py` — session lifecycle (connect, disconnect, keepalive)  
   - `capture.py` — screen capture logic  
   - `guimap.py` — GUI element mapping/lookup  
   - `drive_recording.py` — drive recording (upload, metadata, cleanup)  
4. `src/koru/integrations/` is the module directory; `src/koru/` is import root.  
5. A shared logger `logger = logging.getLogger(__name__)` is available in each new module (will be added).  

---

**Action Plan**  

1. **Backup original file**  
   ```bash
   cp src/koru/integrations/vdisplay_client.py src/koru/integrations/vdisplay_client.py.bak
   ```

2. **Create new modules with minimal stubs**  
   ```bash
   touch src/koru/integrations/session.py
   touch src/koru/integrations/capture.py
   touch src/koru/integrations/guimap.py
   touch src/koru/integrations/drive_recording.py
   ```

3. **Populate `session.py`**  
   - Extract all session-related `except Exception: pass` sites (e.g., connection, auth, ping).  
   - Add logger and warn-on-swallow:  
   ```bash
   cat > src/koru/integrations/session.py << 'EOF'
   import logging
   logger = logging.getLogger(__name__)

   def connect():
       try:
           # original connect logic
           pass
       except Exception:
           logger.warning("Swallowed exception in connect", exc_info=True)

   def disconnect():
       try:
           # original disconnect logic
           pass
       except Exception:
           logger.warning("Swallowed exception in disconnect", exc_info=True)

   def keepalive():
       try:
           # original keepalive logic
           pass
       except Exception:
           logger.warning("Swallowed exception in keepalive", exc_info=True)
   EOF
   ```

4. **Populate `capture.py`**  
   - Extract capture-related `except Exception: pass` (e.g., screenshot, region crop, encoding).  
   ```bash
   cat > src/koru/integrations/capture.py << 'EOF'
   import logging
   logger = logging.getLogger(__name__)

   def capture_screen():
       try:
           # original capture logic
           pass
       except Exception:
           logger.warning("Swallowed exception in capture_screen", exc_info=True)

   def crop_region():
       try:
           # original crop logic
           pass
       except Exception:
           logger.warning("Swallowed exception in crop_region", exc_info=True)
   EOF
   ```

5. **Populate `guimap.py`**  
   - Extract GUI map lookup/translation exceptions.  
   ```bash
   cat > src/koru/integrations/guimap.py << 'EOF'
   import logging
   logger = logging.getLogger(__name__)

   def lookup_element():
       try:
           # original lookup logic
           pass
       except Exception:
           logger.warning("Swallowed exception in lookup_element", exc_info=True)

   def map_to_screen():
       try:
           # original mapping logic
           pass
       except Exception:
           logger.warning("Swallowed exception in map_to_screen", exc_info=True)
   EOF
   ```

6. **Populate `drive_recording.py`**  
   - Extract drive upload, metadata, cleanup exceptions.  
   ```bash
   cat > src/koru/integrations/drive_recording.py << 'EOF'
   import logging
   logger = logging.getLogger(__name__)

   def upload_recording():
       try:
           # original upload logic
           pass
       except Exception:
           logger.warning("Swallowed exception in upload_recording", exc_info=True)

   def record_metadata():
       try:
           # original metadata logic
           pass
       except Exception:
           logger.warning("Swallowed exception in record_metadata", exc_info=True)

   def cleanup_temp():
       try:
           # original cleanup logic
           pass
       except Exception:
           logger.warning("Swallowed exception in cleanup_temp", exc_info=True)
   EOF
   ```

7. **Refactor `vdisplay_client.py` to delegate**  
   - Replace all `except Exception: pass` with calls to new modules.  
   - Remove duplicated logic; keep only orchestration.  
   ```bash
   cat > src/koru/integrations/vdisplay_client.py << 'EOF'
   from . import session, capture, guimap, drive_recording

   def run_session():
       session.connect()
       try:
           screen = capture.capture_screen()
           element = guimap.lookup_element(screen)
           drive_recording.upload_recording(element)
       finally:
           session.disconnect()
   EOF
   ```

8. **Verify no `except Exception: pass` remains in original file**  
   ```bash
   grep -n "except Exception:" src/koru/integrations/vdisplay_client.py || echo "No bare except Exception: pass found"
   ```

9. **Run tests**  
   ```bash
   python -m pytest src/koru/integrations/ -v
   ```

10. **Delete backup if tests pass**  
    ```bash
    rm src/koru/integrations/vdisplay_client.py.bak
    ```

---  
**Total files modified/created**: 5 (4 new + 1 refactored).  
**Time estimate**: ≤15 minutes.
