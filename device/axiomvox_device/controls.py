from __future__ import annotations

from shared.axiomvox_shared import AppState

from .events import ButtonEvent
from .sessions import SessionManager


class ApplianceController:
    def __init__(self, sessions: SessionManager | None = None) -> None:
        self.sessions = sessions

    def handle_button(self, event: ButtonEvent, state: AppState) -> None:
        state.last_button_event = event.label()

        if event.source == "whisplay":
            self._handle_whisplay(event, state)
        else:
            self._handle_pisugar(event, state)

        state.touch()

    def _handle_whisplay(self, event: ButtonEvent, state: AppState) -> None:
        if event.gesture == "short":
            if self.sessions is not None:
                self.sessions.bookmark(state)
            else:
                state.status_message = "Recording control reserved: start/bookmark"
        elif event.gesture == "long":
            if self.sessions is not None:
                self.sessions.stop(state)
            else:
                state.status_message = "Recording control reserved: stop"
        elif event.gesture == "double":
            if self.sessions is not None:
                self.sessions.bookmark(state)
            else:
                state.status_message = "Recording control reserved: bookmark"
        else:
            state.status_message = f"Recording control reserved: {event.gesture}"
        state.active_screen = "recording" if state.current_session is not None else "ready"

    def _handle_pisugar(self, event: ButtonEvent, state: AppState) -> None:
        if event.gesture == "short":
            self.advance_menu(state)
        elif event.gesture == "long":
            self.select_menu_item(state)
        elif event.gesture == "very_long":
            self.request_shutdown_confirm(state)
        else:
            state.status_message = "PiSugar system gesture reserved"

    def advance_menu(self, state: AppState) -> None:
        state.active_screen = "menu"
        state.menu_index = (state.menu_index + 1) % len(state.menu_items)
        state.status_message = f"Menu: {state.menu_items[state.menu_index]}"

    def select_menu_item(self, state: AppState) -> None:
        item = state.menu_items[state.menu_index]
        if item == "Exit":
            state.active_screen = "ready"
            state.status_message = "Ready"
        elif item == "Power":
            state.active_screen = "power"
            state.status_message = "Power menu"
        elif item == "Status":
            state.active_screen = "status"
            state.status_message = "Status"
        else:
            state.status_message = f"{item} configuration is planned"

    def request_shutdown_confirm(self, state: AppState) -> None:
        state.active_screen = "shutdown_confirm"
        state.status_message = "Hold to confirm shutdown"
