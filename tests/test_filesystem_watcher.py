"""Tests for FileSystemWatcher and DropFolderHandler."""

from src.watchers.filesystem_watcher import DropFolderHandler


def test_drop_folder_handler_process_file(tmp_path):
    inbox = tmp_path / "Inbox"
    needs_action = tmp_path / "Needs_Action"
    inbox.mkdir()
    needs_action.mkdir()

    handler = DropFolderHandler(str(tmp_path))

    # Create a test file in inbox
    sample_file = inbox / "client_contract.pdf"
    sample_file.write_bytes(b"%PDF-1.4 test contract content")

    handler.process_file(sample_file)

    # Original file should be removed from inbox
    assert not sample_file.exists()

    # Destination file should exist in Needs_Action with FILE_ prefix
    dest_file = needs_action / "FILE_client_contract.pdf"
    assert dest_file.exists()
    assert dest_file.read_bytes() == b"%PDF-1.4 test contract content"

    # Metadata markdown file should exist
    meta_file = needs_action / "FILE_client_contract.pdf.md"
    assert meta_file.exists()
    content = meta_file.read_text()
    assert "type: file_drop" in content
    assert "original_name: client_contract.pdf" in content
    assert "status: pending" in content


def test_drop_folder_handler_ignores_hidden_files(tmp_path):
    inbox = tmp_path / "Inbox"
    needs_action = tmp_path / "Needs_Action"
    inbox.mkdir()
    needs_action.mkdir()

    handler = DropFolderHandler(str(tmp_path))
    hidden = inbox / ".DS_Store"
    hidden.write_text("hidden")

    handler.process_file(hidden)

    # Hidden file was not moved
    assert hidden.exists()
    assert not (needs_action / "FILE_.DS_Store").exists()


def test_drop_folder_handler_process_existing(tmp_path):
    inbox = tmp_path / "Inbox"
    needs_action = tmp_path / "Needs_Action"
    inbox.mkdir()
    needs_action.mkdir()

    file1 = inbox / "invoice_99.txt"
    file1.write_text("invoice text")
    file2 = inbox / "memo.md"
    file2.write_text("# Memo")

    handler = DropFolderHandler(str(tmp_path))
    handler.process_existing()

    assert not file1.exists()
    assert not file2.exists()
    assert (needs_action / "FILE_invoice_99.txt").exists()
    assert (needs_action / "FILE_invoice_99.txt.md").exists()
    assert (needs_action / "FILE_memo.md").exists()
    assert (needs_action / "FILE_memo.md.md").exists()
