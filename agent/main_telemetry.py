from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, JobContext, RunContext, RoomInputOptions, function_tool
from livekit.plugins import google, silero

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("visiondrone")

PROMPT = """
You are VisionDrone, a realtime visual and voice assistant for a drone operator.
You receive live camera/audio plus SpeedyBee F405 V3 telemetry and YOLO detections.
Use current evidence only. Do not identify people or infer sensitive traits.
Use get_drone_state for flight status, battery, GPS, altitude, speed, heading and
latest detections. Never invent telemetry. You have no flight-control authority.
Never claim to arm, disarm, take off, land, move, or pilot the aircraft.
"""


class VisionDroneAgent(Agent):
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        super().__init__(instructions=PROMPT)

    @function_tool()
    async def get_drone_state(self, context: RunContext) -> dict[str, Any]:
        """Return the latest SpeedyBee F405 V3 telemetry and YOLO detections."""
        return {
            "telemetry": self.state.get("telemetry"),
            "detections": self.state.get("detections", []),
            "telemetry_timestamp": self.state.get("telemetry_timestamp"),
            "detection_timestamp": self.state.get("detection_timestamp"),
        }


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    state: dict[str, Any] = {"telemetry": None, "detections": []}

    @ctx.room.on("data_received")
    def on_data(packet: rtc.DataPacket) -> None:
        if packet.topic not in {"drone.telemetry", "vision.objects"}:
            return
        try:
            payload = json.loads(packet.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if payload.get("type") == "drone.telemetry":
            state["telemetry"] = payload.get("data")
            state["telemetry_timestamp"] = payload.get("ts")
        elif payload.get("type") == "vision.objects":
            state["detections"] = payload.get("detections", [])
            state["detection_timestamp"] = payload.get("ts")

    session = AgentSession(
        vad=silero.VAD.load(),
        llm=google.realtime.RealtimeModel(
            model=os.getenv("VISION_MODEL", "gemini-3.1-flash-live-preview"),
            api_key=os.environ["GOOGLE_API_KEY"],
            voice=os.getenv("VISION_VOICE", "Puck"),
            temperature=0.3,
        ),
    )
    await session.start(
        room=ctx.room,
        agent=VisionDroneAgent(state),
        room_input_options=RoomInputOptions(video_enabled=True),
    )
    await session.generate_reply(instructions="Briefly greet the operator and say you are ready to inspect the live camera, audio, detections, and SpeedyBee telemetry.")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
