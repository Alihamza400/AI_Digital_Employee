"""
Approval HTTP Server - Lightweight server for clickable approve/reject links
"""
import json
import logging
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

HTML_SUCCESS = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Employee - {result}</title>
<style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f5f5f5}}
.card{{background:white;border-radius:12px;padding:2rem;box-shadow:0 2px 8px rgba(0,0,0,.1);text-align:center;max-width:400px}}
.icon{{font-size:48px;margin-bottom:1rem}}
h1{{margin:0 0 .5rem;color:{color}}}
p{{color:#666;margin:.5rem 0}}
.code{{background:#f0f0f0;padding:.5rem;border-radius:6px;font-family:monospace;word-break:break-all;margin:1rem 0}}</style></head><body>
<div class="card">
<div class="icon">{icon}</div>
<h1>{title}</h1>
<p>{message}</p>
<div class="code">{filename}</div>
<p><a href="/" style="color:#666;">← Back to pending list</a></p>
</div></body></html>"""

HTML_LIST = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Employee - Pending Approvals</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:2rem auto;padding:0 1rem;background:#f5f5f5}}
h1{{color:#333}}
.pending{{background:white;border-radius:8px;padding:1rem;margin:.5rem 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.id{{font-size:.8rem;color:#888}}
.actions{{margin-top:.5rem}}
.actions a{{display:inline-block;padding:.4rem 1rem;border-radius:6px;text-decoration:none;margin-right:.5rem;font-size:.9rem}}
.approve{{background:#22c55e;color:white}}
.reject{{background:#ef4444;color:white}}
.empty{{color:#888;text-align:center;margin-top:3rem}}</style></head><body>
<h1>⏳ Pending Approvals</h1>
{items}
</body></html>"""


class ApprovalRequestHandler(BaseHTTPRequestHandler):
    vault_path: Path = Path("AI_Employee_Vault")
    secret: str = ""

    def log_message(self, fmt, *args):
        logger.info(f"[HTTP] {args[0]}")

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _redirect(self, path):
        self.send_response(302)
        self.send_header("Location", path)
        self.end_headers()

    def _verify_secret(self, params):
        if not self.secret:
            return True
        return params.get("token", [None])[0] == self.secret

    def _list_pending(self):
        pending_dir = self.vault_path / "Pending_Approval"
        files = sorted(pending_dir.glob("*.json"))
        if not files:
            items = '<p class="empty">No pending approvals.</p>'
        else:
            items = ""
            for f in files:
                try:
                    data = json.loads(f.read_text())
                    aid = data.get("id", "?")[:12]
                    atype = data.get("action_type", "?")
                    items += f'<div class="pending">'
                    items += f'<strong>{atype}</strong> <span class="id">({aid})</span>'
                    items += f'<div class="actions">'
                    items += f'<a class="approve" href="/approve?id={f.name}">✅ Approve</a>'
                    items += f'<a class="reject" href="/reject?id={f.name}">❌ Reject</a>'
                    items += f'</div></div>'
                except Exception:
                    items += f'<div class="pending">⚠ Could not read: {f.name}</div>'
        html = HTML_LIST.replace("{items}", items)
        self._send_html(html)

    def _handle_approve(self, params):
        filename = (params.get("id") or [None])[0]
        if not filename or ".." in filename or "/" in filename:
            self._send_html(HTML_SUCCESS.format(icon="⚠️", title="Invalid Request",
                          color="#eab308", message="No filename provided.",
                          filename="", result="Error"), 400)
            return
        src = self.vault_path / "Pending_Approval" / filename
        dst = self.vault_path / "Approved" / filename
        if not src.exists():
            self._send_html(HTML_SUCCESS.format(icon="⚠️", title="Not Found",
                          color="#eab308", message="Approval request not found.",
                          filename=filename, result="Error"), 404)
            return
        src.rename(dst)
        self._send_html(HTML_SUCCESS.format(icon="✅", title="Approved!",
                      color="#22c55e", message="Action has been approved and queued for execution.",
                      filename=filename, result="Approved"))

    def _handle_reject(self, params):
        filename = (params.get("id") or [None])[0]
        if not filename or ".." in filename or "/" in filename:
            self._send_html(HTML_SUCCESS.format(icon="⚠️", title="Invalid Request",
                          color="#eab308", message="No filename provided.",
                          filename="", result="Error"), 400)
            return
        src = self.vault_path / "Pending_Approval" / filename
        dst = self.vault_path / "Rejected" / filename
        if not src.exists():
            self._send_html(HTML_SUCCESS.format(icon="⚠️", title="Not Found",
                          color="#eab308", message="Approval request not found.",
                          filename=filename, result="Error"), 404)
            return
        src.rename(dst)
        self._send_html(HTML_SUCCESS.format(icon="❌", title="Rejected",
                      color="#ef4444", message="Action has been rejected.",
                      filename=filename, result="Rejected"))

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path.rstrip("/")

        if path == "" or path == "/":
            return self._list_pending()
        elif path == "/approve":
            return self._handle_approve(params)
        elif path == "/reject":
            return self._handle_reject(params)
        else:
            self._send_html(HTML_SUCCESS.format(icon="404", title="Not Found",
                          color="#666", message="Page not found.",
                          filename="", result="Error"), 404)


class ApprovalServer:
    def __init__(self, vault_path: str, port: int = 8080, secret: str = ""):
        self.vault_path = Path(vault_path)
        self.port = port
        self.secret = secret
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def run(self):
        ApprovalRequestHandler.vault_path = self.vault_path
        ApprovalRequestHandler.secret = self.secret
        self.server = HTTPServer(("0.0.0.0", self.port), ApprovalRequestHandler)
        logger.info(f"✅ Approval HTTP server running on http://localhost:{self.port}")
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            logger.info(f"   📱 Network access: http://{ip}:{self.port}")
        except Exception:
            pass
        if self.secret:
            logger.info(f"   🔑 Secret token: {self.secret}")
        self.server.serve_forever()

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        return self.thread

    def stop(self):
        if self.server:
            self.server.shutdown()


def start_approval_server(vault_path: str, port: int = 8080, secret: str = "") -> ApprovalServer:
    server = ApprovalServer(vault_path, port, secret)
    server.start()
    return server
