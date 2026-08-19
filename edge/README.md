# Edge Drone Client — SpeedyBee F405 V3

The edge layer runs beside the camera and reads **read-only** Betaflight MSP telemetry from a SpeedyBee F405 V3.

## Hardware path

`SpeedyBee F405 V3 -> USB/UART -> Edge computer -> LiveKit/WebRTC -> Vision Agent`

The F405 V3 is a Betaflight target named `SPEEDYBEEF405V3`. Its current Betaflight target exposes MSP on UART4 by default, while UART5 is the ESC sensor port. Verify the actual UART assignment in Betaflight Configurator before wiring the edge computer.

## Local test

```bash
export SPEEDYBEE_PORT=/dev/ttyUSB0
export SPEEDYBEE_BAUD=115200
python -m edge.telemetry_bridge
```

The bridge emits newline-delimited JSON events. It does not send ARM, RC, motor, configuration, or other control commands.

## Camera / LiveKit

The next edge process can run beside this bridge and publish the camera and microphone into the same LiveKit room. LiveKit Agents supports realtime audio/video/data and live video input with supported realtime models.
