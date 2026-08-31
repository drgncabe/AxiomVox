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
                state.status_message = "Whisplay short: start recording or bookmark"
        elif event.gesture == "long":
            if self.sessions is not None:
                self.sessions.stop(state)
            else:
                state.status_message = "Whisplay long: stop recording"
        elif event.gesture == "double":
            if self.sessions is not None:
                self.sessions.bookmark(state)
            else:
                state.status_message = "Whisplay double: bookmark"
        else:
            state.status_message = f"Whisplay {event.gesture}: recording control"
        state.active_screen = "recording" if state.current_session is not None else "ready"

    def _handle_pisugar(self, event: ButtonEvent, state: AppState) -> None:
        if event.gesture == "very_long" and state.active_screen in {"shutdown_confirm", "reboot_confirm"}:
            action = "shutdown" if state.active_screen == "shutdown_confirm" else "reboot"
            state.power_action_requested = action
            state.shutdown_requested = action == "shutdown"
            state.status_message = f"{action.title()} requested"
            return

        if event.gesture == "short":
            self.advance_menu(state)
        elif event.gesture == "long":
            self.select_menu_item(state)
        elif event.gesture == "very_long":
            self.request_shutdown_confirm(state)
        else:
            state.status_message = "PiSugar system gesture reserved"

    def advance_menu(self, state: AppState) -> None:
        if state.active_screen in {"shutdown_confirm", "reboot_confirm"}:
            state.active_screen = "menu"
            state.status_message = "Back to menu"
            return
        if state.active_screen == "settings_menu":
            state.settings_index = (state.settings_index + 1) % len(state.settings_items)
            state.status_message = f"Settings: {state.settings_items[state.settings_index]}"
            return
        if state.active_screen == "power":
            state.power_index = (state.power_index + 1) % len(state.power_items)
            state.status_message = f"Power: {state.power_items[state.power_index]}"
            return
        if state.active_screen == "display_settings":
            self.adjust_brightness(state)
            return

        state.active_screen = "menu"
        state.menu_index = (state.menu_index + 1) % len(state.menu_items)
        state.status_message = f"Menu: {state.menu_items[state.menu_index]}"

    def select_menu_item(self, state: AppState) -> None:
        if state.active_screen == "power":
            self.select_power_item(state)
            return
        if state.active_screen == "settings_menu":
            self.select_settings_item(state)
            return
        if state.active_screen == "display_settings":
            state.active_screen = "settings_menu"
            state.status_message = "Back to settings"
            return
        if state.active_screen in {"status", "settings", "sessions", "logs", "reboot_confirm", "shutdown_confirm"}:
            state.active_screen = "menu"
            state.status_message = "Back to menu"
            return
        if state.active_screen == "pisugar_diagnostics":
            state.active_screen = "settings_menu"
            state.status_message = "Back to settings"
            return

        item = state.menu_items[state.menu_index]
        if item == "Exit":
            state.active_screen = "ready"
            state.status_message = "Ready"
        elif item == "Power":
            state.active_screen = "power"
            state.power_index = 0
            state.status_message = f"Power: {state.power_items[state.power_index]}"
        elif item == "Status":
            state.active_screen = "status"
            state.status_message = "Status"
        elif item == "Settings":
            state.active_screen = "settings_menu"
            state.settings_index = 0
            state.status_message = f"Settings: {state.settings_items[state.settings_index]}"
        elif item == "Sessions":
            state.active_screen = "sessions"
            state.status_message = f"Sessions: {len(state.recent_sessions)} recent"
        else:
            state.status_message = f"{item} configuration is planned"

    def select_settings_item(self, state: AppState) -> str:
        item = state.settings_items[state.settings_index]
        if item == "Back":
            state.active_screen = "menu"
            state.status_message = "Back to menu"
            return "back"
        if item == "Display":
            state.active_screen = "display_settings"
            state.status_message = f"Brightness: {state.brightness}%"
            return "display"
        if item == "Power":
            state.active_screen = "power"
            state.power_index = 0
            state.status_message = f"Power: {state.power_items[state.power_index]}"
            return "power"
        if item == "Logs":
            state.active_screen = "logs"
            state.status_message = "Logs available on web"
            return "logs"
        if item == "PiSugar":
            state.active_screen = "pisugar_diagnostics"
            state.status_message = "PiSugar diagnostics available on web"
            return "pisugar"
        return "unknown"

    def select_power_item(self, state: AppState) -> str:
        item = state.power_items[state.power_index]
        if item == "Back":
            state.active_screen = "menu"
            state.status_message = "Menu"
            return "back"
        if item == "Shutdown":
            self.request_shutdown_confirm(state)
            return "shutdown"
        if item == "Reboot":
            state.active_screen = "reboot_confirm"
            state.status_message = "Hold to confirm reboot"
            return "reboot"
        return "unknown"

    def adjust_brightness(self, state: AppState) -> None:
        current_index = 0
        if state.brightness in state.brightness_levels:
            current_index = state.brightness_levels.index(state.brightness)
        state.brightness = state.brightness_levels[(current_index + 1) % len(state.brightness_levels)]
        state.status_message = f"Brightness: {state.brightness}%"

    def request_shutdown_confirm(self, state: AppState) -> None:
        state.active_screen = "shutdown_confirm"
        state.status_message = "Hold to confirm shutdown"
