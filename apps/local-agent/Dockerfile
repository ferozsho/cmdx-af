FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Shared protocol package (ToolRequest / ToolResult schemas)
COPY packages/protocol /app/packages/protocol
RUN pip install --no-cache-dir /app/packages/protocol

# Install the CPU-only PyTorch wheel before sentence-transformers. The default
# Linux wheel pulls several gigabytes of CUDA libraries that the daemon never
# uses because embeddings are explicitly executed on CPU.
RUN pip install --no-cache-dir \
    torch==2.11.0 \
    --index-url https://download.pytorch.org/whl/cpu

# Cache third-party dependencies independently from application source edits.
COPY apps/local-agent/pyproject.toml apps/local-agent/README.md /tmp/local-agent/
RUN pip install --no-cache-dir /tmp/local-agent

# Local Execution Daemon source. Dependencies are already present above, so a
# code-only rebuild does not reinstall the ML stack.
COPY apps/local-agent /app/apps/local-agent
RUN pip install --no-cache-dir --no-deps -e /app/apps/local-agent

RUN groupadd --gid 10001 agentforge \
    && useradd --uid 10001 --gid agentforge --create-home agentforge \
    && mkdir -p /home/agentforge/.agentforge /home/agentforge/.cache/huggingface \
    && chown -R agentforge:agentforge /home/agentforge

# Make the self-configuring entrypoint executable.
RUN chmod +x /app/apps/local-agent/entrypoint.sh

WORKDIR /app/apps/local-agent

ENV HOME=/home/agentforge

# The agent operates on the client's own mounted project folders (owned by the
# host user), so it runs as root by default. Clients may lock it down with a
# `--user` override if they prefer.
USER root

# Self-configuring entrypoint: reads AGENTFORGE_* env vars, registers the
# client's workspaces, then runs the daemon. Override the command for other
# CLI operations, e.g.:
#   docker run --rm -it agentforge-local agentforge connect AGF-XXXX
ENTRYPOINT ["/app/apps/local-agent/entrypoint.sh"]
CMD ["start"]
