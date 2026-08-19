from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass

from .msp import MSPClient, MSPError


@dataclass(slots=True)
class SpeedyBeeState:
    connected: bool = False
    firmware: str = "betaflight"
    fix: int | None = None
    satellites: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    ground_speed_mps: float | None = None
    ground_course_deg: float | None = None
    roll_deg: float | None = None
    pitch_deg: float | None = None
    yaw_deg: float | None = None
    battery_voltage: float | None = None
    current_a: float | None = None
    rssi: int | None = None
    last_error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class SpeedyBeeTelemetry:
    """Read-only polling adapter for SpeedyBee F405 V3 running Betaflight."""

    def __init__(self, port: str, baudrate: int = 115200, interval_s: float = 0.25) -> None:
        self.client = MSPClient(port, baudrate)
        self.interval_s = interval_s
        self.state = SpeedyBeeState()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.client.open()
        self.state.connected = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="speedybee-telemetry", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self.client.close()
        self.state.connected = False

    def snapshot(self) -> dict:
        return self.state.as_dict()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                gps = self.client.read_raw_gps()
                attitude = self.client.read_attitude()
                altitude = self.client.read_altitude()
                analog = self.client.read_analog()
                self.state.connected = True
                for source in (gps, attitude, altitude, analog):
                    for key, value in source.items():
                        if hasattr(self.state, key):
                            setattr(self.state, key, value)
                self.state.last_error = None
            except (MSPError, OSError, ValueError) as exc:
                self.state.last_error = str(exc)
            self._stop.wait(self.interval_s)
