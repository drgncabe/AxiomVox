from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    service_name: str = "axiomvox.service"
    shutdown_command: tuple[str, ...] = ("sudo", "-n", "/usr/bin/systemctl", "poweroff")
    reboot_command: tuple[str, ...] = ("sudo", "-n", "/usr/bin/systemctl", "reboot")
    allow_shutdown: bool = False
    simulate_hardware: bool = False
    status_file: Path | None = None
    session_dir: Path = Path("/var/lib/axiomvox/sessions")
    capture_enabled: bool = True
    capture_device: str = "plughw:whisplaysound,0"
    capture_format: str = "S32_LE"
    capture_rate: int = 48000
    capture_channels: int = 2
