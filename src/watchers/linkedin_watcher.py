"""
LinkedIn Watcher and Post Creator - Monitors LinkedIn and creates posts
"""
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Template

from .base_watcher import BaseWatcher
from .playwright_manager import manager as pw_manager

logger = logging.getLogger(__name__)


STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
]


class LinkedInWatcher(BaseWatcher):
    """Monitors LinkedIn for notifications and messages"""
    
    def __init__(self, vault_path: str, session_path: str, check_interval: int = 300):
        super().__init__(vault_path, check_interval)
        self.session_path = Path(session_path)
        self.browser = None
        self.context = None
        self.page = None
        self.processed_notifications = set()
        self._session_valid = False
        self._init_browser()

    def _has_valid_session(self) -> bool:
        return self.session_path.is_dir() and any(self.session_path.iterdir())

    def _is_logged_in(self):
        """Check if we're on the LinkedIn feed (logged in) by URL"""
        return '/feed/' in (self.page.url if self.page else '')

    def _init_browser(self):
        pw_manager.start()
        self.browser = pw_manager.create_context(
            self.session_path, headless=True,
            args=STEALTH_ARGS,
            viewport={'width': 1280, 'height': 720}
        )
        self.page = self.browser.pages[0]
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        self.page.goto('https://www.linkedin.com')
        self.page.wait_for_timeout(5000)
        if self._is_logged_in():
            self._session_valid = True
            logger.info("LinkedIn session valid (headless)")
        else:
            self._session_valid = False
            logger.warning("LinkedIn session expired. Call ensure_session() for re-login.")
        logger.info("LinkedIn Watcher initialized")

    def ensure_session(self):
        """Open headed browser for re-login if session is expired"""
        if self._session_valid:
            return True
        if self.browser:
            self.browser.close()
        self.browser = pw_manager.create_context(
            self.session_path, headless=False,
            args=STEALTH_ARGS,
            viewport={'width': 1280, 'height': 720}
        )
        self.page = self.browser.pages[0]
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        self.page.goto('https://www.linkedin.com')
        logger.warning("==> Please log in to LinkedIn in the opened browser window <==")
        try:
            self.page.wait_for_timeout(5000)
            for _ in range(60):
                if self._is_logged_in():
                    self._session_valid = True
                    logger.info("LinkedIn re-login successful")
                    return True
                self.page.wait_for_timeout(5000)
            logger.error("LinkedIn re-login timed out")
            return False
        except:
            logger.error("LinkedIn re-login timed out")
            return False

    def _get_notification_count(self) -> int:
        """Parse notification count from nav aria-labels"""
        try:
            notif_link = self.page.query_selector('a[aria-label*="Notifications"]')
            if notif_link:
                label = notif_link.get_attribute('aria-label') or ''
                import re
                match = re.search(r'(\d+)', label)
                if match:
                    return int(match.group(1))
        except:
            pass
        return 0

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check for new notifications and messages"""
        if not self.page:
            return []
        if not self._session_valid:
            logger.warning("Session expired, cannot check LinkedIn.")
            return []

        try:
            notifications = []
            count = self._get_notification_count()
            logger.info(f"LinkedIn notifications count: {count}")

            if count > 0:
                notif_link = self.page.query_selector('a[aria-label*="Notifications"]')
                if notif_link:
                    notif_link.click()
                    self.page.wait_for_timeout(3000)
                    items = self.page.query_selector_all('[data-notification-id], [data-feed-id], article')
                    for item in items[:count]:
                        text = item.inner_text()
                        notif_id = str(hash(text))
                        if notif_id not in self.processed_notifications:
                            self.processed_notifications.add(notif_id)
                            notifications.append({
                                'type': 'notification',
                                'text': text,
                                'timestamp': datetime.now().isoformat(),
                                'notification_id': notif_id
                            })

            return notifications
        except Exception as e:
            logger.error(f"Error checking LinkedIn: {e}")
            return []
    
    def create_action_file(self, item) -> Path:
        """Create action file for LinkedIn notification"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"LINKEDIN_{item.get('notification_id', item.get('type', 'notif'))}_{timestamp}.md"
        filepath = self.needs_action / filename
        
        content = f"""---
type: linkedin
notification_type: {item.get('type', 'unknown')}
received: {item['timestamp']}
priority: medium
status: pending
---

## LinkedIn Notification
{item['text']}

## Suggested Actions
- [ ] Review notification
- [ ] Respond if needed
- [ ] Archive after processing
"""
        
        filepath = self.needs_action / filename
        filepath.write_text(content)
        logger.info("Created action file for LinkedIn notification")
        
        return filepath
    
    def close(self):
        """Close browser"""
        if self.browser:
            self.browser.close()
        pw_manager.stop()

    def stop(self):
        self.close()


