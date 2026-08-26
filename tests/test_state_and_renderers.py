from shared.axiomvox_shared import AppState, HardwareStatus
from device.axiomvox_device.display import HdmiRenderer, WhisplayRenderer


def test_whisplay_ready_screen_includes_m0_status() -> None:
    state = AppState(
        hardware=HardwareStatus(
            whisplay_detected=True,
            lcd_initialized=True,
            microphones_detected=True,
            whisplay_button_detected=True,
            pisugar_detected=True,
            battery_percentage=73,
            pisugar_button_detected=True,
            hdmi_detected=True,
        ),
        web_reachable=True,
    )

    rendered = WhisplayRenderer().render(state)

    assert "AxiomVox READY" in rendered
    assert "BAT 73%" in rendered
    assert "WEB OK" in rendered


def test_hdmi_status_uses_shared_application_state() -> None:
    state = AppState(hardware=HardwareStatus(pisugar_detected=True))

    rendered = HdmiRenderer().render(state)

    assert "AxiomVox Device Status" in rendered
    assert "Mode: READY" in rendered
    assert "- PiSugar: OK" in rendered
