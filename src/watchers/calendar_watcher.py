"""Google Calendar watcher for upcoming and changed events."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

from .base_watcher import BaseWatcher

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarWatcher(BaseWatcher):
    """Monitors the primary calendar for new and changed upcoming events."""

    def __init__(
        self,
        vault_path: str,
        client_config: dict,
        token_data: dict,
        check_interval: int = 120,
    ):
        super().__init__(vault_path, check_interval)
        self.client_config = client_config
        self.token_data = token_data
        self.service = None
        self.processed_versions: Dict[str, str] = {}
        self._authenticate()

    def _authenticate(self):
        creds = None
        if self.token_data:
            try:
                creds = Credentials.from_authorized_user_info(self.token_data, SCOPES)
            except (ValueError, json.JSONDecodeError) as exc:
                logger.warning("Invalid Calendar token data: %s", exc)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Calendar token refreshed")
            elif self.client_config:
                flow = InstalledAppFlow.from_client_config(self.client_config, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Calendar re-authenticated via browser")
            else:
                raise RuntimeError("No Calendar credentials configured")

        self.service = build("calendar", "v3", credentials=creds)
        logger.info("Calendar API authenticated successfully")

    def check_for_updates(self) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        response = (
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            )
            .execute()
        )

        updates = []
        for event in response.get("items", []):
            if event.get("status") == "cancelled" or not event.get("id"):
                continue
            version = event.get("updated") or self._event_version(event)
            if self.processed_versions.get(event["id"]) != version:
                updates.append(event)
        return updates

    def create_action_file(self, event: Dict[str, Any]) -> Path:
        event_id = event["id"]
        version = event.get("updated") or self._event_version(event)
        start = event.get("start", {})
        end = event.get("end", {})
        attendees = ", ".join(
            attendee.get("email", "")
            for attendee in event.get("attendees", [])
            if attendee.get("email")
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.needs_action / f"CALENDAR_{event_id}_{timestamp}.md"
        content = f"""---
type: calendar_event
event_id: {event_id}
status: {event.get('status', 'confirmed')}
updated: {version}
priority: normal
---

## Calendar Event
**Title:** {event.get('summary', 'Untitled event')}
**Start:** {self._time_value(start)}
**End:** {self._time_value(end)}
**Location:** {event.get('location', 'Not specified')}
**Organizer:** {event.get('organizer', {}).get('email', 'Not specified')}
**Attendees:** {attendees or 'None listed'}

## Description
{event.get('description', '[No description]')}

## Suggested Actions
- [ ] Prepare for the meeting
- [ ] Create a follow-up task
- [ ] Send an approved response
"""
        filepath.write_text(content)
        self.processed_versions[event_id] = version
        logger.info("Created action file for calendar event: %s", event_id)
        return filepath

    @staticmethod
    def _time_value(value: Dict[str, Any]) -> str:
        return value.get("dateTime") or value.get("date") or "Not specified"

    @staticmethod
    def _event_version(event: Dict[str, Any]) -> str:
        return "|".join(
            [
                event.get("id", ""),
                event.get("summary", ""),
                CalendarWatcher._time_value(event.get("start", {})),
                CalendarWatcher._time_value(event.get("end", {})),
            ]
        )
