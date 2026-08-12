FROM node:20-slim AS node-runtime

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the official slim Node runtime instead of installing Debian's npm
# package, which brings hundreds of unrelated build-time JavaScript packages.
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Keep a standalone ESLint available for repositories that do not vendor it.
# ESLint 8 supports the Node.js runtime and remains config-compatible
# with both legacy .eslintrc files and explicit flat-config projects.
RUN npm install --global eslint@8.57.1 \
    && npm cache clean --force

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
# Verification commands run inside this image against mounted workspaces, so
# install the development tool extra as an intentional runtime capability.
RUN pip install --no-cache-dir "/tmp/local-agent[dev]"

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
