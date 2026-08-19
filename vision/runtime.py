from __future__ import annotations

import os
from typing import Any

from .detector import ObjectDetector


DEFAULT_CLASSES = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck", "train",
    "traffic light", "stop sign", "bird", "cat", "dog", "horse",
}


def build_detector() -> ObjectDetector:
    """Load YOLO only when explicitly enabled; agent still works without it."""
    if os.getenv("YOLO_ENABLED", "0").lower() not in {"1", "true", "yes"}:
        return ObjectDetector()
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("YOLO_ENABLED=1 but ultralytics is not installed") from exc
    model = YOLO(os.getenv("YOLO_MODEL", "yolo11n.pt"))
    return ObjectDetector(model=model, confidence=float(os.getenv("YOLO_CONFIDENCE", "0.35")))


def summarize(detections: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in detections:
        counts[item.label] = counts.get(item.label, 0) + 1
    return counts
