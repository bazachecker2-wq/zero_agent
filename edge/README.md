# VisionDrone Edge Client

The onboard client joins one LiveKit room and publishes:

- V4L2 camera as a WebRTC video track;
- read-only SpeedyBee F405 V3 / Betaflight MSP telemetry as a lossy LiveKit data stream on `drone.telemetry`.

The flight controller is never given ARM, RC, motor, navigation, or configuration commands.

## Linux test

```bash
export LIVEKIT_URL=wss://your-livekit-host
export LIVEKIT_API_KEY=...
export LIVEKIT_API_SECRET=...
export LIVEKIT_ROOM=visiondrone
export SPEEDYBEE_PORT=/dev/ttyUSB0
export CAMERA_DEVICE=/dev/video0
python -m edge.livekit_client
```

Verify devices first:

```bash
v4l2-ctl --list-devices
ls -l /dev/ttyUSB* /dev/ttyACM*
```

## Docker

```bash
docker compose -f edge/docker-compose.edge.yml up --build
```

The compose file uses host networking because WebRTC/UDP connectivity is sensitive to NAT. The camera and serial device paths must be changed to match the actual edge computer.

## Audio

The edge media path intentionally does not guess an ALSA device. A board-specific audio capture pipeline should publish an `AudioSource`/track after the camera path is validated. This avoids silently selecting the wrong microphone on embedded Linux.
