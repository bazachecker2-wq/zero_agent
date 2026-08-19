from __future__ import annotations

import asyncio
import struct
from dataclasses import asdict, dataclass
from typing import AsyncIterator

import serial_asyncio


MSP_API_VERSION = 1
MSP_FC_VARIANT = 2
MSP_FC_VERSION = 3
MSP_STATUS = 101
MSP_RAW_GPS = 106
MSP_ATTITUDE = 108
MSP_ALTITUDE = 109
MSP_ANALOG = 110
MSP_BATTERY_STATE = 130


@dataclass(slots=True)
class SpeedyBeeState:
    connected: bool = False
    armed: bool = False
    mode: str = "UNKNOWN"
    latitude: float | None = None
    longitude: float | None = None
    satellites: int | None = None
    altitude_m: float | None = None
    ground_speed_mps: float | None = None
    course_deg: float | None = None
    roll_deg: float | None = None
    pitch_deg: float | None = None
    yaw_deg: float | None = None
    battery_voltage: float | None = None
    battery_current_a: float | None = None
    battery_percent: float | None = None
    rssi: int | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def frame(command: int, payload: bytes = b"") -> bytes:
    body = bytes([MSP_API_VERSION, command & 0xFF, len(payload) & 0xFF]) + payload
    checksum = 0
    for b in body:
        checksum ^= b
    return b"$M<" + body + bytes([checksum])


async def read_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    while True:
        if await reader.readexactly(1) != b"$":
            continue
        if await reader.readexactly(2) != b"M<":
            continue
        header = await reader.readexactly(3)
        _version, command, size = header
        payload = await reader.readexactly(size)
        checksum = await reader.readexactly(1)
        if (sum(header) + sum(payload)) & 0xFF != checksum[0]:
            continue
        return command, payload


class SpeedyBeeMSP:
    """Read-only MSP telemetry client for SpeedyBee F405 V3 / Betaflight."""

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.state = SpeedyBeeState()

    async def connect(self) -> None:
        self.reader, self.writer = await serial_asyncio.open_serial_connection(
            url=self.port, baudrate=self.baudrate
        )
        self.state.connected = True

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.state.connected = False

    async def request(self, command: int) -> bytes:
        if not self.writer or not self.reader:
            raise RuntimeError("SpeedyBee MSP is not connected")
        self.writer.write(frame(command))
        await self.writer.drain()
        _, payload = await asyncio.wait_for(read_frame(self.reader), timeout=1.0)
        return payload

    async def poll_once(self) -> SpeedyBeeState:
        status = await self.request(MSP_STATUS)
        if len(status) >= 11:
            cycle_time, i2c_errors, sensors, mode_flags, profile = struct.unpack_from("<HHIBB", status)
            self.state.armed = bool(mode_flags & 0x01)
            self.state.mode = "ARMED" if self.state.armed else "DISARMED"

        gps = await self.request(MSP_RAW_GPS)
        if len(gps) >= 16:
            fix, sats, lat, lon, alt_cm, speed_cms, course = struct.unpack_from("<BBiiHHH", gps)
            self.state.satellites = sats
            if fix:
                self.state.latitude = lat / 10_000_000
                self.state.longitude = lon / 10_000_000
            self.state.altitude_m = alt_cm / 100
            self.state.ground_speed_mps = speed_cms / 100
            self.state.course_deg = course / 10

        attitude = await self.request(MSP_ATTITUDE)
        if len(attitude) >= 6:
            roll, pitch, yaw = struct.unpack_from("<hhh", attitude)
            self.state.roll_deg = roll / 10
            self.state.pitch_deg = pitch / 10
            self.state.yaw_deg = float(yaw)

        battery = await self.request(MSP_BATTERY_STATE)
        if len(battery) >= 4:
            cell_count, voltage, mah_drawn, current = struct.unpack_from("<BBHH", battery)
            self.state.battery_voltage = voltage / 10
            self.state.battery_current_a = current / 100
            # Percent is intentionally not fabricated: FC firmware/config determines capacity.

        return self.state

    async def stream(self, interval: float = 0.25) -> AsyncIterator[SpeedyBeeState]:
        while True:
            try:
                yield await self.poll_once()
            except (asyncio.TimeoutError, ConnectionError, serial_asyncio.serial.SerialException):
                self.state.connected = False
            await asyncio.sleep(interval)
