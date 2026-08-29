from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

from shared.axiomvox_shared import AppState

from .buttons import PiSugarButtonPoller, WhisplayButtonPoller
from .audio import validate_wav
from .config import DeviceConfig
from .controls import ApplianceController
from .display import HdmiRenderer, WhisplayRenderer
from .hardware import HardwareProbe
from .lcd import WhisplayLcdDriver
from .sessions import SessionManager
from .shutdown import ShutdownController
from .system_stats import collect_system_stats
from .web import StatusServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AxiomVox M0 device app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--allow-shutdown", action="store_true")
    parser.add_argument("--simulate-hardware", action="store_true")
    parser.add_argument("--once", action="store_true", help="Probe and render status once")
    parser.add_argument("--self-test", action="store_true", help="Run M1 diagnostics and exit")
    parser.add_argument("--no-lcd", action="store_true", help="Do not attempt Whisplay LCD hardware updates")
    parser.add_argument("--lcd-on", action="store_true", help="Turn on the Whisplay LCD backlight and exit")
    parser.add_argument("--audio-self-test", type=Path, help="Validate an existing WAV file and exit")
    parser.add_argument("--status-file", type=Path)
    parser.add_argument("--session-dir", type=Path, default=Path("/var/lib/axiomvox/sessions"))
    parser.add_argument("--metadata-only", action="store_true", help="Do not launch ALSA capture")
    parser.add_argument("--capture-device", default="plughw:whisplaysound,0")
    parser.add_argument("--capture-format", default="S32_LE")
    parser.add_argument("--capture-rate", type=int, default=48000)
    parser.add_argument("--capture-channels", type=int, default=2)
    parser.add_argument("--display-sleep-timeout", type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = DeviceConfig(
        host=args.host,
        port=args.port,
        allow_shutdown=args.allow_shutdown,
        simulate_hardware=args.simulate_hardware,
        status_file=args.status_file,
        session_dir=args.session_dir,
        capture_enabled=not args.metadata_only,
        capture_device=args.capture_device,
        capture_format=args.capture_format,
        capture_rate=args.capture_rate,
        capture_channels=args.capture_channels,
    )
    state = AppState()
    state.display_sleep_timeout_seconds = max(0, args.display_sleep_timeout)
    probe = HardwareProbe(simulate=config.simulate_hardware)
    sessions = SessionManager(config)
    power = ShutdownController(config)
    controller = ApplianceController(sessions)
    whisplay = WhisplayRenderer()
    hdmi = HdmiRenderer()
    lcd = None if args.no_lcd else WhisplayLcdDriver()
    whisplay_board = lcd.board if lcd is not None else None
    pollers = [WhisplayButtonPoller(probe, whisplay_board), PiSugarButtonPoller(probe)]

    state.hardware = probe.collect()
    state.system = collect_system_stats()
    sessions.load_recent(state)
    state.touch()

    if args.audio_self_test:
        result = validate_wav(args.audio_self_test)
        print(json.dumps(result.to_dict(), indent=2), file=sys.stdout)
        return 0 if result.status == "ok" else 1

    if args.lcd_on:
        print(lcd.turn_on() if lcd is not None else "LCD disabled", file=sys.stdout)
        return 0 if lcd is not None and lcd.available() else 1

    if args.self_test:
        return _run_self_test(state, whisplay, hdmi, lcd)

    if args.once:
        _publish_status(state, whisplay, hdmi, lcd, config.status_file)
        return 0

    server = StatusServer(state, config, controller, lcd)
    stop = False

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    server.start()
    next_hardware_refresh = 0.0
    next_system_refresh = 0.0
    next_display_refresh = 0.0
    last_display_activity = time.monotonic()
    last_user_action_sequence = state.user_action_sequence
    try:
        while not stop:
            now = time.monotonic()
            if now >= next_hardware_refresh:
                state.hardware = probe.collect()
                state.touch()
                next_hardware_refresh = now + 10

            if now >= next_system_refresh:
                state.system = collect_system_stats()
                state.touch()
                next_system_refresh = now + 5

            display_dirty = False
            for poller in pollers:
                for event in poller.poll():
                    if not state.display_awake and event.source == "pisugar":
                        state.display_awake = True
                        state.status_message = "Display awake"
                        state.touch()
                    else:
                        controller.handle_button(event, state)
                    last_display_activity = now
                    state.display_awake = True
                    display_dirty = True

            if state.user_action_sequence != last_user_action_sequence:
                last_user_action_sequence = state.user_action_sequence
                last_display_activity = now
                state.display_awake = True
                display_dirty = True

            if state.power_action_requested:
                action = state.power_action_requested
                state.power_action_requested = ""
                state.shutdown_message = power.request_power(action)
                state.status_message = state.shutdown_message
                state.touch()
                display_dirty = True

            if (
                state.display_sleep_timeout_seconds > 0
                and state.display_awake
                and now - last_display_activity >= state.display_sleep_timeout_seconds
            ):
                state.display_awake = False
                state.status_message = "Display sleeping"
                state.touch()
                display_dirty = True

            if display_dirty or now >= next_display_refresh:
                _publish_status(state, whisplay, hdmi, lcd, config.status_file)
                next_display_refresh = now + 2

            time.sleep(0.2)
    finally:
        if state.current_session is not None:
            sessions.stop(state)
        server.stop()

    return 0


def _publish_status(
    state: AppState,
    whisplay: WhisplayRenderer,
    hdmi: HdmiRenderer,
    lcd: WhisplayLcdDriver | None,
    status_file: Path | None,
) -> None:
    print(whisplay.render(state), file=sys.stdout, flush=True)
    print("", file=sys.stdout, flush=True)
    print(hdmi.render(state), file=sys.stdout, flush=True)
    if lcd is not None:
        print(lcd.render(state), file=sys.stdout, flush=True)
    if status_file:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def _run_self_test(
    state: AppState,
    whisplay: WhisplayRenderer,
    hdmi: HdmiRenderer,
    lcd: WhisplayLcdDriver | None,
) -> int:
    checks = [
        ("Whisplay detected", state.hardware.whisplay_detected),
        ("LCD initialized", state.hardware.lcd_initialized),
        ("Microphones detected", state.hardware.microphones_detected),
        ("Whisplay button detected", state.hardware.whisplay_button_detected),
        ("PiSugar detected", state.hardware.pisugar_detected),
        ("Battery readable", state.hardware.battery_percentage is not None),
        ("PiSugar button detected", state.hardware.pisugar_button_detected),
        ("HDMI detected", state.hardware.hdmi_detected),
    ]
    if lcd is not None:
        lcd_result = lcd.render(state)
        checks.append(("Whisplay LCD render", _lcd_render_ok(lcd_result)))
    else:
        lcd_result = "LCD self-test skipped"

    print(whisplay.render(state), file=sys.stdout)
    print("", file=sys.stdout)
    print(hdmi.render(state), file=sys.stdout)
    print("", file=sys.stdout)
    print("M1 Self-Test", file=sys.stdout)
    for name, ok in checks:
        print(f"- {name}: {'PASS' if ok else 'FAIL'}", file=sys.stdout)
    if lcd is not None:
        print(f"- Whisplay LCD detail: {lcd_result}", file=sys.stdout)
        if _lcd_resource_busy(lcd_result):
            print(
                "- Whisplay LCD hint: stop axiomvox.service before running an LCD-inclusive self-test",
                file=sys.stdout,
            )

    return 0 if all(ok for _, ok in checks) else 1


def _lcd_render_ok(result: str) -> bool:
    return "updated" in result.lower()


def _lcd_resource_busy(result: str) -> bool:
    lowered = result.lower()
    return "device or resource busy" in lowered or "errno 16" in lowered


if __name__ == "__main__":
    raise SystemExit(main())
