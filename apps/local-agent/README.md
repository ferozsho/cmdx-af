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
