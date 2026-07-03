"""
Personal AI Employee - Your autonomous assistant
"""
import sys, time, signal, logging, socket, subprocess, threading, re
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.watchers import (
    FileSystemWatcher, GmailWatcher,
    AIReasoningWatcher, ApprovalWatcher, start_approval_server,
    MCPServer, ScheduledTaskManager
)
from src.config import Settings, settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VAULT = settings.vault


def _detect_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def _start_tunnel(local_port: int) -> tuple[threading.Thread, str | None]:
    result_holder = []
    def _run():
        try:
            cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-R", f"80:localhost:{local_port}",
                "nokey@localhost.run"
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                line = line.strip()
                logger.info(f"[tunnel] {line}")
                m = re.search(r'(https://[a-z0-9-]+\.lhr\.life)', line)
                if m and not result_holder:
                    result_holder.append(m.group(1))
            proc.wait()
        except Exception as e:
            logger.warning(f"Tunnel failed: {e}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(10)
    url = result_holder[0] if result_holder else None
    return t, url


def print_qr(url: str):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=2)
        qr.add_data(url)
        print("\n" + "─" * 40)
        qr.print_ascii()
        print("─" * 40)
        print(f"  Scan QR or open: {url}\n")
    except ImportError:
        print(f"\n  Open on phone: {url}\n")


def print_status(s: Settings, tunnel_url: str | None = None):
    url = tunnel_url or s.approval_url or f"http://localhost:{s.approval_port}"
    email = s.notify_email or 'not set'
    print("""
╔══════════════════════════════════════════════╗
║       Personal AI Employee — Running         ║
╚══════════════════════════════════════════════╝
""")
    print(f"  📧  Email:    {email}")
    print(f"  📁  Inbox:    {s.vault / 'Inbox'}")
    if tunnel_url:
        print(f"  🌐  Tunnel:   {tunnel_url}")
    print(f"  🌐  Approve:  {url}")
    print(f"  ⏹   Stop:     Ctrl+C")
    print()

    if tunnel_url or 'localhost' not in url:
        print_qr(url)


class PersonalAIEmployee:
    def __init__(self, s: Settings):
        self.settings = s
        self.vault_path = s.vault
        self.running = False
        self.threads: list[Thread] = []
        self.mcp = MCPServer(str(s.vault), s.to_dict())
        self.filesystem_watcher = None
        self.gmail_watcher = None
        self.ai_reasoning_watcher = None
        self.approval_watcher = None
        self.approval_server = None
        self.task_manager = None
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.running = False

    def initialize(self):
        logger.info("Starting components...")

        self.filesystem_watcher = FileSystemWatcher(str(self.vault_path))
        t = Thread(target=self.filesystem_watcher.run, daemon=True)
        t.start()
        self.threads.append(t)

        if self.settings.gmail_configured:
            try:
                self.gmail_watcher = GmailWatcher(
                    str(self.vault_path),
                    self.settings.gmail_client_config_dict,
                    self.settings.gmail_token_dict
                )
                t = Thread(target=self.gmail_watcher.run, daemon=True)
                t.start()
                self.threads.append(t)
            except Exception as e:
                logger.warning(f"Gmail: {e}")
        else:
            logger.info("Gmail: not configured (set GMAIL_CLIENT_CONFIG and GMAIL_TOKEN_JSON in .env)")

        try:
            self.ai_reasoning_watcher = AIReasoningWatcher(str(self.vault_path))
            t = Thread(target=self.ai_reasoning_watcher.run, daemon=True)
            t.start()
            self.threads.append(t)
        except Exception as e:
            logger.warning(f"AIReasoning: {e}")

        try:
            approval_port = self.settings.approval_port
            self.approval_server = start_approval_server(str(self.vault_path), approval_port)
            self.threads.append(self.approval_server.thread)
        except Exception as e:
            logger.warning(f"Approval server: {e}")
            self.approval_server = None

        try:
            self.approval_watcher = ApprovalWatcher(
                str(self.vault_path), self.mcp,
                self.settings.notify_email,
                self.settings.approval_port,
                self.settings.approval_url or None
            )
            t = Thread(target=self.approval_watcher.run, daemon=True)
            t.start()
            self.threads.append(t)
        except Exception as e:
            logger.warning(f"ApprovalWatcher: {e}")

        try:
            self.task_manager = ScheduledTaskManager(str(self.vault_path), self.mcp)
            self.task_manager.start()
            logger.info("ScheduledTaskManager started")
        except Exception as e:
            logger.warning(f"ScheduledTaskManager: {e}")

    def run(self):
        self.running = True
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self):
        self.running = False
        if self.task_manager:
            self.task_manager.stop()
        for t in self.threads:
            t.join(timeout=3)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Personal AI Employee')
    parser.add_argument('--email', help='Email for approval notifications')
    parser.add_argument('--approval-url', help='Public URL for links (e.g. http://192.168.1.100:8080)')
    parser.add_argument('--approval-port', type=int, default=8080)
    parser.add_argument('--tunnel', action='store_true', help='Create public tunnel via localhost.run')
    parser.add_argument('--test', action='store_true', help='Run tests')
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    s = Settings()

    if args.email:
        s.notify_email = args.email
    if args.approval_url:
        s.approval_url = args.approval_url

    s.approval_port = args.approval_port

    tunnel_url = None
    if args.tunnel:
        s.approval_url = ''
        print("\n🌐 Creating public tunnel via localhost.run...")
        _, tunnel_url = _start_tunnel(args.approval_port)
        if tunnel_url:
            s.approval_url = tunnel_url
            print(f"\n  ✅ Tunnel URL: {tunnel_url}\n")
        else:
            print("  ⚠ Tunnel failed, falling back to local network\n")

    print_status(s, tunnel_url)

    employee = PersonalAIEmployee(s)
    employee.initialize()
    employee.run()


def run_tests():
    import unittest

    class TestAIEmployee(unittest.TestCase):
        def test_vault(self):
            self.assertTrue(VAULT.exists())
            for folder in ['Inbox', 'Needs_Action', 'Done', 'Logs']:
                self.assertTrue((VAULT / folder).exists())
        def test_config(self):
            s = Settings()
            self.assertTrue(hasattr(s, 'notify_email'))

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAIEmployee)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n✅ All tests passed")
    else:
        print(f"\n❌ {len(result.failures) + len(result.errors)} test(s) failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
