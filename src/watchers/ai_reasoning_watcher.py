"""
AI Reasoning Watcher - Monitors Needs_Action/ and triggers opencode automatically
"""

import json
import time
import logging
import subprocess
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class NeedsActionHandler(FileSystemEventHandler):
    """Handles new files in Needs_Action/ by triggering opencode"""

    def __init__(
        self,
        needs_action_dir: Path,
        vault_path: Path,
        model: str = None,
        agent: str = None,
        timeout: int = 300,
    ):
        self.needs_action_dir = needs_action_dir
        self.vault_path = vault_path
        self.model = model
        self.agent = agent
        self.timeout = timeout
        self.processed = set()
        self.done_dir = needs_action_dir / "Done"
        self.done_dir.mkdir(parents=True, exist_ok=True)
        self._load_processed()

    def _load_processed(self):
        if self.done_dir.exists():
            for f in self.done_dir.iterdir():
                if f.is_file():
                    self.processed.add(f.name)

    def _should_process(self, filepath: Path) -> bool:
        if not filepath.is_file():
            return False
        if filepath.suffix not in (".md", ".json"):
            return False
        if filepath.name in self.processed:
            return False
        if filepath.parent != self.needs_action_dir:
            return False
        return True

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        if self._should_process(filepath):
            self._process_file(filepath)

    def on_moved(self, event):
        if event.is_directory:
            return
        filepath = Path(event.dest_path)
        if self._should_process(filepath):
            self._process_file(filepath)

    def _process_file(self, filepath: Path):
        if filepath.name in self.processed:
            return
        self.processed.add(filepath.name)
        logger.info(f"New action file: {filepath.name}, triggering opencode...")
        thread = threading.Thread(target=self._run_opencode, args=(filepath,), daemon=True)
        thread.start()

    def _run_opencode(self, filepath: Path):
        try:
            relative = filepath.relative_to(self.vault_path.parent)
            prompt = (
                f"Process {relative} according to the AI Employee handbook. "
                "Read the file, create a detailed plan in Plans/, "
                "and submit an approval request JSON to Pending_Approval/. "
                "Then move the file to Needs_Action/Done/."
            )

            cmd = ["opencode", "run", prompt, "--print-logs", "--format", "json", "--auto"]
            if self.agent:
                cmd.extend(["--agent", self.agent])
            if self.model:
                cmd.extend(["--model", self.model])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.vault_path.parent,
            )

            if result.returncode == 0:
                # opencode exits 0 even when the model call failed (e.g. quota or
                # billing errors), so inspect the event stream before calling it a win.
                error_msg = None
                for line in result.stdout.strip().split("\n"):
                    if line:
                        try:
                            evt = json.loads(line)
                            if evt.get("type") == "error":
                                error_msg = (
                                    evt.get("error", {})
                                    .get("data", {})
                                    .get("message", "unknown error")
                                )
                                break
                        except json.JSONDecodeError:
                            pass
                if error_msg:
                    logger.error(f"opencode reported an error for {filepath.name}: {error_msg}")
                else:
                    logger.info(f"opencode processed {filepath.name} successfully")
            else:
                # Extract error from JSON output
                msg = result.stderr[:300]
                for line in result.stdout.strip().split("\n"):
                    if line:
                        try:
                            evt = json.loads(line)
                            if evt.get("type") == "error":
                                msg = evt.get("error", {}).get("data", {}).get("message", msg)
                                break
                        except json.JSONDecodeError:
                            pass
                logger.error(f"opencode failed for {filepath.name}: {msg}")
        except subprocess.TimeoutExpired:
            logger.error(
                f"opencode timed out after {self.timeout}s for {filepath.name}. "
                f"Using model={self.model or 'opencode default'}, agent={self.agent or 'default'}. "
                "Set OPENCODE_MODEL in .env to a funded model and/or raise OPENCODE_TIMEOUT."
            )
        except FileNotFoundError:
            logger.error("opencode not found in PATH")
        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")


class AIReasoningWatcher:
    """Watches Needs_Action/ and triggers opencode for reasoning"""

    def __init__(self, vault_path: str, model: str = None, agent: str = None, timeout: int = 300):
        self.vault_path = Path(vault_path)
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.model = model
        self.agent = agent
        self.timeout = timeout
        self.running = False
        self.observer = None
        self.handler = None
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        (self.needs_action_dir / "Done").mkdir(parents=True, exist_ok=True)

    def run(self):
        self.running = True
        self.handler = NeedsActionHandler(
            self.needs_action_dir,
            self.vault_path,
            model=self.model,
            agent=self.agent,
            timeout=self.timeout,
        )
        if not self.model:
            logger.warning(
                "No OPENCODE_MODEL configured — opencode will use its default model, "
                "which may be rate-limited or unfunded. Set OPENCODE_MODEL in .env."
            )
        logger.info(
            f"AI reasoning using model={self.model or 'opencode default'}, "
            f"agent={self.agent or 'default'}, timeout={self.timeout}s"
        )

        # Start watching first: a file that lands between the catch-up scan and
        # observer.start() would otherwise never be reasoned about.
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.needs_action_dir), recursive=False)
        self.observer.start()
        logger.info(f"AIReasoningWatcher watching: {self.needs_action_dir}")

        # Process any files that arrived while offline
        for f in sorted(self.needs_action_dir.iterdir()):
            if self.handler._should_process(f):
                self.handler._process_file(f)
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
