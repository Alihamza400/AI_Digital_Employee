"""Security regression tests: approval authentication and vault path confinement."""

import json
import socket

import httpx

from src.watchers.approval_server import ApprovalServer
from src.watchers.approval_watcher import PendingHandler
from src.watchers.mcp_server import ActionRequest, ActionStatus, ActionType, MCPServer


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _pending_file(vault, name, action_data):
    pending = vault / "Pending_Approval"
    pending.mkdir(parents=True, exist_ok=True)
    (vault / "Approved").mkdir(parents=True, exist_ok=True)
    (vault / "Rejected").mkdir(parents=True, exist_ok=True)
    path = pending / name
    path.write_text(json.dumps(action_data))
    return path


def test_secret_requires_token_on_every_endpoint(tmp_path):
    """Approve/reject must be gated too, not just the listing page."""
    port = _free_port()
    server = ApprovalServer(str(tmp_path), port=port, secret="s3cret-token")
    server.start()
    try:
        _pending_file(tmp_path, "APPROVAL_create_task_sec-1.json", {"id": "sec-1"})
        base = f"http://127.0.0.1:{port}"

        for path in (
            "/",
            "/approve?id=APPROVAL_create_task_sec-1.json",
            "/reject?id=APPROVAL_create_task_sec-1.json",
        ):
            resp = httpx.get(f"{base}{path}", timeout=5)
            assert resp.status_code == 401, path
            assert "Unauthorized" in resp.text

        # Nothing moved while unauthenticated.
        assert (tmp_path / "Pending_Approval" / "APPROVAL_create_task_sec-1.json").exists()
        assert not list((tmp_path / "Approved").glob("*.json"))
    finally:
        server.stop()


def test_notification_links_are_usable_against_authenticated_server(tmp_path):
    """A token-protected server must still accept the links it emails out."""
    port = _free_port()
    secret = "link-token-xyz"
    server = ApprovalServer(str(tmp_path), port=port, secret=secret)
    server.start()

    sent = {}

    class FakeSender:
        def send_email(self, to, subject, body, html_body=None, **kwargs):
            sent["body"] = body
            sent["html"] = html_body
            return {"success": True}

    try:
        pending = tmp_path / "Pending_Approval"
        pending.mkdir(parents=True, exist_ok=True)
        (tmp_path / "Approved").mkdir(parents=True, exist_ok=True)
        action_file = pending / "APPROVAL_create_task_notify-1.json"
        action_file.write_text(
            json.dumps(
                {
                    "id": "notify-1",
                    "action_type": "create_task",
                    "parameters": {"title": "Call the client"},
                    "status": "pending",
                }
            )
        )

        handler = PendingHandler(
            pending,
            gmail_sender=FakeSender(),
            notify_email="ops@example.com",
            base_url=f"http://127.0.0.1:{port}",
            secret=secret,
        )
        handler._notify(action_file)

        assert f"token={secret}" in sent["body"]
        assert f"token={secret}" in sent["html"]

        # The approve link from the notification body must actually work.
        approve_url = next(
            line.split("Approve: ")[1].strip()
            for line in sent["body"].splitlines()
            if "Approve: " in line
        )
        assert f"token={secret}" in approve_url
        resp = httpx.get(approve_url, timeout=5)
        assert resp.status_code == 200
        assert "Approved!" in resp.text
        assert (tmp_path / "Approved" / action_file.name).exists()
    finally:
        server.stop()


def test_servers_do_not_share_handler_state(tmp_path):
    """A second server on another vault must not retarget the first one."""
    vault_a = tmp_path / "vault_a"
    vault_b = tmp_path / "vault_b"
    vault_a.mkdir()
    vault_b.mkdir()

    port_a = _free_port()
    port_b = _free_port()
    server_a = ApprovalServer(str(vault_a), port=port_a, secret="aaa")
    server_b = ApprovalServer(str(vault_b), port=port_b, secret="bbb")
    server_a.start()
    server_b.start()
    try:
        _pending_file(vault_a, "APPROVAL_create_task_act-a.json", {"id": "act-a"})
        _pending_file(vault_b, "APPROVAL_create_task_act-b.json", {"id": "act-b"})

        list_a = httpx.get(f"http://127.0.0.1:{port_a}/?token=aaa", timeout=5)
        assert list_a.status_code == 200
        assert "act-a" in list_a.text
        assert "act-b" not in list_a.text

        # Server B's secret must not be accepted by server A.
        assert httpx.get(f"http://127.0.0.1:{port_a}/?token=bbb", timeout=5).status_code == 401
    finally:
        server_a.stop()
        server_b.stop()


def test_file_operation_rejects_absolute_path_outside_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    mcp = MCPServer(str(vault), {})
    outside = tmp_path / "outside_vault.txt"

    req = ActionRequest(
        id="escape-01",
        action_type=ActionType.FILE_OPERATION,
        parameters={"operation": "create_file", "path": str(outside), "content": "pwned"},
        status=ActionStatus.APPROVED,
        created_at="2026-01-01T00:00:00",
    )

    result = mcp.action_executor.execute(req)

    assert result["success"] is False
    assert req.status == ActionStatus.FAILED
    assert not outside.exists()


def test_file_operation_rejects_traversal_escape(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    mcp = MCPServer(str(vault), {})

    req = ActionRequest(
        id="escape-02",
        action_type=ActionType.FILE_OPERATION,
        parameters={"operation": "create_file", "path": "../escaped.txt", "content": "pwned"},
        status=ActionStatus.APPROVED,
        created_at="2026-01-01T00:00:00",
    )

    result = mcp.action_executor.execute(req)

    assert result["success"] is False
    assert not (tmp_path / "escaped.txt").exists()


def test_file_operation_cannot_delete_outside_vault(tmp_path):
    """The destructive path matters most: deletion must be confined too."""
    vault = tmp_path / "vault"
    vault.mkdir()
    mcp = MCPServer(str(vault), {})
    precious = tmp_path / "precious.txt"
    precious.write_text("do not delete")

    req = ActionRequest(
        id="escape-03",
        action_type=ActionType.FILE_OPERATION,
        parameters={"operation": "delete_file", "path": str(precious)},
        status=ActionStatus.APPROVED,
        created_at="2026-01-01T00:00:00",
    )

    result = mcp.action_executor.execute(req)

    assert result["success"] is False
    assert precious.exists()


def test_file_operation_allows_relative_path_inside_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    mcp = MCPServer(str(vault), {})

    req = ActionRequest(
        id="inside-01",
        action_type=ActionType.FILE_OPERATION,
        parameters={
            "operation": "create_file",
            "path": "Drafts/note.md",
            "content": "legitimate content",
        },
        status=ActionStatus.APPROVED,
        created_at="2026-01-01T00:00:00",
    )

    result = mcp.action_executor.execute(req)

    assert result["success"] is True
    assert (vault / "Drafts" / "note.md").read_text() == "legitimate content"


def test_file_operation_requires_a_path(tmp_path):
    mcp = MCPServer(str(tmp_path), {})

    req = ActionRequest(
        id="nopath-01",
        action_type=ActionType.FILE_OPERATION,
        parameters={"operation": "create_file", "content": "no path supplied"},
        status=ActionStatus.APPROVED,
        created_at="2026-01-01T00:00:00",
    )

    result = mcp.action_executor.execute(req)

    assert result["success"] is False
    assert "path" in result["error"]
