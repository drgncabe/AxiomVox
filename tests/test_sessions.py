from pathlib import Path

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
