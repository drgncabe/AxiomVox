from shared.axiomvox_shared import AppState, HardwareStatus
from device.axiomvox_device.display import HdmiRenderer, WhisplayRenderer
from device.axiomvox_device.main import _run_self_test


class FailingLcd:
    def render(self, state: AppState) -> str:
        return "Whisplay runtime load failed: missing spidev"


def test_self_test_prints_lcd_failure_detail(capsys) -> None:
    state = AppState(
        hardware=HardwareStatus(
            whisplay_detected=True,
            lcd_initialized=True,
            microphones_detected=True,
            whisplay_button_detected=True,
            pisugar_detected=True,
            battery_percentage=100,
            pisugar_button_detected=True,
            hdmi_detected=True,
        )
    )

    result = _run_self_test(state, WhisplayRenderer(), HdmiRenderer(), FailingLcd())

    output = capsys.readouterr().out
    assert result == 1
    assert "Whisplay LCD render: FAIL" in output
    assert "missing spidev" in output
