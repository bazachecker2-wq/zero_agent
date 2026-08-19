# Edge Drone Client — SpeedyBee F405 V3

The edge computer runs beside the camera and reads **read-only** Betaflight MSP telemetry from a SpeedyBee F405 V3, then publishes it into the same LiveKit room as the drone media.

## Realtime path

```text
Camera ────────────────> LiveKit video track
Microphone ────────────> LiveKit audio track
SpeedyBee F405 V3 ─MSP─> Edge ─> LiveKit data packet: drone.telemetry
                                      |
                                      v
                              VisionDrone Agent
```

The F405 V3 is a Betaflight target named `SPEEDYBEEF405V3`. Verify the actual UART assignment and wiring in Betaflight Configurator before connecting the edge computer.

## Run telemetry publisher

```bash
export LIVEKIT_URL=wss://YOUR_PROJECT.livekit.cloud
export LIVEKIT_API_KEY=...
export LIVEKIT_API_SECRET=...
export LIVEKIT_ROOM=visiondrone
export SPEEDYBEE_PORT=/dev/ttyUSB0
export SPEEDYBEE_BAUD=115200
export SPEEDYBEE_INTERVAL=0.25
python -m edge.livekit_client
```

Telemetry is published on the `drone.telemetry` topic as lossy packets. This is deliberate: for continuous telemetry, a newer sample is more useful than retransmitting a stale sample.

## Camera/audio boundary

`livekit_client.py` is telemetry-first. The camera and microphone are intended to be published as normal LiveKit media tracks by the edge media process using the host's V4L2/ALSA devices. Keeping media capture separate avoids coupling hardware-specific Linux capture code to the flight-controller serial adapter.

## Safety boundary

The edge process is read-only with respect to the flight controller. It does not implement ARM/DISARM, RC injection, motor control, configuration writes, or autonomous flight commands.
