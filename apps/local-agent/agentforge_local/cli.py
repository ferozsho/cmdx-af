"""Command Line Interface for AgentForge Local Execution Daemon."""

import argparse
import asyncio
import logging
import sys
from agentforge_local.config import local_settings
from agentforge_local.connection.wss_client import LocalWSSClient
from agentforge_local.handler import ToolHandler
from agentforge_local.workspaces.manager import WorkspaceManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main() -> None:
    """CLI entrypoint for managing local agent daemon."""
    parser = argparse.ArgumentParser(description="AgentForge Local Execution Daemon")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("start", help="Start the local agent WSS daemon")

    ws_add = subparsers.add_parser("workspace-add", help="Add an authorized local workspace path")
    ws_add.add_argument("workspace_id", help="Workspace UUID or key")
    ws_add.add_argument("path", help="Local directory path")

    ws_list = subparsers.add_parser("workspace-list", help="List registered workspaces")

    args = parser.parse_args()

    ws_mgr = WorkspaceManager(local_settings.CONFIG_DIR)

    if args.command == "workspace-add":
        resolved = ws_mgr.add_workspace(args.workspace_id, args.path)
        print(f"✅ Registered workspace '{args.workspace_id}' -> {resolved}")
    elif args.command == "workspace-list":
        workspaces = ws_mgr.list_workspaces()
        print("Registered Workspaces:")
        for ws_id, path in workspaces.items():
            print(f"  - {ws_id}: {path}")
    elif args.command == "start":
        print("🚀 Starting AgentForge Local Execution Daemon...")
        device_id = local_settings.DEVICE_ID or "dev_feroz_pc"
        handler = ToolHandler(ws_mgr)
        client = LocalWSSClient(local_settings.CLOUD_WSS_URL, device_id, handler.handle_request)
        try:
            asyncio.run(client.start())
        except KeyboardInterrupt:
            print("Daemon stopped by user.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
