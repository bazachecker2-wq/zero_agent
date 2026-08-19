# SpeedyBee F405 V3

Read-only Betaflight MSP telemetry adapter for the VisionDrone edge client.

## Wiring / port

Connect the companion computer to a configured MSP serial port on the FC. The FC must expose MSP on that UART and use a supported MSP baudrate (115200 is the default here). Do not connect this adapter to a receiver-only UART.

## Environment

```env
SPEEDYBEE_ENABLED=0
SPEEDYBEE_PORT=/dev/ttyUSB0
SPEEDYBEE_BAUD=115200
SPEEDYBEE_POLL_HZ=4
```

The adapter is intentionally read-only: it does not implement arming, RC injection, motor commands, configuration writes, or flight-control commands.

## Data

The adapter reads GPS, attitude, altitude and analog/battery telemetry using Betaflight MSP v1 read commands and exposes one normalized `SpeedyBeeState` snapshot.
