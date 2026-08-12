#!/bin/sh
# AgentForge Local Agent — container entrypoint.
#
# Makes the image self-configuring so the SAME image works for any client
# anywhere in the world:
#
#   AGENTFORGE_SERVER_URL   - public AgentForge server base URL, e.g.
#                             https://your-agentforge.example.com
#                             (unset -> local dev stack)
#   AGENTFORGE_DEVICE_ID    - device id from pairing (or run `agentforge
#                             connect <code>` inside the container)
#   AGENTFORGE_DEVICE_TOKEN - device token from pairing
#   AGENTFORGE_WORKSPACES   - comma-separated "ws-id=/path/to/project"
#                             entries. The paths MUST be mounted into the
#                             container (client mounts their own folders).
#
# The agent always connects OUTBOUND to the server over WebSocket, so it works
# from behind NAT/firewalls — no inbound ports or public IP required.
set -eu

# Derive the cloud WSS/API URLs from the server base URL unless the client
# overrode them explicitly.
if [ -n "${AGENTFORGE_SERVER_URL:-}" ]; then
    : "${CLOUD_WSS_URL:=${AGENTFORGE_SERVER_URL%/}/api/v1/ws/devices}"
    : "${CLOUD_API_URL:=${AGENTFORGE_SERVER_URL%/}/api/v1}"
    export CLOUD_WSS_URL CLOUD_API_URL
fi

# Auto-register the client's workspaces BEFORE the daemon starts, so the
# daemon picks them up on boot (its registry is loaded once at startup).
if [ -n "${AGENTFORGE_WORKSPACES:-}" ]; then
    _old_ifs=$IFS
    IFS=,
    for _entry in $AGENTFORGE_WORKSPACES; do
        [ -z "$_entry" ] && continue
        _ws_id=${_entry%%=*}
        _ws_path=${_entry#*=}
        if [ -z "$_ws_id" ] || [ -z "$_ws_path" ]; then
            echo "agentforge: skipping malformed workspace '$entry'" >&2
            continue
        fi
        echo "agentforge: registering workspace $_ws_id -> $_ws_path"
        agentforge workspace-add "$_ws_id" "$_ws_path"
    done
    IFS=$_old_ifs
fi

# Mark workspace roots as safe for git (they are owned by the host user, so
# without this git rejects them with "dubious ownership").
if command -v git >/dev/null 2>&1; then
    git config --global --add safe.directory '*' 2>/dev/null || true
fi

# Default command is `start`; other CLI commands (connect, workspace-list, ...)
# can be passed as arguments.
exec agentforge "$@"
