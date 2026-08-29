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
  "sample_rate": 48000,
  "channels": 2
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
arecord -q -D plughw:whisplaysound,0 -f S32_LE -r 48000 -c 2 -t wav audio.wav
```

This keeps local capture close to the Whisplay HAT's native clock. Future
speech-to-text pipelines can downsample from this source when needed.

The Whisplay sound card should be addressed by its stable ALSA card name
instead of whichever capture device happens to be the system default. If audio
sounds distorted, first compare AxiomVox output with the vendor-style manual
recording command:

```bash
arecord -D plughw:whisplaysound,0 -f S32_LE -r 48000 -c 2 -d 10 /tmp/whisplay-test.wav
aplay -D plughw:whisplaysound,0 /tmp/whisplay-test.wav
```

The service can still be tuned without code changes:

```bash
axiomvox-device --capture-device plughw:whisplaysound,0 --capture-format S32_LE --capture-rate 48000 --capture-channels 2
```
