import math
import struct
import wave
from pathlib import Path

from device.axiomvox_device.audio import validate_wav


def test_validate_wav_reports_usable_audio(tmp_path: Path) -> None:
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        frames = bytearray()
        for idx in range(1600):
            sample = round(12000 * math.sin(idx / 8))
            frames.extend(struct.pack("<h", sample))
        wav.writeframes(bytes(frames))

    result = validate_wav(path)

    assert result.status == "ok"
    assert result.sample_rate == 16000
    assert result.channels == 1
    assert result.duration_seconds == 0.1
    assert result.peak and result.peak > 1000
    assert result.rms and result.rms > 1000


def test_validate_wav_reports_silent_audio(tmp_path: Path) -> None:
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 1600)

    result = validate_wav(path)

    assert result.status == "silent"
    assert result.detail == "audio looks extremely quiet"
