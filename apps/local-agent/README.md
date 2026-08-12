# AgentForge Local Agent

The Local Agent is AgentForge's workstation execution plane. It makes an
outbound authenticated WebSocket connection to the cloud control plane and
executes only authorized filesystem, Git, development-command, and local RAG
operations inside registered workspace roots.

## Install and run

Install the shared protocol package and this package, then pair the device with
the one-time code shown in the AgentForge Devices screen:

```bash
python -m pip install ../../packages/protocol
python -m pip install .
agentforge connect <pairing-code>
agentforge workspace-add <workspace-id> /absolute/project/path
agentforge start
```

Credentials and workspace registrations are stored in the user's AgentForge
configuration directory. Application secrets are never read from workspace
`.env` files, and the daemon has no inbound listener.

For the container deployment, use `infrastructure/docker-compose.local-agent.yml`
with pairing credentials supplied from the repository's root `.env` file.

## Run from anywhere (public / multi-tenant)

The agent always dials **outbound** to the AgentForge server over WebSocket, so
it works on any machine — behind NAT, firewalls, or without a public IP. No
inbound ports are ever opened.

The container image is self-configuring from environment variables, so the same
image works for any client:

```bash
docker run -d --name agentforge-local \
  -e AGENTFORGE_SERVER_URL=https://your-agentforge.example.com \
  -e AGENTFORGE_DEVICE_ID=... \
  -e AGENTFORGE_DEVICE_TOKEN=... \
  -e 'AGENTFORGE_WORKSPACES=ws-proj=/app/my-project,ws-web=/app/my-web' \
  -v /absolute/path/to/my-project:/app/my-project \
  -v /absolute/path/to/my-web:/app/my-web \
  -v agentforge_config:/home/agentforge/.agentforge \
  agentforge-local:latest
```

| Variable | Purpose |
|---|---|
| `AGENTFORGE_SERVER_URL` | Public server base URL (e.g. `https://app.example.com`). The WSS + API URLs are derived from it automatically. |
| `AGENTFORGE_DEVICE_ID` / `AGENTFORGE_DEVICE_TOKEN` | Device credentials from pairing (`agentforge connect <code>`), or the Devices page flow. |
| `AGENTFORGE_WORKSPACES` | Comma-separated `workspace-id=/absolute/path` entries. Paths are **client-specific** and must be mounted into the container. Registered automatically before the daemon starts. |
| `QDRANT_URL` | A Qdrant the client controls (default `http://localhost:6333`); used for the local RAG index. |

Isolation model:

- **Per device**: every client gets a unique `device_id` + token (stored hashed
  server-side). The server only talks to the client's own device.
- **Per workspace**: the client registers their own `workspace-id → path`
  mapping. The server never sees the client's filesystem — it ships tool
  requests over the WSS connection and the agent executes them locally inside
  the registered workspace roots only.
- **Per user**: projects in the control plane belong to the user that owns the
  device, so tenants never see each other's projects or devices.
