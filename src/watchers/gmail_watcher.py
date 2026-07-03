"""
Gmail Watcher - Monitors Gmail for new emails using Gmail API
"""
import time
import json
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_watcher import BaseWatcher
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']


class GmailWatcher(BaseWatcher):
    """Monitors Gmail for new unread emails"""

    def __init__(self, vault_path: str, client_config: dict, token_data: dict, check_interval: int = 120):
        super().__init__(vault_path, check_interval)
        self.client_config = client_config
        self.token_data = token_data
        self.service = None
        self.processed_ids = set()
        self._authenticate()

    def _authenticate(self):
        creds = None
        if self.token_data:
            try:
                creds = Credentials.from_authorized_user_info(self.token_data, SCOPES)
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Invalid token data: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Gmail token refreshed")
            elif self.client_config:
                flow = InstalledAppFlow.from_client_config(self.client_config, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Gmail re-authenticated via browser")
            else:
                raise RuntimeError("No Gmail credentials configured")

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API authenticated successfully")

    def check_for_updates(self) -> List[Dict[str, Any]]:
        try:
            query = 'is:unread'
            results = self.service.users().messages().list(userId='me', q=query, maxResults=50).execute()
            messages = results.get('messages', [])

            new_messages = []
            for msg in messages:
                if msg['id'] not in self.processed_ids:
                    new_messages.append({'id': msg['id']})

            return new_messages
        except Exception as e:
            logger.error(f"Error checking Gmail: {e}")
            return []

    def create_action_file(self, item) -> Path:
        message_id = item['id']

        message = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()

        headers = {h['name']: h['value'] for h in message['payload']['headers']}

        body = self._get_message_body(message['payload'])

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"EMAIL_{message_id}_{timestamp}.md"
        filepath = self.needs_action / filename

        content = f"""---
type: email
message_id: {message_id}
from: {headers.get('From', 'Unknown')}
to: {headers.get('To', 'Unknown')}
subject: {headers.get('Subject', 'No Subject')}
date: {headers.get('Date', datetime.now().isoformat())}
received: {datetime.now().isoformat()}
priority: high
status: pending
---

## Email Details
**From:** {headers.get('From', 'Unknown')}
**To:** {headers.get('To', 'Unknown')}
**Subject:** {headers.get('Subject', 'No Subject')}
**Date:** {headers.get('Date', 'Unknown')}

## Email Content
{body}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Create task from email
- [ ] Archive after processing
"""

        filepath.write_text(content)
        self.processed_ids.add(message_id)
        logger.info(f"Created action file for email: {message_id}")

        return filepath

    def _get_message_body(self, payload: Dict) -> str:
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        return body or "[No text content]"


class GmailSender:
    """Sends emails via Gmail API"""

    def __init__(self, client_config: dict, token_data: dict):
        self.client_config = client_config
        self.token_data = token_data
        self.service = None
        self._authenticate()

    def _authenticate(self):
        creds = None
        if self.token_data:
            try:
                creds = Credentials.from_authorized_user_info(self.token_data, SCOPES)
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Invalid token data: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Gmail token refreshed")
            elif self.client_config:
                flow = InstalledAppFlow.from_client_config(self.client_config, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Gmail re-authenticated via browser")
            else:
                raise RuntimeError("No Gmail credentials configured")

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail Sender authenticated successfully")

    def send_email(self, to: str, subject: str, body: str, attachments: List[str] = None,
                   html_body: str = None) -> Dict:
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders

            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject

            message.attach(MIMEText(body, 'plain'))
            if html_body:
                message.attach(MIMEText(html_body, 'html'))

            if attachments:
                for file_path in attachments:
                    path = Path(file_path)
                    if path.exists():
                        with open(path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={path.name}')
                        message.attach(part)

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"Email sent to {to}: {result.get('id')}")
            return {'success': True, 'message_id': result.get('id')}

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {'success': False, 'error': str(e)}

    def create_draft(self, to: str, subject: str, body: str) -> Dict:
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            result = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()

            logger.info(f"Draft created: {result.get('id')}")
            return {'success': True, 'draft_id': result.get('id')}

        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            return {'success': False, 'error': str(e)}