class LinkedInPostCreator:
    """Creates LinkedIn posts from templates"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.templates_path = self.vault_path / "LinkedIn_Templates"
        self.templates_path.mkdir(exist_ok=True)
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default LinkedIn post templates"""
        templates = {
            "business_update.j2": """{{company_name}} Update - {{date}}

{{update_text}}

#{{industry}} #businessupdate #growth""",
            
            "case_study.j2": """Case Study: {{project_name}}

Challenge: {{challenge}}
Solution: {{solution}}
Results: {{results}}

{{client_testimonial}}

#casestudy #{{industry}} #success""",
            
            "thought_leadership.j2": """{{title}}

{{content}}

What are your thoughts? 👇

#thoughtleadership #{{industry}} #leadership""",
            
            "promotional.j2": """🚀 Exciting news from {{company_name}}!

{{announcement_text}}

Learn more: {{link}}

#{{company_name}} #news #{{industry}}""",
            
            "engagement.j2": """{{question}}

A) {{option_a}}
B) {{option_b}}
C) {{option_c}}

Vote in the comments!

#poll #engagement #{{industry}}"""
        }
        
        for name, content in templates.items():
            template_file = self.templates_path / name
            if not template_file.exists():
                template_file.write_text(content)
    
    def create_post(self, template_name: str, **kwargs) -> str:
        """Create a LinkedIn post from a template"""
        template_file = self.templates_path / f"{template_name}.j2"
        if not template_file.exists():
            raise ValueError(f"Template {template_name} not found")
        
        template = Template(template_file.read_text())
        return template.render(**kwargs)
    
    def create_business_post(self, business_data: Dict) -> str:
        """Create a business update post"""
        return self.create_post("business_update", **business_data)
    
    def create_case_study_post(self, case_study: Dict) -> str:
        """Create a case study post"""
        return self.create_post("case_study", **case_study)
    
    def create_thought_leadership_post(self, thought_data: Dict) -> str:
        """Create a thought leadership post"""
        return self.create_post("thought_leadership", **thought_data)
    
    def create_promotional_post(self, promo_data: Dict) -> str:
        """Create a promotional post"""
        return self.create_post("promotional", **promo_data)
    
    def create_engagement_post(self, engagement_data: Dict) -> str:
        """Create an engagement/poll post"""
        return self.create_post("engagement", **engagement_data)
    
    def list_templates(self) -> List[str]:
        """List available templates"""
        return [f.stem for f in self.templates_path.glob("*.j2")]


