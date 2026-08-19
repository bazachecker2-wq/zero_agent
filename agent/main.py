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
You are VisionDrone, a realtime visual and voice assistant.

You receive live camera frames and audio. Describe only what is reasonably visible or
supported by the available telemetry. You can discuss people and vehicles as object
categories, but do not identify people by name or infer sensitive traits.

When asked what is visible, prioritize: scene, object counts, relative positions,
motion if observable, hazards, and uncertainty. Never invent GPS, altitude, identity,
vehicle speed, or other telemetry.

You are an observer/operator assistant. In this MVP you have NO direct flight-control
authority. Never claim to have moved, landed, armed, disarmed, or piloted a drone.
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
            model="gemini-2.0-flash-live-001",
            api_key=os.environ["GOOGLE_API_KEY"],
            voice="Puck",
            temperature=0.3,
        ),
    )

    await session.start(
        room=ctx.room,
        agent=VisionDroneAgent(),
        room_input_options=RoomInputOptions(
            video_enabled=True,
        ),
    )

    await session.generate_reply(
        instructions="Briefly greet the operator and say you are ready to inspect the live camera feed."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
