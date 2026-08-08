"""Local Workspace File System Watcher."""

from pathlib import Path
from typing import Any
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from agentforge_local.rag.indexer import _IGNORED_PARTS


class RAGWatcherHandler(FileSystemEventHandler):
    """File modification event handler triggering RAG re-indexing."""

    def __init__(self, callback: Any) -> None:
        self.callback = callback

    def _is_ignored(self, path: str) -> bool:
        """True when the path lives under an ignored dir (venv, caches, etc.)."""
        return bool(set(Path(path).parts) & _IGNORED_PARTS)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and not self._is_ignored(event.src_path):
            self.callback(event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and not self._is_ignored(event.src_path):
            self.callback(event.src_path)


class WorkspaceWatcher:
    """Monitors workspace folder for real-time changes."""

    def __init__(self, workspace_path: str, callback: Any) -> None:
        self.workspace_path = workspace_path
        self.handler = RAGWatcherHandler(callback)
        self.observer = Observer()

    def start(self) -> None:
        """Start directory monitoring thread."""
        self.observer.schedule(self.handler, path=self.workspace_path, recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop directory monitoring thread."""
        self.observer.stop()
        self.observer.join()
