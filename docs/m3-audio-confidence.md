# M3 Audio Confidence

M3 verifies that local session capture is producing useful WAV files before
AxiomVox adds live transcription or AVTP server streaming.

## Scope

- Validate saved `audio.wav` files after each completed session.
- Record duration, size, sample rate, channel count, peak, RMS, and status in
  `metadata.json`.
- Load recent sessions from disk when the service starts.
- Show recent session audio status in the web dashboard.
- Provide dashboard download links for `audio.wav` and `metadata.json`.
- Provide a command-line WAV validator for bench checks.

## Audio Self-Test

Validate any saved session WAV:

```bash
axiomvox-device --audio-self-test /var/lib/axiomvox/sessions/<session-id>/audio.wav
```

Successful output includes:

```json
{
  "status": "ok",
  "detail": "audio looks usable",
  "sample_rate": 16000,
  "channels": 1
}
```

## Status Values

| Status | Meaning |
| --- | --- |
| `ok` | WAV opened and appears usable for transcription. |
| `silent` | WAV is valid but extremely quiet. |
| `warn` | WAV exists but does not match the expected format. |
| `empty` | WAV has no meaningful audio frames. |
| `missing` | The expected audio file was not found. |
| `invalid` | The file could not be read as WAV. |

## Expected Format

Device capture currently targets:

```text
wav pcm_s16le 16000hz mono
```

This is intentionally conservative for the Raspberry Pi Zero W and suitable for
future speech-to-text pipelines.
