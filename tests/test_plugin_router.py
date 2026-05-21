from __future__ import annotations

from dataclasses import dataclass, field

from koruide.plugin_router import PluginRouter


@dataclass
class _Sock:
    fd: int

    def fileno(self) -> int:
        return self.fd


@dataclass
class _Client:
    fd: int
    role: str = "plugin"
    ide: str | None = None
    dropped: bool = False
    sock: _Sock = field(init=False)

    def __post_init__(self) -> None:
        self.sock = _Sock(self.fd)


def test_plugin_for_prefers_newest_matching_client() -> None:
    first = _Client(1, ide="vscode")
    second = _Client(2, ide="vscode")
    clients = {1: first, 2: second}
    router = PluginRouter(clients, drop_client=lambda _c: None)

    picked = router.plugin_for("vscode")
    assert picked is second


def test_drop_stale_plugins_removes_older_same_ide() -> None:
    current = _Client(3, ide="vscode")
    stale_a = _Client(1, ide="vscode")
    stale_b = _Client(2, ide="vscode")
    other = _Client(4, ide="cursor")
    clients = {1: stale_a, 2: stale_b, 3: current, 4: other}

    def _drop(client: _Client) -> None:
        client.dropped = True
        clients.pop(client.fd, None)

    router = PluginRouter(clients, drop_client=_drop)
    dropped = router.drop_stale_plugins(current, "vscode")

    assert dropped == 2
    assert stale_a.dropped is True
    assert stale_b.dropped is True
    assert 1 not in clients and 2 not in clients
    assert 3 in clients and 4 in clients


def test_status_rows_include_only_plugin_clients() -> None:
    plugin = _Client(1, ide="vscode")
    cli = _Client(2, role="cli", ide=None)
    clients = {1: plugin, 2: cli}
    router = PluginRouter(clients, drop_client=lambda _c: None)

    rows = router.status_rows()
    assert [row.to_dict() for row in rows] == [{"ide": "vscode", "fd": 1}]
