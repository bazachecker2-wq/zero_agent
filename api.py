from __future__ import annotations

import os
from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field

from drone.telemetry import DroneTelemetry, TelemetryAdapter
from vision.detector import ObjectDetector

app = FastAPI(title="VisionDrone API", version="0.2.0")
telemetry = TelemetryAdapter()
detector = ObjectDetector()
events: deque[dict[str, Any]] = deque(maxlen=500)


class TelemetryUpdate(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = Field(default=None, ge=-1000, le=10000)
    heading_deg: float | None = Field(default=None, ge=0, le=360)
    battery_pct: float | None = Field(default=None, ge=0, le=100)
    velocity_mps: float | None = Field(default=None, ge=0, le=150)


def emit(kind: str, payload: dict[str, Any]) -> None:
    events.appendleft({
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "payload": payload,
    })


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "visiondrone", "model": os.getenv("VISION_MODEL", "gemini-3.1-flash-live-preview")}


@app.get("/api/telemetry")
def get_telemetry() -> dict[str, Any]:
    return telemetry.snapshot().as_dict()


@app.post("/api/telemetry")
def update_telemetry(update: TelemetryUpdate) -> dict[str, Any]:
    value = telemetry.update(**update.model_dump(exclude_none=True))
    emit("telemetry", value.as_dict())
    return value.as_dict()


@app.get("/api/events")
def get_events(limit: int = 50) -> list[dict[str, Any]]:
    if limit < 1 or limit > 200:
        raise HTTPException(400, "limit must be between 1 and 200")
    return list(events)[:limit]


@app.post("/api/vision/detect")
async def detect(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(415, "image upload required")
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise HTTPException(503, "opencv/numpy are not installed") from exc

    data = await file.read()
    frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "invalid image")
    detections = detector.detect(frame)
    result = [d.__dict__ if hasattr(d, "__dict__") else {
        "label": d.label, "confidence": d.confidence,
        "x1": d.x1, "y1": d.y1, "x2": d.x2, "y2": d.y2,
    } for d in detections]
    emit("vision", {"detections": result})
    return {"count": len(result), "detections": result}
