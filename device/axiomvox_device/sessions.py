from __future__ import annotations

import json
import shutil
import subprocess
from uuid import uuid4
from pathlib import Path

from shared.axiomvox_shared import AppState, SessionSummary, utc_now_iso

from .audio import validate_wav
from .config import DeviceConfig


class SessionManager:
    def __init__(self, config: DeviceConfig) -> None:
        self.config = config
        self.capture_process: subprocess.Popen[bytes] | None = None

    def load_recent(self, state: AppState, limit: int = 10) -> None:
        if not self.config.session_dir.exists():
            return

        sessions = []
        for metadata_path in sorted(self.config.session_dir.glob("*/metadata.json"), reverse=True):
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            sessions.append(_session_from_metadata(payload, metadata_path))
            if len(sessions) >= limit:
                break

        state.recent_sessions = sessions

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
        session.audio_capture_command = self._capture_command(audio_path)
        self._start_capture(session.audio_capture_command)
        session.audio_capture = self._capture_note()
        self._write_metadata(session)
        state.touch()
        return state.status_message

    def bookmark(self, state: AppState) -> str:
        if state.current_session is None:
            return self.start(state)

        bookmark = utc_now_iso()
        state.current_session.bookmarks.append(bookmark)
        state.status_message = f"Bookmark {len(state.current_session.bookmarks)} saved"
        state.current_session.audio_capture = self._capture_note()
        self._write_metadata(state.current_session)
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
        self.validate_session_audio(session)
        self._write_metadata(session)
        state.recent_sessions.insert(0, session)
        state.recent_sessions = state.recent_sessions[:10]
        state.current_session = None
        state.mode = "READY"
        state.status_message = f"Saved {session.id}"
        state.touch()
        return state.status_message

    def validate_session_audio(self, session: SessionSummary) -> None:
        if session.audio_path is None:
            session.audio_status = "missing"
            session.audio_detail = "session has no audio path"
            return

        result = validate_wav(Path(session.audio_path))
        session.audio_status = result.status
        session.audio_detail = result.detail
        session.audio_duration_seconds = result.duration_seconds
        session.audio_size_bytes = result.size_bytes
        session.audio_sample_rate = result.sample_rate
        session.audio_channels = result.channels
        session.audio_peak = result.peak
        session.audio_rms = result.rms

    def _start_capture(self, command: list[str]) -> None:
        if not self.config.capture_enabled:
            return
        if shutil.which("arecord") is None:
            return
        self.capture_process = subprocess.Popen(
            command,
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
    def _write_metadata(session: SessionSummary) -> None:
        if session.metadata_path is None:
            return
        payload = {
            "id": session.id,
            "status": session.status,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "audio_path": session.audio_path,
            "bookmarks": session.bookmarks,
            "audio_capture": session.audio_capture,
            "audio_capture_command": session.audio_capture_command,
            "audio_format": _capture_format_label(session),
            "audio_status": session.audio_status,
            "audio_detail": session.audio_detail,
            "audio_duration_seconds": session.audio_duration_seconds,
            "audio_size_bytes": session.audio_size_bytes,
            "audio_sample_rate": session.audio_sample_rate,
            "audio_channels": session.audio_channels,
            "audio_peak": session.audio_peak,
            "audio_rms": session.audio_rms,
            "transcription": "not implemented",
        }
        Path(session.metadata_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _capture_command(self, audio_path: Path) -> list[str]:
        return [
            "arecord",
            "-q",
            "-D",
            self.config.capture_device,
            "-f",
            self.config.capture_format,
            "-r",
            str(self.config.capture_rate),
            "-c",
            str(self.config.capture_channels),
            "-t",
            "wav",
            str(audio_path),
        ]


def _session_id() -> str:
    stamp = utc_now_iso().replace("-", "").replace(":", "").replace("+00:00", "Z")
    return f"{stamp}-{uuid4().hex[:6]}"


def _session_from_metadata(payload: dict[str, object], metadata_path: Path) -> SessionSummary:
    return SessionSummary(
        id=str(payload.get("id") or metadata_path.parent.name),
        status=str(payload.get("status") or "unknown"),
        started_at=str(payload.get("started_at") or ""),
        ended_at=_string_or_none(payload.get("ended_at")),
        audio_path=_string_or_none(payload.get("audio_path")),
        metadata_path=str(metadata_path),
        audio_capture=str(payload.get("audio_capture") or "metadata-only"),
        audio_capture_command=[
            str(item) for item in payload.get("audio_capture_command", []) if isinstance(item, str)
        ]
        if isinstance(payload.get("audio_capture_command"), list)
        else [],
        audio_status=str(payload.get("audio_status") or "unknown"),
        audio_detail=str(payload.get("audio_detail") or ""),
        audio_duration_seconds=_float_or_none(payload.get("audio_duration_seconds")),
        audio_size_bytes=_int_or_none(payload.get("audio_size_bytes")),
        audio_sample_rate=_int_or_none(payload.get("audio_sample_rate")),
        audio_channels=_int_or_none(payload.get("audio_channels")),
        audio_peak=_int_or_none(payload.get("audio_peak")),
        audio_rms=_int_or_none(payload.get("audio_rms")),
        bookmarks=[str(item) for item in payload.get("bookmarks", []) if isinstance(item, str)]
        if isinstance(payload.get("bookmarks"), list)
        else [],
    )


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _capture_format_label(session: SessionSummary) -> str:
    command = session.audio_capture_command
    if not command:
        return "wav"
    try:
        sample_format = command[command.index("-f") + 1].lower()
        sample_rate = command[command.index("-r") + 1]
        channels = command[command.index("-c") + 1]
    except (ValueError, IndexError):
        return "wav"

    channel_label = "mono" if channels == "1" else "stereo" if channels == "2" else f"{channels}ch"
    return f"wav pcm_{sample_format.lower()} {sample_rate}hz {channel_label}"
