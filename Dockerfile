FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

RUN chmod +x /app/docker-entrypoint.sh

RUN mkdir -p /app/instance && chown app:app /app/instance

USER app

EXPOSE 5555

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:5555/healthz || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "run.py"]
