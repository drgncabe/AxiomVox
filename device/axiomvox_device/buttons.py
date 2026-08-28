from __future__ import annotations

import time
from collections import deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .events import ButtonEvent
from .hardware import HardwareProbe


class ButtonPoller:
    def poll(self) -> Iterable[ButtonEvent]:
        return ()


class PiSugarButtonPoller(ButtonPoller):
    def __init__(self, probe: HardwareProbe) -> None:
        self.probe = probe
        self.previous: str | None = None

    def poll(self) -> Iterable[ButtonEvent]:
        value = self.probe.read_pisugar_button_state()
        if not value or value == self.previous:
            return ()

        self.previous = value
        gesture = _gesture_from_text(value)
        if gesture:
            return (ButtonEvent("pisugar", gesture),)
        return ()


class WhisplayButtonPoller(ButtonPoller):
    LONG_PRESS_SECONDS = 1.2
    DOUBLE_PRESS_SECONDS = 0.45

    def __init__(self, probe: HardwareProbe, board: Any = None) -> None:
        self.probe = probe
        self.previous: str | None = None
        self.board = board
        self.press_started_at: float | None = None
        self.last_short_at: float | None = None
        self.events: deque[ButtonEvent] = deque()
        self.callback_detail = ""
        self._attach_callbacks()

    def poll(self) -> Iterable[ButtonEvent]:
        if self.events:
            events = tuple(self.events)
            self.events.clear()
            return events

        event_path = Path("/run/axiomvox/whisplay-button-event")
        if not event_path.exists():
            return ()

        value = event_path.read_text(errors="ignore").strip().lower()
        if not value or value == self.previous:
            return ()

        self.previous = value
        gesture = _gesture_from_text(value)
        if gesture:
            return (ButtonEvent("whisplay", gesture),)
        return ()

    def _attach_callbacks(self) -> None:
        if self.board is None:
            return

        on_press = getattr(self.board, "on_button_press", None)
        on_release = getattr(self.board, "on_button_release", None)
        if not callable(on_press) or not callable(on_release):
            self.callback_detail = "Whisplay runtime does not expose button callbacks"
            return

        try:
            on_press(self._on_press)
            on_release(self._on_release)
            self.callback_detail = "Whisplay button callbacks attached"
        except Exception as exc:
            self.callback_detail = f"Whisplay button callback setup failed: {exc}"

    def _on_press(self, *args: object) -> None:
        self.press_started_at = time.monotonic()

    def _on_release(self, *args: object) -> None:
        if self.press_started_at is None:
            return

        now = time.monotonic()
        duration = now - self.press_started_at
        self.press_started_at = None

        if duration >= self.LONG_PRESS_SECONDS:
            self.last_short_at = None
            self.events.append(ButtonEvent("whisplay", "long"))
            return

        if self.last_short_at is not None and now - self.last_short_at <= self.DOUBLE_PRESS_SECONDS:
            self.last_short_at = None
            self.events.append(ButtonEvent("whisplay", "double"))
            return

        self.last_short_at = now
        self.events.append(ButtonEvent("whisplay", "short"))


def _gesture_from_text(value: str) -> str | None:
    value = value.lower()
    if "very" in value:
        return "very_long"
    if "long" in value:
        return "long"
    if "double" in value:
        return "double"
    if "short" in value or "single" in value or "click" in value or value in {"1", "pressed"}:
        return "short"
    return None
