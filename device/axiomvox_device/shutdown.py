from __future__ import annotations

import subprocess

from .config import DeviceConfig


class ShutdownController:
    def __init__(self, config: DeviceConfig) -> None:
        self.config = config

    def request(self) -> str:
        if not self.config.allow_shutdown:
            return "Shutdown requested. Dry-run mode is active."

        try:
            subprocess.Popen(self.config.shutdown_command)
        except OSError as exc:
            return f"Shutdown request failed: {exc}"
        return "Graceful shutdown requested."
