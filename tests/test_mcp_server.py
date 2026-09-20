"""Tests for MCP Server and action execution."""

import json
from pathlib import Path
from src.watchers.approval_watcher import ApprovalHandler
from src.watchers.mcp_server import (
    MCPServer,
    ActionType,
    ActionStatus,
    ActionRequest,
    ApprovalWorkflow,
)


def test_action_type_case_insensitivity():
    assert ActionType("SEND_EMAIL") == ActionType.SEND_EMAIL
    assert ActionType("send_email") == ActionType.SEND_EMAIL
    assert ActionType("FILE_OPERATION") == ActionType.FILE_OPERATION
    assert ActionType("create_task") == ActionType.CREATE_TASK


def test_action_status_case_insensitivity():
    assert ActionStatus("PENDING") == ActionStatus.PENDING
    assert ActionStatus("pending") == ActionStatus.PENDING
    assert ActionStatus("APPROVED") == ActionStatus.APPROVED
    assert ActionStatus("approved") == ActionStatus.APPROVED


def test_action_request_roundtrip():
    req = ActionRequest(
        id="act-001",
        action_type=ActionType.CREATE_TASK,
        parameters={"title": "Test Task", "priority": "high"},
        status=ActionStatus.PENDING,
        created_at="2026-09-19T10:00:00",
        requires_approval=True,
    )
    d = req.to_dict()
    assert d["id"] == "act-001"
    assert d["action_type"] == "create_task"
    assert d["status"] == "pending"

    restored = ActionRequest.from_dict(d)
    assert restored.id == "act-001"
    assert restored.action_type == ActionType.CREATE_TASK
    assert restored.status == ActionStatus.PENDING
    assert restored.parameters["title"] == "Test Task"


def test_action_request_from_dict_fallback():
    # Unknown action type falls back to CREATE_TASK
    d = {"id": "act-002", "action_type": "UNKNOWN_ACTION", "parameters": {}}
    restored = ActionRequest.from_dict(d)
    assert restored.action_type == ActionType.CREATE_TASK
    assert restored.status == ActionStatus.PENDING


def test_approval_workflow(tmp_path):
    workflow = ApprovalWorkflow(str(tmp_path))
    req = ActionRequest(
        id="req-123",
        action_type=ActionType.SEND_EMAIL,
        parameters={"to": "client@example.com", "subject": "Hello"},
        status=ActionStatus.PENDING,
        created_at="2026-09-19T10:00:00",
    )

    req_file = workflow.create_approval_request(req)
    assert req_file.exists()
    assert (tmp_path / "Pending_Approval" / req_file.name).exists()

    # Approve
    success = workflow.approve("req-123")
    assert success is True
    assert not (tmp_path / "Pending_Approval" / req_file.name).exists()
    assert (tmp_path / "Approved" / req_file.name).exists()


def test_approval_workflow_reject(tmp_path):
    workflow = ApprovalWorkflow(str(tmp_path))
    req = ActionRequest(
        id="req-456",
        action_type=ActionType.POST_LINKEDIN,
        parameters={"content": "Exciting news!"},
        status=ActionStatus.PENDING,
        created_at="2026-09-19T10:00:00",
    )

    req_file = workflow.create_approval_request(req)
    assert req_file.exists()

    success = workflow.reject("req-456", reason="Not ready yet")
    assert success is True
    assert not (tmp_path / "Pending_Approval" / req_file.name).exists()
    assert (tmp_path / "Rejected" / req_file.name).exists()


