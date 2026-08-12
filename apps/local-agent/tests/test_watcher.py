"""Incremental RAG watcher event coverage."""

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

from agentforge_local.watcher.fs_watcher import RAGWatcherHandler


def test_watcher_reindexes_create_modify_delete_and_move() -> None:
    paths: list[str] = []
    handler = RAGWatcherHandler(paths.append)

    handler.on_created(FileCreatedEvent("/workspace/new.py"))
    handler.on_modified(FileModifiedEvent("/workspace/new.py"))
    handler.on_deleted(FileDeletedEvent("/workspace/new.py"))
    handler.on_moved(
        FileMovedEvent("/workspace/old.py", "/workspace/renamed.py")
    )

    assert paths == [
        "/workspace/new.py",
        "/workspace/new.py",
        "/workspace/new.py",
        "/workspace/renamed.py",
    ]


def test_watcher_ignores_dependency_and_cache_events() -> None:
    paths: list[str] = []
    handler = RAGWatcherHandler(paths.append)

    handler.on_created(FileCreatedEvent("/workspace/node_modules/pkg.js"))
    handler.on_deleted(FileDeletedEvent("/workspace/.venv/module.py"))
    handler.on_moved(
        FileMovedEvent(
            "/workspace/.next/old.js",
            "/workspace/.next/new.js",
        )
    )

    assert paths == []
