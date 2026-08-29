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
class SystemStats:
    uptime_seconds: int | None = None
    load_1m: float | None = None
    load_5m: float | None = None
    load_15m: float | None = None
    memory_total_mb: int | None = None
    memory_available_mb: int | None = None
    memory_used_percent: float | None = None


@dataclass(slots=True)
class SessionSummary:
    id: str
    status: str
    started_at: str
    ended_at: str | None = None
    audio_path: str | None = None
    metadata_path: str | None = None
    audio_capture: str = "metadata-only"
    audio_capture_command: list[str] = field(default_factory=list)
    audio_status: str = "pending"
    audio_detail: str = ""
    audio_duration_seconds: float | None = None
    audio_size_bytes: int | None = None
    audio_sample_rate: int | None = None
    audio_channels: int | None = None
    audio_peak: int | None = None
    audio_rms: int | None = None
    bookmarks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppState:
    mode: str = "READY"
    started_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    hardware: HardwareStatus = field(default_factory=HardwareStatus)
    system: SystemStats = field(default_factory=SystemStats)
    web_reachable: bool = False
    active_screen: str = "ready"
    menu_items: list[str] = field(
        default_factory=lambda: ["Status", "Settings", "Sessions", "Exit"]
    )
    menu_index: int = 0
    settings_items: list[str] = field(default_factory=lambda: ["Display", "Power", "Logs", "Back"])
    settings_index: int = 0
    power_items: list[str] = field(default_factory=lambda: ["Shutdown", "Reboot", "Back"])
    power_index: int = 0
    brightness_levels: list[int] = field(default_factory=lambda: [20, 40, 60, 80, 100])
    brightness: int = 80
    display_awake: bool = True
    display_sleep_timeout_seconds: int = 300
    user_action_sequence: int = 0
    status_message: str = "Ready"
    last_button_event: str = ""
    current_session: SessionSummary | None = None
    recent_sessions: list[SessionSummary] = field(default_factory=list)
    shutdown_requested: bool = False
    power_action_requested: str = ""
    shutdown_message: str = ""

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def mark_user_action(self) -> None:
        self.user_action_sequence += 1
        self.display_awake = True
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
