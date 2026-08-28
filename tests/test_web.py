from shared.axiomvox_shared import AppState, HardwareStatus, ServiceStatus, SessionSummary
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


def test_dashboard_shows_active_and_recent_sessions() -> None:
    state = AppState(
        current_session=SessionSummary(
            id="20260828T170000Z",
            status="recording",
            started_at="2026-08-28T17:00:00+00:00",
            bookmarks=["2026-08-28T17:01:00+00:00"],
        ),
        recent_sessions=[
            SessionSummary(
                id="20260828T160000Z",
                status="complete",
                started_at="2026-08-28T16:00:00+00:00",
            )
        ],
    )

    html = render_dashboard(state)

    assert "20260828T170000Z" in html
    assert "Bookmarks: 1" in html
    assert "20260828T160000Z" in html
