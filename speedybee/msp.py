from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import BinaryIO

MSP_API_VERSION = 1
MSP_FC_VARIANT = 2
MSP_FC_VERSION = 3
MSP_BOARD_INFO = 4
MSP_STATUS = 101
MSP_RAW_GPS = 106
MSP_ATTITUDE = 108
MSP_ALTITUDE = 109
MSP_ANALOG = 110
MSP_BATTERY_STATE = 130


class MSPError(RuntimeError):
    pass


def crc8_dvb_s2(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def frame_v1(command: int, payload: bytes = b"") -> bytes:
    if command > 255 or len(payload) > 255:
        raise ValueError("MSP v1 command/payload out of range")
    body = bytes((len(payload), command)) + payload
    checksum = 0
    for b in body:
        checksum ^= b
    return b"$M<" + body + bytes((checksum,))


@dataclass(slots=True)
class MSPPacket:
    command: int
    payload: bytes


class MSPClient:
    """Small read-only MSP v1 client for a serial-connected Betaflight FC.

    The client intentionally exposes only request/response reads. No RC, motor,
    arming, or configuration writes are implemented.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.25) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: BinaryIO | None = None

    def open(self) -> None:
        try:
            import serial
        except ImportError as exc:
            raise MSPError("pyserial is required for SpeedyBee serial access") from exc
        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def request(self, command: int, payload: bytes = b"") -> MSPPacket:
        if self._serial is None:
            raise MSPError("MSP serial port is not open")
        self._serial.reset_input_buffer()
        self._serial.write(frame_v1(command, payload))
        deadline = time.monotonic() + self.timeout
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._serial.read(64)
            if chunk:
                buf.extend(chunk)
                packet = self._parse(bytes(buf), command)
                if packet:
                    return packet
        raise MSPError(f"MSP timeout waiting for command {command}")

    @staticmethod
    def _parse(data: bytes, expected: int) -> MSPPacket | None:
        start = data.find(b"$M>")
        if start < 0 or len(data) < start + 6:
            return None
        size = data[start + 3]
        total = start + 6 + size
        if len(data) < total:
            return None
        command = data[start + 4]
        payload = data[start + 5:start + 5 + size]
        checksum = data[start + 5 + size]
        if command != expected:
            return None
        if checksum != __import__("functools").reduce(lambda a, b: a ^ b, data[start + 3:start + 5 + size], 0):
            raise MSPError("MSP checksum mismatch")
        return MSPPacket(command, payload)

    def read_raw_gps(self) -> dict:
        p = self.request(MSP_RAW_GPS).payload
        if len(p) < 16:
            raise MSPError("Invalid MSP_RAW_GPS payload")
        fix, sats, lat, lon, alt, speed, course = struct.unpack_from("<BBiiIHH", p, 0)
        return {
            "fix": fix,
            "satellites": sats,
            "latitude": lat / 10_000_000,
            "longitude": lon / 10_000_000,
            "altitude_m": alt / 100.0,
            "ground_speed_mps": speed / 100.0,
            "ground_course_deg": course / 10.0,
        }

    def read_attitude(self) -> dict:
        p = self.request(MSP_ATTITUDE).payload
        if len(p) < 6:
            raise MSPError("Invalid MSP_ATTITUDE payload")
        roll, pitch, yaw = struct.unpack_from("<hhh", p, 0)
        return {"roll_deg": roll / 10.0, "pitch_deg": pitch / 10.0, "yaw_deg": float(yaw)}

    def read_altitude(self) -> dict:
        p = self.request(MSP_ALTITUDE).payload
        if len(p) < 4:
            raise MSPError("Invalid MSP_ALTITUDE payload")
        altitude_cm = struct.unpack_from("<i", p, 0)[0]
        return {"altitude_m": altitude_cm / 100.0}

    def read_analog(self) -> dict:
        p = self.request(MSP_ANALOG).payload
        if len(p) < 5:
            raise MSPError("Invalid MSP_ANALOG payload")
        vbat, power, rssi, amp = struct.unpack_from("<BHBB", p, 0)
        return {"battery_voltage": vbat / 10.0, "power_used": power, "rssi": rssi, "current_a": amp / 100.0}
