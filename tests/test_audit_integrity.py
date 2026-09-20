"""Regression tests for the audit trail, inbox intake, scheduler and dashboard."""

import json
from datetime import datetime
from threading import Thread

from src.watchers.filesystem_watcher import DropFolderHandler
from src.watchers.mcp_server import (
    ActionRequest,
    ActionStatus,
    ActionType,
    ApprovalWorkflow,
    MCPServer,
)
from src.watchers.scheduler import AutomatedTasks, CronScheduler, ScheduledTaskManager


def _today_log(vault):
    return vault / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.json"


def test_concurrent_action_logging_keeps_every_entry(tmp_path):
    """
    The daily log is read-modify-written by several threads at once. An
    unserialized write silently drops entries and corrupts the audit trail.
    """
    mcp = MCPServer(str(tmp_path), {})
    log_file = _today_log(tmp_path)
    writes_per_thread = 30
    thread_count = 12

    def worker(worker_id: int):
        for i in range(writes_per_thread):
            mcp._save_action(
                ActionRequest(
                    id=f"{worker_id}-{i}",
                    action_type=ActionType.CREATE_TASK,
                    parameters={"title": f"task {worker_id}-{i}"},
                    status=ActionStatus.COMPLETED,
                    created_at="2026-01-01T00:00:00",
                )
            )

    threads = [Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    entries = json.loads(log_file.read_text())
    expected = writes_per_thread * thread_count
    assert len(entries) == expected
    assert len({e["id"] for e in entries}) == expected


def test_approval_decision_is_persisted_before_archiving(tmp_path):
    """The archived request must record the human decision, not a stale 'pending'."""
    workflow = ApprovalWorkflow(str(tmp_path))
    req = ActionRequest(
        id="persist-01",
        action_type=ActionType.CREATE_TASK,
        parameters={"title": "Persist me"},
        status=ActionStatus.PENDING,
        created_at="2026-01-01T00:00:00",
    )
    workflow.create_approval_request(req)

    assert workflow.approve("persist-01") is True

    archived = next((tmp_path / "Approved").glob("*.json"))
    data = json.loads(archived.read_text())
    assert data["status"] == "approved"
    assert data["approved_at"]


def test_rejection_reason_is_persisted_before_archiving(tmp_path):
    workflow = ApprovalWorkflow(str(tmp_path))
    req = ActionRequest(
        id="persist-02",
        action_type=ActionType.POST_LINKEDIN,
        parameters={"content": "draft"},
        status=ActionStatus.PENDING,
        created_at="2026-01-01T00:00:00",
    )
    workflow.create_approval_request(req)

    assert workflow.reject("persist-02", reason="Not on brand") is True

    archived = next((tmp_path / "Rejected").glob("*.json"))
    data = json.loads(archived.read_text())
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Not on brand"
    assert data["rejected_at"]


def test_dropping_the_same_filename_twice_keeps_both_action_files(tmp_path):
    """A repeat drop must not silently overwrite the earlier action file."""
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "Needs_Action").mkdir()
    handler = DropFolderHandler(str(tmp_path))

    first = tmp_path / "Inbox" / "report.pdf"
    first.write_bytes(b"first version")
    handler.process_file(first)

    second = tmp_path / "Inbox" / "report.pdf"
    second.write_bytes(b"second version")
    handler.process_file(second)

    needs_action = tmp_path / "Needs_Action"
    original = needs_action / "FILE_report.pdf"
    duplicate = needs_action / "FILE_report_1.pdf"

    assert original.read_bytes() == b"first version"
    assert duplicate.read_bytes() == b"second version"

    # Each payload keeps its own metadata file.
    assert (needs_action / "FILE_report.pdf.md").exists()
    assert (needs_action / "FILE_report_1.pdf.md").exists()


def test_scheduler_records_success_telemetry(tmp_path):
    """A job that ran must report a run count and last-run timestamp."""
    scheduler = CronScheduler(str(tmp_path))
    calls = {"count": 0}

    def job():
        calls["count"] += 1

    scheduler.add_interval_job("telemetry", "Telemetry Job", job, interval_seconds=3600)

    assert scheduler.run_job_now("telemetry") is True

    status = {s["task_id"]: s for s in scheduler.get_job_status()}["telemetry"]
    assert calls["count"] == 1
    assert status["run_count"] == 1
    assert status["last_run"] is not None
    assert status["last_error"] is None


def test_scheduler_records_failure_telemetry(tmp_path):
    scheduler = CronScheduler(str(tmp_path))

    def boom():
        raise RuntimeError("kaboom")

    scheduler.add_interval_job("boom", "Failing Job", boom, interval_seconds=3600)

    assert scheduler.run_job_now("boom") is True

    status = {s["task_id"]: s for s in scheduler.get_job_status()}["boom"]
    assert status["run_count"] == 1
    assert "kaboom" in status["last_error"]


def test_paused_job_is_skipped(tmp_path):
    scheduler = CronScheduler(str(tmp_path))
    calls = {"count": 0}

    def job():
        calls["count"] += 1

    scheduler.add_interval_job("paused", "Paused Job", job, interval_seconds=3600)
    scheduler.tasks["paused"].enabled = False

    scheduler.run_job_now("paused")

    assert calls["count"] == 0


def test_failed_job_add_does_not_leave_a_ghost_task(tmp_path):
    scheduler = CronScheduler(str(tmp_path))

    try:
        scheduler.add_cron_job("broken", "Broken", lambda: None, "not a cron expression")
    except Exception:
        pass

    assert "broken" not in scheduler.tasks
    assert scheduler.get_job_status() == []


def test_dashboard_counts_archived_completed_actions(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    for subfolder in ("executed", "failed"):
        target = tmp_path / "Completed" / subfolder
        target.mkdir(parents=True, exist_ok=True)
        (target / f"APPROVAL_{subfolder}.json").write_text("{}")

    AutomatedTasks(str(tmp_path), mcp).update_dashboard()

    dashboard = (tmp_path / "Dashboard.md").read_text()
    assert "| Completed | 2 |" in dashboard


def test_dashboard_reports_actual_scheduled_job_count(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    manager = ScheduledTaskManager(str(tmp_path), mcp)

    manager.tasks.update_dashboard()

    dashboard = (tmp_path / "Dashboard.md").read_text()
    job_count = len(manager.scheduler.tasks)
    assert job_count > 0
    assert f"✅ RUNNING ({job_count} jobs)" in dashboard
