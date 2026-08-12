FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY packages/protocol /app/packages/protocol
RUN pip install --no-cache-dir /app/packages/protocol

COPY apps/api /app/apps/api
RUN pip install --no-cache-dir -e /app/apps/api

RUN chmod 0755 /app/apps/api/docker-entrypoint.sh
RUN groupadd --gid 10001 agentforge \
    && useradd --uid 10001 --gid agentforge --create-home agentforge \
    && mkdir -p /app/apps/api/data \
    && chown -R agentforge:agentforge /app/apps/api/data

WORKDIR /app/apps/api

ENV PYTHONDONTWRITEBYTECODE=1

USER agentforge

EXPOSE 8000

ENTRYPOINT ["/app/apps/api/docker-entrypoint.sh"]
