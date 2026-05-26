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
    awaiting_plugin: object | None = None
    workspace_name: str | None = None
    workspace_folders: list[str] = field(default_factory=list)
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


def test_plugin_for_matches_canonical_aliases() -> None:
    vscode = _Client(1, ide="vscode")
    cursor = _Client(2, ide="Cursor")
    clients = {1: vscode, 2: cursor}
    router = PluginRouter(clients, drop_client=lambda _c: None)

    assert router.plugin_for("code") is vscode
    assert router.plugin_for("cursor") is cursor


def test_plugin_for_prefers_workspace_matching_client() -> None:
    other_workspace = _Client(2, ide="vscode", workspace_name="other", workspace_folders=["/tmp/other"])
    matching = _Client(1, ide="vscode", workspace_name="koru", workspace_folders=["/repo/koru"])
    clients = {1: matching, 2: other_workspace}
    router = PluginRouter(clients, drop_client=lambda _c: None)

    assert router.plugin_for("vscode", project="/repo/koru") is matching


def test_plugin_for_rejects_workspace_mismatch() -> None:
    other_workspace = _Client(1, ide="vscode", workspace_name="other", workspace_folders=["/tmp/other"])
    clients = {1: other_workspace}
    router = PluginRouter(clients, drop_client=lambda _c: None)

    assert router.plugin_for("vscode", project="/repo/koru") is None


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


def test_drop_stale_plugins_matches_canonical_aliases() -> None:
    current = _Client(3, ide="vscode")
    stale = _Client(1, ide="code")
    other = _Client(4, ide="cursor")
    clients = {1: stale, 3: current, 4: other}

    def _drop(client: _Client) -> None:
        client.dropped = True
        clients.pop(client.fd, None)

    router = PluginRouter(clients, drop_client=_drop)
    dropped = router.drop_stale_plugins(current, "vscode")

    assert dropped == 1
    assert stale.dropped is True
    assert 1 not in clients
    assert 3 in clients and 4 in clients


def test_drop_stale_plugins_keeps_plugin_with_pending_drive() -> None:
    current = _Client(3, ide="vscode")
    pending = _Client(1, ide="vscode", awaiting_plugin=object())
    stale = _Client(2, ide="vscode")
    clients = {1: pending, 2: stale, 3: current}

    def _drop(client: _Client) -> None:
        client.dropped = True
        clients.pop(client.fd, None)

    router = PluginRouter(clients, drop_client=_drop)
    dropped = router.drop_stale_plugins(current, "vscode")

    assert dropped == 1
    assert pending.dropped is False
    assert stale.dropped is True
    assert 1 in clients and 2 not in clients and 3 in clients


def test_drop_stale_plugins_keeps_workspace_aware_plugin_when_current_is_old() -> None:
    current = _Client(3, ide="vscode")
    workspace_aware = _Client(1, ide="vscode", workspace_folders=["/repo/koru"])
    legacy = _Client(2, ide="vscode")
    clients = {1: workspace_aware, 2: legacy, 3: current}

    def _drop(client: _Client) -> None:
        client.dropped = True
        clients.pop(client.fd, None)

    router = PluginRouter(clients, drop_client=_drop)
    dropped = router.drop_stale_plugins(current, "vscode")

    assert dropped == 1
    assert workspace_aware.dropped is False
    assert legacy.dropped is True
    assert 1 in clients and 2 not in clients and 3 in clients


def test_drop_stale_plugins_keeps_different_workspaces_connected() -> None:
    current = _Client(3, ide="vscode", workspace_name="koru", workspace_folders=["/repo/koru"])
    other_workspace = _Client(1, ide="vscode", workspace_name="c2004", workspace_folders=["/repo/c2004"])
    same_workspace = _Client(2, ide="vscode", workspace_name="koru-old", workspace_folders=["/repo/koru"])
    legacy = _Client(4, ide="vscode")
    clients = {1: other_workspace, 2: same_workspace, 3: current, 4: legacy}

    def _drop(client: _Client) -> None:
        client.dropped = True
        clients.pop(client.fd, None)

    router = PluginRouter(clients, drop_client=_drop)
    dropped = router.drop_stale_plugins(current, "vscode")

    assert dropped == 2
    assert other_workspace.dropped is False
    assert same_workspace.dropped is True
    assert legacy.dropped is True
    assert 1 in clients and 2 not in clients and 3 in clients and 4 not in clients


def test_status_rows_include_only_plugin_clients() -> None:
    plugin = _Client(1, ide="vscode")
    cli = _Client(2, role="cli", ide=None)
    clients = {1: plugin, 2: cli}
    router = PluginRouter(clients, drop_client=lambda _c: None)

    rows = router.status_rows()
    assert [row.to_dict() for row in rows] == [{"ide": "vscode", "fd": 1}]
