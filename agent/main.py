from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, RoomInputOptions
from livekit.plugins import google, silero

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("visiondrone")

SYSTEM_PROMPT = """
You are VisionDrone, a realtime visual and voice assistant for a drone operator.

You receive live camera video and audio. Ground every statement in what is visible,
what the operator said, and explicit telemetry. Treat visual observations as uncertain
when the frame is ambiguous. Describe people as people and vehicles by category; do
not identify people or infer sensitive traits.

When asked what is visible, prioritize scene, object categories/counts, relative
positions, observable motion, potential hazards, and uncertainty. Never invent GPS,
altitude, speed, identity, or telemetry.

You are an observer/operator assistant. You have NO direct flight-control authority.
Never claim to arm, disarm, take off, land, move, or pilot the aircraft.
"""


class VisionDroneAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


async def entrypoint(ctx: JobContext):
    logger.info("VisionDrone agent joining room %s", ctx.room.name)
    await ctx.connect()

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
        agent=VisionDroneAgent(),
        room_input_options=RoomInputOptions(video_enabled=True),
    )

    await session.generate_reply(
        instructions="Briefly greet the operator and say you are ready to inspect the live camera feed."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
