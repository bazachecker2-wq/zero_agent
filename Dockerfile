FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent ./agent
COPY vision ./vision
COPY drone ./drone
COPY mcp ./mcp

CMD ["python", "-m", "agent.main", "start"]
