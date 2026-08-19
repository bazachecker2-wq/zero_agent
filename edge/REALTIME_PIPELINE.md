# Realtime Edge Pipeline

The production path is now:

```text
SpeedyBee F405 V3 --MSP--> Edge
Camera --V4L2--------------> Edge --LiveKit--> VisionDrone Agent
Mic --ALSA/arecord---------> Edge --LiveKit--> VisionDrone Agent
YOLO ----------------------> Edge --data-----> VisionDrone Agent
Telemetry -----------------> Edge --data-----> VisionDrone Agent
```

## Edge environment

```bash
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_ROOM=visiondrone
SPEEDYBEE_PORT=/dev/ttyUSB0
SPEEDYBEE_BAUD=115200
CAMERA_DEVICE=/dev/video0
CAMERA_FPS=20
EDGE_CAMERA_ENABLED=true
EDGE_AUDIO_ENABLED=true
AUDIO_DEVICE=default
AUDIO_SAMPLE_RATE=48000
AUDIO_CHANNELS=1
AUDIO_FRAME_MS=20
YOLO_ENABLED=true
YOLO_MODEL=yolo11n.pt
YOLO_EVERY_N_FRAMES=5
YOLO_CONF=0.35
```

The edge container requires access to `/dev/video0`, the SpeedyBee serial device, and `/dev/snd`. ALSA capture uses `arecord` and publishes signed 16-bit PCM frames through a LiveKit `AudioSource`.

YOLO runs locally on the edge computer every N frames and publishes compact `vision.objects` lossy data packets. SpeedyBee telemetry is published on `drone.telemetry` lossy data packets. The agent subscribes to both topics and exposes the latest state through the `get_drone_state` function tool.

No flight-control commands are implemented in this pipeline.
