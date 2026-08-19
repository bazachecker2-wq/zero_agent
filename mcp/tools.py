from __future__ import annotations

from drone.telemetry import TelemetryAdapter

telemetry = TelemetryAdapter()


def get_drone_telemetry() -> dict:
    """MCP-ready read-only tool for the current drone telemetry snapshot."""
    return telemetry.snapshot().as_dict()


def describe_detection_counts(detections: list[dict]) -> dict[str, int]:
    """Aggregate detector output without performing person identification."""
    counts: dict[str, int] = {}
    for item in detections:
        label = str(item.get("label", "unknown"))
        counts[label] = counts.get(label, 0) + 1
    return counts
