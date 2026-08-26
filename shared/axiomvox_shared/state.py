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
class AppState:
    mode: str = "READY"
    started_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    hardware: HardwareStatus = field(default_factory=HardwareStatus)
    web_reachable: bool = False
    shutdown_requested: bool = False
    shutdown_message: str = ""

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
