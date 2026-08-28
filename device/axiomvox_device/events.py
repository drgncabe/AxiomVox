from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ButtonSource = Literal["whisplay", "pisugar"]
ButtonGesture = Literal["short", "double", "long", "very_long"]


@dataclass(frozen=True, slots=True)
class ButtonEvent:
    source: ButtonSource
    gesture: ButtonGesture

    def label(self) -> str:
        return f"{self.source}:{self.gesture}"
