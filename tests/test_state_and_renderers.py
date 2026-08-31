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
        system=SystemStats(
            uptime_seconds=3660,
            cpu_used_percent=12.5,
            load_1m=0.25,
            memory_total_mb=512,
            memory_available_mb=256,
        ),
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


def test_whisplay_sound_settings_screen_shows_volume() -> None:
    state = AppState(active_screen="sound_settings", chimes_enabled=False, chime_volume=25)

    rendered = WhisplayRenderer().render(state)

    assert "SOUND" in rendered
    assert "Chimes off" in rendered
    assert "Volume 25%" in rendered


def test_whisplay_stopping_screen_acknowledges_stop() -> None:
    rendered = WhisplayRenderer().render(AppState(active_screen="stopping", mode="STOPPING"))

    assert "AxiomVox STOP" in rendered
    assert "Stopping..." in rendered


def test_state_records_bounded_system_history() -> None:
    state = AppState(system=SystemStats(cpu_used_percent=10.0, memory_used_percent=20.0, load_1m=0.5))

    state.record_system_sample(limit=1)
    state.system.cpu_used_percent = 30.0
    state.record_system_sample(limit=1)

    assert len(state.system_history) == 1
    assert state.system_history[0].cpu_used_percent == 30.0


def test_whisplay_logs_screen_points_to_web_console() -> None:
    rendered = WhisplayRenderer().render(AppState(active_screen="logs"))

    assert "AxiomVox LOGS" in rendered
    assert "/settings/logs" in rendered


def test_whisplay_pisugar_screen_points_to_web_console() -> None:
    rendered = WhisplayRenderer().render(AppState(active_screen="pisugar_diagnostics"))

    assert "PISUGAR DIAG" in rendered
    assert "/settings/pisugar" in rendered
