"""
WhatsApp Watcher - Monitors WhatsApp Web for new messages
"""
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .base_watcher import BaseWatcher
from .playwright_manager import manager as pw_manager

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class WhatsAppWatcher(BaseWatcher):
    """Monitors WhatsApp Web for new messages"""
    
    STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
    ]
    STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""

    def __init__(self, vault_path: str, session_path: str, check_interval: int = 30):
        super().__init__(vault_path, check_interval)
        self.session_path = Path(session_path)
        self.keywords = ['urgent', 'asap', 'invoice', 'payment', 'help', 'order', 'quote']
        self.processed_messages = set()
        self.browser = None
        self.context = None
        self.page = None
        self._session_valid = False
        self._init_browser()

    def _init_browser(self):
        pw_manager.start()
        self.browser = pw_manager.create_context(
            self.session_path, headless=True,
            args=self.STEALTH_ARGS,
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        )
        self.page = self.browser.pages[0]
        self.page.add_init_script(self.STEALTH_SCRIPT)
        self.page.goto('https://web.whatsapp.com')
        self._session_valid = self._wait_for_session()
        logger.info("WhatsApp Watcher initialized")

    def _wait_for_session(self, timeout: int = 90) -> bool:
        """Poll for chat-list selector with increasing waits"""
        for i in range(timeout):
            try:
                if self.page.query_selector('[data-testid="chat-list"]'):
                    logger.info("WhatsApp session valid (headless)")
                    return True
            except:
                pass
            time.sleep(1)
        logger.warning("WhatsApp session expired or still loading.")
        return False

    def ensure_session(self):
        if self._session_valid:
            return True
        if self.browser:
            self.browser.close()
        self.browser = pw_manager.create_context(
            self.session_path, headless=False,
            args=self.STEALTH_ARGS,
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        )
        self.page = self.browser.pages[0]
        self.page.add_init_script(self.STEALTH_SCRIPT)
        self.page.goto('https://web.whatsapp.com')
        logger.warning("==> Please log in to WhatsApp Web in the opened browser window <==")
        self._session_valid = self._wait_for_session(timeout=300)
        if self._session_valid:
            logger.info("WhatsApp re-login successful")
            return True
        logger.error("WhatsApp re-login timed out")
        return False

    def _has_valid_session(self) -> bool:
        """Check if a valid Playwright session directory exists."""
        return self.session_path.is_dir() and any(self.session_path.iterdir())
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check for new messages with keywords"""
        if not PLAYWRIGHT_AVAILABLE or not self.page:
            return []
        
        try:
            # Find unread messages
            unread_chats = self.page.query_selector_all('[aria-label*="unread"]')
            messages = []
            
            for chat in unread_chats:
                text = chat.inner_text().lower()
                if any(kw in text for kw in self.keywords):
                    chat_id = chat.get_attribute('data-chat-id') or str(hash(chat.inner_text()))
                    if chat_id not in self.processed_messages:
                        messages.append({
                            'chat_id': chat_id,
                            'text': chat.inner_text(),
                            'timestamp': datetime.now().isoformat()
                        })
            
            return messages
        except Exception as e:
            logger.error(f"Error checking WhatsApp: {e}")
            return []
    
    def create_action_file(self, item) -> Path:
        """Create action file for WhatsApp message"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"WHATSAPP_{item['chat_id']}_{timestamp}.md"
        filepath = self.needs_action / filename
        
        content = f"""---
type: whatsapp
chat_id: {item['chat_id']}
received: {item['timestamp']}
priority: high
status: pending
---

## WhatsApp Message
{item['text']}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Create task from message
- [ ] Archive after processing
"""
        
        filepath = self.needs_action / filename
        filepath.write_text(content)
        self.processed_messages.add(item['chat_id'])
        logger.info(f"Created action file for WhatsApp message: {item['chat_id']}")
        
        return filepath
    
    def close(self):
        """Close browser"""
        if self.browser:
            self.browser.close()
        pw_manager.stop()

    def stop(self):
        self.close()

class WhatsAppSender:
    """Sends WhatsApp messages via WhatsApp Web"""

    STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
    ]
    STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""

    def __init__(self, session_path: str):
        self.session_path = Path(session_path)
        self.browser = None
        self.page = None
        self._session_valid = False
        self._init_browser()

    def _has_valid_session(self) -> bool:
        return self.session_path.is_dir() and any(self.session_path.iterdir())

    def _init_browser(self):
        try:
            pw_manager.start()
            self.browser = pw_manager.create_context(
                self.session_path, headless=True,
                args=self.STEALTH_ARGS,
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
            )
            self.page = self.browser.pages[0]
            self.page.add_init_script(self.STEALTH_SCRIPT)
            self.page.goto('https://web.whatsapp.com')
            self._session_valid = self._wait_for_session()
            logger.info("WhatsApp Sender initialized")
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp Sender: {e}")

    def _wait_for_session(self, timeout: int = 90) -> bool:
        for i in range(timeout):
            try:
                if self.page.query_selector('[data-testid="chat-list"]'):
                    logger.info("WhatsApp Sender session valid")
                    return True
            except:
                pass
            time.sleep(1)
        logger.warning("WhatsApp Sender session expired or still loading.")
        return False

    def ensure_session(self):
        if self._session_valid:
            return True
        if self.browser:
            self.browser.close()
        self.browser = pw_manager.create_context(
            self.session_path, headless=False,
            args=self.STEALTH_ARGS,
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        )
        self.page = self.browser.pages[0]
        self.page.add_init_script(self.STEALTH_SCRIPT)
        self.page.goto('https://web.whatsapp.com')
        logger.warning("==> Please log in to WhatsApp Web in the opened browser window <==")
        self._session_valid = self._wait_for_session(timeout=300)
        if self._session_valid:
            logger.info("WhatsApp re-login successful")
            return True
        logger.error("WhatsApp re-login timed out")
        return False

    def send_message(self, phone_number: str, message: str) -> Dict:
        """Send a WhatsApp message"""
        if not self.page:
            return {'success': False, 'error': 'WhatsApp not initialized'}
        if not self._session_valid:
            return {'success': False, 'error': 'WhatsApp session expired. Call ensure_session() first.'}

        try:
            url = f'https://web.whatsapp.com/send?phone={phone_number}&text={message}'
            self.page.goto(url)
            self.page.wait_for_selector('[data-testid="compose-btn-send"]', timeout=30000)
            self.page.click('[data-testid="compose-btn-send"]')
            
            logger.info(f"Message sent to {phone_number}")
            return {'success': True}
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {'success': False, 'error': str(e)}
    
    def close(self):
        if self.browser:
            self.browser.close()
        pw_manager.stop()