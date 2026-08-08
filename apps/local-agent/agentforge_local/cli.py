"""Command Line Interface for AgentForge Local Execution Daemon."""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from agentforge_local.config import local_settings
from agentforge_local.connection.device_auth import (
    load_device_credentials,
    pair_with_cloud,
)
from agentforge_local.connection.wss_client import LocalWSSClient
from agentforge_local.handler import ToolHandler
from agentforge_local.workspaces.manager import WorkspaceManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
watcher_logger = logging.getLogger("agentforge.local.watcher")


def _start_watchers(ws_mgr: WorkspaceManager) -> List[Any]:
    """Start file watchers for all registered workspaces (RAG auto re-index)."""
    from agentforge_local.rag.indexer import LocalRAGIndexer
    from agentforge_local.watcher.fs_watcher import WorkspaceWatcher

    watchers: List[Any] = []
    debounce: Dict[str, float] = {}

    def make_callback(ws_id: str, ws_path: str):
        def callback(path: str) -> None:
            now = time.time()
            if now - debounce.get(ws_id, 0) < 5:
                return
            debounce[ws_id] = now
            try:
                indexer = LocalRAGIndexer(ws_path)
                count = indexer.index_workspace()
                watcher_logger.info(
                    "Re-indexed workspace %s (%d chunks) after %s",
                    ws_id, count, path,
                )
            except Exception as e:
                watcher_logger.warning("Re-index failed: %s", e)

        return callback

    for ws_id, ws_path in ws_mgr.list_workspaces().items():
        if not Path(ws_path).exists():
            continue
        watcher = WorkspaceWatcher(ws_path, make_callback(ws_id, ws_path))
        watcher.start()
        watchers.append(watcher)
    return watchers


def main() -> None:
    """CLI entrypoint for managing local agent daemon."""
    parser = argparse.ArgumentParser(description="AgentForge Local Execution Daemon")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("start", help="Start the local agent WSS daemon")

    connect = subparsers.add_parser(
        "connect", help="Pair this workstation with the cloud using a code"
    )
    connect.add_argument("pairing_code", help="8-character pairing code from the Devices page")

    ws_add = subparsers.add_parser("workspace-add", help="Add an authorized local workspace path")
    ws_add.add_argument("workspace_id", help="Workspace UUID or key")
    ws_add.add_argument("path", help="Local directory path")

    ws_list = subparsers.add_parser("workspace-list", help="List registered workspaces")

    args = parser.parse_args()

    ws_mgr = WorkspaceManager(local_settings.CONFIG_DIR)

    if args.command == "connect":
        try:
            data = asyncio.run(pair_with_cloud(args.pairing_code))
            print(
                f"✅ Paired! Device ID: {data['device_id']}\n"
                f"   Token saved. Run 'agentforge start' to connect."
            )
        except Exception as e:
            print(f"✗ Pairing failed: {e}")
            sys.exit(1)
    elif args.command == "workspace-add":
        resolved = ws_mgr.add_workspace(args.workspace_id, args.path)
        print(f"✅ Registered workspace '{args.workspace_id}' -> {resolved}")
    elif args.command == "workspace-list":
        workspaces = ws_mgr.list_workspaces()
        print("Registered Workspaces:")
        for ws_id, path in workspaces.items():
            print(f"  - {ws_id}: {path}")
    elif args.command == "start":
        print("🚀 Starting AgentForge Local Execution Daemon...")
        creds = load_device_credentials()
        device_id = creds.get("device_id") or local_settings.DEVICE_ID or "dev_feroz_pc"
        handler = ToolHandler(ws_mgr)
        client = LocalWSSClient(local_settings.CLOUD_WSS_URL, device_id, handler.handle_request)

        watchers = _start_watchers(ws_mgr)
        if watchers:
            print(f"👀 Watching {len(watchers)} workspace(s) for RAG auto re-indexing")
        elif creds:
            print("ℹ️  No workspaces registered — run 'agentforge workspace-add'")

        try:
            asyncio.run(client.start())
        except KeyboardInterrupt:
            print("Daemon stopped by user.")
        finally:
            for w in watchers:
                w.stop()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
