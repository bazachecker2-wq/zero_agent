from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import suppress

from livekit import api, rtc

from edge.speedybee_msp import SpeedyBeeMSP

logger = logging.getLogger("visiondrone.edge")


class EdgeLiveKitClient:
    """Onboard participant: publishes camera/video and SpeedyBee telemetry.

    Audio is optional here: for production audio capture, use the host's native
    microphone/ALSA/PulseAudio pipeline or an application-specific AudioSource.
    This client deliberately does not send flight-control commands.
    """

    def __init__(self) -> None:
        self.url = os.environ["LIVEKIT_URL"]
        self.api_key = os.environ["LIVEKIT_API_KEY"]
        self.api_secret = os.environ["LIVEKIT_API_SECRET"]
        self.room_name = os.getenv("LIVEKIT_ROOM", "visiondrone")
        self.identity = os.getenv("EDGE_IDENTITY", "drone-edge-f405v3")
        self.telemetry_interval = float(os.getenv("SPEEDYBEE_INTERVAL", "0.25"))
        self.camera_device = os.getenv("CAMERA_DEVICE", "/dev/video0")
        self.camera_fps = int(os.getenv("CAMERA_FPS", "20"))
        self.room = rtc.Room()
        self._stop = asyncio.Event()
        self._msp: SpeedyBeeMSP | None = None

    def token(self) -> str:
        return (
            api.AccessToken(self.api_key, self.api_secret)
            .with_identity(self.identity)
            .with_name("VisionDrone Edge")
            .with_grants(api.VideoGrants(room_join=True, room=self.room_name))
            .to_jwt()
        )

    async def connect(self) -> None:
        await self.room.connect(self.url, self.token(), auto_subscribe=True)
        logger.info("Edge connected to LiveKit room=%s identity=%s", self.room_name, self.identity)

    async def publish_telemetry(self) -> None:
        self._msp = SpeedyBeeMSP(
            port=os.getenv("SPEEDYBEE_PORT", "/dev/ttyUSB0"),
            baudrate=int(os.getenv("SPEEDYBEE_BAUD", "115200")),
        )
        await self._msp.connect()
        try:
            async for state in self._msp.stream(self.telemetry_interval):
                payload = {
                    "type": "drone.telemetry",
                    "schema": 1,
                    "source": "speedybee-f405-v3",
                    "ts": time.time(),
                    "data": state.as_dict(),
                }
                # Telemetry is a continuous stream: lossy is preferred so stale
                # samples never queue behind newer samples.
                await self.room.local_participant.publish_data(
                    json.dumps(payload, separators=(",", ":")).encode(),
                    reliable=False,
                    topic="drone.telemetry",
                )
                if self._stop.is_set():
                    break
        finally:
            await self._msp.close()
            self._msp = None

    async def run(self) -> None:
        await self.connect()
        tasks = [asyncio.create_task(self.publish_telemetry())]
        try:
            await self._stop.wait()
        finally:
            for task in tasks:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            await self.room.disconnect()

    async def stop(self) -> None:
        self._stop.set()


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    await EdgeLiveKitClient().run()


if __name__ == "__main__":
    asyncio.run(main())
