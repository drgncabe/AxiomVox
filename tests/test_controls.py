from shared.axiomvox_shared import AppState
from device.axiomvox_device.controls import ApplianceController
from device.axiomvox_device.events import ButtonEvent


def test_whisplay_button_is_reserved_for_recording_controls() -> None:
    state = AppState()

    ApplianceController().handle_button(ButtonEvent("whisplay", "short"), state)

    assert state.active_screen == "ready"
    assert state.last_button_event == "whisplay:short"
    assert "Recording control reserved" in state.status_message


def test_pisugar_short_press_advances_system_menu() -> None:
    state = AppState()

    ApplianceController().handle_button(ButtonEvent("pisugar", "short"), state)

    assert state.active_screen == "menu"
    assert state.menu_index == 1
    assert state.status_message == "Menu: Display"


def test_pisugar_very_long_press_opens_shutdown_confirmation() -> None:
    state = AppState()

    ApplianceController().handle_button(ButtonEvent("pisugar", "very_long"), state)

    assert state.active_screen == "shutdown_confirm"
    assert state.status_message == "Hold to confirm shutdown"
