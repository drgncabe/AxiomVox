from __future__ import annotations

import subprocess

from .config import DeviceConfig


class ShutdownController:
    def __init__(self, config: DeviceConfig) -> None:
        self.config = config

    def request(self) -> str:
        return self.request_power("shutdown")

    def request_power(self, action: str) -> str:
        commands = {
            "shutdown": self.config.shutdown_command,
            "reboot": self.config.reboot_command,
        }
        if action not in commands:
            return f"Unknown power action: {action}"

        if not self.config.allow_shutdown:
            return f"{action.title()} requested. Dry-run mode is active."

        try:
            subprocess.Popen(commands[action])
        except OSError as exc:
            return f"{action.title()} request failed: {exc}"
        return f"Graceful {action} requested."
