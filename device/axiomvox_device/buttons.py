from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

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
    def __init__(self, probe: HardwareProbe) -> None:
        self.probe = probe
        self.previous: str | None = None

    def poll(self) -> Iterable[ButtonEvent]:
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
