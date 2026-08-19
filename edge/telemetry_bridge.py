from __future__ import annotations

import asyncio
import json
import os
import time

from edge.speedybee_msp import SpeedyBeeMSP


async def run() -> None:
    client = SpeedyBeeMSP(
        port=os.getenv("SPEEDYBEE_PORT", "/dev/ttyUSB0"),
        baudrate=int(os.getenv("SPEEDYBEE_BAUD", "115200")),
    )
    await client.connect()
    interval = float(os.getenv("SPEEDYBEE_INTERVAL", "0.25"))
    try:
        async for state in client.stream(interval):
            event = {
                "type": "drone.telemetry",
                "source": "speedybee-f405-v3",
                "ts": time.time(),
                "data": state.as_dict(),
            }
            print(json.dumps(event, separators=(",", ":")), flush=True)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(run())
