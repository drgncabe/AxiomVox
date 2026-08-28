from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class ServiceStatus:
    name: str
    ok: bool
    detail: str = ""


@dataclass(slots=True)
class HardwareStatus:
    whisplay_detected: bool = False
    lcd_initialized: bool = False
    microphones_detected: bool = False
    whisplay_button_detected: bool = False
    pisugar_detected: bool = False
    battery_percentage: int | None = None
    pisugar_button_detected: bool = False
    hdmi_detected: bool = False
    diagnostics: list[ServiceStatus] = field(default_factory=list)


@dataclass(slots=True)
class SessionSummary:
    id: str
    status: str
    started_at: str
    ended_at: str | None = None
    audio_path: str | None = None
    metadata_path: str | None = None
    bookmarks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppState:
    mode: str = "READY"
    started_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    hardware: HardwareStatus = field(default_factory=HardwareStatus)
    web_reachable: bool = False
    active_screen: str = "ready"
    menu_items: list[str] = field(
        default_factory=lambda: ["Status", "Display", "Network", "Power", "Advanced", "Exit"]
    )
    menu_index: int = 0
    status_message: str = "Ready"
    last_button_event: str = ""
    current_session: SessionSummary | None = None
    recent_sessions: list[SessionSummary] = field(default_factory=list)
    shutdown_requested: bool = False
    shutdown_message: str = ""

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
