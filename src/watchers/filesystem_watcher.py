import time
import logging
import shutil
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .base_watcher import BaseWatcher


class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: str):
        self.needs_action = Path(vault_path) / "Needs_Action"
        self.inbox = Path(vault_path) / "Inbox"
        self.logger = logging.getLogger("DropFolderHandler")
        # The startup scan and the inotify callback can race on the same drop;
        # without a claim, one file would be filed twice.
        self._in_flight = set()
        self._lock = threading.Lock()

    def _unique_destination(self, name: str) -> Path:
        """
        Pick a destination that does not clobber an existing action file.

        Dropping two files with the same name must not silently overwrite the
        earlier one — the vault is the audit trail, so both drops are preserved.
        """
        dest = self.needs_action / name
        if not dest.exists():
            return dest
        stem, suffix = dest.stem, dest.suffix
        counter = 1
        while True:
            candidate = self.needs_action / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def process_file(self, source: Path):
        if source.name.startswith("."):
            return

        key = str(source)
        with self._lock:
            if key in self._in_flight:
                return
            self._in_flight.add(key)

        try:
            if not source.is_file():
                return
            self.needs_action.mkdir(parents=True, exist_ok=True)
            dest = self._unique_destination(f"FILE_{source.name}")
            shutil.copy2(source, dest)
            self._create_metadata(source, dest)
            source.unlink(missing_ok=True)
            self.logger.info(f"Processed: {source.name} -> {dest.name}")
        except OSError as e:
            self.logger.warning(f"Could not process {source.name}: {e}")
        finally:
            with self._lock:
                self._in_flight.discard(key)

    def process_existing(self):
        for f in sorted(self.inbox.iterdir()):
            self.process_file(f)

    def on_created(self, event):
        if event.is_directory:
            return
        self.process_file(Path(event.src_path))

    def _create_metadata(self, source: Path, dest: Path):
        meta_path = dest.with_name(f"{dest.name}.md")
        content = f"""---
type: file_drop
original_name: {source.name}
size: {source.stat().st_size}
created: {time.strftime('%Y-%m-%dT%H:%M:%S')}
status: pending
---

## Dropped File: {source.name}

File copied to Needs_Action for processing.

## Suggested Actions
- [ ] Review file contents
- [ ] Process as needed
- [ ] Move to /Done when complete
"""
        meta_path.write_text(content)


class FileSystemWatcher(BaseWatcher):
    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=5)
        self.inbox_path = self.vault_path / "Inbox"
        self.observer = Observer()
        self.handler = DropFolderHandler(vault_path)
        self.running = False

    def check_for_updates(self) -> list:
        return []

    def create_action_file(self, item) -> Path:
        return Path()

    def run(self):
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        self.needs_action.mkdir(parents=True, exist_ok=True)

        # Start watching *before* the catch-up scan. Scanning first leaves a gap
        # in which a file dropped between the scan and observer.start() would be
        # seen by neither, and would sit in Inbox/ forever.
        self.running = True
        self.observer.schedule(self.handler, str(self.inbox_path), recursive=False)
        self.observer.start()
        self.logger.info(f"Watching inbox: {self.inbox_path}")

        self.handler.process_existing()

        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.observer.stop()
            self.observer.join()

    def stop(self):
        self.running = False