class LinkedInPoster:
    """Posts content to LinkedIn via web automation"""

    def __init__(self, session_path: str):
        self.session_path = Path(session_path)
        self.browser = None
        self.page = None
        self._session_valid = False
        self._init_browser()

    def _has_valid_session(self) -> bool:
        return self.session_path.is_dir() and any(self.session_path.iterdir())

    def _init_browser(self):
        pw_manager.start()
        self.browser = pw_manager.create_context(
            self.session_path, headless=True,
            args=STEALTH_ARGS,
            viewport={'width': 1280, 'height': 720}
        )
        self.page = self.browser.pages[0]
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        self.page.goto('https://www.linkedin.com')
        self.page.wait_for_timeout(5000)
        if '/feed/' in self.page.url:
            self._session_valid = True
            logger.info("LinkedIn Poster session valid (headless)")
        else:
            self._session_valid = False
            logger.warning("LinkedIn Poster session expired.")
        logger.info("LinkedIn Poster initialized")

    def ensure_session(self):
        """Open headed browser for re-login if session is expired"""
        if self._session_valid:
            return True
        if self.browser:
            self.browser.close()
        self.browser = pw_manager.create_context(
            self.session_path, headless=False,
            args=STEALTH_ARGS,
            viewport={'width': 1280, 'height': 720}
        )
        self.page = self.browser.pages[0]
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        self.page.goto('https://www.linkedin.com')
        logger.warning("==> Please log in to LinkedIn in the opened browser window <==")
        try:
            self.page.wait_for_timeout(5000)
            for _ in range(60):
                if '/feed/' in self.page.url:
                    self._session_valid = True
                    logger.info("LinkedIn Poster re-login successful")
                    return True
                self.page.wait_for_timeout(5000)
            logger.error("LinkedIn Poster re-login timed out")
            return False
        except:
            logger.error("LinkedIn Poster re-login timed out")
            return False
    
    def create_draft(self, content: str) -> Dict:
        """Save a LinkedIn post as a draft file in the vault"""
        try:
            from datetime import datetime
            drafts_dir = Path("AI_Employee_Vault") / "Drafts"
            drafts_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            draft_file = drafts_dir / f"linkedin_draft_{timestamp}.md"
            draft_file.write_text(content)
            logger.info(f"LinkedIn draft saved: {draft_file}")
            return {'success': True, 'draft_file': str(draft_file)}
        except Exception as e:
            logger.error(f"Failed to create LinkedIn draft: {e}")
            return {'success': False, 'error': str(e)}

    def _click_first(self, selectors: list, timeout: int = 10000):
        """Click the first visible element matching any of the given selectors"""
        for sel in selectors:
            try:
                el = self.page.wait_for_selector(sel, timeout=3000)
                if el and el.is_visible():
                    el.click()
                    return True
            except:
                continue
        return False

    def _type_into_editor(self, content: str):
        """Type content into the LinkedIn post editor"""
        selectors = ['.ql-editor', 'div[contenteditable="true"]', 'textarea', '[role="textbox"]']
        for sel in selectors:
            try:
                el = self.page.wait_for_selector(sel, timeout=3000)
                if el and el.is_visible():
                    el.fill(content)
                    return True
            except:
                continue
        return False

    def post_content(self, content: str, image_paths: List[str] = None) -> Dict:
        """Post content to LinkedIn"""
        if not self.page:
            return {'success': False, 'error': 'LinkedIn not initialized'}
        if not self._session_valid:
            return {'success': False, 'error': 'LinkedIn session expired. Call ensure_session() first.'}

        try:
            self.page.goto('https://www.linkedin.com/feed/')

            # Open post composer
            composer_btns = [
                'button[aria-label*="Start a post"]',
                '.share-box-feed-entry__trigger',
                '[data-test-id="post-button"]',
                'button:has-text("Start a post")',
            ]
            if not self._click_first(composer_btns):
                return {'success': False, 'error': 'Could not find post button'}

            self.page.wait_for_timeout(2000)

            # Type content
            if not self._type_into_editor(content):
                return {'success': False, 'error': 'Could not find post editor'}

            # Post
            post_btns = [
                'button[aria-label*="Post"]',
                '[data-test-id="post-submit-button"]',
                'button:has-text("Post")',
            ]
            if not self._click_first(post_btns):
                return {'success': False, 'error': 'Could not find Post button'}

            self.page.wait_for_timeout(2000)
            logger.info("LinkedIn post published successfully")
            return {'success': True}
        except Exception as e:
            logger.error(f"Failed to post LinkedIn content: {e}")
            return {'success': False, 'error': str(e)}

    def save_linkedin_draft(self, content: str) -> Dict:
        """Save a draft on LinkedIn (Save as draft instead of Post)"""
        if not self.page:
            return {'success': False, 'error': 'LinkedIn not initialized'}
        if not self._session_valid:
            return {'success': False, 'error': 'LinkedIn session expired. Call ensure_session() first.'}

        try:
            self.page.goto('https://www.linkedin.com/feed/')

            composer_btns = [
                'button[aria-label*="Start a post"]',
                '.share-box-feed-entry__trigger',
                '[data-test-id="post-button"]',
                'button:has-text("Start a post")',
            ]
            if not self._click_first(composer_btns):
                return {'success': False, 'error': 'Could not open post composer'}

            self.page.wait_for_timeout(2000)

            if not self._type_into_editor(content):
                return {'success': False, 'error': 'Could not find editor'}

            # Click "Save as draft" via the ... menu if visible, or save button
            save_btns = [
                'button[aria-label*="Save"]',
                'button:has-text("Save")',
                'button[aria-label*="Close"]',
            ]
            if self._click_first(save_btns):
                # Confirm save draft if dialog appears
                confirm = [
                    'button:has-text("Save draft")',
                    'button[data-test-dialog-primary-btn]',
                ]
                self._click_first(confirm)
            else:
                # Fallback: save local draft
                self.create_draft(content)
                return {'success': True, 'draft_type': 'local'}

            logger.info("LinkedIn draft saved on profile")
            return {'success': True, 'draft_type': 'linkedin'}
        except Exception as e:
            logger.error(f"Failed to save LinkedIn draft: {e}")
            return {'success': False, 'error': str(e)}
    
    def close(self):
        if self.browser:
            self.browser.close()
        pw_manager.stop()