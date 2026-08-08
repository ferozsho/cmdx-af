FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Shared protocol package (ToolRequest / ToolResult schemas)
COPY packages/protocol /app/packages/protocol
RUN pip install --no-cache-dir /app/packages/protocol

# Local Execution Daemon (deps: websockets, httpx, watchdog, gitpython,
# qdrant-client, sentence-transformers)
COPY apps/local-agent /app/apps/local-agent
RUN pip install --no-cache-dir -e /app/apps/local-agent

WORKDIR /app/apps/local-agent

# Run the daemon by default; override with other CLI commands, e.g.
#   docker run --rm agentforge-local agentforge connect AGF-XXXX
ENTRYPOINT ["agentforge"]
CMD ["start"]
