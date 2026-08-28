from __future__ import annotations

import os
import socket
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from shared.axiomvox_shared import HardwareStatus, ServiceStatus


@dataclass(frozen=True, slots=True)
class ProbeResult:
    ok: bool
    detail: str


class HardwareProbe:
    def __init__(self, simulate: bool = False) -> None:
        self.simulate = simulate

    def collect(self) -> HardwareStatus:
        if self.simulate:
            return HardwareStatus(
                whisplay_detected=True,
                lcd_initialized=True,
                microphones_detected=True,
                whisplay_button_detected=True,
                pisugar_detected=True,
                battery_percentage=87,
                pisugar_button_detected=True,
                hdmi_detected=True,
                diagnostics=[
                    ServiceStatus("simulation", True, "Simulated M0 hardware"),
                ],
            )

        whisplay = self._probe_whisplay()
        lcd = self._probe_lcd()
        microphones = self._probe_microphones()
        whisplay_button = self._probe_whisplay_button()
        pisugar = self._probe_pisugar()
        battery = self._read_battery_percentage()
        pisugar_button = self._probe_pisugar_button()
        hdmi = self._probe_hdmi()

        return HardwareStatus(
            whisplay_detected=whisplay.ok,
            lcd_initialized=lcd.ok,
            microphones_detected=microphones.ok,
            whisplay_button_detected=whisplay_button.ok,
            pisugar_detected=pisugar.ok,
            battery_percentage=battery,
            pisugar_button_detected=pisugar_button.ok,
            hdmi_detected=hdmi.ok,
            diagnostics=[
                ServiceStatus("whisplay", whisplay.ok, whisplay.detail),
                ServiceStatus("lcd", lcd.ok, lcd.detail),
                ServiceStatus("microphones", microphones.ok, microphones.detail),
                ServiceStatus("whisplay_button", whisplay_button.ok, whisplay_button.detail),
                ServiceStatus("pisugar", pisugar.ok, pisugar.detail),
                ServiceStatus("pisugar_button", pisugar_button.ok, pisugar_button.detail),
                ServiceStatus("hdmi", hdmi.ok, hdmi.detail),
            ],
        )

    def _probe_whisplay(self) -> ProbeResult:
        i2c_devices = Path("/sys/bus/i2c/devices")
        if i2c_devices.exists() and any(i2c_devices.iterdir()):
            return ProbeResult(True, "I2C bus has attached devices")
        return ProbeResult(False, "No I2C devices found")

    def _probe_lcd(self) -> ProbeResult:
        fb_devices = sorted(Path("/dev").glob("fb*"))
        if fb_devices:
            return ProbeResult(True, f"Framebuffer present: {fb_devices[0]}")
        return ProbeResult(False, "No framebuffer device found")

    def _probe_microphones(self) -> ProbeResult:
        arecord = shutil.which("arecord")
        if not arecord:
            return ProbeResult(False, "arecord is not installed")
        result = subprocess.run(
            [arecord, "-l"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        output = result.stdout + result.stderr
        if "card" in output.lower():
            return ProbeResult(True, "ALSA capture device found")
        return ProbeResult(False, "No ALSA capture device reported")

    def _probe_input(self, keyword: str) -> ProbeResult:
        proc_bus_input = Path("/proc/bus/input/devices")
        if not proc_bus_input.exists():
            return ProbeResult(False, "/proc/bus/input/devices not available")
        text = proc_bus_input.read_text(errors="ignore").lower()
        if keyword in text:
            return ProbeResult(True, f"Input device mentions {keyword}")
        return ProbeResult(False, f"No input device mentions {keyword}")

    def _probe_whisplay_button(self) -> ProbeResult:
        runtime = Path("/opt/axiomvox-vendor/Whisplay/runtime/whisplay.py")
        if runtime.exists():
            return ProbeResult(True, "Whisplay runtime button API is installed")

        daemon = self._query_whisplay_daemon("health.ping")
        if daemon:
            return ProbeResult(True, "Whisplay daemon socket responded")

        generic_input = self._probe_any_input(["whisplay", "gpio", "button", "key"])
        if generic_input.ok:
            return ProbeResult(True, generic_input.detail)
        return ProbeResult(False, "No Whisplay runtime, daemon, or GPIO/button input found")

    def _probe_pisugar(self) -> ProbeResult:
        model = self._query_pisugar("get model")
        if model:
            return ProbeResult(True, f"PiSugar API responded: {self._parse_pisugar_value(model)}")

        i2c = self._read_i2c_byte(0x57, 0x2A)
        if i2c is not None:
            return ProbeResult(True, "PiSugar I2C battery register responded at 0x57")

        candidates = [
            Path("/sys/class/power_supply/pisugar-battery"),
            Path("/sys/class/power_supply/pisugar"),
        ]
        if any(path.exists() for path in candidates):
            return ProbeResult(True, "PiSugar power supply entry found")

        service = self._systemctl_is_active("pisugar-server")
        if service.ok:
            return ProbeResult(True, "pisugar-server service is active but API did not respond")

        if shutil.which("pisugar-server"):
            return ProbeResult(True, "pisugar-server command found but service/API did not respond")

        return ProbeResult(False, "PiSugar power interface not found")

    def _probe_pisugar_button(self) -> ProbeResult:
        responses = []
        for gesture in ("single", "double", "long"):
            response = self._query_pisugar(f"get button_enable {gesture}")
            if response:
                responses.append(f"{gesture}={self._parse_pisugar_button_value(response)}")

        if responses:
            return ProbeResult(True, "PiSugar button API responded: " + ", ".join(responses))

        response = self._query_pisugar("get button_enable")
        if response:
            return ProbeResult(True, f"PiSugar button API responded: {self._parse_pisugar_value(response)}")

        generic_input = self._probe_input("pisugar")
        if generic_input.ok:
            return generic_input

        service = self._systemctl_is_active("pisugar-server")
        if service.ok:
            return ProbeResult(False, "pisugar-server is active but button API did not respond")

        button_register = self._read_i2c_byte(0x57, 0x08)
        if button_register is not None:
            return ProbeResult(
                True,
                f"PiSugar I2C custom button register readable at 0x57/0x08: 0x{button_register:02x}",
            )
        return ProbeResult(False, f"PiSugar button API did not respond; {service.detail}")

    def _read_battery_percentage(self) -> int | None:
        pisugar_battery = self._query_pisugar("get battery")
        if pisugar_battery:
            try:
                value = self._parse_pisugar_value(pisugar_battery)
                return max(0, min(100, round(float(value))))
            except ValueError:
                pass

        i2c_battery = self._read_i2c_byte(0x57, 0x2A)
        if i2c_battery is not None:
            return max(0, min(100, i2c_battery))

        power_supply = Path("/sys/class/power_supply")
        if not power_supply.exists():
            return None

        for capacity in power_supply.glob("*/capacity"):
            try:
                value = int(capacity.read_text().strip())
            except ValueError:
                continue
            name = capacity.parent.name.lower()
            if "bat" in name or "pisugar" in name or os.environ.get("AXIOMVOX_ACCEPT_ANY_BATTERY"):
                return max(0, min(100, value))
        return None

    def _query_pisugar(self, command: str) -> str | None:
        for socket_path in ("/tmp/pisugar-server.sock", "/tmp/pisugar.sock"):
            response = self._query_unix_socket(socket_path, command)
            if response:
                return response
        response = self._query_tcp_socket("127.0.0.1", 8423, command)
        if response:
            return response
        return None

    def _query_whisplay_daemon(self, command: str) -> str | None:
        return self._query_unix_socket("/tmp/whisplay-daemon.sock", command)

    def _query_unix_socket(self, socket_path: str, command: str) -> str | None:
        if not Path(socket_path).exists():
            return None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(1)
                client.connect(socket_path)
                client.sendall(f"{command}\n".encode("utf-8"))
                return client.recv(256).decode("utf-8", errors="ignore").strip()
        except OSError:
            return None

    def _query_tcp_socket(self, host: str, port: int, command: str) -> str | None:
        try:
            with socket.create_connection((host, port), timeout=1) as client:
                client.settimeout(1)
                client.sendall(f"{command}\n".encode("utf-8"))
                return client.recv(256).decode("utf-8", errors="ignore").strip()
        except OSError:
            return None

    def _systemctl_is_active(self, service: str) -> ProbeResult:
        systemctl = shutil.which("systemctl")
        if not systemctl:
            return ProbeResult(False, "systemctl is not available")
        result = subprocess.run(
            [systemctl, "is-active", service],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        status = (result.stdout or result.stderr).strip()
        return ProbeResult(result.returncode == 0, f"{service} status: {status or 'unknown'}")

    def _read_i2c_byte(self, address: int, register: int, bus: int = 1) -> int | None:
        i2cget = shutil.which("i2cget")
        if not i2cget:
            return None
        result = subprocess.run(
            [i2cget, "-y", str(bus), hex(address), hex(register)],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return None
        value = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        try:
            return int(value, 0)
        except ValueError:
            return None

    def _parse_pisugar_value(self, response: str) -> str:
        if ":" in response:
            return response.split(":", 1)[1].strip()
        return response.strip()

    def _parse_pisugar_button_value(self, response: str) -> str:
        value = self._parse_pisugar_value(response)
        parts = value.split()
        if parts:
            return parts[-1]
        return value

    def _probe_any_input(self, keywords: list[str]) -> ProbeResult:
        proc_bus_input = Path("/proc/bus/input/devices")
        if not proc_bus_input.exists():
            return ProbeResult(False, "/proc/bus/input/devices not available")
        text = proc_bus_input.read_text(errors="ignore").lower()
        for keyword in keywords:
            if keyword in text:
                return ProbeResult(True, f"Input device mentions {keyword}")
        return ProbeResult(False, "No matching input device found")

    def _probe_hdmi(self) -> ProbeResult:
        drm = Path("/sys/class/drm")
        if not drm.exists():
            return ProbeResult(False, "/sys/class/drm not available")
        for status in drm.glob("card*-HDMI-A-*/status"):
            if status.read_text(errors="ignore").strip().lower() == "connected":
                return ProbeResult(True, f"{status.parent.name} connected")
        return ProbeResult(False, "No connected HDMI status found")
