FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends alsa-utils libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY agent ./agent
COPY vision ./vision
COPY drone ./drone
COPY mcp ./mcp
COPY web ./web
COPY edge ./edge
COPY api.py server.py ./

EXPOSE 8000
CMD ["python", "-m", "agent.main_telemetry", "start"]
