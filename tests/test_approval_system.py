"""Tests for Approval Server, ApprovalWatcher, and CLI approval tool."""

import json
import socket
import httpx
from src.watchers.approval_server import ApprovalServer
from src.watchers.approval_watcher import ApprovalHandler
from src.watchers.mcp_server import MCPServer
from src.scripts import approve as approve_cli


def _get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def test_approval_server_flow(tmp_path):
    port = _get_free_port()
    server = ApprovalServer(str(tmp_path), port=port)
    server.start()

    # Create pending approval file
    pending_dir = tmp_path / "Pending_Approval"
    pending_dir.mkdir(parents=True)
    (tmp_path / "Approved").mkdir(parents=True)
    (tmp_path / "Rejected").mkdir(parents=True)

    action_data = {
        "id": "act-web-1",
        "action_type": "file_operation",
        "parameters": {
            "operation": "create_file",
            "path": str(tmp_path / "created.txt"),
            "content": "hello",
        },
        "status": "pending",
        "requires_approval": True,
        "created_at": "2026-09-19T10:00:00",
    }
    action_file = pending_dir / "APPROVAL_file_operation_act-web-1.json"
    action_file.write_text(json.dumps(action_data))

    base_url = f"http://127.0.0.1:{port}"
    try:
        # Test 1: List pending approvals
        resp = httpx.get(base_url, timeout=5)
        assert resp.status_code == 200
        assert "act-web-1" in resp.text
        assert "file_operation" in resp.text

        # Test 2: Approve action
        approve_resp = httpx.get(f"{base_url}/approve?id={action_file.name}", timeout=5)
        assert approve_resp.status_code == 200
        assert "Approved!" in approve_resp.text
        assert not action_file.exists()
        assert (tmp_path / "Approved" / action_file.name).exists()

        # Create another file to test rejection
        action_file2 = pending_dir / "APPROVAL_file_operation_act-web-2.json"
        action_file2.write_text(json.dumps(action_data))

        reject_resp = httpx.get(f"{base_url}/reject?id={action_file2.name}", timeout=5)
        assert reject_resp.status_code == 200
        assert "Rejected" in reject_resp.text
        assert not action_file2.exists()
        assert (tmp_path / "Rejected" / action_file2.name).exists()

    finally:
        server.stop()


def test_approval_server_with_secret_token(tmp_path):
    port = _get_free_port()
    server = ApprovalServer(str(tmp_path), port=port, secret="mysecrettoken123")
    server.start()

    pending_dir = tmp_path / "Pending_Approval"
    pending_dir.mkdir(parents=True)
    (tmp_path / "Approved").mkdir(parents=True)

    action_file = pending_dir / "APPROVAL_test.json"
    action_file.write_text(json.dumps({"id": "sec-1", "action_type": "test"}))

    base_url = f"http://127.0.0.1:{port}"
    try:
        # Unauthorized without token
        unauth_resp = httpx.get(base_url, timeout=5)
        assert unauth_resp.status_code == 401
        assert "Unauthorized" in unauth_resp.text

        # Authorized with correct token
        auth_resp = httpx.get(f"{base_url}/?token=mysecrettoken123", timeout=5)
        assert auth_resp.status_code == 200
        assert "Pending Approvals" in auth_resp.text
    finally:
        server.stop()


def test_approval_handler_executes_and_archives(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    approved_dir = tmp_path / "Approved"
    rejected_dir = tmp_path / "Rejected"

    handler = ApprovalHandler(approved_dir, rejected_dir, mcp)

    target_file = tmp_path / "executed_target.txt"
    action_data = {
        "id": "act-exec-1",
        "action_type": "file_operation",
        "parameters": {
            "operation": "create_file",
            "path": str(target_file),
            "content": "executed content",
        },
        "status": "approved",
        "created_at": "2026-09-19T10:00:00",
    }

    action_file = approved_dir / "APPROVAL_file_operation_act-exec-1.json"
    action_file.write_text(json.dumps(action_data))

    handler._handle_file(action_file)

    # File operation executed
    assert target_file.exists()
    assert target_file.read_text() == "executed content"

    # Action file moved to Completed/executed/
    assert not action_file.exists()
    assert (tmp_path / "Completed" / "executed" / action_file.name).exists()


def test_approve_cli_operations(tmp_path, monkeypatch):
    monkeypatch.setattr(approve_cli, "VAULT", tmp_path)
    monkeypatch.setattr(approve_cli, "PENDING", tmp_path / "Pending_Approval")
    monkeypatch.setattr(approve_cli, "APPROVED", tmp_path / "Approved")
    monkeypatch.setattr(approve_cli, "REJECTED", tmp_path / "Rejected")

    pending_dir = tmp_path / "Pending_Approval"
    approved_dir = tmp_path / "Approved"
    rejected_dir = tmp_path / "Rejected"
    pending_dir.mkdir(parents=True)
    approved_dir.mkdir(parents=True)
    rejected_dir.mkdir(parents=True)

    action_data = {
        "id": "cli-1",
        "action_type": "create_task",
        "parameters": {"title": "CLI Test Task"},
        "status": "pending",
    }
    f1 = pending_dir / "APPROVAL_cli_1.json"
    f1.write_text(json.dumps(action_data))

    # Test list
    pending_files = approve_cli.list_pending()
    assert len(pending_files) == 1

    # Test approve
    res = approve_cli.approve("APPROVAL_cli_1.json")
    assert res is True
    assert not f1.exists()
    assert (approved_dir / "APPROVAL_cli_1.json").exists()

    # Test reject
    f2 = pending_dir / "APPROVAL_cli_2.json"
    f2.write_text(json.dumps(action_data))
    res2 = approve_cli.reject("APPROVAL_cli_2.json")
    assert res2 is True
    assert not f2.exists()
    assert (rejected_dir / "APPROVAL_cli_2.json").exists()
