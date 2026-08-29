from shared.axiomvox_shared import AppState
from device.axiomvox_device.controls import ApplianceController
from device.axiomvox_device.events import ButtonEvent


class FakeSessions:
    def bookmark(self, state: AppState) -> str:
        state.status_message = "fake bookmark"
        return state.status_message

    def stop(self, state: AppState) -> str:
        state.status_message = "fake stop"
        return state.status_message


def test_whisplay_button_is_reserved_for_recording_controls() -> None:
    state = AppState()

    ApplianceController().handle_button(ButtonEvent("whisplay", "short"), state)

    assert state.active_screen == "ready"
    assert state.last_button_event == "whisplay:short"
    assert "Recording control reserved" in state.status_message


def test_whisplay_button_delegates_to_session_manager_when_available() -> None:
    state = AppState()

    ApplianceController(FakeSessions()).handle_button(ButtonEvent("whisplay", "short"), state)

    assert state.last_button_event == "whisplay:short"
    assert state.status_message == "fake bookmark"


def test_pisugar_short_press_advances_system_menu() -> None:
    state = AppState()

    ApplianceController().handle_button(ButtonEvent("pisugar", "short"), state)

    assert state.active_screen == "menu"
    assert state.menu_index == 1
    assert state.status_message == "Menu: Settings"


def test_pisugar_very_long_press_opens_shutdown_confirmation() -> None:
    state = AppState()

    ApplianceController().handle_button(ButtonEvent("pisugar", "very_long"), state)

    assert state.active_screen == "shutdown_confirm"
    assert state.status_message == "Hold to confirm shutdown"


def test_very_long_press_on_confirm_requests_power_action() -> None:
    state = AppState(active_screen="reboot_confirm")

    ApplianceController().handle_button(ButtonEvent("pisugar", "very_long"), state)

    assert state.power_action_requested == "reboot"
    assert state.status_message == "Reboot requested"


def test_select_settings_opens_settings_menu() -> None:
    state = AppState()
    state.menu_index = state.menu_items.index("Settings")

    ApplianceController().handle_button(ButtonEvent("pisugar", "long"), state)

    assert state.active_screen == "settings_menu"
    assert state.status_message == "Settings: Display"


def test_settings_menu_opens_display_settings() -> None:
    state = AppState(active_screen="settings_menu")

    ApplianceController().handle_button(ButtonEvent("pisugar", "long"), state)

    assert state.active_screen == "display_settings"
    assert state.status_message == "Brightness: 80%"


def test_settings_menu_opens_logs_page() -> None:
    state = AppState(active_screen="settings_menu")
    state.settings_index = state.settings_items.index("Logs")

    result = ApplianceController().select_settings_item(state)

    assert result == "logs"
    assert state.active_screen == "logs"
    assert state.status_message == "Logs available on web"


def test_power_menu_cycles_and_selects_reboot_confirmation() -> None:
    state = AppState(active_screen="power")

    ApplianceController().handle_button(ButtonEvent("pisugar", "short"), state)
    ApplianceController().handle_button(ButtonEvent("pisugar", "long"), state)

    assert state.power_items[state.power_index] == "Reboot"
    assert state.active_screen == "reboot_confirm"
    assert state.status_message == "Hold to confirm reboot"


def test_brightness_screen_cycles_levels() -> None:
    state = AppState(active_screen="display_settings", brightness=80)

    ApplianceController().handle_button(ButtonEvent("pisugar", "short"), state)

    assert state.brightness == 100
    assert state.status_message == "Brightness: 100%"
