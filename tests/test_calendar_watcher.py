from src.watchers.calendar_watcher import CalendarWatcher


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeEvents:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    def list(self, **kwargs):
        self.request = kwargs
        return FakeRequest(self.payload)


class FakeCalendarService:
    def __init__(self, payload):
        self.events_api = FakeEvents(payload)

    def events(self):
        return self.events_api


def make_watcher(tmp_path, payload):
    watcher = object.__new__(CalendarWatcher)
    watcher.service = FakeCalendarService(payload)
    watcher.processed_versions = {}
    watcher.needs_action = tmp_path / "Needs_Action"
    watcher.needs_action.mkdir()
    return watcher


def test_calendar_watcher_detects_new_and_changed_events(tmp_path):
    event = {
        "id": "event-1",
        "summary": "Client meeting",
        "updated": "2026-09-25T10:00:00Z",
        "start": {"dateTime": "2026-09-26T10:00:00Z"},
        "end": {"dateTime": "2026-09-26T11:00:00Z"},
    }
    watcher = make_watcher(tmp_path, {"items": [event]})

    assert watcher.check_for_updates() == [event]
    watcher.create_action_file(event)
    assert watcher.check_for_updates() == []

    event["updated"] = "2026-09-25T11:00:00Z"
    assert watcher.check_for_updates() == [event]


def test_calendar_watcher_writes_action_file(tmp_path):
    event = {
        "id": "event-2",
        "summary": "Planning session",
        "updated": "2026-09-25T10:00:00Z",
        "start": {"date": "2026-09-27"},
        "end": {"date": "2026-09-28"},
        "location": "Online",
        "attendees": [{"email": "client@example.com"}],
        "description": "Review the delivery plan.",
    }
    watcher = make_watcher(tmp_path, {"items": []})

    action_file = watcher.create_action_file(event)

    content = action_file.read_text()
    assert action_file.name.startswith("CALENDAR_event-2_")
    assert "type: calendar_event" in content
    assert "Planning session" in content
    assert "client@example.com" in content
    assert "Review the delivery plan." in content
