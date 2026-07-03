"""Open persistent browsers for WhatsApp & LinkedIn login, then save sessions."""
from playwright.sync_api import sync_playwright
from pathlib import Path

vault = Path("AI_Employee_Vault")
whatsapp_session = vault / "whatsapp_session"
linkedin_session = vault / "linkedin_session"

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/126.0.0.0 Safari/537.36',
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""

with sync_playwright() as p:
    wa_context = p.chromium.launch_persistent_context(
        str(whatsapp_session), headless=False,
        viewport={"width": 1280, "height": 720}
    )
    wa_page = wa_context.pages[0]
    wa_page.goto("https://web.whatsapp.com")
    print("WhatsApp Web opened — scan QR code to log in.")

    li_context = p.chromium.launch_persistent_context(
        str(linkedin_session), headless=False,
        args=STEALTH_ARGS,
        viewport={"width": 1280, "height": 720}
    )
    li_page = li_context.pages[0]
    li_page.add_init_script(STEALTH_SCRIPT)
    li_page.goto("https://www.linkedin.com")
    print("LinkedIn opened with Chromium + stealth — log in.")

    print("\nBoth browsers open. Log in, then Ctrl+C to save sessions.")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSaving sessions...")
        wa_context.close()
        li_context.close()
        print("Done!")
