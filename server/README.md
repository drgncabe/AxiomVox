# AxiomVox Server

The AxiomVox Server is planned as a Docker-first service that receives AVTP/1
audio streams and returns transcript events.

M0 intentionally does not implement the server runtime. This directory exists
to mark the boundary for future milestones.

Planned components:

- AVTP/1 WebSocket endpoint.
- Session stream manager.
- faster-whisper transcription runtime.
- Model manager.
- Health/status API.
- CPU baseline container.
- Optional CUDA container.
