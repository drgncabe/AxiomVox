from __future__ import annotations

from shared.axiomvox_shared import AppState


def _mark(ok: bool) -> str:
    return "OK" if ok else "MISS"


class WhisplayRenderer:
    def render(self, state: AppState) -> str:
        battery = (
            f"{state.hardware.battery_percentage}%"
            if state.hardware.battery_percentage is not None
            else "n/a"
        )
        if state.active_screen == "menu":
            selected = state.menu_items[state.menu_index]
            return "\n".join(
                [
                    "AxiomVox MENU",
                    f"> {selected}",
                    "Short: next",
                    "Long: select",
                ]
            )
        if state.active_screen == "shutdown_confirm":
            return "\n".join(
                [
                    "SHUTDOWN?",
                    "Hold PiSugar",
                    "Release cancels",
                    "Web also available",
                ]
            )
        if state.current_session is not None:
            return "\n".join(
                [
                    "AxiomVox REC",
                    state.current_session.id,
                    f"BAT {battery}  BK {len(state.current_session.bookmarks)}",
                    "Long: stop",
                ]
            )
        if state.recent_sessions:
            recent = state.recent_sessions[0]
            return "\n".join(
                [
                    "AxiomVox READY",
                    f"BAT {battery}  LAST {recent.audio_status.upper()}",
                    f"{_duration_text(recent.audio_duration_seconds)}  {_size_text(recent.audio_size_bytes)}",
                    "Short: record",
                ]
            )
        return "\n".join(
            [
                "AxiomVox READY",
                f"HW {_mark(_core_hardware_ready(state))}  BAT {battery}",
                f"LCD {_mark(state.hardware.lcd_initialized)}  MIC {_mark(state.hardware.microphones_detected)}",
                f"WEB {_mark(state.web_reachable)}  HDMI {_mark(state.hardware.hdmi_detected)}",
            ]
        )


class HdmiRenderer:
    def render(self, state: AppState) -> str:
        hardware = state.hardware
        rows = [
            ("Whisplay", hardware.whisplay_detected),
            ("LCD", hardware.lcd_initialized),
            ("Microphones", hardware.microphones_detected),
            ("Whisplay button", hardware.whisplay_button_detected),
            ("PiSugar", hardware.pisugar_detected),
            ("PiSugar button", hardware.pisugar_button_detected),
            ("HDMI", hardware.hdmi_detected),
            ("Web service", state.web_reachable),
        ]
        battery = (
            f"{hardware.battery_percentage}%"
            if hardware.battery_percentage is not None
            else "not readable"
        )
        lines = [
            "AxiomVox Device Status",
            f"Mode: {state.mode}",
            f"Screen: {state.active_screen}",
            f"Started: {state.started_at}",
            f"Updated: {state.updated_at}",
            f"Battery: {battery}",
            f"Message: {state.status_message}",
            f"Last button: {state.last_button_event or 'none'}",
            f"Current session: {state.current_session.id if state.current_session else 'none'}",
            f"Recent sessions: {len(state.recent_sessions)}",
            "",
            "M0 Checklist",
        ]
        lines.extend(f"- {name}: {_mark(ok)}" for name, ok in rows)
        return "\n".join(lines)


def _core_hardware_ready(state: AppState) -> bool:
    hardware = state.hardware
    return all(
        [
            hardware.whisplay_detected,
            hardware.lcd_initialized,
            hardware.microphones_detected,
            hardware.whisplay_button_detected,
            hardware.pisugar_detected,
            hardware.pisugar_button_detected,
            hardware.hdmi_detected,
        ]
    )


def _duration_text(duration: float | None) -> str:
    if duration is None:
        return "--s"
    return f"{duration:.1f}s"


def _size_text(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "--"
    if size_bytes < 1024:
        return f"{size_bytes}B"
    return f"{size_bytes / 1024:.0f}K"
