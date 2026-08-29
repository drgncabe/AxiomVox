from shared.axiomvox_shared import AppState, HardwareStatus, ServiceStatus, SessionSummary, SystemStats
from device.axiomvox_device.web import (
    _session_file_path,
    render_dashboard,
    render_display_settings,
    render_log_settings,
    render_power_settings,
)


def test_dashboard_documents_future_sections_without_implementing_them() -> None:
    state = AppState(
        hardware=HardwareStatus(
            battery_percentage=55,
            diagnostics=[ServiceStatus("pisugar", True, "available")],
        ),
        system=SystemStats(uptime_seconds=60, load_1m=0.1, load_5m=0.2, load_15m=0.3),
        web_reachable=True,
    )

    html = render_dashboard(state)

    assert "Device status shell" in html
    assert "Sessions" in html
    assert "Development" in html
    assert "55%" in html
    assert "1m" in html
    assert "Brightness" in html
    assert "/settings/display" in html
    assert "/settings/power" in html
    assert "/settings/logs" in html
    assert "<span class=\"detail\">available</span>" in html


def test_display_settings_page_shows_brightness_and_sleep() -> None:
    state = AppState(brightness=40, display_sleep_timeout_seconds=30)

    html = render_display_settings(state)

    assert "Display Settings" in html
    assert "Current: 40%" in html
    assert "Current: 30s" in html


def test_power_settings_page_shows_power_actions() -> None:
    html = render_power_settings(AppState())

    assert "Power Settings" in html
    assert "Reboot" in html
    assert "Shutdown" in html


def test_log_settings_page_shows_search_and_watch_controls() -> None:
    html = render_log_settings()

    assert "AxiomVox service" in html
    assert "System" in html
    assert "/api/logs" in html
    assert "Search" in html
    assert "Watch" in html


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
                audio_status="ok",
                audio_duration_seconds=3.2,
                audio_size_bytes=50000,
                audio_rms=1200,
            )
        ],
    )

    html = render_dashboard(state)

    assert "20260828T170000Z" in html
    assert "Bookmarks: 1" in html
    assert "20260828T160000Z" in html
    assert "audio ok" in html
    assert "3.2s" in html
    assert "/sessions/20260828T160000Z/audio.wav" in html


def test_session_file_path_stays_under_session_dir(tmp_path) -> None:
    assert _session_file_path(tmp_path, "/sessions/abc/audio.wav") == tmp_path.resolve() / "abc" / "audio.wav"
    assert _session_file_path(tmp_path, "/sessions/../metadata.json") is None
    assert _session_file_path(tmp_path, "/sessions/abc/other.txt") is None
