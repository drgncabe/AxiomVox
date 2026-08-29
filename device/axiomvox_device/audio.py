from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioValidation:
    status: str
    detail: str
    duration_seconds: float | None = None
    size_bytes: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    sample_width: int | None = None
    peak: int | None = None
    rms: int | None = None

    def to_dict(self) -> dict[str, int | float | str | None]:
        return {
            "status": self.status,
            "detail": self.detail,
            "duration_seconds": self.duration_seconds,
            "size_bytes": self.size_bytes,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
            "peak": self.peak,
            "rms": self.rms,
        }


def validate_wav(path: Path) -> AudioValidation:
    if not path.exists():
        return AudioValidation("missing", "audio.wav not found")

    size_bytes = path.stat().st_size
    if size_bytes <= 44:
        return AudioValidation("empty", "WAV file has no audio frames", size_bytes=size_bytes)

    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            duration = frame_count / sample_rate if sample_rate else 0
            peak, rms = _scan_pcm(wav, sample_width)
    except wave.Error as exc:
        return AudioValidation("invalid", f"invalid WAV: {exc}", size_bytes=size_bytes)
    except OSError as exc:
        return AudioValidation("invalid", f"could not read WAV: {exc}", size_bytes=size_bytes)

    if frame_count == 0 or duration <= 0:
        status = "empty"
        detail = "WAV opened, but contains no frames"
    elif sample_width != 2:
        status = "warn"
        detail = f"expected 16-bit PCM, got {sample_width * 8}-bit samples"
    elif sample_rate != 16000 or channels != 1:
        status = "warn"
        detail = f"expected 16000 Hz mono, got {sample_rate} Hz / {channels} channel(s)"
    elif (rms or 0) < 20 and (peak or 0) < 200:
        status = "silent"
        detail = "audio looks extremely quiet"
    else:
        status = "ok"
        detail = "audio looks usable"

    return AudioValidation(
        status=status,
        detail=detail,
        duration_seconds=round(duration, 2),
        size_bytes=size_bytes,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        peak=peak,
        rms=rms,
    )


def _scan_pcm(wav: wave.Wave_read, sample_width: int) -> tuple[int | None, int | None]:
    if sample_width not in {1, 2}:
        return None, None

    peak = 0
    total_square = 0
    total_samples = 0
    while True:
        frames = wav.readframes(4096)
        if not frames:
            break

        if sample_width == 1:
            for value in frames:
                centered = value - 128
                peak = max(peak, abs(centered))
                total_square += centered * centered
                total_samples += 1
        else:
            for idx in range(0, len(frames) - 1, 2):
                value = int.from_bytes(frames[idx : idx + 2], byteorder="little", signed=True)
                peak = max(peak, abs(value))
                total_square += value * value
                total_samples += 1

    if total_samples == 0:
        return 0, 0
    return peak, round(math.sqrt(total_square / total_samples))
