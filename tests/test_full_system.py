"""
End-to-end system test.

Unlike tests/test_end_to_end.py (which simulates the reasoning step), this test
boots the real watcher stack — watchdog observers, threads, the opencode
subprocess, the HTTP approval server and the execution watcher — and drives a
file from Inbox/ all the way to Completed/executed/.

`opencode` is replaced by a stub executable on PATH that performs what the
@ai-employee subagent is contracted to do: write a plan, submit an approval
request, and move the action file to Needs_Action/Done/.
"""

import json
import os
import shutil
import stat
import threading
import time
from datetime import datetime

import httpx
import pytest

from src.watchers import (
    AIReasoningWatcher,
    ApprovalWatcher,
    FileSystemWatcher,
    MCPServer,
    NeedsActionHandler,
    start_approval_server,
)

STUB_OPENCODE = '''#!/usr/bin/env python3
"""Stub opencode CLI used by the end-to-end test."""
import json
import os
import re
import sys
from pathlib import Path

argv = sys.argv[1:]
recorded = os.environ.get("STUB_OPENCODE_CALLS")
if recorded:
    with open(recorded, "a") as fh:
        fh.write(json.dumps({"argv": argv, "cwd": os.getcwd()}) + "\\n")

prompt = " ".join(argv)
match = re.search(r"([\\w./-]*Needs_Action/[\\w.-]+\\.md)", prompt)
if not match:
    print(json.dumps({"type": "error", "error": {"data": {"message": "no action file"}}}))
    sys.exit(1)

action_file = Path(match.group(1))
vault = action_file.parent.parent
stem = action_file.stem
req_id = "e2e-" + re.sub(r"[^A-Za-z0-9_-]", "_", stem)

(vault / "Plans").mkdir(parents=True, exist_ok=True)
(vault / "Plans" / f"PLAN_{req_id}.md").write_text(
    f"# Plan for {stem}\\n\\n1. Read the request.\\n2. Create a task.\\n3. Request approval.\\n"
)

(vault / "Pending_Approval").mkdir(parents=True, exist_ok=True)
(vault / "Pending_Approval" / f"APPROVAL_create_task_{req_id}.json").write_text(
    json.dumps(
        {
            "id": req_id,
            "action_type": "create_task",
            "parameters": {
                "title": f"Follow up on {stem}",
                "description": "Created by the stubbed reasoning agent",
                "priority": "high",
            },
            "status": "pending",
            "requires_approval": True,
            "created_at": "2026-01-01T00:00:00",
        },
        indent=2,
    )
)

done = vault / "Needs_Action" / "Done"
done.mkdir(parents=True, exist_ok=True)
action_file.rename(done / action_file.name)

print(json.dumps({"type": "text", "text": "processed"}))
'''


def wait_for(predicate, timeout: float = 20.0, interval: float = 0.1):
    """Poll until predicate() is truthy or the deadline passes."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


@pytest.fixture
def stub_opencode(tmp_path, monkeypatch):
    """Put a fake `opencode` on PATH and record how it was invoked."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "opencode"
    stub.write_text(STUB_OPENCODE)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    calls_log = tmp_path / "opencode_calls.jsonl"
    monkeypatch.setenv("STUB_OPENCODE_CALLS", str(calls_log))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    assert shutil.which("opencode") == str(stub)
    return calls_log


def test_reasoning_subprocess_contract(tmp_path, stub_opencode):
    """
    The real subprocess invocation must run the configured agent/model, with a
    working directory from which the prompt's relative path resolves.
    """
    vault = tmp_path / "vault"
    MCPServer(str(vault), {})
    needs_action = vault / "Needs_Action"
    action_file = needs_action / "FILE_invoice.txt.md"
    action_file.write_text("---\ntype: file_drop\n---\n\nInvoice request\n")

    handler = NeedsActionHandler(
        needs_action, vault, model="stub/model", agent="ai-employee", timeout=30
    )
    handler._run_opencode(action_file)

    calls = [json.loads(line) for line in stub_opencode.read_text().splitlines() if line]
    assert len(calls) == 1
    argv, cwd = calls[0]["argv"], calls[0]["cwd"]

    assert argv[0] == "run"
    assert "--agent" in argv and "ai-employee" in argv
    assert "--model" in argv and "stub/model" in argv
    assert "--auto" in argv
    assert "--format" in argv and "json" in argv
    # The prompt must reference a path that exists relative to the working dir.
    assert os.path.samefile(cwd, str(vault.parent))
    assert (vault / "Needs_Action" / "FILE_invoice.txt.md").exists() is False  # moved to Done/
    assert (vault / "Needs_Action" / "Done" / "FILE_invoice.txt.md").exists()


