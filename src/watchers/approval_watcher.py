"""
Approval Watcher - Watches approval directories, notifies, and executes actions
"""
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .mcp_server import MCPServer, ActionRequest, ActionStatus
from .gmail_watcher import GmailSender

logger = logging.getLogger(__name__)


class PendingHandler(FileSystemEventHandler):
    """Watches Pending_Approval/ and sends email notification with clickable links"""

    def __init__(self, pending_dir: Path, gmail_sender: Optional[GmailSender] = None,
                 notify_email: Optional[str] = None, base_url: str = "http://localhost:8080"):
        self.pending_dir = pending_dir
        self.gmail_sender = gmail_sender
        self.notify_email = notify_email
        self.base_url = base_url
        self.seen = set()

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        if filepath.suffix == '.json' and filepath.name not in self.seen:
            self.seen.add(filepath.name)
            self._notify(filepath)

    def on_moved(self, event):
        if event.is_directory:
            return
        filepath = Path(event.dest_path)
        if filepath.suffix == '.json' and filepath.name not in self.seen:
            self.seen.add(filepath.name)
            self._notify(filepath)

    def _notify(self, filepath: Path):
        try:
            data = json.loads(filepath.read_text())
        except Exception:
            data = {}

        action_type = data.get('action_type', '?')
        req_id = data.get('id', '?')[:8]
        summary = str(list(data.get('parameters', {}).values())[0] if data.get('parameters') else '')[:60]

        logger.info(f"New approval request: {action_type} ({req_id})")

        if not self.gmail_sender or not self.notify_email:
            logger.info("  → Check pending: python3 approve.py")
            return

        approve_url = f"{self.base_url}/approve?id={filepath.name}"
        reject_url = f"{self.base_url}/reject?id={filepath.name}"
        pending_url = self.base_url
        body = (
            f"A new approval request has been submitted:\n\n"
            f"  Action: {action_type}\n"
            f"  ID: {req_id}\n"
            f"  Summary: {summary}\n\n"
            f"  ✅ Approve: {approve_url}\n"
            f"  ❌ Reject: {reject_url}\n"
            f"  📋 List all: {pending_url}\n\n"
            f"Or use the CLI:\n"
            f"  python3 approve.py approve {filepath.name}\n"
            f"  python3 approve.py reject {filepath.name}"
        )
        html_body = (
            f"<h2>Approval Needed: {action_type}</h2>"
            f"<p><b>ID:</b> {req_id}<br><b>Summary:</b> {summary}</p>"
            f"<p style='margin:24px 0'>"
            f"<a href='{approve_url}' style='display:inline-block;background:#22c55e;color:white;padding:10px 24px;border-radius:6px;text-decoration:none;font-size:16px;margin-right:8px'>✅ Approve</a>"
            f"<a href='{reject_url}' style='display:inline-block;background:#ef4444;color:white;padding:10px 24px;border-radius:6px;text-decoration:none;font-size:16px'>❌ Reject</a>"
            f"</p>"
            f"<p><a href='{pending_url}' style='color:#666'>📋 View all pending</a></p>"
            f"<hr><p style='color:#888;font-size:12px'>Or use CLI: <code>python3 approve.py approve {filepath.name}</code></p>"
        )
        try:
            self.gmail_sender.send_email(
                to=self.notify_email,
                subject=f"[AI Employee] Approval Needed: {action_type}",
                body=body,
                html_body=html_body
            )
            logger.info(f"Email notification sent to {self.notify_email}")
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")


