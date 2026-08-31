from pathlib import Path
import json
import wave

from shared.axiomvox_shared import AppState
from device.axiomvox_device.config import DeviceConfig
from device.axiomvox_device.sessions import SessionManager


def test_session_manager_writes_metadata_and_tracks_recent_sessions(tmp_path: Path) -> None:
    state = AppState()
    manager = SessionManager(DeviceConfig(session_dir=tmp_path, capture_enabled=False))

    manager.start(state)
    manager.bookmark(state)
    manager.stop(state)

    assert state.mode == "READY"
    assert state.current_session is None
    assert len(state.recent_sessions) == 1
    assert state.recent_sessions[0].status == "complete"
    assert state.recent_sessions[0].bookmarks
    assert Path(state.recent_sessions[0].metadata_path or "").exists()
    metadata = json.loads(Path(state.recent_sessions[0].metadata_path or "").read_text(encoding="utf-8"))
    assert metadata["audio_capture"] == "disabled"


class FakeCaptureProcess:
    def __init__(self) -> None:
        self.terminated = False

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int) -> int:
        return 0


class FakeSound:
    def __init__(self) -> None:
        self.played = []

    def play(self, name: str, state: AppState) -> str:
        self.played.append(name)
        return f"played {name}"


def test_session_manager_preserves_arecord_capture_mode_after_stop(tmp_path: Path, monkeypatch) -> None:
    state = AppState()
    manager = SessionManager(DeviceConfig(session_dir=tmp_path, capture_enabled=True))
    process = FakeCaptureProcess()
    monkeypatch.setattr("device.axiomvox_device.sessions.shutil.which", lambda name: "/usr/bin/arecord")
    monkeypatch.setattr("device.axiomvox_device.sessions.subprocess.Popen", lambda *args, **kwargs: process)

    manager.start(state)
    manager.stop(state)

    session = state.recent_sessions[0]
    metadata = json.loads(Path(session.metadata_path or "").read_text(encoding="utf-8"))
    assert process.terminated
    assert session.audio_capture == "arecord"
    assert metadata["audio_capture"] == "arecord"


def test_session_manager_plays_start_and_stop_chimes(tmp_path: Path) -> None:
    state = AppState()
    sound = FakeSound()
    manager = SessionManager(DeviceConfig(session_dir=tmp_path, capture_enabled=False), sound)

    manager.start(state)
    manager.stop(state)

    assert sound.played == ["start", "stop"]


def test_session_manager_validates_saved_wav_and_loads_recent(tmp_path: Path) -> None:
    state = AppState()
    manager = SessionManager(DeviceConfig(session_dir=tmp_path, capture_enabled=False))

    manager.start(state)
    audio_path = Path(state.current_session.audio_path or "")
    with wave.open(str(audio_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(4)
        wav.setframerate(48000)
        wav.writeframes(b"\x00\x00\x01\x10" * 9600)
    manager.stop(state)

    saved = state.recent_sessions[0]
    assert saved.audio_status == "ok"
    assert saved.audio_duration_seconds == 0.1
    assert saved.audio_size_bytes and saved.audio_size_bytes > 44
    assert "plughw:whisplaysound,0" in saved.audio_capture_command

    restarted_state = AppState()
    manager.load_recent(restarted_state)

    assert restarted_state.recent_sessions[0].id == saved.id
    assert restarted_state.recent_sessions[0].audio_status == "ok"
    assert "plughw:whisplaysound,0" in restarted_state.recent_sessions[0].audio_capture_command
