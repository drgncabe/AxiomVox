from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from shared.axiomvox_shared import AppState


class WhisplayLcdDriver:
    WIDTH = 240
    HEIGHT = 280
    DEFAULT_BACKLIGHT = 80

    def __init__(self, runtime_path: Path | None = None) -> None:
        self.runtime_path = runtime_path or Path("/opt/axiomvox-vendor/Whisplay/runtime/whisplay.py")
        self.board = None
        self.detail = "Whisplay runtime not loaded"
        self.backlight_enabled = False
        self.backlight = self.DEFAULT_BACKLIGHT
        self.applied_backlight: int | None = None
        self._load_runtime()

    def available(self) -> bool:
        return self.board is not None

    def turn_on(self) -> str:
        if self.board is None:
            return self.detail
        try:
            self.backlight = self.DEFAULT_BACKLIGHT
            self.applied_backlight = None
            self._ensure_backlight()
        except Exception as exc:
            self.detail = f"Whisplay backlight update failed: {exc}"
            return self.detail
        return f"Whisplay backlight set to {self.DEFAULT_BACKLIGHT}"

    def set_brightness(self, brightness: int) -> str:
        self.backlight = max(0, min(100, brightness))
        self.applied_backlight = None
        self._ensure_backlight()
        return f"Whisplay backlight set to {self.backlight}"

    def render(self, state: AppState) -> str:
        if self.board is None:
            return self.detail

        try:
            self.backlight = state.brightness if state.display_awake else 0
            self._ensure_backlight()
            image = self._build_image(state)
            draw_image = getattr(self.board, "draw_image", None)
            if callable(draw_image):
                draw_image(0, 0, self.WIDTH, self.HEIGHT, image)
                return "Whisplay LCD updated via draw_image"
            display = getattr(self.board, "display", None)
            if callable(display):
                display(image)
                return "Whisplay LCD updated via display"
        except Exception as exc:
            self.detail = f"Whisplay LCD update failed: {exc}"
            return self.detail

        self.detail = "Whisplay runtime loaded, but no supported display method was found"
        return self.detail

    def _load_runtime(self) -> None:
        if not self.runtime_path.exists():
            return

        try:
            sys.path.insert(0, str(self.runtime_path.parent))
            spec = importlib.util.spec_from_file_location("axiomvox_whisplay_runtime", self.runtime_path)
            if spec is None or spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            board_class = getattr(module, "WhisplayBoard", None) or getattr(module, "Whisplay", None)
            if board_class is None:
                self.detail = "Whisplay runtime loaded, but board class was not found"
                return
            self.board = board_class()
            self._ensure_backlight()
            self.detail = "Whisplay runtime loaded"
        except Exception as exc:
            self.detail = f"Whisplay runtime load failed: {exc}"

    def _ensure_backlight(self) -> None:
        if self.board is None or self.applied_backlight == self.backlight:
            return
        set_backlight = getattr(self.board, "set_backlight", None)
        if callable(set_backlight):
            set_backlight(self.backlight)
            self.backlight_enabled = True
            self.applied_backlight = self.backlight

    def _build_image(self, state: AppState) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise RuntimeError("python3-pil is required for LCD rendering") from exc

        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), "#101820")
        draw = ImageDraw.Draw(image)
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        battery = (
            f"{state.hardware.battery_percentage}%"
            if state.hardware.battery_percentage is not None
            else "--"
        )

        draw.rectangle((0, 0, self.WIDTH, 42), fill="#1b4d6b")
        draw.text((10, 14), "AxiomVox", fill="white", font=title_font)
        draw.text((10, 58), state.mode, fill="#7ee787", font=title_font)
        draw.text((10, 84), f"BAT {battery}", fill="white", font=body_font)
        draw.text((10, 108), f"WEB {'OK' if state.web_reachable else '--'}", fill="white", font=body_font)
        draw.text((10, 132), f"HDMI {'OK' if state.hardware.hdmi_detected else '--'}", fill="white", font=body_font)
        draw.text((10, 170), state.status_message[:28], fill="#ffd166", font=body_font)

        # Whisplay runtimes commonly expect RGB565 bytes.
        return _rgb888_to_rgb565(image.tobytes())


def _rgb888_to_rgb565(rgb: bytes) -> bytes:
    out = bytearray()
    for idx in range(0, len(rgb), 3):
        r, g, b = rgb[idx], rgb[idx + 1], rgb[idx + 2]
        value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out.append((value >> 8) & 0xFF)
        out.append(value & 0xFF)
    return bytes(out)