class ApprovalHandler(FileSystemEventHandler):
    """Handles new files in Approved/ and Rejected/ directories"""

    def __init__(self, approved_dir: Path, rejected_dir: Path, mcp: Optional[MCPServer] = None):
        self.approved_dir = approved_dir
        self.rejected_dir = rejected_dir
        self.mcp = mcp
        self.processed = set()
        self.completed_dir = approved_dir.parent / "Completed"
        self.completed_dir.mkdir(parents=True, exist_ok=True)

    def _load_action(self, filepath: Path) -> Optional[dict]:
        try:
            with open(filepath) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load action file {filepath}: {e}")
            return None

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        self._handle_file(filepath)

    def on_moved(self, event):
        if event.is_directory:
            return
        filepath = Path(event.dest_path)
        self._handle_file(filepath)

    def _handle_file(self, filepath: Path):
        if filepath.suffix != '.json':
            return
        if filepath.name in self.processed:
            return
        self.processed.add(filepath.name)

        parent_dir = filepath.parent

        if parent_dir == self.approved_dir:
            self._process_approved(filepath)
        elif parent_dir == self.rejected_dir:
            self._process_rejected(filepath)

    def _process_approved(self, filepath: Path):
        """Execute an approved action"""
        data = self._load_action(filepath)
        if not data:
            return

        logger.info(f"Action approved: {data.get('id', 'unknown')} ({data.get('action_type', '?')})")

        if not self.mcp:
            logger.warning("No MCP Server available, cannot execute action")
            self._archive_file(filepath, "approved_unprocessed")
            return

        try:
            action = ActionRequest.from_dict(data)
            action.status = ActionStatus.APPROVED
            action.approved_at = datetime.now().isoformat()

            result = self.mcp.action_executor.execute(action)
            self.mcp._save_action(action)

            if result.get('success'):
                logger.info(f"✅ Action executed: {action.id}")
            else:
                logger.error(f"❌ Action failed: {action.id} - {result.get('error')}")

            self._archive_file(filepath, "executed" if result.get('success') else "failed")
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            self._archive_file(filepath, "failed")

    def _process_rejected(self, filepath: Path):
        """Log a rejected action"""
        data = self._load_action(filepath)
        if data:
            logger.info(f"Action rejected: {data.get('id', 'unknown')} ({data.get('action_type', '?')})")
        self._archive_file(filepath, "rejected")

    def _archive_file(self, filepath: Path, subfolder: str):
        """Move processed file to Completed/<subfolder>/"""
        target_dir = self.completed_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filepath.name
        filepath.rename(target)
        logger.info(f"Archived {filepath.name} to Completed/{subfolder}/")


class ApprovalWatcher:
    """Watches approval directories, notifies, and executes actions"""

    def __init__(self, vault_path: str, mcp_server: Optional[MCPServer] = None,
                 notify_email: Optional[str] = None, approval_port: int = 8080,
                 approval_url: Optional[str] = None):
        self.vault_path = Path(vault_path)
        self.notify_email = notify_email
        self.approval_port = approval_port
        self.approval_url = approval_url
        self.pending_dir = self.vault_path / "Pending_Approval"
        self.approved_dir = self.vault_path / "Approved"
        self.rejected_dir = self.vault_path / "Rejected"
        self.mcp = mcp_server
        self.running = False
        self.observer = None
        self.handler = None
        self.pending_handler = None

        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)
        self.rejected_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        self.running = True
        self.handler = ApprovalHandler(self.approved_dir, self.rejected_dir, self.mcp)

        # Setup email notifier if configured
        gmail_sender = None
        if self.mcp and self.notify_email:
            try:
                sender = self.mcp.gmail_sender
                if sender:
                    gmail_sender = sender
            except Exception:
                logger.warning("GmailSender not available — notifications disabled")
        if self.approval_url:
            base_url = self.approval_url
        else:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                base_url = f"http://{ip}:{self.approval_port}"
                logger.info(f"Auto-detected local IP: {ip}")
            except Exception:
                base_url = f"http://localhost:{self.approval_port}"
                logger.warning("Could not detect local IP, falling back to localhost")
        self.pending_handler = PendingHandler(self.pending_dir, gmail_sender, self.notify_email, base_url)

        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.approved_dir), recursive=False)
        self.observer.schedule(self.handler, str(self.rejected_dir), recursive=False)
        self.observer.schedule(self.pending_handler, str(self.pending_dir), recursive=False)
        self.observer.start()
        logger.info(f"ApprovalWatcher watching: {self.pending_dir}, {self.approved_dir}, {self.rejected_dir}")
        if self.notify_email:
            logger.info(f"Email notifications to: {self.notify_email}")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
