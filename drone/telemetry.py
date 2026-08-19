from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DroneTelemetry:
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    heading_deg: float | None = None
    battery_pct: float | None = None
    velocity_mps: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_m": self.altitude_m,
            "heading_deg": self.heading_deg,
            "battery_pct": self.battery_pct,
            "velocity_mps": self.velocity_mps,
        }


class TelemetryAdapter:
    """Read-only boundary for MAVLink/DroneKit/PX4/ArduPilot adapters."""

    def __init__(self) -> None:
        self._telemetry = DroneTelemetry()

    def update(self, **values: float | None) -> DroneTelemetry:
        for key, value in values.items():
            if hasattr(self._telemetry, key):
                setattr(self._telemetry, key, value)
        return self._telemetry

    def snapshot(self) -> DroneTelemetry:
        return self._telemetry
