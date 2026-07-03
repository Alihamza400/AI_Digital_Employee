"""
Session Health Check - Verifies LinkedIn and WhatsApp sessions are valid
without opening headed browser windows.

Usage:
    python3 scripts/check_sessions.py
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.watchers.playwright_manager import manager as pw_manager

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("session_check")

VAULT = Path("AI_Employee_Vault")

def check_session(name: str, session_path: Path, url: str, selector: str) -> str:
    if not session_path.is_dir() or not any(session_path.iterdir()):
        return "❌ No session directory"
    try:
        pw_manager.start()
        pw = pw_manager._playwright
        browser = pw.chromium.launch_persistent_context(
            str(session_path), headless=True, channel="chromium",
            viewport={'width': 1280, 'height': 720}
        )
        page = browser.pages[0]
        page.goto(url)
        try:
            page.wait_for_selector(selector, timeout=15000)
            result = "✅ Valid"
        except Exception:
            result = "⚠️  Expired — run the login script"
        browser.close()
        return result
    except Exception as e:
        return f"❌ Error: {e}"
    finally:
        pw_manager.stop()

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              Session Health Check                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    print(f"  LinkedIn  {check_session('LinkedIn', VAULT/'linkedin_session', 'https://www.linkedin.com', '[data-test-id=\"nav-home\"]')}")
    print(f"  WhatsApp  {check_session('WhatsApp', VAULT/'whatsapp_session', 'https://web.whatsapp.com', '[data-testid=\"chat-list\"]')}")
    print()
    print("  To refresh a session:")
    print("    python3 scripts/login_linkedin.py")
    print()

if __name__ == "__main__":
    main()
