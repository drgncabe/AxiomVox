from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    shutdown_command: tuple[str, ...] = ("systemctl", "poweroff")
    allow_shutdown: bool = False
    simulate_hardware: bool = False
    status_file: Path | None = None
