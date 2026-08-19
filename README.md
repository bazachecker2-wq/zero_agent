# VisionDrone Agent

Realtime camera + voice AI agent built around LiveKit Agents.

## Architecture

Camera/WebRTC or drone RTSP -> LiveKit -> Vision/Agent Runtime -> MCP tools -> Memory -> AI Operator -> Live Log.

The first MVP uses LiveKit Agents with Gemini Live for realtime multimodal conversation. Object detection is intentionally separated behind an optional YOLO worker so the language model is not responsible for frame-by-frame detection.

### MVP capabilities
- realtime microphone + camera input through LiveKit
- spoken questions and spoken answers
- scene understanding with a multimodal model
- optional YOLO object detection for people/vehicles/objects
- structured detections emitted as agent events
- MCP-ready tool layer
- drone telemetry adapter boundary (GPS, altitude, heading, battery)
- safety boundary between AI reasoning and flight-control commands
- Docker deployment

## Quick start

1. Create a LiveKit Cloud project and obtain `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`.
2. Obtain `GOOGLE_API_KEY` for Gemini Live.
3. Copy `.env.example` to `.env` and fill the values.
4. Install Python 3.11+ dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. Start the agent:

```bash
python -m agent.main dev
```

6. Connect from LiveKit Agents Playground with camera enabled.

## Drone video

For a drone, publish the camera stream into LiveKit using a WebRTC-capable gateway. For RTSP sources, place an RTSP->WebRTC/LiveKit gateway in front of the agent. Do not connect an LLM directly to the flight controller.

## Safety

The `drone/` layer is telemetry-only in this MVP. Any future flight-control tool must have explicit operator authorization, allowlists, geofencing, rate limits and an independent flight-controller safety layer.
