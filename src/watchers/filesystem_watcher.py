import time
import logging
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .base_watcher import BaseWatcher


class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: str):
        self.needs_action = Path(vault_path) / "Needs_Action"
        self.inbox = Path(vault_path) / "Inbox"
        self.logger = logging.getLogger("DropFolderHandler")

    def process_file(self, source: Path):
        if not source.is_file() or source.name.startswith('.'):
            return
        dest = self.needs_action / f"FILE_{source.name}"
        shutil.copy2(source, dest)
        self._create_metadata(source, dest)
        source.unlink()
        self.logger.info(f"Processed: {source.name}")

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

    def check_for_updates(self) -> list:
        return []

    def create_action_file(self, item) -> Path:
        return Path()

    def run(self):
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        self.needs_action.mkdir(parents=True, exist_ok=True)

        self.handler.process_existing()

        self.observer.schedule(self.handler, str(self.inbox_path), recursive=False)
        self.observer.start()
        self.logger.info(f"Watching inbox: {self.inbox_path}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
