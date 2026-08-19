from __future__ import annotations

import asyncio
import logging
import os

from livekit import rtc

logger = logging.getLogger("visiondrone.audio")


async def publish_alsa_microphone(room: rtc.Room) -> rtc.LocalAudioTrack:
    """Capture S16_LE PCM from ALSA using arecord and publish it to LiveKit."""
    sample_rate = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))
    channels = int(os.getenv("AUDIO_CHANNELS", "1"))
    frame_ms = int(os.getenv("AUDIO_FRAME_MS", "20"))
    device = os.getenv("AUDIO_DEVICE", "default")
    samples = sample_rate * frame_ms // 1000
    bytes_per_frame = samples * channels * 2

    source = rtc.AudioSource(sample_rate, channels, queue_size_ms=200)
    track = rtc.LocalAudioTrack.create_audio_track("drone-microphone", source)
    await room.local_participant.publish_track(
        track,
        rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE),
    )

    proc = await asyncio.create_subprocess_exec(
        "arecord", "-q", "-D", device, "-t", "raw", "-f", "S16_LE",
        "-r", str(sample_rate), "-c", str(channels), "-B", "20",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def loop() -> None:
        assert proc.stdout is not None
        try:
            while True:
                data = await proc.stdout.readexactly(bytes_per_frame)
                frame = rtc.AudioFrame(
                    data=data,
                    sample_rate=sample_rate,
                    num_channels=channels,
                    samples_per_channel=samples,
                )
                await source.capture_frame(frame)
        except (asyncio.IncompleteReadError, asyncio.CancelledError):
            pass
        finally:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    proc.kill()
            await source.aclose()

    task = asyncio.create_task(loop())
    track._visiondrone_audio_task = task  # type: ignore[attr-defined]
    logger.info("ALSA microphone published: device=%s %sHz/%sch", device, sample_rate, channels)
    return track
