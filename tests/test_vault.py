"""Tests for Obsidian Vault structure and setup."""

from pathlib import Path
from src.watchers.mcp_server import MCPServer


def test_vault_core_files_exist():
    vault = Path("AI_Employee_Vault")
    assert vault.exists()
    assert (vault / "Company_Handbook.md").exists()
    assert (vault / "Business_Goals.md").exists()
    assert (vault / "Dashboard.md").exists()
    assert (vault / "LinkedIn_Templates").exists()


def test_mcp_setup_directories(tmp_path):
    MCPServer(str(tmp_path), {})
    expected_dirs = [
        "Inbox",
        "Needs_Action",
        "Needs_Action/Done",
        "In_Progress",
        "Done",
        "Plans",
        "Pending_Approval",
        "Approved",
        "Rejected",
        "Completed",
        "Completed/executed",
        "Completed/failed",
        "Completed/rejected",
        "Logs",
        "Briefings",
        "Audits",
        "Accounting",
        "LinkedIn_Templates",
        "Drafts",
    ]
    for d in expected_dirs:
        assert (tmp_path / d).exists()
        assert (tmp_path / d).is_dir()