def test_full_lifecycle_inbox_to_completed(tmp_path, stub_opencode):
    """
    Drop a file in Inbox/ and assert the whole chain completes:

    Inbox -> FileSystemWatcher -> Needs_Action -> AIReasoningWatcher (opencode
    subprocess) -> Plans/ + Pending_Approval/ -> HTTP approval -> Approved/ ->
    ApprovalWatcher -> MCP execution -> Completed/executed/ + Logs/
    """
    vault = tmp_path / "vault"
    mcp = MCPServer(str(vault), {})

    port = _free_port()
    secret = "e2e-token"
    filesystem_watcher = FileSystemWatcher(str(vault))
    reasoning_watcher = AIReasoningWatcher(
        str(vault), model="stub/model", agent="ai-employee", timeout=30
    )
    approval_watcher = ApprovalWatcher(
        str(vault),
        mcp,
        notify_email=None,
        approval_port=port,
        approval_url=f"http://127.0.0.1:{port}",
        approval_secret=secret,
    )
    approval_server = start_approval_server(str(vault), port, secret)

    threads = []

    def spawn(target):
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        threads.append(thread)

    try:
        spawn(filesystem_watcher.run)
        spawn(reasoning_watcher.run)
        spawn(approval_watcher.run)

        # --- Perception: drop a file and let the watcher file it -------------
        request = vault / "Inbox" / "invoice_request.txt"
        request.write_text("Please invoice Acme Corp for 3 hours of consulting.")

        # The payload stays in Needs_Action/ (only the .md action file is consumed
        # by the reasoning agent), so it is the stable proof that the drop landed.
        payload = vault / "Needs_Action" / "FILE_invoice_request.txt"
        assert wait_for(payload.exists), "FileSystemWatcher never filed the drop"
        assert not request.exists(), "inbox file was not consumed"

        action_file = vault / "Needs_Action" / "FILE_invoice_request.txt.md"
        assert wait_for(
            lambda: action_file.exists()
            or (vault / "Needs_Action" / "Done" / action_file.name).exists()
        ), "no action file was created for the drop"

        # --- Reasoning: the opencode subprocess produced a plan + approval ---
        pending_dir = vault / "Pending_Approval"
        assert wait_for(
            lambda: any(pending_dir.glob("APPROVAL_*.json"))
        ), "reasoning agent produced no approval request"
        approval_file = next(pending_dir.glob("APPROVAL_*.json"))
        request_id = json.loads(approval_file.read_text())["id"]

        assert (vault / "Plans" / f"PLAN_{request_id}.md").exists()
        assert wait_for(
            lambda: (vault / "Needs_Action" / "Done" / action_file.name).exists()
        ), "processed action file was not moved to Needs_Action/Done/"

        # --- Human-in-the-loop: approve over HTTP, unauthenticated first -----
        base_url = f"http://127.0.0.1:{port}"
        unauth = httpx.get(f"{base_url}/approve?id={approval_file.name}", timeout=5)
        assert unauth.status_code == 401
        assert approval_file.exists()

        approved_resp = httpx.get(
            f"{base_url}/approve?id={approval_file.name}&token={secret}", timeout=5
        )
        assert approved_resp.status_code == 200
        assert "Approved!" in approved_resp.text

        # --- Action + reflection: executed, archived and logged --------------
        archived = vault / "Completed" / "executed" / approval_file.name
        assert wait_for(archived.exists), "approved action was never executed/archived"

        log_file = vault / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        assert wait_for(log_file.exists), "no audit log written"

        entries = json.loads(log_file.read_text())
        executed = [e for e in entries if e["id"] == request_id]
        assert executed, "executed action missing from the audit log"
        assert executed[-1]["status"] == "completed"
        assert executed[-1]["completed_at"]

        # The side effect of the approved action must exist.
        tasks = list((vault / "Plans").glob("TASK_*.md"))
        assert tasks, "create_task produced no task file"
        assert "Follow up on" in tasks[0].read_text()

        assert not approval_file.exists()
        assert not (vault / "Approved" / approval_file.name).exists()
    finally:
        filesystem_watcher.stop()
        reasoning_watcher.stop()
        approval_watcher.stop()
        approval_server.stop()
        for thread in threads:
            thread.join(timeout=5)


def test_rejected_action_is_archived_and_never_executed(tmp_path, stub_opencode):
    """A rejection must not execute, and must land in Completed/rejected/."""
    vault = tmp_path / "vault"
    mcp = MCPServer(str(vault), {})

    port = _free_port()
    secret = "reject-token"
    approval_watcher = ApprovalWatcher(
        str(vault),
        mcp,
        notify_email=None,
        approval_port=port,
        approval_url=f"http://127.0.0.1:{port}",
        approval_secret=secret,
    )
    approval_server = start_approval_server(str(vault), port, secret)
    thread = threading.Thread(target=approval_watcher.run, daemon=True)
    thread.start()

    try:
        pending_dir = vault / "Pending_Approval"
        approval_file = pending_dir / "APPROVAL_create_task_reject-1.json"
        approval_file.write_text(
            json.dumps(
                {
                    "id": "reject-1",
                    "action_type": "create_task",
                    "parameters": {"title": "Should never run"},
                    "status": "pending",
                    "created_at": "2026-01-01T00:00:00",
                }
            )
        )

        resp = httpx.get(
            f"http://127.0.0.1:{port}/reject?id={approval_file.name}&token={secret}", timeout=5
        )
        assert resp.status_code == 200

        archived = vault / "Completed" / "rejected" / approval_file.name
        assert wait_for(archived.exists), "rejected request was not archived"

        assert not list((vault / "Plans").glob("TASK_*.md"))
        assert not (vault / "Completed" / "executed" / approval_file.name).exists()
    finally:
        approval_watcher.stop()
        approval_server.stop()
        thread.join(timeout=5)


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]
