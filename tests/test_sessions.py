from pathlib import Path
import json

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


class FakeCaptureProcess:
    def __init__(self) -> None:
        self.terminated = False

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int) -> int:
        return 0


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
