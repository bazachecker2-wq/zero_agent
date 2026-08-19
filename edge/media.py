from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from livekit import rtc

logger = logging.getLogger("visiondrone.media")


async def publish_v4l2_video(room: rtc.Room, device: str, fps: int) -> rtc.LocalVideoTrack:
    """Publish V4L2 frames and optional YOLO detections to LiveKit."""
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

    model = None
    if os.getenv("YOLO_ENABLED", "true").lower() in {"1", "true", "yes"}:
        try:
            from ultralytics import YOLO
            model = YOLO(os.getenv("YOLO_MODEL", "yolo11n.pt"))
            logger.info("YOLO loaded")
        except Exception:
            logger.exception("YOLO unavailable; continuing with video only")

    async def loop() -> None:
        period = 1.0 / max(fps, 1)
        frame_no = 0
        every = max(1, int(os.getenv("YOLO_EVERY_N_FRAMES", "5")))
        try:
            while True:
                ok, frame = await asyncio.to_thread(cap.read)
                if not ok:
                    await asyncio.sleep(period)
                    continue
                frame_no += 1
                if model is not None and frame_no % every == 0:
                    await publish_yolo_events(room, model, frame, frame_no)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                source.capture_frame(rtc.VideoFrame(width, height, rtc.VideoBufferType.RGB24, rgb.tobytes()))
                await asyncio.sleep(period)
        finally:
            cap.release()

    task = asyncio.create_task(loop())
    track._visiondrone_capture_task = task  # type: ignore[attr-defined]
    return track


async def publish_yolo_events(room: rtc.Room, model, frame, frame_no: int) -> None:
    results = await asyncio.to_thread(model.predict, frame, verbose=False, conf=float(os.getenv("YOLO_CONF", "0.35")), imgsz=640)
    result = results[0]
    names = result.names
    detections = []
    if result.boxes is not None:
        for box in result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            detections.append({"class": names.get(cls, str(cls)), "confidence": round(conf, 4), "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]})
    payload = {"type": "vision.objects", "schema": 1, "source": "yolo", "ts": time.time(), "frame": frame_no, "detections": detections}
    await room.local_participant.publish_data(json.dumps(payload, separators=(",", ":")).encode(), reliable=False, topic="vision.objects")


async def publish_microphone(room: rtc.Room) -> rtc.LocalAudioTrack | None:
    if os.getenv("EDGE_AUDIO_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return None
    from edge.audio_alsa import publish_alsa_microphone
    return await publish_alsa_microphone(room)
