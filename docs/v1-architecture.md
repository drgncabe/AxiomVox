# V1 Architecture

## Goals

AxiomVox V1 is split into a Raspberry Pi appliance device and a Docker-first
AxiomVox Server. M0 implements only the device foundation and documents the
server boundary.

```text
AxiomVox Device
|-- device application
|   |-- application state
|   |-- hardware diagnostics
|   |-- Whisplay LCD renderer
|   |-- passive HDMI status renderer
|   |-- web configurator
|   `-- systemd startup
|
|-- future audio
|   |-- Whisplay microphones
|   |-- VAD
|   |-- buffering
|   `-- FLAC recording
|
`-- future transcription
    |-- AVTP client
    |-- cloud client
    `-- local whisper.cpp option

AxiomVox Server
|-- AVTP WebSocket endpoint
|-- session streams
|-- faster-whisper runtime
|-- model manager
`-- health/status API
```

## Device Components

The device application is written in Python and launched by systemd. It owns
the shared state used by all M0 surfaces:

- Hardware probe results.
- Battery percentage.
- Display status.
- Web service status.
- Startup mode.
- Shutdown request state.

M0 keeps hardware integration behind small probe classes so real Raspberry Pi
implementations can replace file-based and command-based checks without
changing the app flow.

## Device Profiles

M0 supports:

- Raspberry Pi Zero W with Raspberry Pi OS Lite 32-bit.
- Raspberry Pi Zero 2 W with Raspberry Pi OS Lite 64-bit.

The Zero W profile is an appliance-only target. It should run hardware
validation, status displays, the local web configurator, and future lightweight
recording controls. Heavy transcription and Docker server workloads belong on a
separate AxiomVox Server.

## Server Boundary

The server is Docker-first. M0 creates the repository boundary and documents the
intended shape, but it does not implement transcription or AVTP runtime code.

Future server milestones should provide:

- CPU baseline container.
- Optional CUDA container.
- AVTP/1 WebSocket endpoint.
- Model download/cache management.
- Health and readiness endpoints.

## Startup

The device runs under `axiomvox.service`. The service starts after network
availability, restarts on failure, and exposes the web configurator on the
configured host and port.

## M0 Non-Goals

- Audio capture.
- Recording.
- Transcription.
- AVTP client/server runtime.
- Full menu navigation.
- User authentication.
- Cloud integrations.
