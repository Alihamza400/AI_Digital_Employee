"""End-to-end tests for AI Digital Employee full workflow."""

import json
from datetime import datetime
from src.watchers.filesystem_watcher import DropFolderHandler
from src.watchers.approval_watcher import ApprovalHandler
from src.watchers.mcp_server import MCPServer
from src.watchers.scheduler import AutomatedTasks
from src.scripts import approve as approve_cli


def test_complete_end_to_end_lifecycle(tmp_path, monkeypatch):
    """
    Test complete perception -> reasoning -> approval -> action -> reflection lifecycle:
    1. Drop file in Inbox/
    2. FileSystemWatcher processes to Needs_Action/ with metadata
    3. AI Reasoning processes: creates Plan, Pending_Approval JSON, moves to Needs_Action/Done/
    4. Human approval via CLI moves file to Approved/
    5. ApprovalWatcher executes action via MCPServer, logs action, archives to Completed/executed/
    6. Scheduler updates Dashboard.md with accurate real-time metrics
    """
    vault = tmp_path
    mcp = MCPServer(str(vault), {})

    inbox = vault / "Inbox"
    needs_action = vault / "Needs_Action"
    done_dir = needs_action / "Done"
    plans_dir = vault / "Plans"
    pending_dir = vault / "Pending_Approval"
    approved_dir = vault / "Approved"
    rejected_dir = vault / "Rejected"
    completed_dir = vault / "Completed"
    logs_dir = vault / "Logs"

    # Step 1 & 2: Drop file in Inbox and perceive
    sample_invoice_request = inbox / "generate_invoice_acme.txt"
    sample_invoice_request.write_text(
        "Please create an invoice for Acme Corp for 3 units of Consulting at $500 each."
    )

    fs_handler = DropFolderHandler(str(vault))
    fs_handler.process_file(sample_invoice_request)

    assert not sample_invoice_request.exists()
    action_file = needs_action / "FILE_generate_invoice_acme.txt"
    meta_file = needs_action / "FILE_generate_invoice_acme.txt.md"
    assert action_file.exists()
    assert meta_file.exists()

    # Step 3: Reasoning phase (simulating AI agent reasoning output)
    req_id = "inv-acme-100"
    plan_file = plans_dir / f"PLAN_{req_id}.md"
    plan_file.write_text(f"""# Execution Plan for {action_file.name}
1. Review invoice request from customer Acme Corp.
2. Generate PDF invoice for 3 units of Consulting at $500 each ($1500 total).
3. Submit approval request before creating invoice.
""")

    approval_data = {
        "id": req_id,
        "action_type": "create_invoice",
        "parameters": {
            "invoice_id": req_id,
            "client": "Acme Corp",
            "items": [{"description": "Consulting", "amount": 500.0, "quantity": 3}],
        },
        "status": "pending",
        "requires_approval": True,
        "created_at": datetime.now().isoformat(),
    }
    approval_file = pending_dir / f"APPROVAL_create_invoice_{req_id}.json"
    approval_file.write_text(json.dumps(approval_data, indent=2))

    # Move processed file to Needs_Action/Done/
    action_file.rename(done_dir / action_file.name)
    assert (done_dir / action_file.name).exists()
    assert not action_file.exists()

    # Step 4: Human-in-the-loop approval via CLI
    monkeypatch.setattr(approve_cli, "VAULT", vault)
    monkeypatch.setattr(approve_cli, "PENDING", pending_dir)
    monkeypatch.setattr(approve_cli, "APPROVED", approved_dir)
    monkeypatch.setattr(approve_cli, "REJECTED", rejected_dir)

    pending_list = approve_cli.list_pending()
    assert len(pending_list) == 1
    assert pending_list[0].name == approval_file.name

    approve_success = approve_cli.approve(approval_file.name)
    assert approve_success is True
    assert not approval_file.exists()
    approved_file = approved_dir / approval_file.name
    assert approved_file.exists()

    # Step 5: Execution via ApprovalHandler and MCPServer
    app_handler = ApprovalHandler(approved_dir, rejected_dir, mcp)
    app_handler._handle_file(approved_file)

    # Verify action execution: PDF invoice generated
    invoice_pdf = vault / "Accounting" / f"Invoice_{req_id}.pdf"
    assert invoice_pdf.exists()
    assert invoice_pdf.stat().st_size > 0

    # Verify approved file moved to Completed/executed/
    assert not approved_file.exists()
    archived_file = completed_dir / "executed" / approved_file.name
    assert archived_file.exists()

    # Verify action logged in Logs/YYYY-MM-DD.json
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"
    assert log_file.exists()
    logs = json.loads(log_file.read_text())
    assert len(logs) >= 1
    assert logs[-1]["id"] == req_id
    assert logs[-1]["status"] == "completed"

    # Step 6: Reflection and metrics update in Dashboard.md
    tasks = AutomatedTasks(str(vault), mcp)
    tasks.update_dashboard()

    dashboard = vault / "Dashboard.md"
    assert dashboard.exists()
    dash_text = dashboard.read_text()
    assert "Dashboard - Personal AI Employee Real-Time Status" in dash_text
    assert "| Actions Today | 1 |" in dash_text
    assert "| Pending Approvals | 0 |" in dash_text
    assert "Invoice" in str(dash_text) or "create_invoice" in str(dash_text)
