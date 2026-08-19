from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Iterable

from .detector import Detection


@dataclass(slots=True)
class Track:
    id: int
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    first_seen: float = field(default_factory=monotonic)
    last_seen: float = field(default_factory=monotonic)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class CentroidTracker:
    """Small dependency-free tracker for stable object IDs between frames."""

    def __init__(self, max_distance: float = 90.0, max_age_s: float = 1.5) -> None:
        self.max_distance = max_distance
        self.max_age_s = max_age_s
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    def update(self, detections: Iterable[Detection]) -> list[Track]:
        now = monotonic()
        candidates = list(detections)
        used: set[int] = set()
        result: list[Track] = []

        for det in candidates:
            cx = (det.x1 + det.x2) / 2
            cy = (det.y1 + det.y2) / 2
            best_id = None
            best_dist = self.max_distance
            for track_id, track in self._tracks.items():
                if track_id in used or track.label != det.label:
                    continue
                tx, ty = track.center
                dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
                if dist < best_dist:
                    best_id, best_dist = track_id, dist

            if best_id is None:
                best_id = self._next_id
                self._next_id += 1
                track = Track(best_id, det.label, det.confidence, det.x1, det.y1, det.x2, det.y2)
                self._tracks[best_id] = track
            else:
                track = self._tracks[best_id]
                track.confidence = det.confidence
                track.x1, track.y1, track.x2, track.y2 = det.x1, det.y1, det.x2, det.y2
                track.last_seen = now
            used.add(best_id)
            result.append(track)

        self._tracks = {k: v for k, v in self._tracks.items() if now - v.last_seen <= self.max_age_s}
        return result
