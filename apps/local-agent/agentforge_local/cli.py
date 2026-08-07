"""Command Line Interface for AgentForge Local Execution Daemon."""

import argparse
import sys
from agentforge_local.config import local_settings
from agentforge_local.workspaces.manager import WorkspaceManager


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
        print(f"Connecting to Cloud WSS: {local_settings.CLOUD_WSS_URL}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
