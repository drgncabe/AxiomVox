from shared.axiomvox_shared import AppState, HardwareStatus, ServiceStatus
from device.axiomvox_device.web import render_dashboard


def test_dashboard_documents_future_sections_without_implementing_them() -> None:
    state = AppState(
        hardware=HardwareStatus(
            battery_percentage=55,
            diagnostics=[ServiceStatus("pisugar", True, "available")],
        ),
        web_reachable=True,
    )

    html = render_dashboard(state)

    assert "Device status shell" in html
    assert "Sessions" in html
    assert "Development" in html
    assert "55%" in html
    assert "<span class=\"detail\">available</span>" in html
