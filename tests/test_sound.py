import wave

from shared.axiomvox_shared import AppState
from device.axiomvox_device.config import DeviceConfig
from device.axiomvox_device.sound import SoundFeedback, clamp_volume


def test_clamp_volume_bounds_values() -> None:
    assert clamp_volume(-1) == 0
    assert clamp_volume(60) == 60
    assert clamp_volume(150) == 100


def test_sound_feedback_generates_test_chime(tmp_path) -> None:
    sound = SoundFeedback(DeviceConfig(), sound_dir=tmp_path)

    path = sound._ensure_chime("test")

    assert path.exists()
    with wave.open(str(path), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000
        assert wav.getnframes() > 0


def test_sound_feedback_skips_disabled_chimes(tmp_path) -> None:
    sound = SoundFeedback(DeviceConfig(), sound_dir=tmp_path)
    state = AppState(chimes_enabled=False)

    assert sound.play("start", state) == "Chimes disabled"
