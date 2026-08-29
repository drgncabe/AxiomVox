from shared.axiomvox_shared import AppState, HardwareStatus, SystemStats
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
    state = AppState(
        hardware=HardwareStatus(pisugar_detected=True),
        system=SystemStats(uptime_seconds=3660, load_1m=0.25, memory_total_mb=512, memory_available_mb=256),
        brightness=60,
    )

    rendered = HdmiRenderer().render(state)

    assert "AxiomVox Device Status" in rendered
    assert "Mode: READY" in rendered
    assert "Uptime: 1h 1m" in rendered
    assert "Memory: 256/512MB" in rendered
    assert "Brightness: 60%" in rendered
    assert "- PiSugar: OK" in rendered


def test_whisplay_settings_screen_shows_system_stats() -> None:
    state = AppState(
        active_screen="settings",
        system=SystemStats(uptime_seconds=120, load_1m=0.5, memory_total_mb=512, memory_available_mb=300),
    )

    rendered = WhisplayRenderer().render(state)

    assert "AxiomVox STATUS" in rendered
    assert "UP 2m" in rendered
    assert "LOAD 0.50" in rendered


def test_whisplay_display_settings_screen_shows_sleep_timeout() -> None:
    state = AppState(active_screen="display_settings", brightness=60, display_sleep_timeout_seconds=30)

    rendered = WhisplayRenderer().render(state)

    assert "DISPLAY" in rendered
    assert "Brightness 60%" in rendered
    assert "Sleep 30s" in rendered
