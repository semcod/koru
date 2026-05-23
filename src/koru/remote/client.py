import json
import urllib.request
import urllib.error
from typing import Any


class KoruRemoteClient:
    """SDK for controlling and monitoring remote Koru nodes and active IDEs."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, use_ssl: bool = False) -> None:
        schema = "https" if use_ssl else "http"
        self.base_url = f"{schema}://{host}:{port}"

    def _request(self, path: str, method: str = "GET", data: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5.0) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                err_body = json.loads(exc.read().decode("utf-8"))
                err_msg = err_body.get("error", exc.reason)
            except Exception:
                err_msg = exc.reason
            raise RuntimeError(f"Remote command failed: HTTP {exc.code} - {err_msg}") from exc
        except Exception as exc:
            raise RuntimeError(f"Cannot reach remote Koru node at {self.base_url}: {exc}") from exc

    def get_status(self) -> dict[str, Any]:
        """Get remote dashboard state, active project, and connected IDE plugins."""
        return self._request("/api/dashboard")

    def get_logs(self, limit: int = 100) -> dict[str, Any]:
        """Fetch clamped (10KB per session) plugin console logs from the remote node."""
        return self._request(f"/api/plugin-logs?limit={limit}")

    def send_drive_command(self, ide: str, text: str, require_plugin: bool = False) -> dict[str, Any]:
        """Inject a high-level text prompt directly into the remote IDE's chat window."""
        payload = {
            "ide": ide,
            "text": text,
            "require_plugin": require_plugin
        }
        return self._request("/api/remote/drive", method="POST", data=payload)

    def list_running_ides(self) -> list[dict[str, Any]]:
        """List all detected running IDE processes on the remote machine."""
        status = self.get_status()
        return status.get("ides", [])

    def list_connected_plugins(self) -> list[dict[str, Any]]:
        """List all IDE plugins currently connected to the remote autopilot daemon."""
        status = self.get_status()
        return status.get("plugins", [])
