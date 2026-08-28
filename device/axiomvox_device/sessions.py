from __future__ import annotations

import json
import shutil
import subprocess
from uuid import uuid4
from pathlib import Path

from shared.axiomvox_shared import AppState, SessionSummary, utc_now_iso

from .config import DeviceConfig


class SessionManager:
    def __init__(self, config: DeviceConfig) -> None:
        self.config = config
        self.capture_process: subprocess.Popen[bytes] | None = None

    def start(self, state: AppState) -> str:
        if state.current_session is not None:
            return f"Already recording: {state.current_session.id}"

        session_id = _session_id()
        session_path = self.config.session_dir / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        audio_path = session_path / "audio.wav"
        metadata_path = session_path / "metadata.json"
        session = SessionSummary(
            id=session_id,
            status="recording",
            started_at=utc_now_iso(),
            audio_path=str(audio_path),
            metadata_path=str(metadata_path),
        )
        state.current_session = session
        state.mode = "RECORDING"
        state.status_message = f"Recording {session_id}"
        self._start_capture(audio_path)
        self._write_metadata(session, capture_note=self._capture_note())
        state.touch()
        return state.status_message

    def bookmark(self, state: AppState) -> str:
        if state.current_session is None:
            return self.start(state)

        bookmark = utc_now_iso()
        state.current_session.bookmarks.append(bookmark)
        state.status_message = f"Bookmark {len(state.current_session.bookmarks)} saved"
        self._write_metadata(state.current_session, capture_note=self._capture_note())
        state.touch()
        return state.status_message

    def stop(self, state: AppState) -> str:
        if state.current_session is None:
            state.status_message = "No active recording"
            state.mode = "READY"
            state.touch()
            return state.status_message

        self._stop_capture()
        session = state.current_session
        session.status = "complete"
        session.ended_at = utc_now_iso()
        self._write_metadata(session, capture_note=self._capture_note())
        state.recent_sessions.insert(0, session)
        state.recent_sessions = state.recent_sessions[:10]
        state.current_session = None
        state.mode = "READY"
        state.status_message = f"Saved {session.id}"
        state.touch()
        return state.status_message

    def _start_capture(self, audio_path: Path) -> None:
        if not self.config.capture_enabled:
            return
        if shutil.which("arecord") is None:
            return
        self.capture_process = subprocess.Popen(
            ["arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "wav", str(audio_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _stop_capture(self) -> None:
        if self.capture_process is None:
            return
        self.capture_process.terminate()
        try:
            self.capture_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.capture_process.kill()
            self.capture_process.wait(timeout=2)
        finally:
            self.capture_process = None

    def _capture_note(self) -> str:
        if not self.config.capture_enabled:
            return "disabled"
        if self.capture_process is None:
            return "metadata-only"
        if self.capture_process.poll() is None:
            return "arecord"
        return "arecord-exited"

    @staticmethod
    def _write_metadata(session: SessionSummary, capture_note: str) -> None:
        if session.metadata_path is None:
            return
        payload = {
            "id": session.id,
            "status": session.status,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "audio_path": session.audio_path,
            "bookmarks": session.bookmarks,
            "audio_capture": capture_note,
            "audio_format": "wav pcm_s16le 16000hz mono",
            "transcription": "not implemented",
        }
        Path(session.metadata_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _session_id() -> str:
    stamp = utc_now_iso().replace("-", "").replace(":", "").replace("+00:00", "Z")
    return f"{stamp}-{uuid4().hex[:6]}"
