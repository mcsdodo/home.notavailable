FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl \
    && pip install docker requests \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY caddy-agent-watch.py /app/caddy-agent.py
WORKDIR /app
CMD ["python", "caddy-agent.py"]
