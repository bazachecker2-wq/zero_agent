from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Detection:
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


class ObjectDetector:
    """Optional local detector boundary.

    Plug a YOLO model into this class without coupling frame detection to the
    realtime language model. The detector should return categories such as
    person, car, truck, bicycle, motorcycle, bus and other configured classes.
    """

    def __init__(self, model: Any | None = None, confidence: float = 0.35) -> None:
        self.model = model
        self.confidence = confidence

    def detect(self, frame: Any) -> list[Detection]:
        if self.model is None:
            return []

        result = self.model(frame, conf=self.confidence, verbose=False)[0]
        names = result.names
        detections: list[Detection] = []
        for box in result.boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            detections.append(Detection(names[cls], conf, x1, y1, x2, y2))
        return detections
