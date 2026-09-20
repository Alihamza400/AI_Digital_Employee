"""Tests for AIReasoningWatcher and NeedsActionHandler."""

from unittest.mock import patch, MagicMock
from src.watchers.ai_reasoning_watcher import NeedsActionHandler


def test_needs_action_handler_should_process(tmp_path):
    needs_action = tmp_path / "Needs_Action"
    needs_action.mkdir()
    done = needs_action / "Done"
    done.mkdir()

    handler = NeedsActionHandler(needs_action, tmp_path)

    valid_md = needs_action / "EMAIL_123.md"
    valid_md.write_text("email content")

    valid_json = needs_action / "TASK_456.json"
    valid_json.write_text("{}")

    invalid_ext = needs_action / "image.png"
    invalid_ext.write_text("png")

    file_in_done = done / "EMAIL_old.md"
    file_in_done.write_text("old")

    assert handler._should_process(valid_md) is True
    assert handler._should_process(valid_json) is True
    assert handler._should_process(invalid_ext) is False
    assert handler._should_process(file_in_done) is False


def test_needs_action_handler_ignores_already_processed(tmp_path):
    needs_action = tmp_path / "Needs_Action"
    needs_action.mkdir()
    done = needs_action / "Done"
    done.mkdir()

    already_done = done / "PROCESSED_FILE.md"
    already_done.write_text("done")

    handler = NeedsActionHandler(needs_action, tmp_path)
    assert "PROCESSED_FILE.md" in handler.processed

    duplicate = needs_action / "PROCESSED_FILE.md"
    duplicate.write_text("duplicate")
    assert handler._should_process(duplicate) is False


@patch("subprocess.run")
def test_needs_action_handler_run_opencode_command(mock_subproc, tmp_path):
    vault = tmp_path / "AI_Employee_Vault"
    needs_action = vault / "Needs_Action"
    needs_action.mkdir(parents=True)
    handler = NeedsActionHandler(needs_action, vault, model="anthropic/claude-3-5-sonnet")

    target_file = needs_action / "FILE_invoice.md"
    target_file.write_text("invoice details")

    mock_subproc.return_value = MagicMock(returncode=0, stdout='{"type":"done"}', stderr="")

    handler._run_opencode(target_file)

    mock_subproc.assert_called_once()
    called_cmd = mock_subproc.call_args[0][0]
    assert called_cmd[0] == "opencode"
    assert called_cmd[1] == "run"
    assert "--model" in called_cmd
    assert "anthropic/claude-3-5-sonnet" in called_cmd
    assert "--auto" in called_cmd


@patch("subprocess.run")
def test_run_opencode_passes_agent_and_timeout(mock_subproc, tmp_path):
    """The configured agent and timeout must reach the opencode subprocess."""
    vault = tmp_path / "AI_Employee_Vault"
    needs_action = vault / "Needs_Action"
    needs_action.mkdir(parents=True)
    handler = NeedsActionHandler(
        needs_action,
        vault,
        model="google/gemini-3.6-flash",
        agent="ai-employee",
        timeout=45,
    )

    target_file = needs_action / "FILE_invoice.md"
    target_file.write_text("invoice details")

    mock_subproc.return_value = MagicMock(returncode=0, stdout="", stderr="")
    handler._run_opencode(target_file)

    called_cmd = mock_subproc.call_args[0][0]
    assert "--agent" in called_cmd
    assert "ai-employee" in called_cmd
    assert mock_subproc.call_args.kwargs["timeout"] == 45


@patch("subprocess.run")
def test_run_opencode_omits_agent_when_unset(mock_subproc, tmp_path):
    vault = tmp_path / "AI_Employee_Vault"
    needs_action = vault / "Needs_Action"
    needs_action.mkdir(parents=True)
    handler = NeedsActionHandler(needs_action, vault)

    target_file = needs_action / "FILE_invoice.md"
    target_file.write_text("invoice details")

    mock_subproc.return_value = MagicMock(returncode=0, stdout="", stderr="")
    handler._run_opencode(target_file)

    called_cmd = mock_subproc.call_args[0][0]
    assert "--agent" not in called_cmd
    assert "--model" not in called_cmd


def test_process_file_is_not_triggered_twice(tmp_path):
    """A file already dispatched must not spawn a second reasoning run."""
    vault = tmp_path / "AI_Employee_Vault"
    needs_action = vault / "Needs_Action"
    needs_action.mkdir(parents=True)
    handler = NeedsActionHandler(needs_action, vault)

    target_file = needs_action / "FILE_dupe.md"
    target_file.write_text("content")

    with patch.object(handler, "_run_opencode") as mock_run:
        handler._process_file(target_file)
        handler._process_file(target_file)

    assert mock_run.call_count == 1
