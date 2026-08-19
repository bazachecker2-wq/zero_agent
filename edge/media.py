from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress

from livekit import rtc

logger = logging.getLogger("visiondrone.media")


async def publish_v4l2_video(room: rtc.Room, device: str, fps: int) -> rtc.LocalVideoTrack:
    """Publish frames from a Linux V4L2 camera.

    Uses OpenCV for capture and LiveKit's VideoSource for WebRTC publishing.
    The capture loop is isolated in a thread so camera reads do not block asyncio.
    """
    import cv2

    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera: {device}")
    cap.set(cv2.CAP_PROP_FPS, fps)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    source = rtc.VideoSource(width, height)
    track = rtc.LocalVideoTrack.create_video_track("drone-camera", source)
    await room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA))

    async def loop() -> None:
        period = 1.0 / max(fps, 1)
        try:
            while True:
                ok, frame = await asyncio.to_thread(cap.read)
                if not ok:
                    await asyncio.sleep(period)
                    continue
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                video_frame = rtc.VideoFrame(width, height, rtc.VideoBufferType.RGB24, frame.tobytes())
                source.capture_frame(video_frame)
                await asyncio.sleep(period)
        finally:
            cap.release()

    task = asyncio.create_task(loop())
    track._visiondrone_capture_task = task  # type: ignore[attr-defined]
    return track


async def publish_microphone(room: rtc.Room) -> rtc.LocalAudioTrack | None:
    """Publish host microphone through LiveKit when enabled.

    For heterogeneous Linux boards, audio capture is intentionally delegated to
    LiveKit's native audio source integration. Set EDGE_AUDIO_ENABLED=false to
    disable it on boards without ALSA/PulseAudio.
    """
    if os.getenv("EDGE_AUDIO_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return None
    logger.warning("Native microphone capture must be supplied by the board's audio pipeline; skipping generic ALSA autodetection")
    return None
