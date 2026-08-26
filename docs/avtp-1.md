# AVTP/1 Protocol

AVTP/1 is the planned AxiomVox transport protocol for device-to-server live
audio streaming and transcription results. M0 defines the lightweight protocol
shape only; no runtime implementation is included.

## Transport

- WebSocket connection from device to server.
- JSON text frames for control messages.
- Binary frames for encoded audio chunks.
- UTF-8 JSON.
- Protocol version string: `AVTP/1`.

## Session Flow

```text
DEVICE                         SERVER

HELLO ------------------------>
      <---------------------- WELCOME

SESSION_START ---------------->

[binary audio]
[binary audio] --------------->
[binary audio]

      <---------- TRANSCRIPT_PARTIAL
      <------------ TRANSCRIPT_FINAL

BOOKMARK --------------------->

SESSION_END ------------------>
      <------------- SESSION_COMPLETE
```

## Control Frame Envelope

```json
{
  "protocol": "AVTP/1",
  "type": "HELLO",
  "id": "01J...",
  "timestamp": "2026-08-25T14:30:00Z",
  "payload": {}
}
```

## Client-To-Server Control Types

- `HELLO`: device identity, software version, capabilities.
- `SESSION_START`: begins a recording/transcription session.
- `BOOKMARK`: marks an important moment in the active session.
- `SESSION_END`: ends the active session.
- `PING`: keepalive.

## Server-To-Client Control Types

- `WELCOME`: accepted protocol version and server capabilities.
- `TRANSCRIPT_PARTIAL`: unstable transcript text.
- `TRANSCRIPT_FINAL`: committed transcript text.
- `SESSION_COMPLETE`: final session metadata.
- `ERROR`: recoverable or terminal protocol error.
- `PONG`: keepalive response.

## Binary Audio Frames

Binary frames belong to the active session established by `SESSION_START`.
Initial V1 preference is FLAC chunks after device-side capture/buffering
exists. Exact chunk duration and audio metadata will be locked before the first
runtime implementation.

## Versioning

Protocol-breaking changes must use a new protocol string such as `AVTP/2`.
Backward-compatible additions may add optional payload fields.
