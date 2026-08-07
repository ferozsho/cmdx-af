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

WORKDIR /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
