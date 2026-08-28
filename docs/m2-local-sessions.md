# M2 Local Sessions

M2 adds the first recording-session foundation. It is still device-only: no
transcription, AVTP streaming, server upload, or speaker diarization is
implemented in this milestone.

## Scope

- Whisplay short press starts a local session when idle.
- Whisplay short or double press adds a bookmark while a session is active.
- Whisplay long press stops and saves the active session.
- PiSugar button remains reserved for system/menu/shutdown controls.
- Session metadata is written under `/var/lib/axiomvox/sessions` by default.
- Local audio capture uses `arecord` when available.
- If `arecord` is unavailable, AxiomVox still writes metadata so the control
  loop can be tested.
- The web dashboard exposes active/recent sessions and browser test buttons.

## Session Layout

Each session gets its own directory:

```text
/var/lib/axiomvox/sessions/
└── 20260828T170000Z/
    ├── audio.wav
    └── metadata.json
```

`metadata.json` records the session id, start/end timestamps, bookmark
timestamps, audio path, capture mode, and a clear marker that transcription is
not implemented yet.

## Bench Testing

Use the dashboard buttons or the physical Whisplay button:

```text
Whisplay short: start or bookmark
Whisplay long: stop
```

For metadata-only testing without opening the ALSA capture device:

```bash
axiomvox-device --metadata-only --session-dir ./sessions --once
```

## Notes

This milestone intentionally keeps the first recording path simple. The next
recording work should validate the actual Whisplay ALSA device name, add
session duration and disk-space checks, and then choose the FLAC/WAV storage
policy before AVTP streaming is introduced.
