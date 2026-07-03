"""
LinkedIn Login Utility - Regenerates fresh Playwright session cookies
Run once in headed mode, scan QR/enter credentials, then the session
works for headless posting and monitoring.

Usage:
    python3 scripts/login_linkedin.py
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.watchers.playwright_manager import manager as pw_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("linkedin_login")

SESSION_PATH = Path("AI_Employee_Vault/linkedin_session")
SESSION_PATH.mkdir(parents=True, exist_ok=True)

def main():
    was_alive = False
    try:
        pw_manager.start()
        pw = pw_manager._playwright

        print("\n╔══════════════════════════════════════════════════════════╗")
        print("║              LinkedIn Session Login                    ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print("  A browser window will open.")
        print("  1. Log in to LinkedIn manually (or scan QR)")
        print("  2. Wait until your feed appears")
        print("  3. This script will detect login and save the session")
        print()

        browser = pw.chromium.launch_persistent_context(
            str(SESSION_PATH),
            headless=False,
            channel="chromium",
            viewport={'width': 1280, 'height': 720}
        )
        page = browser.pages[0]
        page.goto('https://www.linkedin.com')

        print("  ⏳ Waiting for login (up to 5 minutes)...")
        print("     (The script auto-detects when you're logged in)")
        page.wait_for_selector('[data-test-id="nav-home"]', timeout=300000)
        print("  ✅ Login detected! Session saved.")

        # Verify feed loaded
        title = page.title()
        print(f"  📄 Page title: {title}")

        browser.close()
        print("  ✅ LinkedIn session saved to", SESSION_PATH)
        print()

        # Verify session works headlessly
        print("  🔍 Verifying session in headless mode...")
        browser2 = pw.chromium.launch_persistent_context(
            str(SESSION_PATH),
            headless=True,
            channel="chromium",
            viewport={'width': 1280, 'height': 720}
        )
        page2 = browser2.pages[0]
        page2.goto('https://www.linkedin.com')
        try:
            page2.wait_for_selector('[data-test-id="nav-home"]', timeout=15000)
            print("  ✅ Headless verification passed!")
        except Exception:
            print("  ⚠️  Headless verification failed. Session may need re-login.")
        browser2.close()

    except KeyboardInterrupt:
        print("\n  ⏹ Cancelled by user")
    except Exception as e:
        logger.error(f"Failed: {e}")
    finally:
        pw_manager.stop()

if __name__ == "__main__":
    main()
