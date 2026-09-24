"""Tests for CronScheduler and AutomatedTasks."""

from datetime import datetime, timedelta
from src.watchers.scheduler import CronScheduler, AutomatedTasks
from src.watchers.mcp_server import MCPServer


def test_cron_scheduler_job_management(tmp_path):
    scheduler = CronScheduler(str(tmp_path))
    flag = {"run": False}

    def sample_job():
        flag["run"] = True

    # Add job
    task_id = scheduler.add_interval_job("job-1", "Test Job", sample_job, interval_seconds=10)
    assert task_id == "job-1"
    assert "job-1" in scheduler.tasks

    # Status
    status = scheduler.get_job_status()
    assert any(s["task_id"] == "job-1" for s in status)
    assert scheduler.scheduler.get_job("job-1").args[-1] == {}

    # Remove
    scheduler.remove_job("job-1")
    assert "job-1" not in scheduler.tasks


def test_automated_tasks_update_dashboard(tmp_path):
    mcp = MCPServer(str(tmp_path), {})
    tasks = AutomatedTasks(str(tmp_path), mcp)

    # Place sample files in directories
    (tmp_path / "Needs_Action" / "file1.md").write_text("action 1")
    (tmp_path / "Pending_Approval" / "app1.json").write_text("{}")
    (tmp_path / "Plans" / "plan1.md").write_text("# Plan")

    tasks.update_dashboard()

    dashboard = tmp_path / "Dashboard.md"
    assert dashboard.exists()
    content = dashboard.read_text()
    assert "Dashboard - Personal AI Employee Real-Time Status" in content
    assert "| Needs Action | 1 |" in content
    assert "| Pending Approvals | 1 |" in content
    assert "| Plans | 1 |" in content


def test_automated_tasks_generate_ceo_briefing(tmp_path):
    tasks = AutomatedTasks(str(tmp_path))
    tasks.generate_ceo_briefing()

    today = datetime.now().strftime("%Y-%m-%d")
    briefing = tmp_path / "Briefings" / f"{today}_CEO_Briefing.md"
    assert briefing.exists()
    content = briefing.read_text()
    assert "CEO Briefing" in content
    assert "Executive Summary" in content


def test_automated_tasks_cleanup_old_files(tmp_path):
    tasks = AutomatedTasks(str(tmp_path))
    done_dir = tmp_path / "Done"
    done_dir.mkdir(parents=True)

    old_file = done_dir / "old_done.md"
    old_file.write_text("old file")

    # Change modification time to 40 days ago
    old_time = (datetime.now() - timedelta(days=40)).timestamp()
    import os

    os.utime(old_file, (old_time, old_time))

    new_file = done_dir / "new_done.md"
    new_file.write_text("new file")

    tasks.cleanup_old_files(days=30)

    assert not old_file.exists()
    assert new_file.exists()
