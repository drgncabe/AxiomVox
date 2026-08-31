from __future__ import annotations

import math
import shutil
import subprocess
import wave
from array import array
from pathlib import Path

from shared.axiomvox_shared import AppState

from .config import DeviceConfig


class SoundFeedback:
    def __init__(self, config: DeviceConfig, sound_dir: Path = Path("/run/axiomvox/sounds")) -> None:
        self.config = config
        self.sound_dir = sound_dir

    def apply_state(self, state: AppState) -> str:
        state.chime_volume = clamp_volume(state.chime_volume)
        message = self.set_volume(state.chime_volume)
        return message

    def set_volume(self, volume: int) -> str:
        volume = clamp_volume(volume)
        amixer = shutil.which("amixer")
        if amixer is None:
            return "Volume saved; amixer not installed"

        result = subprocess.run(
            [amixer, "sset", self.config.mixer_control, f"{volume}%"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return f"Volume: {volume}%"
        detail = (result.stderr or result.stdout).strip()
        return f"Volume saved; mixer unavailable: {detail or result.returncode}"

    def play(self, name: str, state: AppState) -> str:
        if not state.chimes_enabled:
            return "Chimes disabled"

        aplay = shutil.which("aplay")
        if aplay is None:
            return "Chime skipped; aplay not installed"

        try:
            path = self._ensure_chime(name)
        except OSError as exc:
            return f"Chime unavailable: {exc}"

        subprocess.Popen(
            [aplay, "-q", "-D", self.config.playback_device, str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Chime: {name}"

    def _ensure_chime(self, name: str) -> Path:
        path = self.sound_dir / f"{name}.wav"
        if path.exists():
            return path

        self.sound_dir.mkdir(parents=True, exist_ok=True)
        if name == "start":
            _write_tone(path, [660, 880], 0.08)
        elif name == "stop":
            _write_tone(path, [880, 660], 0.08)
        else:
            _write_tone(path, [720], 0.1)
        return path


def clamp_volume(volume: int) -> int:
    return max(0, min(100, volume))


def _write_tone(path: Path, frequencies: list[int], segment_seconds: float, sample_rate: int = 16000) -> None:
    samples = array("h")
    amplitude = 9000
    for frequency in frequencies:
        frame_count = round(sample_rate * segment_seconds)
        for idx in range(frame_count):
            envelope = min(1.0, idx / 120, (frame_count - idx) / 120)
            value = round(amplitude * envelope * math.sin(2 * math.pi * frequency * idx / sample_rate))
            samples.append(value)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())