def test_action_executor_file_operations(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    target_file = tmp_path / "test_file.txt"

    # Create file
    create_req = ActionRequest(
        id="file-01",
        action_type=ActionType.FILE_OPERATION,
        parameters={"operation": "create_file", "path": str(target_file), "content": "Hello World"},
        status=ActionStatus.APPROVED,
        created_at="2026-09-19T10:00:00",
    )
    result = mcp.action_executor.execute(create_req)
    assert result["success"] is True
    assert target_file.exists()
    assert target_file.read_text() == "Hello World"

    # Delete file
    delete_req = ActionRequest(
        id="file-02",
        action_type=ActionType.FILE_OPERATION,
        parameters={"operation": "delete_file", "path": str(target_file)},
        status=ActionStatus.APPROVED,
        created_at="2026-09-19T10:00:00",
    )
    del_result = mcp.action_executor.execute(delete_req)
    assert del_result["success"] is True
    assert not target_file.exists()


def test_action_executor_create_task(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    task_req = ActionRequest(
        id="task-01",
        action_type=ActionType.CREATE_TASK,
        parameters={
            "title": "Q3 Financial Audit",
            "description": "Review expenses",
            "priority": "high",
        },
        status=ActionStatus.APPROVED,
        created_at="2026-09-19T10:00:00",
    )
    result = mcp.action_executor.execute(task_req)
    assert result["success"] is True
    task_path = Path(result["result"]["path"])
    assert task_path.exists()
    content = task_path.read_text()
    assert "Q3 Financial Audit" in content
    assert "priority: high" in content


def test_action_executor_create_invoice(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    inv_req = ActionRequest(
        id="inv-01",
        action_type=ActionType.CREATE_INVOICE,
        parameters={
            "invoice_id": "INV-2026-001",
            "client": "TechCorp",
            "items": [
                {"description": "Cloud Architecture Review", "amount": 2500.0, "quantity": 1}
            ],
        },
        status=ActionStatus.APPROVED,
        created_at="2026-09-19T10:00:00",
    )
    result = mcp.action_executor.execute(inv_req)
    assert result["success"] is True
    assert result["result"]["total"] == 2500.0
    pdf_path = Path(result["result"]["path"])
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_action_executor_propagates_handler_failure(tmp_path):
    """A handler that reports failure must not be recorded as completed."""
    mcp = MCPServer(str(tmp_path), {})
    req = ActionRequest(
        id="bad-01",
        action_type=ActionType.FILE_OPERATION,
        # Unknown operation → handler returns {'success': False, 'error': ...}
        parameters={"source_files": ["a.txt"], "destination": "Done/"},
        status=ActionStatus.APPROVED,
        created_at="2026-09-19T10:00:00",
    )

    result = mcp.action_executor.execute(req)

    assert result["success"] is False
    assert req.status == ActionStatus.FAILED
    assert req.completed_at is None
    assert req.error and "Unknown operation" in req.error


def test_failed_action_is_archived_to_failed_not_executed(tmp_path):
    """The approval watcher must not file a failed action as executed."""
    mcp = MCPServer(str(tmp_path), {})
    approved_dir = tmp_path / "Approved"
    rejected_dir = tmp_path / "Rejected"
    approved_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)

    handler = ApprovalHandler(approved_dir, rejected_dir, mcp)
    action_file = approved_dir / "APPROVAL_file_operation_bad-01.json"
    action_file.write_text(
        json.dumps(
            {
                "id": "bad-01",
                "action_type": "file_operation",
                "parameters": {"source_files": ["a.txt"], "destination": "Done/"},
                "status": "approved",
                "created_at": "2026-09-19T10:00:00",
            }
        )
    )

    handler._handle_file(action_file)

    assert (tmp_path / "Completed" / "failed" / action_file.name).exists()
    assert not (tmp_path / "Completed" / "executed" / action_file.name).exists()


def test_mcp_save_and_load_history(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    act = ActionRequest(
        id="hist-01",
        action_type=ActionType.CREATE_TASK,
        parameters={"title": "History test"},
        status=ActionStatus.COMPLETED,
        created_at="2026-09-19T10:00:00",
    )
    mcp._save_action(act)

    # Re-instantiate MCP to test loading
    mcp2 = MCPServer(str(tmp_path), {})
    assert len(mcp2.action_history) == 1
    assert mcp2.action_history[0].id == "hist-01"
